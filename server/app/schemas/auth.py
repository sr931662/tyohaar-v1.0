from pydantic import BaseModel


class OTPRequest(BaseModel):
    phone: str


class OTPVerify(BaseModel):
    phone: str
    otp: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    phone: str
    name: str | None
    email: str | None
    profile_photo: str | None
    city: str | None
    state: str | None

    model_config = {"from_attributes": True}
