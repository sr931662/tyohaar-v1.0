import random
import string

# In-memory OTP store — replace with Redis in production
_otp_store: dict[str, str] = {}


def generate_otp(phone: str) -> str:
    otp = "".join(random.choices(string.digits, k=6))
    _otp_store[phone] = otp
    # TODO: send OTP via SMS gateway (e.g. Twilio, MSG91)
    print(f"[DEV] OTP for {phone}: {otp}")
    return otp


def verify_otp(phone: str, otp: str) -> bool:
    stored = _otp_store.get(phone)
    if stored and stored == otp:
        del _otp_store[phone]
        return True
    return False
