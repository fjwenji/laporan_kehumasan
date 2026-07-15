"""
Pydantic schemas for authentication - Secure implementation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    username: str
    role: str  # "admin" or "user"


class User(UserBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    nama_lengkap: Optional[str] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user", pattern="^(admin|user)$")
    nama_lengkap: Optional[str] = Field(None, max_length=255)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username hanya boleh huruf, angka, dan underscore')
        return v.strip().lower()


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    nama_lengkap: Optional[str] = Field(None, max_length=255)


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password minimal 8 karakter')
        return v


class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password minimal 8 karakter')
        return v
