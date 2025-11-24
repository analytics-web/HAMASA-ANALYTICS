import secrets
import string
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from core.security import hash_password
from db.db import SessionLocal, get_db
from models.client import Client
from models.hamasa_user import HamasaUser as User, UserRole
from models.client_user import ClientUser
from dotenv import load_dotenv
from api.deps import oauth2_scheme, require_role

from schemas.client import ClientCreate, ClientFilters, ClientOut, ClientUpdate, ClientUserFilters, PaginatedResponse
from schemas.client_user import UserClient, UserClientAssign, UserClientCollaboratorCreate, UserClientCollaboratorOut, UserClientCreateOut, UserClientOut, UserClientCreate, UserClientUpdate, UserClientUpdatePassword
import logging

from schemas.project import ClientUserOut
from utils.client_helpers import client_paginate_queryset, split_contact_person, validate_unique_client_fields
from utils.pagination import paginate_queryset
from fastapi_limiter.depends import RateLimiter


logger = logging.getLogger(__name__)

load_dotenv() 



router = APIRouter()

def generate_password() -> str:
    """Generate a 4-character password in format: [A-Z][a-z][1-9][1-9]"""
    upper = secrets.choice(string.ascii_uppercase) 
    lower = secrets.choice(string.ascii_lowercase)  
    digit1 = secrets.choice("123456789")            
    digit2 = secrets.choice("123456789")           

    return f"{upper}{lower}{digit1}{digit2}"





# ----------------------------- 
# create client and client user 
# ------------------------------ 
@router.post(
    "/clients/",
    response_model=UserClientCreateOut,
    status_code=status.HTTP_200_OK,
    summary="Create Client and the associated org admin user",
)
def createClient(
    client_data: UserClientCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):
    # -----------------------------------------------------
    # 1. Check if a user with this email or phone already exists
    # -----------------------------------------------------
    existing_user = db.query(ClientUser).filter(
        (ClientUser.email.ilike(client_data.email)) |
        (ClientUser.phone_number.ilike(client_data.phone_number))
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email or phone number already exists"
        )

    # -----------------------------------------------------
    # 2. Check unique fields for Client (ignores soft-deleted ones)
    # -----------------------------------------------------
    existing_name_of_organisation = db.query(Client).filter(
        Client.name_of_organisation.ilike(client_data.name_of_organisation),
        Client.is_deleted == False,
    ).first()

    if existing_name_of_organisation:
        raise HTTPException(
            status_code=400,
            detail="Client with that organisation name already exists"
        )

    existing_phone_number = db.query(Client).filter(
        Client.phone_number.ilike(client_data.phone_number),
        Client.is_deleted == False,
    ).first()

    if existing_phone_number:
        raise HTTPException(
            status_code=400,
            detail="Client with that phone number already exists"
        )

    existing_email = db.query(Client).filter(
        Client.email.ilike(client_data.email),
        Client.is_deleted == False,
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Client with that email already exists"
        )

    # -----------------------------------------------------
    # 3. Create Client (only commit once)
    # -----------------------------------------------------
    try:
        client = Client(
            name_of_organisation=client_data.name_of_organisation,
            country=client_data.country,
            contact_person=f"{client_data.first_name} {client_data.last_name}",
            phone_number=client_data.phone_number,
            email=client_data.email,
        )

        db.add(client)
        db.commit()
        db.refresh(client)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create client: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create client")

    # -----------------------------------------------------
    # 4. Create Org Admin User for the New Client
    # -----------------------------------------------------

    plain_password = generate_password()

    hashed_password = hash_password(plain_password)

    try:
        new_user = ClientUser(
            client_id=client.id,
            first_name=client_data.first_name,
            last_name=client_data.last_name,
            phone_number=client_data.phone_number,
            email=client_data.email,
            hashed_password=hashed_password,
            is_active=False,
            role=UserRole.org_admin,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create client admin user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create user")

    # -----------------------------------------------------
    # Return Response
    # -----------------------------------------------------

    return UserClientCreateOut(
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        phone_number=new_user.phone_number,
        email=new_user.email,
        role=new_user.role,
        name_of_organisation=client.name_of_organisation,
        country=client.country,
        plain_password=plain_password,
    )


#------------------------------ 
# get all clients 
# -----------------------------
@router.get(
    "/clients/",
    response_model=PaginatedResponse
)
def get_all_clients(
        request: Request,
        filters: ClientFilters = Depends(),
        page: int = 1,
        page_size: int = 10,
        current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
        db: Session = Depends(get_db),
    ):
    
    query = db.query(Client).filter(Client.is_deleted == False)

    # Filters
    if filters.name:
        query = query.filter(Client.name_of_organisation.ilike(f"%{filters.name}%"))

    if filters.country:
        query = query.filter(Client.country.ilike(f"%{filters.country}%"))

    # Sorting by created_at
    if filters.sort and filters.sort.lower() == "asc":
        query = query.order_by(Client.created_at.asc())
    else:
        query = query.order_by(Client.created_at.desc())

    base_url = str(request.url).split("?")[0]

    logger.info(f"User {current_user['id']} accessed all clients")

    return paginate_queryset(query, page, page_size, base_url, ClientOut)


#------------------------------
# get client by id
#------------------------------
@router.get("/clients/{id}", response_model=ClientOut)
def get_client(
    id: uuid.UUID,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin
    ])),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == id,
        Client.is_deleted == False
    ).first()

    if not client:
        raise HTTPException(404, "Client not found")

    # Split contact_person → first_name & last_name
    first_name, last_name = split_contact_person(client.contact_person)

    return ClientOut(
        id=client.id,
        name_of_organisation=client.name_of_organisation,
        country=client.country,
        phone_number=client.phone_number,
        email=client.email,
        first_name=first_name,
        last_name=last_name
    )

#------------------------ 
# update client details 
# -----------------------
@router.patch(
    "/clients/{client_id}",
    response_model=ClientOut,
    status_code=status.HTTP_200_OK,
    summary="Update client details"
)
def update_client(
    client_id: uuid.UUID,
    client_data: ClientUpdate,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db)
):
    # Fetch client
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Org admin can ONLY edit their own client
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(client.id):
            raise HTTPException(
                status_code=403,
                detail="You cannot modify another organisation"
            )

    # Extract updated fields
    update_data = client_data.model_dump(exclude_unset=True)

    # --- Handle name updates (first/last → contact_person) ---
    if "first_name" in update_data or "last_name" in update_data:
        new_first = update_data.pop("first_name", None)
        new_last = update_data.pop("last_name", None)

        old_first, old_last = split_contact_person(client.contact_person)

        updated_first = new_first if new_first is not None else old_first
        updated_last = new_last if new_last is not None else old_last

        update_data["contact_person"] = f"{updated_first} {updated_last}"

    # Validate unique fields
    validate_unique_client_fields(db, client.id, update_data)

    # Apply updates
    for field, value in update_data.items():
        setattr(client, field, value)

    # Commit once
    try:
        db.commit()
        db.refresh(client)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update client {client.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update client")

    # Response split
    first_name, last_name = split_contact_person(client.contact_person)

    return ClientOut(
        id=client.id,
        name_of_organisation=client.name_of_organisation,
        country=client.country,
        first_name=first_name,
        last_name=last_name,
        phone_number=client.phone_number,
        email=client.email
    )


#--------------------------
# Delete client (soft delete)
#--------------------------
@router.delete(
    "/clients/{client_id}",
    status_code=200,
    summary="Soft delete a client",
)
def delete_client(
    client_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db)
):
    # Fetch client
    client = db.query(Client).filter(Client.id == client_id).first()

    if client is None:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )

    # Org Admins can ONLY delete their own client
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(client.id):
            raise HTTPException(
                status_code=403,
                detail="You cannot delete another organisation"
            )

    # Already deleted?
    if client.is_deleted:
        raise HTTPException(
            status_code=400,
            detail="Client already deleted"
        )

    # Soft delete
    try:
        client.is_deleted = True
        db.commit()
        db.refresh(client)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete client {client_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete client")

    logger.info(f"User {current_user['id']} deleted client {client_id}")

    return {"message": "Client deleted successfully", "client_id": str(client_id)}

