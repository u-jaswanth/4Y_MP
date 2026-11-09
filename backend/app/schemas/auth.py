import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = "patient"


class UserLogin(BaseModel):
    """One login box for all four roles.

    Patients type their email. Hospitals and doctors type the ID they
    were issued (HOSP-K7M2Q4, DOC-P4X9R2), which is not an email
    address - so `identifier` is a plain string, not an EmailStr.

    The old shape `{ email, password }` still validates, so any client
    that has not been updated keeps working.
    """

    identifier: Optional[str] = None
    email: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def require_one_identifier(self):
        if not (self.identifier or self.email):
            raise ValueError("Enter your email or the ID you were issued.")
        return self

    @property
    def principal(self) -> str:
        return (self.identifier or self.email or "").strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    # The client needs all three of these at login: which portal to
    # open, whether to divert to the password screen first, and what to
    # put in the greeting.
    role: str = "patient"
    must_change_password: bool = False
    display_name: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class AccountOut(BaseModel):
    """`/auth/me`, with the bits the portals need to render a header."""

    id: uuid.UUID
    email: EmailStr
    role: str
    login_id: Optional[str] = None
    must_change_password: bool = False
    display_name: Optional[str] = None

    class Config:
        from_attributes = True


class PatientOut(BaseModel):
    id: uuid.UUID
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    health_id: Optional[str] = None
    aadhaar_photo_url: Optional[str] = None

    class Config:
        from_attributes = True
