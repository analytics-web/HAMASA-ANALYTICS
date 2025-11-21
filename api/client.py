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

    plain_password = "12345678"  # replace with generate_password()

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



#----------------------------------------------------------------------------------------------------#
#----------------------------------- Client User Endpoints ----------------------------------#
#----------------------------------------------------------------------------------------------------#



# # ---------------------- 
# # Client User Create Collaborators 
# # ---------------------- 
# @router.post(
#     "/client-users/",
#     status_code=status.HTTP_200_OK,
#     response_model=UserClientCollaboratorOut,
#     summary="Organisation Admin or Super Admin can create collaborators",
# )
# def create_collaborator(
#     client_data: UserClientCollaboratorCreate,
#     current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
#     db: Session = Depends(get_db),
# ):

#     # ----------------------------------------------------
#     # 1. Check client exists and is not deleted
#     # ----------------------------------------------------
#     client = (
#         db.query(Client)
#         .filter(
#             Client.id == client_data.client_id,
#             Client.is_deleted == False
#         )
#         .first()
#     )

#     if not client:
#         raise HTTPException(404, "Client not found")

#     # ----------------------------------------------------
#     # 2. Org admin can ONLY create users for their own org
#     # ----------------------------------------------------
#     if current_user["role"] == UserRole.org_admin:
#         if str(current_user["client_id"]) != str(client.id):
#             raise HTTPException(
#                 403,
#                 "You cannot create users for another organisation"
#             )

#     # ----------------------------------------------------
#     # 3. Check if user exists EXACT match (not ilike)
#     # ----------------------------------------------------
#     existing_user = db.query(ClientUser).filter(
#         (ClientUser.email == client_data.email) |
#         (ClientUser.phone_number == client_data.phone_number)
#     ).first()

#     if existing_user:
#         raise HTTPException(400, "A user with that email or phone number already exists")

#     # ----------------------------------------------------
#     # 4. Validate role (prevent privilege escalation)
#     # ----------------------------------------------------
#     if client_data.role in [UserRole.super_admin]:
#         raise HTTPException(
#             400,
#             "Collaborators cannot be assigned a super admin role"
#         )

#     # org_admin must not create another org_admin unless allowed
#     if current_user["role"] == UserRole.org_admin:
#         if client_data.role == UserRole.org_admin:
#             raise HTTPException(
#                 403,
#                 "Org admins cannot create other org admins"
#             )

#     # ----------------------------------------------------
#     # 5. Create user
#     # ----------------------------------------------------
#     plain_password = generate_password()
#     hashed_password = hash_password(plain_password)

#     try:
#         new_client_user = ClientUser(
#             client_id=client.id,
#             first_name=client_data.first_name,
#             last_name=client_data.last_name,
#             phone_number=client_data.phone_number,
#             email=client_data.email,
#             hashed_password=hashed_password,
#             is_active=False,
#             role=client_data.role,
#         )

#         db.add(new_client_user)
#         db.commit()
#         db.refresh(new_client_user)

#     except Exception as e:
#         db.rollback()
#         logger.error(f"Failed to create client user for client {client.id}: {str(e)}")
#         raise HTTPException(500, "Failed to create collaborator")

#     # ----------------------------------------------------
#     # 6. Return output
#     # ----------------------------------------------------
#     return UserClientCollaboratorOut(
#         id=new_client_user.id,
#         client_id=new_client_user.client_id,
#         first_name=new_client_user.first_name,
#         last_name=new_client_user.last_name,
#         phone_number=new_client_user.phone_number,
#         email=new_client_user.email,
#         role=new_client_user.role,
#         is_active=new_client_user.is_active,
#         plain_password=plain_password
#     )


# # ------------------------ 
# # get all client-users 
# # ------------------------
# @router.get(
#     "/client-users/",
#     response_model=PaginatedResponse,
#     summary="Get all client users (with filtering and sorting)"
# )
# def get_all_client_users(
#     request: Request,
#     filters: ClientUserFilters = Depends(),
#     page: int = 1,
#     page_size: int = 10,
#     sort: str = "desc",  # NEW: sorting based on created_at
#     current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
#     db: Session = Depends(get_db),
# ):

#     query = db.query(ClientUser)

#     # Org admins can ONLY see users in their own org
#     if current_user["role"] == UserRole.org_admin:
#         query = query.filter(ClientUser.client_id == current_user["client_id"])

#     # Apply filters
#     if filters.client_id:
#         query = query.filter(ClientUser.client_id == filters.client_id)

#     if filters.email:
#         query = query.filter(ClientUser.email.ilike(f"%{filters.email}%"))

#     if filters.is_active is not None:
#         query = query.filter(ClientUser.is_active == filters.is_active)

#     # Sorting
#     if sort.lower() == "asc":
#         query = query.order_by(ClientUser.created_at.asc())
#     else:
#         query = query.order_by(ClientUser.created_at.desc())

#     base_url = str(request.url).split("?")[0]

#     logger.info(f"User {current_user['id']} accessed client users list")

#     return paginate_queryset(query, page, page_size, base_url, UserClientOut)



# #---------------------------- 
# # update client User details 
# # ---------------------------
# @router.patch(
#     "/client-users/",
#     response_model=UserClientOut,
#     status_code=status.HTTP_200_OK,
#     summary="Update Client User",
#     description="Update client user details based on ID or phone number"
# )
# def update_client_user(
#     client_user_data: UserClientUpdate,
#     client_user_id: Optional[uuid.UUID] = None,
#     client_user_phone_number: Optional[str] = None,
#     current_user=Depends(require_role([
#         UserRole.super_admin, 
#         UserRole.org_admin, 
#         UserRole.reviewer, 
#         UserRole.data_clerk, 
#         UserRole.org_user
#     ])),
#     db: Session = Depends(get_db)
# ):
#     """
#     Role Permissions:
#     - super_admin: update any client user
#     - org_admin: update any user within their org
#     - reviewer, data_clerk, org_user: can ONLY update their own profile
#     """

#     # Must supply exactly one identifier
#     if (client_user_id is None and client_user_phone_number is None) or \
#        (client_user_id is not None and client_user_phone_number is not None):
#         raise HTTPException(
#             status_code=400,
#             detail="Provide exactly one of client_user_id or client_user_phone_number"
#         )

#     # Fetch the user
#     if client_user_id:
#         client_user = db.query(ClientUser).filter(ClientUser.id == client_user_id).first()
#     else:
#         client_user = db.query(ClientUser).filter(
#             ClientUser.phone_number.ilike(f"%{client_user_phone_number}%")
#         ).first()

#     if not client_user:
#         raise HTTPException(
#             status_code=404,
#             detail="Client user not found"
#         )

#     # Role-based access control
#     if current_user["role"] not in [UserRole.super_admin, UserRole.org_admin]:

#         # Regular users can only update themselves
#         if str(current_user["id"]) != str(client_user.id):
#             raise HTTPException(
#                 status_code=403,
#                 detail="You are not allowed to update this user"
#             )

#     # org_admin can update ONLY users in their org
#     if current_user["role"] == UserRole.org_admin:
#         if str(current_user["client_id"]) != str(client_user.client_id):
#             raise HTTPException(
#                 status_code=403,
#                 detail="You cannot update users outside your organisation"
#             )

#     # Fields allowed for update
#     allowed_fields = {"first_name", "last_name", "phone_number", "email"}
#     update_data = client_user_data.model_dump(exclude_unset=True)

#     invalid_fields = set(update_data.keys()) - allowed_fields
#     if invalid_fields:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Cannot update restricted fields: {invalid_fields}"
#         )

#     # Uniqueness validation
#     if "phone_number" in update_data:
#         exists = db.query(ClientUser).filter(
#             ClientUser.phone_number == update_data["phone_number"],
#             ClientUser.id != client_user.id
#         ).first()
#         if exists:
#             raise HTTPException(400, "Phone number already exists")

#     if "email" in update_data:
#         exists = db.query(ClientUser).filter(
#             ClientUser.email == update_data["email"],
#             ClientUser.id != client_user.id
#         ).first()
#         if exists:
#             raise HTTPException(400, "Email already exists")

#     # Apply updates
#     for field, value in update_data.items():
#         setattr(client_user, field, value)

#     try:
#         db.commit()
#         db.refresh(client_user)
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Failed to update client user {client_user.id}: {str(e)}")
#         raise HTTPException(500, "Failed to update user")

#     logger.info(f"User {current_user['id']} updated user {client_user.id}")

#     return UserClientOut(
#         id=client_user.id,
#         first_name=client_user.first_name,
#         last_name=client_user.last_name,
#         phone_number=client_user.phone_number,
#         email=client_user.email,
#     )



# #----------------------------- 
# # update client User passwords 
# # ----------------------------
# @router.patch(
#     "/client-users/update-password/",
#     response_model=UserClientOut,
#     status_code=status.HTTP_200_OK,
#     summary="Update Client user password",
#     description="Update client user password",
#     dependencies=[Depends(RateLimiter(times=5, seconds=3600))]  # 5 requests/hour
# )
# def update_client_user_password(
#     client_user_data: UserClientUpdatePassword,
#     client_user_id: Optional[uuid.UUID] = None,
#     client_user_phone_number: Optional[str] = None,
#     current_user=Depends(require_role([
#         UserRole.super_admin,
#         UserRole.org_admin,
#         UserRole.reviewer,
#         UserRole.data_clerk,
#         UserRole.org_user
#     ])),
#     db: Session = Depends(get_db)
# ):
#     """
#     super admins can update any client user password
#     org admins can update any client user password within their org
#     reviewers, data clerks and org users can update their own password only
#     """

#     # Validating input: must provide exactly one identifier
#     if (client_user_id is None and client_user_phone_number is None) or \
#        (client_user_id is not None and client_user_phone_number is not None):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Exactly one of client_user_id or phone_number must be provided"
#         )

#     # Fetch target user
#     client_user = None
#     if client_user_id:
#         client_user = db.query(ClientUser).filter(ClientUser.id == client_user_id).first()
#     else:
#         client_user = db.query(ClientUser).filter(
#             ClientUser.phone_number.ilike(f"%{client_user_phone_number}%")
#         ).first()

#     if not client_user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Client user does not exist"
#         )

#     # Permission checks
#     if current_user['role'] not in [UserRole.super_admin, UserRole.org_admin]:
#         # Regular users can update only their own password
#         if str(current_user['id']) != str(client_user.id):
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="You do not have permission to update another user's password"
#             )
#     else:
#         # Org admin must stay in their own org
#         if current_user['role'] == UserRole.org_admin:
#             if str(current_user["client_id"]) != str(client_user.client_id):
#                 raise HTTPException(
#                     status_code=status.HTTP_403_FORBIDDEN,
#                     detail="You cannot modify a user outside your organisation"
#                 )

#     # Extract passwords
#     password = client_user_data.password
#     confirm_password = client_user_data.confirm_password

#     # Validation: match
#     if password != confirm_password:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Passwords do not match"
#         )

#     # Validation: Medium strength (Rule B)
#     # Min 8 characters and at least one number
#     if len(password) < 8 or not any(ch.isdigit() for ch in password):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Password must be at least 8 characters long and contain at least one number"
#         )

#     # Hash new password
#     hashed_password = hash_password(password)

#     # Update password
#     try:
#         client_user.hashed_password = hashed_password
#         db.commit()
#         db.refresh(client_user)
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Failed to update client user password {client_user.id}: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail="Failed to update password"
#         )

#     # Audit Log
#     logger.info(
#         f"Password updated for user {client_user.id} by user {current_user['id']} (role: {current_user['role']})"
#     )

#     return UserClientOut(
#         id=client_user.id,
#         first_name=client_user.first_name,
#         last_name=client_user.last_name,
#         phone_number=client_user.phone_number,
#         email=client_user.email
#     )

# #--------------------------------
# # Delete client user (Soft delete)
# #--------------------------------                             
# @router.delete(
#     "/client-users/{user_id}",
#     status_code=200,
#     summary="Delete a client user"
# )
# def delete_client_user(
#     user_id: uuid.UUID,
#     current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
#     db: Session = Depends(get_db)
# ):
#     client_user = db.query(ClientUser).filter(ClientUser.id == user_id).first()

#     if not client_user:
#         raise HTTPException(404, "Client user not found")

#     # org_admin must only delete users in their own org
#     if current_user["role"] == UserRole.org_admin:
#         if str(client_user.client_id) != str(current_user["client_id"]):
#             raise HTTPException(403, "You cannot delete users outside your organisation")

#     try:
#         client_user.is_deleted = True
#         db.commit()
#         db.refresh(client_user)
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Failed to delete client user {user_id}: {e}")
#         raise HTTPException(500, "Failed to delete user")

#     logger.info(f"User {current_user['id']} deleted client user {user_id}")

#     return {"message": "User deleted successfully"}


# #----------------------------- 
# # Activate / Deactivate client user
# #-----------------------------
# @router.patch(
#     "/client-users/{user_id}/status",
#     summary="Activate or deactivate a client user",
#     status_code=200
# )
# def update_user_status(
#     user_id: uuid.UUID,
#     is_active: bool,
#     current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
#     db: Session = Depends(get_db)
# ):
#     client_user = db.query(ClientUser).filter(ClientUser.id == user_id).first()

#     if not client_user:
#         raise HTTPException(404, "Client user not found")

#     # org_admin may only update users in their org
#     if current_user["role"] == UserRole.org_admin:
#         if str(client_user.client_id) != str(current_user["client_id"]):
#             raise HTTPException(403, "You cannot update users outside your organisation")

#     try:
#         client_user.is_active = is_active
#         db.commit()
#         db.refresh(client_user)
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Failed to update status for user {user_id}: {e}")
#         raise HTTPException(500, "Failed to update status")

#     logger.info(
#         f"User {current_user['id']} set user {user_id} active={is_active}"
#     )

#     return {
#         "id": client_user.id,
#         "is_active": client_user.is_active,
#         "message": "User status updated successfully"
#     }


# #----------------------------- 
# # Promote / Demote client user
# #-----------------------------
# @router.patch(
#     "/client-users/{user_id}/role",
#     summary="Promote or demote a client user",
#     status_code=200
# )
# def update_user_role(
#     user_id: uuid.UUID,
#     new_role: UserRole,
#     current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
#     db: Session = Depends(get_db)
# ):
#     client_user = db.query(ClientUser).filter(ClientUser.id == user_id).first()

#     if not client_user:
#         raise HTTPException(404, "Client user not found")

#     # org_admin may only manage users in their org
#     if current_user["role"] == UserRole.org_admin:
#         if str(client_user.client_id) != str(current_user["client_id"]):
#             raise HTTPException(403, "You cannot update users outside your organisation")

#         # org_admin cannot assign super_admin role
#         if new_role == UserRole.super_admin:
#             raise HTTPException(403, "You cannot assign super admin role")

#     try:
#         client_user.role = new_role
#         db.commit()
#         db.refresh(client_user)
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Failed to change role for user {user_id}: {e}")
#         raise HTTPException(500, "Failed to change role")

#     logger.info(
#         f"User {current_user['id']} changed role for user {user_id} to {new_role}"
#     )

#     return {
#         "id": client_user.id,
#         "role": client_user.role,
#         "message": "User role updated successfully"
#     }



# ----------------------------------------------------------------------------------------------------#
# ----------------------------------- Client User Endpoints ------------------------------------------#
# ----------------------------------------------------------------------------------------------------#

# ---------------------- 
# Client User Create Collaborators 
# ---------------------- 
@router.post(
    "/client-users/",
    status_code=status.HTTP_200_OK,
    response_model=UserClientCollaboratorOut,
    summary="Organisation Admin or Super Admin can create collaborators",
)
def create_collaborator(
    client_data: UserClientCollaboratorCreate,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    # 1. Check client exists and is not deleted
    client = (
        db.query(Client)
        .filter(
            Client.id == client_data.client_id,
            Client.is_deleted == False
        )
        .first()
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # 2. Org admin can ONLY create users for their own org
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(client.id):
            raise HTTPException(
                status_code=403,
                detail="You cannot create users for another organisation",
            )

    # 3. Check if user exists EXACT match (not ilike)
    existing_user = (
        db.query(ClientUser)
        .filter(
            (ClientUser.email == client_data.email) |
            (ClientUser.phone_number == client_data.phone_number)
        )
        .filter(ClientUser.is_deleted == False)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with that email or phone number already exists",
        )

    # 4. Validate role (prevent privilege escalation)
    if client_data.role in [UserRole.super_admin]:
        raise HTTPException(
            status_code=400,
            detail="Collaborators cannot be assigned a super admin role",
        )

    # org_admin must not create another org_admin
    if current_user["role"] == UserRole.org_admin:
        if client_data.role == UserRole.org_admin:
            raise HTTPException(
                status_code=403,
                detail="Org admins cannot create other org admins",
            )

    # 5. Create user
    plain_password = generate_password()
    hashed_password = hash_password(plain_password)

    try:
        new_client_user = ClientUser(
            client_id=client.id,
            first_name=client_data.first_name,
            last_name=client_data.last_name,
            phone_number=client_data.phone_number,
            email=client_data.email,
            hashed_password=hashed_password,
            is_active=False,
            role=client_data.role.value if isinstance(client_data.role, UserRole) else client_data.role,
        )

        db.add(new_client_user)
        db.commit()
        db.refresh(new_client_user)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create client user for client {client.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create collaborator")

    # 6. Return output
    return UserClientCollaboratorOut(
        id=new_client_user.id,
        client_id=new_client_user.client_id,
        first_name=new_client_user.first_name,
        last_name=new_client_user.last_name,
        phone_number=new_client_user.phone_number,
        email=new_client_user.email,
        role=new_client_user.role,
        is_active=new_client_user.is_active,
        plain_password=plain_password,
    )


# ------------------------ 
# Get all client-users 
# ------------------------
@router.get(
    "/client-users/",
    response_model=PaginatedResponse,
    summary="Get all client users (with filtering and sorting)",
)
def get_all_client_users(
    request: Request,
    filters: ClientUserFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    sort: str = "desc",  # sorting based on created_at
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    query = (
        db.query(ClientUser)
        .filter(ClientUser.is_deleted == False)
    )

    # Org admins can ONLY see users in their own org
    if current_user["role"] == UserRole.org_admin:
        query = query.filter(ClientUser.client_id == current_user["client_id"])

    # Apply filters
    if filters.client_id:
        query = query.filter(ClientUser.client_id == filters.client_id)

    if filters.email:
        query = query.filter(ClientUser.email.ilike(f"%{filters.email}%"))

    if filters.is_active is not None:
        query = query.filter(ClientUser.is_active == filters.is_active)

    # Sorting
    if sort.lower() == "asc":
        query = query.order_by(ClientUser.created_at.asc())
    else:
        query = query.order_by(ClientUser.created_at.desc())

    base_url = str(request.url).split("?")[0]

    logger.info(f"User {current_user['id']} accessed client users list")

    return client_paginate_queryset(query, page, page_size, base_url, UserClientOut)


# ---------------------------- 
# Update client user details 
# ---------------------------
@router.patch(
    "/client-users/",
    response_model=UserClientOut,
    status_code=status.HTTP_200_OK,
    summary="Update Client User",
    description="Update client user details based on ID or phone number",
)
def update_client_user(
    client_user_data: UserClientUpdate,
    client_user_id: Optional[uuid.UUID] = None,
    client_user_phone_number: Optional[str] = None,
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
            UserRole.reviewer,
            UserRole.data_clerk,
            UserRole.org_user,
        ])
    ),
    db: Session = Depends(get_db),
):
    """
    Role Permissions:
    - super_admin: update any client user
    - org_admin: update any user within their org
    - reviewer, data_clerk, org_user: can ONLY update their own profile
    """

    # Must supply exactly one identifier
    if (client_user_id is None and client_user_phone_number is None) or \
       (client_user_id is not None and client_user_phone_number is not None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of client_user_id or client_user_phone_number",
        )

    # Fetch the user
    if client_user_id:
        client_user = (
            db.query(ClientUser)
            .filter(
                ClientUser.id == client_user_id,
                ClientUser.is_deleted == False,
            )
            .first()
        )
    else:
        client_user = (
            db.query(ClientUser)
            .filter(
                ClientUser.phone_number == client_user_phone_number,
                ClientUser.is_deleted == False,
            )
            .first()
        )

    if not client_user:
        raise HTTPException(
            status_code=404,
            detail="Client user not found",
        )

    # Role-based access control
    if current_user["role"] not in [UserRole.super_admin, UserRole.org_admin]:
        # Regular users can only update themselves
        if str(current_user["id"]) != str(client_user.id):
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to update this user",
            )

    # org_admin can update ONLY users in their org
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(client_user.client_id):
            raise HTTPException(
                status_code=403,
                detail="You cannot update users outside your organisation",
            )

    # Fields allowed for update
    allowed_fields = {"first_name", "last_name", "phone_number", "email"}
    update_data = client_user_data.model_dump(exclude_unset=True)

    invalid_fields = set(update_data.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update restricted fields: {invalid_fields}",
        )

    # Uniqueness validation
    if "phone_number" in update_data:
        exists = (
            db.query(ClientUser)
            .filter(
                ClientUser.phone_number == update_data["phone_number"],
                ClientUser.id != client_user.id,
                ClientUser.is_deleted == False,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Phone number already exists")

    if "email" in update_data:
        exists = (
            db.query(ClientUser)
            .filter(
                ClientUser.email == update_data["email"],
                ClientUser.id != client_user.id,
                ClientUser.is_deleted == False,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Email already exists")

    # Apply updates
    for field, value in update_data.items():
        setattr(client_user, field, value)

    try:
        db.commit()
        db.refresh(client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update client user {client_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user")

    logger.info(f"User {current_user['id']} updated user {client_user.id}")

    return UserClientOut(
        id=client_user.id,
        client_id=client_user.client_id,
        first_name=client_user.first_name,
        last_name=client_user.last_name,
        phone_number=client_user.phone_number,
        email=client_user.email,
        is_active=client_user.is_active,
        role=client_user.role,
    )


# ----------------------------- 
# Update client user passwords 
# ----------------------------
@router.patch(
    "/client-users/update-password/",
    response_model=UserClientOut,
    status_code=status.HTTP_200_OK,
    summary="Update Client user password",
    description="Update client user password",
    dependencies=[Depends(RateLimiter(times=5, seconds=3600))],  # 5 requests/hour
)
def update_client_user_password(
    client_user_data: UserClientUpdatePassword,
    client_user_id: Optional[uuid.UUID] = None,
    client_user_phone_number: Optional[str] = None,
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
            UserRole.reviewer,
            UserRole.data_clerk,
            UserRole.org_user,
        ])
    ),
    db: Session = Depends(get_db),
):
    """
    super admins can update any client user password
    org admins can update any client user password within their org
    reviewers, data clerks and org users can update their own password only
    """

    # Validating input: must provide exactly one identifier
    if (client_user_id is None and client_user_phone_number is None) or \
       (client_user_id is not None and client_user_phone_number is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of client_user_id or phone_number must be provided",
        )

    # Fetch target user
    if client_user_id:
        client_user = (
            db.query(ClientUser)
            .filter(
                ClientUser.id == client_user_id,
                ClientUser.is_deleted == False,
            )
            .first()
        )
    else:
        client_user = (
            db.query(ClientUser)
            .filter(
                ClientUser.phone_number == client_user_phone_number,
                ClientUser.is_deleted == False,
            )
            .first()
        )

    if not client_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client user does not exist",
        )

    # Permission checks
    if current_user["role"] not in [UserRole.super_admin, UserRole.org_admin]:
        # Regular users can update only their own password
        if str(current_user["id"]) != str(client_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update another user's password",
            )
    else:
        # Org admin must stay in their own org
        if current_user["role"] == UserRole.org_admin:
            if str(current_user["client_id"]) != str(client_user.client_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You cannot modify a user outside your organisation",
                )

    # Extract passwords
    password = client_user_data.password
    confirm_password = client_user_data.confirm_password

    # Validation: match
    if password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Validation: Medium strength
    if len(password) < 8 or not any(ch.isdigit() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain at least one number",
        )

    # Hash new password
    hashed_password = hash_password(password)

    # Update password
    try:
        client_user.hashed_password = hashed_password
        db.commit()
        db.refresh(client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update client user password {client_user.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update password",
        )

    # Audit Log
    logger.info(
        f"Password updated for user {client_user.id} by user {current_user['id']} (role: {current_user['role']})"
    )

    return UserClientOut(
        id=client_user.id,
        client_id=client_user.client_id,
        first_name=client_user.first_name,
        last_name=client_user.last_name,
        phone_number=client_user.phone_number,
        email=client_user.email,
        is_active=client_user.is_active,
        role=client_user.role,
    )


# --------------------------------
# Delete client user (Soft delete)
# --------------------------------                             
@router.delete(
    "/client-users/{user_id}",
    status_code=200,
    summary="Delete a client user",
)
def delete_client_user(
    user_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    client_user = (
        db.query(ClientUser)
        .filter(
            ClientUser.id == user_id,
            ClientUser.is_deleted == False,
        )
        .first()
    )

    if not client_user:
        raise HTTPException(status_code=404, detail="Client user not found")

    # org_admin must only delete users in their own org
    if current_user["role"] == UserRole.org_admin:
        if str(client_user.client_id) != str(current_user["client_id"]):
            raise HTTPException(
                status_code=403,
                detail="You cannot delete users outside your organisation",
            )

    try:
        client_user.is_deleted = True
        db.commit()
        db.refresh(client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete client user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

    logger.info(f"User {current_user['id']} deleted client user {user_id}")

    return {"message": "User deleted successfully"}


# ----------------------------- 
# Activate / Deactivate client user
# -----------------------------
@router.patch(
    "/client-users/{user_id}/status",
    summary="Activate or deactivate a client user",
    status_code=200,
)
def update_user_status(
    user_id: uuid.UUID,
    is_active: bool,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    client_user = (
        db.query(ClientUser)
        .filter(
            ClientUser.id == user_id,
            ClientUser.is_deleted == False,
        )
        .first()
    )

    if not client_user:
        raise HTTPException(status_code=404, detail="Client user not found")

    # org_admin may only update users in their org
    if current_user["role"] == UserRole.org_admin:
        if str(client_user.client_id) != str(current_user["client_id"]):
            raise HTTPException(
                status_code=403,
                detail="You cannot update users outside your organisation",
            )

    try:
        client_user.is_active = is_active
        db.commit()
        db.refresh(client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update status for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status")

    logger.info(
        f"User {current_user['id']} set user {user_id} active={is_active}"
    )

    return {
        "id": client_user.id,
        "is_active": client_user.is_active,
        "message": "User status updated successfully",
    }


# ----------------------------- 
# Promote / Demote client user
# -----------------------------
@router.patch(
    "/client-users/{user_id}/role",
    summary="Promote or demote a client user",
    status_code=200,
)
def update_user_role(
    user_id: uuid.UUID,
    new_role: UserRole,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    client_user = (
        db.query(ClientUser)
        .filter(
            ClientUser.id == user_id,
            ClientUser.is_deleted == False,
        )
        .first()
    )

    if not client_user:
        raise HTTPException(status_code=404, detail="Client user not found")

    # org_admin may only manage users in their org
    if current_user["role"] == UserRole.org_admin:
        if str(client_user.client_id) != str(current_user["client_id"]):
            raise HTTPException(
                status_code=403,
                detail="You cannot update users outside your organisation",
            )

        # org_admin cannot assign super_admin role
        if new_role == UserRole.super_admin:
            raise HTTPException(
                status_code=403,
                detail="You cannot assign super admin role",
            )

    try:
        client_user.role = new_role.value if isinstance(new_role, UserRole) else str(new_role)
        db.commit()
        db.refresh(client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to change role for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to change role")

    logger.info(
        f"User {current_user['id']} changed role for user {user_id} to {new_role}"
    )

    return {
        "id": client_user.id,
        "role": client_user.role,
        "message": "User role updated successfully",
    }
