from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import OTPRequest, OTPVerify, TokenResponse
from app.services.auth_service import generate_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/send")
async def send_otp(body: OTPRequest):
    generate_otp(body.phone)
    return {"message": "OTP sent"}


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp_and_login(body: OTPVerify, db: AsyncSession = Depends(get_db)):
    if not verify_otp(body.phone, body.otp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    if not user:
        user = User(phone=body.phone)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
