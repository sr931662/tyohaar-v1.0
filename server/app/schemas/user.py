from pydantic import BaseModel


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    city: str | None = None
    state: str | None = None
    profile_photo: str | None = None


class UserOut(BaseModel):
    id: str
    phone: str
    name: str | None
    email: str | None
    profile_photo: str | None
    city: str | None
    state: str | None

    model_config = {"from_attributes": True}
