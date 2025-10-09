from pydantic import BaseModel, EmailStr, constr, field_validator
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
    id:UUID


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