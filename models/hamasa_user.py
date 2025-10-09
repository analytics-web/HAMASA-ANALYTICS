from pydantic import BaseModel
from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from .base import Base


# ------------------- ENUMS ------------------------------------------ #
class UserRole(str, Enum):
    super_admin = "super_admin"
    reviewer = "reviewer"
    data_clerk = "data_clerk"
    org_admin = "org_admin"
    org_user = "org_user"

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"



class HamasaUser(Base):
    __tablename__ = "hamasa_users"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True,
        default=uuid.uuid4, 
        unique=True,
        nullable=False,
    )
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)   
    is_active = Column(Boolean, index=True, nullable=True, default=False)
    gender = Column(ENUM(Gender, name="gender", create_type=False), nullable=True, default=Gender.male)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(ENUM(UserRole, name="userrole", create_type=False), default=UserRole.org_user, nullable=False)

    client_assignments = relationship(
        "HamasaUserClientAssignment", back_populates="hamasa_user", cascade="all, delete-orphan"
    )



