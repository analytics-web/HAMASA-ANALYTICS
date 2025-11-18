# from datetime import datetime, timedelta, timezone
# from fastapi.security import OAuth2PasswordBearer
# from jose import jwt, JWTError
# from passlib.context import CryptContext
# import os
# from dotenv import load_dotenv
# import random



# load_dotenv()


# pwd_context = CryptContext(schemes=["argon2","bcrypt"], deprecated="auto")
# SECRET_KEY = os.getenv("SECRET_KEY")
# ALGORITHM = os.getenv("ALGORITHM")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
# REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

# # oauth scheme for JWT authentication
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)


# def create_access_token(data:dict, expires_delta:timedelta | None = None) -> str:
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else
#                                            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp":expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


from datetime import datetime, timedelta, timezone
import logging
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
import random


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()


pwd_context = CryptContext(schemes=["argon2","bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

REFRESH_TOKEN_TYPE = "refresh"

# oauth scheme for JWT authentication
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# With this:
oauth2_scheme = HTTPBearer(auto_error=True)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"Created access token: {encoded_jwt}")
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": REFRESH_TOKEN_TYPE})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)