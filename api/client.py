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

from utils.client_helpers import split_contact_person
from utils.pagination import paginate_queryset


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
        responses={
            404: {"description": "Client not found"},
            403: {"description": "You do not have permission to access this resource"},
            400: {"description": "invalid input"},  
        },
            summary="Create Client and the associated org admin user",
            description="Create a new Client along with its primary org admin user",
    )
def createClient( 
    client_data:UserClientCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    #check if user exists
    user = None
    user = db.query(ClientUser).filter(
        (User.email.ilike(f"%{client_data.email}%")) |
        (User.phone_number.ilike(f"%{client_data.email}%"))
    ).first()

    if bool(user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Exists"
        )

    # check for name oforganisation if exists in db
    existing_name_of_organisation = db.query(Client).filter(
        Client.name_of_organisation.ilike(f"%{client_data.name_of_organisation}%")
    ).first()

    existing_phone_number = db.query(Client).filter(
        Client.phone_number.ilike(f"%{client_data.phone_number}%")
    ).first()

    if existing_name_of_organisation is not None:
        raise HTTPException(
            status_code=400,
            detail="Client already exists"
        )
    
    if existing_phone_number is not None:
        raise HTTPException(
            status_code=400,
            detail="Client already exists"
        )
    
    try:
        client = Client(
        name_of_organisation = client_data.name_of_organisation,
        country = client_data.country,
        contact_person= client_data.first_name + ' ' + client_data.last_name,
        phone_number= client_data.phone_number,
        email = client_data.email,
    )
        db.add(client)
        db.commit()
        db.refresh(client)
    except Exception as e:
        db.rollback()
        logger.error(f"failed to create new client due to error: {str(e)}")



        # Auto-generate secure password
    plain_password = "12345678" #generate_password()

    # Hash it before storing
    hashed_password = hash_password(plain_password)

    new_user = None
    try:
        new_user = ClientUser(
            client_id = client.id,
            first_name = client_data.first_name,
            last_name = client_data.last_name,
            phone_number = client_data.phone_number,
            is_active=False,
            email= client_data.email,
            hashed_password=hashed_password,
            role = UserRole.org_admin
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        logger.error(f"failed to create new user due to error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create user"
        )

    return UserClientCreateOut(
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        phone_number=new_user.phone_number,
        email=new_user.email,
        role = new_user.role,
        name_of_organisation=client.name_of_organisation,
        country=client.country,
        sector=client.sector,
        plain_password=plain_password
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
    
    query = db.query(Client)

    if filters.name:
        query = query.filter(Client.name_of_organisation.ilike(f"%{filters.name}%"))

    if filters.country:
        query = query.filter(Client.country.ilike(f"%{filters.country}%"))


    base_url = str(request.url).split("?")[0]

    logger.info(f"User {current_user['id']} accessed all clients")

    return paginate_queryset(query, page, page_size, base_url, ClientOut)




#------------------------ 
# update client details 
# -----------------------
@router.patch(
        "/clients/",
        response_model=ClientOut,
        status_code=status.HTTP_200_OK,
        responses={
            404: {"description": "Client not found"},
            403: {"description": "You do not have permission to access this resource"},
            400: {"description": "invalid input"},  
        },
            summary="Update Client  details",
    )
def UpdateClient(
    client_data:ClientUpdate,
    client_id:Optional[uuid.UUID] = None,
    name_of_organisation: Optional[str] = None,
    token: str = Depends(oauth2_scheme),
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db)
):
    """
    Org Admins can update their own client details
    Super Admins can update any client details
    """
    # validate input
    if(client_id is None and name_of_organisation is None) or (client_id is not None and name_of_organisation is not None):
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of client id or name of organisation must be provided"
        )

    # check for name oforganisation if exists in db
    client = None
    if client_id:
        client = db.query(Client).filter(
            Client.id == client_id
        ).first()
    else:
        client = db.query(Client).filter(
            Client.name_of_organisation.ilike(f"%{name_of_organisation}%")
        ).first()

    if client is  None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client does not exists"
        )

    # Validate fields to be update
    allowed_fields = {'contact_person', 'phone_number', 'email', 'country', 'name_of_organisation'}
    update_data = client_data.model_dump(exclude_unset=True)
    invalid_fields = set(update_data.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update restricted fields: {invalid_fields}"
        )
    
    # update fields dynamically
    try:
        for field, value in update_data.items():
            setattr(client, field, value)
            db.commit()
            db.refresh(client)
    except Exception as e:
        db.rollback()
        logger.error(f"failed to update user {client.id}: {str(e)}")
    

    identifier = client_id if client_id else name_of_organisation
    logger.info(f"User {current_user['id']} updated client details for the client {identifier}")

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



# ---------------------- 
# Client User Create Collaborators 
# ---------------------- 
@router.post(
    "/client-users/",
    status_code=status.HTTP_200_OK,
    response_model=UserClientCollaboratorOut,
    responses={
        404: {"description": "User not found"},
        403: {"description": "Forbidden"},
        400: {"description": "Invalid input data"}, 
    },
    summary="Organisation Admin can create collaborators who are users in their org",
)
def create_collaborator(
    client_data:UserClientCollaboratorCreate,
    current_user: User = Depends(require_role([UserRole.super_admin])), 
    db: Session = Depends(get_db)    
)->UserClientCollaboratorOut:
    
    # search for the client if exists
    client = None
    client_user = None

    client = db.query(Client).filter(client_data.client_id == Client.id).first() 

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # check if user already exists
    client_user = db.query(ClientUser).filter(
        (ClientUser.phone_number.ilike(f"%{client_data.phone_number}%")) |
        (ClientUser.email.ilike(f"%{client_data.email}%"))
    ).first()

    if bool(client_user):
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    plain_password = generate_password()

    hashed_password = hash_password(plain_password)

    # create the user
    try:
        new_client_user = ClientUser(
            client_id= client_data.client_id,
            first_name= client_data.first_name,
            last_name=client_data.last_name,
            phone_number=client_data.phone_number,
            hashed_password = hashed_password,
            role=client_data.role,
            is_active = False,
            email=client_data.email
        )
        db.add(new_client_user)
        db.commit()
        db.refresh(new_client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"failed to create client user {client.id}: {str(e)}")

    return UserClientCollaboratorOut(
        id=new_client_user.id, 
        client_id=new_client_user.client_id, 
        first_name=new_client_user.first_name, 
        last_name=new_client_user.last_name, 
        phone_number=new_client_user.phone_number, 
        email=new_client_user.email, 
        role=new_client_user.role, 
        is_active=new_client_user.is_active, 
        plain_password=plain_password
    )



# ------------------------ 
# get all client-users 
# ------------------------
@router.get(
    "/client-users/",
    response_model=PaginatedResponse
)
def get_all_client_users(
        request: Request,
        filters: ClientUserFilters = Depends(),
        page: int = 1,
        page_size: int = 10,
        current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
        db: Session = Depends(get_db),
    ):

    query = db.query(ClientUser)

    if filters.client_id:
        query = query.filter(ClientUser.client_id == filters.client_id)

    if filters.email:
        query = query.filter(ClientUser.email.ilike(f"%{filters.email}%"))

    if filters.is_active is not None:
        query = query.filter(ClientUser.is_active == filters.is_active)

    base_url = str(request.url).split("?")[0]

    logger.info(f"User {current_user['id']} accessed all client users")

    return paginate_queryset(query, page, page_size, base_url, UserClientOut)




#---------------------------- 
# update client User details 
# ---------------------------
@router.patch(
        "/client-users/",
        response_model=UserClientOut,
        status_code=status.HTTP_200_OK,
        responses={
            404: {"description": "Client not found"},
            403: {"description": "You do not have permission to access this resource"},
            400: {"description": "invalid input"},  
        },
            summary="Update Client user",
            description="Update client user details",
    )
def update_client_user(
    client_user_data:UserClientUpdate,
    client_user_id:Optional[uuid.UUID] = None,
    client_user_phone_number: Optional[str] = None,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin, UserRole.reviewer, UserRole.data_clerk, UserRole.org_user])), 
    db: Session = Depends(get_db)
):
    """
    super admins can update any client user details
    org admins can update any client user details within their org
    reviewers, data clerks and org users can update their own details only
    """
    # validate input
    if(client_user_id is None and client_user_phone_number is None) or (client_user_id is not None and client_user_phone_number is not None):
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of client id or name of organisation must be provided"
        )

    # check for name oforganisation if exists in db
    client_user = None
    if client_user_id:
        client_user = db.query(ClientUser).filter(
            ClientUser.id == client_user_id
        ).first()
    else:
        client_user = db.query(ClientUser).filter(
            ClientUser.phone_number.ilike(f"%{client_user_phone_number}%")
        ).first()

    if client_user is  None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client does not exists"
        )
    
    if client_user.id != client_user_id and current_user['role'] not in [UserRole.super_admin, UserRole.org_admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this user"
        )

    # Validate fields to be update
    allowed_fields = {'first_name','last_name', 'phone_number', 'email'}
    update_data = client_user_data.model_dump(exclude_unset=True)
    invalid_fields = set(update_data.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update restricted fields: {invalid_fields}"
        )
    
    # update fields dynamically
    try:
        for field, value in update_data.items():
            setattr(client_user, field, value)
            db.commit()
            db.refresh(client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"failed to update user {client_user.id}: {str(e)}")
    

    identifier = client_user_id if client_user_id else client_user_phone_number
    logger.info(f"User {current_user['id']} updated client details for the client {identifier}")

    return UserClientOut(
        id=client_user.id, 
        first_name=client_user.first_name, 
        last_name=client_user.last_name, 
        phone_number=client_user.phone_number, 
        email=client_user.email  
    )




#----------------------------- 
# update client User passwords 
# ----------------------------
@router.patch(
        "/client-users/update-password/",
        response_model=UserClientOut,
        status_code=status.HTTP_200_OK,
        responses={
            404: {"description": "Client not found"},
            403: {"description": "You do not have permission to access this resource"},
            400: {"description": "invalid input"},  
        },
            summary="Update Client user password",
            description="Update client user password",
    )
def update_client_user(
    client_user_data:UserClientUpdatePassword,
    client_user_id:Optional[uuid.UUID] = None,
    client_user_phone_number: Optional[str] = None,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin, UserRole.reviewer, UserRole.data_clerk, UserRole.org_user])), 
    db: Session = Depends(get_db)
):
    """
    super admins can update any client user password
    org admins can update any client user password within their org
    reviewers, data clerks and org users can update their own password only
    """
    # validate input
    if(client_user_id is None and client_user_phone_number is None) or (client_user_id is not None and client_user_phone_number is not None):
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of client id or name of organisation must be provided"
        )

    # check for name oforganisation if exists in db
    client_user = None
    if client_user_id:
        client_user = db.query(ClientUser).filter(
            ClientUser.id == client_user_id
        ).first()
    else:
        client_user = db.query(ClientUser).filter(
            ClientUser.phone_number.ilike(f"%{client_user_phone_number}%")
        ).first()

    if client_user is  None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client does not exists"
        )
    
    if client_user.id != client_user_id and current_user['role'] not in [UserRole.super_admin, UserRole.org_admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this user"
        )

    # Validate fields to be update
    password = client_user_data.password
    confirm_password = client_user_data.confirm_password

    if password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    if len(password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 4 characters long"
        )
    hashed_password = hash_password(password)

    # update password
    try:
        client_user.hashed_password = hashed_password
        db.commit()
        db.refresh(client_user)
    except Exception as e:
        db.rollback()
        logger.error(f"failed to update user {client_user.id}: {str(e)}")

    identifier = client_user_id if client_user_id else client_user_phone_number
    logger.info(f"User {current_user['id']} updated client details for the client {identifier}")

    return UserClientOut(
        id=client_user.id, 
        first_name=client_user.first_name, 
        last_name=client_user.last_name, 
        phone_number=client_user.phone_number, 
        email=client_user.email  
    )
