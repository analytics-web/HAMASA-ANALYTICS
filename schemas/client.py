from pydantic import BaseModel, ConfigDict, EmailStr, constr, field_validator
from enum import Enum
from typing import List, Optional
from datetime import date
from uuid import UUID



class ClientBase(BaseModel):
    name_of_organisation: str
    country:str
    sector:str
    contact_person:str
    phone_number:str
    email:EmailStr




class ClientOut(ClientBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class UserClientOut(BaseModel):
    id: UUID
    client_id: UUID
    first_name: str
    last_name: str
    email: Optional[str]
    phone_number: Optional[str]
    is_active: bool
    role: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ClientCreate(ClientBase):
    name_of_organisation: str
    country:str
    sector:str
    contact_person:str
    phone_number:str
    email:EmailStr


class ClientUpdate(BaseModel):
    name_of_organisation: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    contact_person: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None


class ClientFilters(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None


class ClientUserFilters(BaseModel):
    client_id: Optional[UUID] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None



class PaginatedResponse(BaseModel):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: list
