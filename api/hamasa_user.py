from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.params import Body
from api.deps import  require_role
from models.client import Client
from models.client_user import ClientUser
from schemas.client_user import UserClient, UserClientAssign, UserClientOut
from schemas.hamasa_user import (
        UserResponse,
        UserRole, 
        UserListOut, 
        UserBase, 
        UserUpdate,
    )

from sqlalchemy.orm import Session
from db import SessionLocal
from models.hamasa_user import HamasaUser as  User
import logging
from db import get_db

from typing import Optional
from fastapi import Response
from sqlalchemy import func
import math

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hamasa-user", tags=["Hamasa Users"])

# -----------------
# Get Current User
# -----------------
@router.get("/me")
def read_me(
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.reviewer,
        UserRole.org_admin,
        UserRole.org_user,
        UserRole.data_clerk,
    ]))
):
    return current_user



# -----------------
# Get all Users
# -----------------
@router.get("/all-users", response_model=list[UserListOut])
def get_all_users(
    response: Response,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):
    """
    Return paginated list of users.

    Pagination metadata in headers:
      - X-Total-Count
      - X-Total-Pages
      - X-Page
      - X-Page-Size
    """

    # Base query (add is_deleted filter if your User model has it)
    query = db.query(User)
    if hasattr(User, "is_deleted"):
        query = query.filter(User.is_deleted == False)  # noqa: E712

    total: int = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    offset = (page - 1) * page_size

    users = (
        query
        .order_by(User.id)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Set pagination headers
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)

    logger.info(
        f"User {current_user['id']} accessed all users "
        f"(page={page}, page_size={page_size})"
    )

    return users

# -----------------
# Get One User
# -----------------
@router.get("/one/{user_id}", response_model=UserResponse)
def get_one_user(
    user_id: UUID,
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
            UserRole.reviewer,
            UserRole.data_clerk,
            UserRole.org_user,
        ])
    ),
    db: Session = Depends(get_db)
):
    """
    Fetch a single user by ID.
    """

    query = db.query(User).filter(User.id == user_id)

    # If your User model has soft delete, enforce it:
    if hasattr(User, "is_deleted"):
        query = query.filter(User.is_deleted == False)  # noqa: E712

    user = query.first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )

    return user


# ------------------------
# Find User (ID, phone, or email)
# ------------------------
@router.get("/find", response_model=UserResponse)
def find_user(
    user_id: Optional[UUID] = None,
    phone_number: Optional[str] = None,
    email: Optional[str] = None,
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
            UserRole.reviewer,
            UserRole.data_clerk,
            UserRole.org_user,
        ])
    ),
    db: Session = Depends(get_db)
):
    """
    Find a single user by ID, phone number, or email.
    At least one identifier must be provided.
    """

    # ----------------------------
    # Validate input
    # ----------------------------
    if not any([user_id, phone_number, email]):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one identifier: user_id, phone_number, or email"
        )

    # ----------------------------
    # Build dynamic query
    # ----------------------------
    query = db.query(User)

    # Apply soft delete check if column exists
    if hasattr(User, "is_deleted"):
        query = query.filter(User.is_deleted == False)  # noqa: E712

    # Apply search filters
    if user_id:
        query = query.filter(User.id == user_id)

    if phone_number:
        cleaned = phone_number.strip().replace(" ", "").replace("-", "")
        query = query.filter(User.phone_number.ilike(cleaned))

    if email:
        query = query.filter(User.email.ilike(email))

    # ----------------------------
    # Execute query
    # ----------------------------
    user = query.first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user



# -----------------
# Update User
# -----------------
@router.patch(
    "/update-user/",
    response_model=UserBase,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "User not found"},
        403: {"description": "Forbidden"},
        400: {"description": "Invalid input data"},
    },
    summary="Update a user by ID or phone",
)
def update_user(
    user_id: Optional[UUID] = Query(None),
    user_phone: Optional[str] = Query(None),
    user_update: UserUpdate = Body(...),
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):
    """
    Update a user by ID or phone number. Only super_admin can call this.
    """

    # Exactly one of user_id or user_phone must be provided
    if (user_id is None and user_phone is None) or (
        user_id is not None and user_phone is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of user_id or user_phone must be provided",
        )

    # Find user
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        if not user_phone or not user_phone.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number cannot be empty",
            )
        user = db.query(User).filter(User.phone_number.ilike(user_phone)).first()

    if not user:
        identifier = user_id if user_id else user_phone
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with {'ID' if user_id else 'phone number'} {identifier} not found",
        )

    # Only allow these fields to be changed
    allowed_fields = {"first_name", "last_name", "phone_number", "role", "gender", "email", "image_url"}
    update_data = user_update.model_dump(exclude_unset=True)
    invalid_fields = set(update_data.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update restricted fields: {invalid_fields}",
        )

    # Apply updates
    try:
        for field, value in update_data.items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user {getattr(user, 'id', 'unknown')}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user due to a server error",
        )

    identifier = user_id if user_id else user_phone
    logger.info(
        f"User {current_user['role']} updated user with "
        f"{'ID' if user_id else 'phone number'} {identifier}"
    )

    return user


# -----------------
# Delete User
# -----------------
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "User not found"},
        403: {"description": "Forbidden"},
    },
    summary="Delete a user by ID",
)
def delete_user(
    user_id: UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):
    """
    Delete a user by ID. Only accessible to super_admin.
    """

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    db.delete(user)
    db.commit()

    logger.info(f"User {current_user['id']} deleted user {user_id}")

    return {"detail": "User deleted successfully"}



# -----------------
# Assign Roles to Users
# -----------------
@router.patch(
    "/assign-roles/",
    response_model=UserBase,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "User not found"},
        403: {"description": "Forbidden"},
        400: {"description": "Invalid input data"},
    },
    summary="Super Admin only, can change the roles for the users",
)
def assign_roles_to_user(
    user_id: Optional[UUID] = Query(None),
    user_phone: Optional[str] = Query(None),
    user_update: UserUpdate = Body(...),
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):
    """
    Update only role field of a user by ID or phone number.
    Only super_admin can call this.
    """

    # Exactly one of user_id or user_phone must be provided
    if (user_id is None and user_phone is None) or (
        user_id is not None and user_phone is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of user_id or user_phone must be provided",
        )

    # Find user
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        if not user_phone or not user_phone.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number cannot be empty",
            )
        user = db.query(User).filter(User.phone_number.ilike(user_phone)).first()

    if not user:
        identifier = user_id if user_id else user_phone
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with {'ID' if user_id else 'phone number'} {identifier} not found",
        )

    allowed_fields = {"role"}
    update_data = user_update.model_dump(exclude_unset=True)
    invalid_fields = set(update_data.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update restricted fields: {invalid_fields}",
        )

    try:
        for field, value in update_data.items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user {getattr(user, 'id', 'unknown')}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user due to a server error",
        )

    identifier = user_id if user_id else user_phone
    logger.info(
        f"User {current_user['role']} changed role for user with "
        f"{'ID' if user_id else 'phone number'} {identifier}"
    )

    return user


# ----------------------------------
# Assign Reviewer & Clerk to Client
# ----------------------------------
@router.post("/assign-user-to-client", response_model=UserClientOut)
def assign_user_to_client(
    data: UserClientAssign,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    user = db.query(ClientUser).filter(ClientUser.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    client = db.query(Client).filter(Client.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    existing = (
        db.query(UserClient)
        .filter(
            UserClient.user_id == data.user_id,
            UserClient.client_id == data.client_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already assigned to client",
        )

    user_client = UserClient(
        user_id=data.user_id,
        client_id=data.client_id,
        role_within_client=data.role_within_client,
        is_primary_contact=data.is_primary_contact,
    )
    db.add(user_client)
    db.commit()
    db.refresh(user_client)

    return user_client


# --------------------------
# De-Assign User from Client
# --------------------------
@router.delete("/deassign-user-from-client", response_model=dict)
def deassign_user_from_client(
    user_id: Optional[UUID] = Query(None),
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    client_id: Optional[UUID] = Query(None),
    name_of_organisation: Optional[str] = Query(None),
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    if not any([user_id, phone_number, email]):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one user identifier (user_id, phone_number, email)",
        )
    if not any([client_id, name_of_organisation]):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one client identifier (client_id, name_of_organisation)",
        )

    # Find user
    user_query = db.query(ClientUser)
    if user_id:
        user_query = user_query.filter(ClientUser.id == user_id)
    if phone_number:
        user_query = user_query.filter(ClientUser.phone_number.ilike(f"%{phone_number}%"))
    if email:
        user_query = user_query.filter(ClientUser.email.ilike(f"%{email}%"))
    user = user_query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find client
    client_query = db.query(Client)
    if client_id:
        client_query = client_query.filter(Client.id == client_id)
    if name_of_organisation:
        client_query = client_query.filter(
            Client.name_of_organisation.ilike(f"%{name_of_organisation}%")
        )
    client = client_query.first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    user_client = (
        db.query(UserClient)
        .filter(UserClient.user_id == user.id, UserClient.client_id == client.id)
        .first()
    )
    if not user_client:
        raise HTTPException(status_code=404, detail="Assignment not found")

    try:
        db.delete(user_client)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to deassign user: {str(e)}")

    return {"message": f"User {user.id} successfully deassigned from client {client.id}"}
