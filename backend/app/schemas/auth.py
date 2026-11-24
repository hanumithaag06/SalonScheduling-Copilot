# Why: Pydantic schemas for authentication and user accounts.
# Enforces email validity, phone number regex patterns, and password constraints.

import re
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


PHONE_REGEX = re.compile(r"^\+?[0-9\s\-\(\)]{7,20}$")


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    phone: str | None = Field(default=None, max_length=20, description="Contact phone number")
    password: str = Field(..., min_length=6, max_length=100, description="Plain text password")
    role: str = Field(default="customer", description="User role: 'customer' or 'admin'")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            if not PHONE_REGEX.match(v.strip()):
                raise ValueError("Phone number must contain between 7 and 20 digits/symbols (+, -, (), spaces)")
            return v.strip()
        return None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v_clean = v.lower().strip()
        if v_clean not in {"customer", "admin"}:
            raise ValueError("Role must be 'customer' or 'admin'")
        return v_clean


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

