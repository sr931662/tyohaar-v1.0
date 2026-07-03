"""
AuthService — OTP-based authentication, session management, token rotation.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.auth.refresh_token import RefreshToken
from app.models.auth.session import UserSession
from app.models.enums import (
    AccountStatus,
    LoginMethod,
    OTPDeliveryChannel,
    OTPPurpose,
    OTPStatus,
    SessionStatus,
    TokenRevocationReason,
    VerificationStatus,
    UserRole,
)
from app.schemas.auth.create import (
    GoogleAuthCreate,
    OTPVerifyCreate,
    PasswordResetConfirmCreate,
    UserRegisterCreate,
    VendorRegisterCreate,
)
from app.schemas.auth.response import OTPSentResponse, SessionResponse
from app.schemas.users.create import UserCreate
from app.services.auth.constants import (
    ACCESS_TOKEN_EXPIRY_SECONDS,
    MAX_ACTIVE_SESSIONS,
    OTP_EXPIRY_SECONDS,
    OTP_MAX_ATTEMPTS,
    REFRESH_TOKEN_EXPIRY_SECONDS,
)
from app.services.auth.helpers import (
    create_access_token_payload,
    encode_jwt,
    generate_otp,
    generate_token,
    hash_otp,
    hash_token,
)
from app.services.auth.validators import (
    validate_otp_for_verification,
    validate_otp_rate_limit,
    validate_refresh_token,
)
from app.services.base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class TokenPairResponse:
    """Returned by verify_otp and refresh_access_token — raw tokens only."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRY_SECONDS
    session_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class AuthService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Traditional Email/Password Auth ──────────────────────────────────────

    async def register_user(
        self,
        data: UserRegisterCreate,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        from app.core.security import hash_password
        from app.services.users.exceptions import EmailTakenError

        # Transaction 1: create the user and profile, then commit.
        async with self._uow() as uow:
            existing = await uow.users.users.find_by_email(data.email)
            if existing:
                raise EmailTakenError(data.email)

            user_data = {
                "email": data.email,
                "full_name": data.full_name,
                "password_hash": hash_password(data.password),
                "primary_login_provider": LoginMethod.EMAIL_PASSWORD,
                "email_verified": False,
                "role": UserRole.CUSTOMER,
                "account_status": AccountStatus.ACTIVE,
                "verification_status": VerificationStatus.UNVERIFIED,
                "phone": f"TMP-{uuid.uuid4().hex[:10]}",
            }
            user = await uow.users.users.create_from_dict(user_data)
            await uow.users.profiles.create_from_dict({"user_id": user.id})
            new_user_id = user.id  # capture before the session expires on commit

        # Transaction 2: create the session now that the user row is committed.
        # _create_user_session only needs user.id, so pass a lightweight proxy.
        class _UserRef:
            def __init__(self, uid: uuid.UUID) -> None:
                self.id = uid

        return await self._create_user_session(
            _UserRef(new_user_id), ip_address, user_agent, LoginMethod.EMAIL_PASSWORD
        )

    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        from app.core.security import verify_password
        from app.services.auth.exceptions import InvalidCredentialsError

        async with self._uow() as uow:
            user = await uow.users.users.find_by_email(email)
            if not user or not user.password_hash:
                raise InvalidCredentialsError()

            if not verify_password(password, user.password_hash):
                raise InvalidCredentialsError()

            if user.account_status != AccountStatus.ACTIVE:
                from app.services.auth.exceptions import AccountLockedError
                raise AccountLockedError("Account is not active.")

            return await self._create_user_session(
                user, ip_address, user_agent, LoginMethod.EMAIL_PASSWORD
            )

    # ── Vendor Registration ───────────────────────────────────────────────────

    async def register_vendor(self, data: VendorRegisterCreate) -> dict:
        """
        Create a vendor-role user + stub Vendor business profile.

        The account is created as PENDING_VERIFICATION / VendorStatus.PENDING
        and cannot authenticate until an admin activates it, so no session
        or token pair is issued here.
        """
        from app.core.security import hash_password
        from app.services.exceptions import ConflictError
        from app.services.users.exceptions import EmailTakenError

        async with self._uow() as uow:
            existing_email = await uow.users.users.find_by_email(data.email)
            if existing_email:
                raise EmailTakenError(data.email)

            existing_phone = await uow.users.users.find_by_phone(data.phone)
            if existing_phone:
                raise ConflictError("This phone number is already registered.")

            user_data = {
                "email": data.email,
                "phone": data.phone,
                "full_name": data.full_name,
                "password_hash": hash_password(data.password),
                "primary_login_provider": LoginMethod.EMAIL_PASSWORD,
                "email_verified": False,
                "role": UserRole.VENDOR,
                "account_status": AccountStatus.PENDING_VERIFICATION,
                "verification_status": VerificationStatus.UNVERIFIED,
            }
            user = await uow.users.users.create_from_dict(user_data)
            await uow.users.profiles.create_from_dict({"user_id": user.id})

            vendor = await uow.vendors.vendors.create_from_dict({
                "user_id": user.id,
                "business_name": data.business_name,
                "vendor_type": data.vendor_type,
            })
            await uow.vendors.profiles.create_from_dict({"vendor_id": vendor.id})

        return {"status": "pending_approval"}

    # ── Password Reset (OTP-verified) ─────────────────────────────────────────

    async def reset_password(self, data: PasswordResetConfirmCreate) -> None:
        """Verify the emailed OTP and set a new password for the account."""
        from app.core.security import hash_password
        from app.services.auth.exceptions import InvalidCredentialsError

        async with self._uow() as uow:
            await validate_otp_for_verification(
                data.email,
                data.otp_code,
                OTPPurpose.PASSWORD_RESET,
                uow,
                settings.SECRET_KEY,
            )

            user = await uow.users.users.find_by_email(data.email)
            if user is None:
                raise InvalidCredentialsError("No account found for this email address.")

            user.password_hash = hash_password(data.new_password)
            user_id = user.id

        # Revoke all existing sessions now that the password has changed.
        await self.logout_all_devices(user_id=user_id)

    # ── Google Sign-In (Vendor) ───────────────────────────────────────────────

    async def authenticate_vendor_google(
        self,
        id_token_str: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Verify a Google ID token and either log in an existing, approved
        vendor or create a new PENDING_VERIFICATION vendor account.

        Returns a dict with `access_token`/`token_type` when login succeeds,
        or `{"status": "pending_approval"}` when the account is new or
        still awaiting admin approval.
        """
        from app.services.auth.exceptions import InvalidCredentialsError
        from app.services.exceptions import ExternalServiceError

        if not settings.GOOGLE_CLIENT_ID:
            raise ExternalServiceError(
                "Google Sign-In", "Google Sign-In is not configured yet."
            )

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            idinfo = google_id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            raise InvalidCredentialsError("Invalid or expired Google token.")

        email = idinfo.get("email")
        if not email or not idinfo.get("email_verified"):
            raise InvalidCredentialsError("Google account email is not verified.")
        full_name = idinfo.get("name")

        async with self._uow() as uow:
            user = await uow.users.users.find_by_email(email)

            if user is None:
                user_data = {
                    "email": email,
                    "full_name": full_name,
                    "primary_login_provider": LoginMethod.GOOGLE,
                    "email_verified": True,
                    "role": UserRole.VENDOR,
                    "account_status": AccountStatus.PENDING_VERIFICATION,
                    "verification_status": VerificationStatus.UNVERIFIED,
                    "phone": f"TMP-{uuid.uuid4().hex[:10]}",
                }
                user = await uow.users.users.create_from_dict(user_data)
                await uow.users.profiles.create_from_dict({"user_id": user.id})
                return {"status": "pending_approval"}

            if user.role != UserRole.VENDOR:
                raise InvalidCredentialsError(
                    "This Google account is not registered as a vendor."
                )

            if user.account_status != AccountStatus.ACTIVE:
                return {"status": "pending_approval"}

            tokens = await self._create_user_session(
                user, ip_address, user_agent, LoginMethod.GOOGLE
            )
            return {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "token_type": tokens.token_type,
                "expires_in": tokens.expires_in,
            }

    async def _create_user_session(
        self,
        user,
        ip_address: str | None,
        user_agent: str | None,
        login_method: LoginMethod,
        device_id: str | None = None,
    ) -> TokenPairResponse:
        # Refactored common session creation logic
        async with self._uow() as uow:
            # Enforce MAX_ACTIVE_SESSIONS
            active_count = await uow.auth.sessions.count_active_for_user(user.id)
            if active_count >= MAX_ACTIVE_SESSIONS:
                active_sessions = await uow.auth.sessions.find_active_for_user(user.id)
                active_sessions.sort(key=lambda s: s.login_at)
                oldest = active_sessions[0]
                await uow.auth.sessions.revoke_session(oldest, TokenRevocationReason.LOGOUT)
                await uow.auth.refresh_tokens.revoke_for_session(oldest.id, TokenRevocationReason.LOGOUT)

            now = datetime.now(tz=timezone.utc)
            session_expires = now + timedelta(seconds=REFRESH_TOKEN_EXPIRY_SECONDS)
            session_token = generate_token(32)

            session_obj = UserSession(
                user_id=user.id,
                session_token=session_token,
                login_method=login_method,
                status=SessionStatus.ACTIVE,
                login_at=now,
                last_activity_at=now,
                expires_at=session_expires,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id,
                is_active=True,
                is_revoked=False,
            )
            await uow.auth.sessions.create(session_obj)

            access_payload = create_access_token_payload(
                user.id, session_obj.id, ACCESS_TOKEN_EXPIRY_SECONDS
            )
            access_token = encode_jwt(access_payload, settings.SECRET_KEY, settings.ALGORITHM)
            raw_refresh = generate_token(32)
            refresh_hash = hash_token(raw_refresh)
            family_id = uuid.uuid4()
            jti = access_payload["jti"]

            session_obj.access_jti = jti

            rt_expires = now + timedelta(seconds=REFRESH_TOKEN_EXPIRY_SECONDS)
            refresh_record = RefreshToken(
                jti=generate_token(16),
                user_id=user.id,
                session_id=session_obj.id,
                family_id=family_id,
                token_hash=refresh_hash,
                device_id=device_id,
                ip_address=ip_address,
                issued_at=now,
                expires_at=rt_expires,
            )
            await uow.auth.refresh_tokens.create(refresh_record)

            user_id = user.id
            session_id = session_obj.id

        return TokenPairResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=ACCESS_TOKEN_EXPIRY_SECONDS,
            session_id=session_id,
            user_id=user_id,
        )

    # ── Send OTP ──────────────────────────────────────────────────────────────

    async def send_otp(
        self,
        phone: str,
        channel: OTPDeliveryChannel = OTPDeliveryChannel.SMS,
        purpose: OTPPurpose = OTPPurpose.LOGIN,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> OTPSentResponse:
        """
        Rate-limit check → supersede old OTPs → generate + hash → store.
        SMS delivery is stubbed; implement the gateway call after the block.
        """
        from app.models.auth.otp import OTPRecord

        async with self._uow() as uow:
            await validate_otp_rate_limit(phone, uow)

            # Supersede any existing PENDING OTPs for this identifier+purpose
            await uow.auth.otps.supersede_all_pending(phone, purpose)

            raw_otp = generate_otp()
            otp_hash_value = hash_otp(phone, raw_otp, settings.SECRET_KEY)
            now = datetime.now(tz=timezone.utc)
            expires_at = now + timedelta(seconds=OTP_EXPIRY_SECONDS)

            record = OTPRecord(
                identifier=phone,
                channel=channel,
                purpose=purpose,
                status=OTPStatus.PENDING,
                otp_hash=otp_hash_value,
                max_attempts=OTP_MAX_ATTEMPTS,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
            )
            await uow.auth.otps.create(record)
            # commit happens automatically when context exits cleanly

        # Side effect AFTER transaction commits
        logger.info(
            "[SMS STUB] OTP for %s via %s (purpose=%s): %s",
            phone,
            channel,
            purpose,
            raw_otp,
        )

        return OTPSentResponse(
            status=OTPStatus.PENDING,
            channel=channel,
            expires_at=expires_at,
            resend_count=record.resend_count,
            max_resends=record.max_resends,
            attempt_count=record.attempt_count,
            max_attempts=record.max_attempts,
            delivered_at=None,
            delivery_reference=None,
        )

    # ── Verify OTP ────────────────────────────────────────────────────────────

    async def verify_otp(
        self,
        data: OTPVerifyCreate,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_id: str | None = None,
    ) -> TokenPairResponse:
        """
        Verify OTP → upsert user → create session → issue token pair.
        Returns raw (never-hashed) access + refresh tokens.
        """
        async with self._uow() as uow:
            # 1. Validate OTP — marks record VERIFIED on success
            await validate_otp_for_verification(
                data.identifier,
                data.otp_code,
                data.purpose,
                uow,
                settings.SECRET_KEY,
            )

            # 2. Upsert user
            user = await uow.users.users.find_by_phone(data.identifier)
            is_new_user = user is None
            if is_new_user:
                new_user_data = UserCreate(phone=data.identifier).model_dump(exclude_unset=True)
                new_user_data["primary_login_provider"] = LoginMethod.OTP_PHONE
                new_user_data["phone_verified"] = True
                new_user_data["account_status"] = AccountStatus.ACTIVE
                new_user_data["verification_status"] = VerificationStatus.VERIFIED
                user = await uow.users.users.create_from_dict(new_user_data)
                # Create default UserProfile
                await uow.users.profiles.create_from_dict({"user_id": user.id})
            else:
                # Mark phone verified on successful OTP for existing user (if not already)
                if not user.phone_verified:
                    user.phone_verified = True
                    user.account_status = AccountStatus.ACTIVE
                    user.verification_status = VerificationStatus.VERIFIED

            # Update last login
            user.last_login_at = datetime.now(tz=timezone.utc)
            await uow.session.flush()  # type: ignore[union-attr]

        return await self._create_user_session(
            user, ip_address, user_agent, LoginMethod.OTP_PHONE, device_id
        )

    # ── Session Creation for Other Auth Flows (admin, etc.) ───────────────────

    async def create_session_for_user_id(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        login_method: LoginMethod = LoginMethod.EMAIL_PASSWORD,
    ) -> TokenPairResponse:
        """
        Issue a real access/refresh token pair (with a revocable UserSession)
        for a user who has already been authenticated by another flow (e.g.
        admin_login, which validates credentials against the Admin table).
        """
        class _UserRef:
            def __init__(self, uid: uuid.UUID) -> None:
                self.id = uid

        return await self._create_user_session(
            _UserRef(user_id), ip_address, user_agent, login_method
        )

    # ── Refresh Access Token ──────────────────────────────────────────────────

    async def refresh_access_token(
        self,
        raw_refresh_token: str,
        ip_address: str | None = None,
    ) -> TokenPairResponse:
        """
        Token rotation: consume old refresh token → issue new access + refresh pair.
        Detects reuse and revokes entire token family on reuse.
        """
        async with self._uow() as uow:
            old_rt = await validate_refresh_token(raw_refresh_token, uow)

            # Mark old refresh token as used
            now = datetime.now(tz=timezone.utc)
            old_rt.is_used = True
            old_rt.used_at = now
            await uow.session.flush()  # type: ignore[union-attr]

            session_obj = await uow.auth.sessions.get_by_id(old_rt.session_id)
            if session_obj is None or not session_obj.is_valid:
                from app.services.auth.exceptions import SessionExpiredError
                raise SessionExpiredError("Session is no longer valid.")

            # Issue new access JWT
            access_payload = create_access_token_payload(
                old_rt.user_id, session_obj.id, ACCESS_TOKEN_EXPIRY_SECONDS
            )
            access_token = encode_jwt(access_payload, settings.SECRET_KEY, settings.ALGORITHM)
            new_jti = access_payload["jti"]

            # Update session access_jti
            session_obj.access_jti = new_jti
            session_obj.last_activity_at = now
            await uow.session.flush()  # type: ignore[union-attr]

            # Issue new refresh token
            raw_new_refresh = generate_token(32)
            new_refresh_hash = hash_token(raw_new_refresh)
            rt_expires = now + timedelta(seconds=REFRESH_TOKEN_EXPIRY_SECONDS)

            new_rt = RefreshToken(
                jti=generate_token(16),
                user_id=old_rt.user_id,
                session_id=session_obj.id,
                family_id=old_rt.family_id,
                parent_jti=old_rt.jti,
                token_hash=new_refresh_hash,
                device_id=old_rt.device_id,
                ip_address=ip_address,
                issued_at=now,
                expires_at=rt_expires,
            )
            await uow.auth.refresh_tokens.create(new_rt)

            user_id = old_rt.user_id
            session_id = session_obj.id

        return TokenPairResponse(
            access_token=access_token,
            refresh_token=raw_new_refresh,
            expires_in=ACCESS_TOKEN_EXPIRY_SECONDS,
            session_id=session_id,
            user_id=user_id,
        )

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, session_id: uuid.UUID) -> None:
        """Revoke the session and all its refresh tokens."""
        async with self._uow() as uow:
            session_obj = await uow.auth.sessions.get_by_id(session_id)
            if session_obj is not None:
                await uow.auth.sessions.revoke_session(
                    session_obj, TokenRevocationReason.LOGOUT
                )
                await uow.auth.refresh_tokens.revoke_for_session(
                    session_id, TokenRevocationReason.LOGOUT
                )

    # ── Logout All Devices ────────────────────────────────────────────────────

    async def logout_all_devices(self, user_id: uuid.UUID) -> None:
        """Revoke all active sessions and refresh tokens for a user."""
        async with self._uow() as uow:
            await uow.auth.sessions.revoke_all_for_user(
                user_id, TokenRevocationReason.LOGOUT
            )
            # Revoke all non-revoked refresh tokens for this user
            from sqlalchemy import update as sa_update
            from app.models.auth.refresh_token import RefreshToken as RT
            now = datetime.now(tz=timezone.utc)
            stmt = (
                sa_update(RT)
                .where(RT.user_id == user_id)
                .where(RT.is_revoked == False)  # noqa: E712
                .values(
                    is_revoked=True,
                    revoked_at=now,
                    revocation_reason=TokenRevocationReason.LOGOUT,
                )
                .execution_options(synchronize_session="fetch")
            )
            assert uow.session is not None
            await uow.session.execute(stmt)

    # ── Get Active Sessions ───────────────────────────────────────────────────

    async def get_active_sessions(self, user_id: uuid.UUID) -> list[SessionResponse]:
        """Return all active, non-expired sessions for the user."""
        async with self._uow() as uow:
            sessions = await uow.auth.sessions.find_active_for_user(user_id)
            now = datetime.now(tz=timezone.utc)
            valid = [s for s in sessions if s.expires_at > now]
            return [SessionResponse.model_validate(s) for s in valid]
