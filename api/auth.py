from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from api.client import generate_password
from api.deps import get_current_user, require_role
from db import SessionLocal,get_db
from models.client_user import ClientUser
from models.enums import UserRole
from models.hamasa_user import HamasaUser as  HamasaUser
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, oauth2_scheme
from schemas.hamasa_user import (
    PasswordChange,
    UserCreate,
  
    UserAuth,
    UserLoginFlexible,
    Token,
    RefreshTokenRequest,
    UserOut,
    UserResponse
)
from utils.otp import verify_otp, generate_otp
from utils.sms import send_sms_single  
import asyncio
from utils.otp import generate_otp, verify_otp
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from fastapi_limiter.depends import RateLimiter


load_dotenv()  # Load environment variables from .env file


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

SERVICE_TOKEN_EXPIRE_DAYS = 365   # 1 year



router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------------- Register ----------------
@router.post("/register", response_model=UserResponse,
             description= "creating the user ",
             dependencies=[Depends(RateLimiter(times=5, seconds=60))])  # Rate limit to prevent abuse
async def register(
    user: UserCreate, 
    db: Session = Depends(get_db)
):
    # Check if phone already exists
    db_phone = db.query(User).filter(User.phone_number == user.phone_number).first()
    if db_phone:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    db_phone_email = None
    if user.email:
        db_phone_email = db.query(User).filter(User.email == user.email).first()
        if db_phone_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    try:
        # Hash the password
        hashed_password = hash_password(user.password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Create new user
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        gender=user.gender,
        hashed_password=hashed_password,
        role=user.role,
        is_active=user.is_active,
        email=user.email if hasattr(user, 'email') else None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# ---------------- Verify Phone ----------------
@router.post("/verify-phone")
async def verify_phone(phone: str, otp: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if verify_otp(phone, otp):
        user.is_active = True  # Assuming you have is_active field
        db.commit()
        return {"msg": "Phone verified successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")



@router.post("/auth/login", response_model=Token)
def login(form_data: UserLoginFlexible, db: Session = Depends(get_db)):
    identifier = form_data.identifier

    user = None
    user_type = None  # "hamasa" or "client"

    if "@" in identifier:
        user = db.query(HamasaUser).filter(HamasaUser.email == identifier).first()
    else:
        user = db.query(HamasaUser).filter(HamasaUser.phone_number == identifier).first()

    if user:
        user_type = "hamasa"

    if not user:
        if "@" in identifier:
            user = db.query(ClientUser).filter(ClientUser.email == identifier).first()
        else:
            user = db.query(ClientUser).filter(ClientUser.phone_number == identifier).first()

        if user:
            user_type = "client"

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


    role = None
    if user.role:
        role = user.role.value if hasattr(user.role, "value") else user.role

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": role,
            "email": user.email,
            "user_type": user_type,
            "client_id": str(user.client_id) if user_type == "client" else None,
        }  
    )


    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserAuth.from_orm(user),
        "user_type": user_type,
    }



# ---------------- Refresh Token ----------------
@router.post("/refresh-token", response_model=Token)
def refresh_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        token_data = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Create new access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role if user.role else None,
            "email": user.email
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserAuth.from_orm(user),
    }




#----------------------------------------------------
#            Generate Service Token 
#----------------------------------------------------
@router.post("/service-token")
def generate_service_token(
    db: Session = Depends(get_db),
    current_user=Depends(require_role([UserRole.super_admin]))
):
    """
    Generate a long-lived service token for ML automation.
    Only super_admin can create it.
    """

    # 1) Create a dedicated service user if not existing
    service_user = db.query(User).filter(User.role == UserRole.ml_service).first()

    password = generate_password()
    hashed_password = hash_password(password)

    if not service_user:
        service_user = User(
            first_name="ml",
            last_name="service",
            email="ml-service@system.local",
            phone_number="0000000000",
            hashed_password = hashed_password,  # Random password
            gender="other",
            is_active=True,
            role=UserRole.ml_service
        )
        db.add(service_user)
        db.commit()
        db.refresh(service_user)

    # 2) Create long-lived JWT
    expires = timedelta(days=SERVICE_TOKEN_EXPIRE_DAYS)

    token = create_access_token(
        data={"sub": str(service_user.id), "role": service_user.role},
        expires_delta=expires
    )

    return {
        "service_token": token,
        "expires_in_days": SERVICE_TOKEN_EXPIRE_DAYS,
        "role": service_user.role,
        "note": "Use this token in ML scripts. Does not require refresh."
    }



# ---------------- Logout ----------------
@router.post("/logout")
def logout():
    # For JWT, logout is handled client-side by deleting the token
    return {"msg": "Logout successful. Please delete the token on client side."}


@router.patch("/change-password")
def change_password(payload: PasswordChange, db: Session = Depends(get_db)):
    # 1. Find user
    user = db.query(User).filter(User.phone_number == payload.phone_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Verify OTP
    if not verify_otp(payload.phone_number, payload.otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    # 3. Update password
    user.hashed_password = hash_password(payload.new_password)
    db.commit()

    return {"msg": "Password changed successfully. Please login again."}


# ---------------- Forgot Password ----------------
@router.post("/forgot-password")
async def forgot_password(identifier: str, db: Session = Depends(get_db)):
    # Find user by email or phone
    if "@" in identifier:  # looks like email
        user = db.query(User).filter(User.email == identifier).first()
    else:  # treat as phone
        user = db.query(User).filter(User.phone_number == identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate OTP and send via SMS
    otp = generate_otp(user.phone_number)
    message = f"Your password reset OTP is {otp}. It expires in 5 minutes."
    await send_sms_single(message, user.phone_number)

    return {"msg": "OTP sent to your phone number"}


# ---------------- Reset Password ----------------
@router.patch("/reset-password")
def reset_password(
    identifier: str,
    otp: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    # Find user
    if "@" in identifier:  # looks like email
        user = db.query(User).filter(User.email == identifier).first()
    else:  # treat as phone
        user = db.query(User).filter(User.phone_number == identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify OTP
    if not verify_otp(user.phone_number, otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Update password
    user.hashed_password = hash_password(new_password)
    db.commit()

    return {"msg": "Password reset successfully"}


@router.post("/send-otp")
async def send_otp(phone: str):
    otp = generate_otp(phone)
    message = f"Your verification code is {otp}. It expires in 5 minutes."

    await send_sms_single(message, phone)
    return {"status": "OTP sent"}


@router.post("/verify-otp")
async def check_otp(phone: str, otp: str):
    if verify_otp(phone, otp):
        return {"status": "verified"}
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")


# ---------------- Get Current User ----------------
@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return current_user
