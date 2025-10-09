from pydantic import BaseModel, EmailStr, constr, field_validator
from enum import Enum
from typing import List, Optional
from datetime import date
from uuid import UUID

# Pydantic-compatible enums (inherit from str for JSON serialization)
class UserRole(str, Enum):
    super_admin = "super_admin"
    reviewer = "reviewer"
    data_clerk = "data_clerk"
    org_admin = "org_admin"
    org_user = "org_user"

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"




class UserBase(BaseModel):
    first_name: str
    last_name: str
   
    phone_number: str
    gender: Gender
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.org_user
    image_url: Optional[str] = None
    
    @field_validator('phone_number')
    def validate_phone(cls, v):
        # Remove spaces and dashes
        phone = v.replace(' ', '').replace('-', '')
        if not phone.isdigit() or len(phone) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return phone



class UserCreate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    gender: Gender
    password: str
    role: UserRole = UserRole.org_user
    is_active: bool = False
    email: str | None = None

    @field_validator("password")
    def validate_password_length(cls, password):
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes")
        return password

class UserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone_number: str
    gender: Gender
    role: UserRole
    is_active: bool
    image_url: str | None = None

    class Config:
        from_attributes = True


#-----------Schema for updating users (all fields optional except ID)  ----------#
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    image_url: Optional[str] = None

    @field_validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip().title() if v else None
    
    class Config:
        from_attributes=True


#----------------------------- Schema for user authentication responses -----------------------------#
class UserAuth(BaseModel):
    id: UUID
    email: EmailStr | None
    role: UserRole
    first_name: str
    last_name: str
    
    class Config:
        from_attributes = True

#---------------------------- Schema for password change ----------------------------#
class PasswordChange(BaseModel):
    phone_number: str
    otp: str
    new_password: str
    
    @field_validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters')
        return v


#---------------------- Token schemas ----------------------#
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserAuth

#---------------- Token data inside JWT ----------------
class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None

#------------------------ Schema for refresh token request ------------------------#
class RefreshTokenRequest(BaseModel):
    refresh_token: str

#------------------------ Schema for user list/search results ------------------------#
class UserListOut(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    role: UserRole
    phone_number: str
    
    class Config:
        from_attributes = True

# ---------------- Flexible login schema (email or phone) ----------------
class UserLoginFlexible(BaseModel):
    identifier: EmailStr | None
    password: str
    
