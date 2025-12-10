from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from core.security import SECRET_KEY, ALGORITHM
from schemas.hamasa_user import UserRole
from models.hamasa_user import HamasaUser
from models.client_user import ClientUser
from sqlalchemy.orm import Session
from db.db import SessionLocal, get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#         role: str = payload.get("role")
#         if user_id is None or role is None:
#             raise HTTPException(status_code=401, detail="Invalid token")
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid token")

#     return {"id": user_id, "role": role}


# def get_current_user(
#     token: str = Depends(oauth2_scheme), 
#     db: Session = Depends(get_db)
# ):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#         role: str = payload.get("role")
#         if user_id is None or role is None:
#             raise HTTPException(status_code=401, detail="Invalid token")
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid token")

#     # Fetch correct user model based on role
#     user = None
#     if role in [
#         UserRole.super_admin.value,
#         UserRole.reviewer.value,
#         UserRole.data_clerk.value,
#         UserRole.ml_service.value
#     ]:
#         user = db.query(HamasaUser).filter(HamasaUser.id == user_id).first()
#     else:
#         user = db.query(ClientUser).filter(ClientUser.id == user_id).first()

#     if not user:
#         raise HTTPException(status_code=401, detail="User Not found")

#     return {"id": str(user.id), "role": role, "user": user}

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("sub")
        role = payload.get("role")
        user_type = payload.get("user_type")

        if not user_id or not role:
            raise HTTPException(401, "Invalid token")

    except JWTError:
        raise HTTPException(401, "Invalid token")

    # ----------------------------------
    # Fetch by correct table
    # ----------------------------------
    if user_type == "hamasa":
        user = db.query(HamasaUser).filter(HamasaUser.id == user_id).first()
    else:
        user = db.query(ClientUser).filter(ClientUser.id == user_id).first()

    if not user:
        raise HTTPException(401, "User not found")

    return {
        "id": str(user.id),
        "role": role,
        "user_type": user_type,
        "user": user
    }


def require_role(required_roles: list[UserRole]):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user["role"] not in [r.value for r in required_roles]:
            raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
        return current_user
    return role_checker