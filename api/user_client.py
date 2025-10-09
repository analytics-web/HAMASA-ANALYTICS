from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import get_db
from models.client_user import * 

router = APIRouter(prefix="/clients", tags=["Clients"])

