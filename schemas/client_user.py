from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

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


class CLientOut(BaseException):
    id:UUID
    name_of_organisation:Optional[str]
    country:Optional[str] = "Tanzania"    
    contact_person:str
    email:EmailStr

class UserClient(BaseModel):
    user_id:UUID
    client_id:UUID
    role_within_client: Optional[str] = None
    is_primary_contact: Optional[bool] = False

class UserClientOut(BaseModel):
    id:UUID
    first_name:Optional[str] = None
    last_name:Optional[str] = None
    phone_number:Optional[str] = None
    email:Optional[EmailStr] = None

class UserClientAssign(BaseModel):
    user_id: UUID
    client_id: UUID
    role_within_client: Optional[str] = None
    is_primary_contact: Optional[bool] = False




class UserClientCreate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    email: EmailStr
    name_of_organisation: str
    country: Optional[str] = "Tanzania"
    plain_password: Optional[str] = None
    role:UserRole = UserRole.org_admin

    class Config:
        from_attributes = True  


class UserClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None

    class Config:
        from_attributes = True 


class UserClientUpdatePassword(BaseModel):
    password: str
    confirm_password: str

    class Config:
        from_attributes = True 


class UserClientCreateOut(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    email: EmailStr
    name_of_organisation: Optional[str]
    country: Optional[str]
    plain_password: str
    role:UserRole = UserRole.org_admin

    class Config:
        from_attributes = True  



class UserClientCollaboratorCreate(BaseModel):
    client_id:UUID
    first_name:str
    last_name:str
    phone_number:str
    email:EmailStr
    role:UserRole = UserRole.org_user



class UserClientCollaboratorOut(BaseModel):
    id:UUID
    client_id:UUID
    first_name:str
    last_name:str
    phone_number:str
    email:EmailStr
    role:UserRole = UserRole.org_user
    is_active:bool
    plain_password:str