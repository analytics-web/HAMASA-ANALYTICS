from click import DateTime
from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Table, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from .base import Base


class Client(Base):
    __tablename__ = "client"


    id = Column(
        UUID(as_uuid=True), 
        primary_key=True,
        default=uuid.uuid4, 
        unique=True,
        nullable=False,
    )
    name_of_organisation = Column(
        String, index=True, nullable=False
    )
    country = Column(
        String, index=True, nullable=False 
    )
    contact_person = Column(
        String, index=True, nullable=False
    )  
    phone_number = Column(
        String, index=True, nullable=False
    )
    email = Column(
        String, index=True, nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)   

    hamasa_assignments = relationship(
        "HamasaUserClientAssignment", back_populates="client", cascade="all, delete-orphan"
    )
    users = relationship("ClientUser", back_populates="client", cascade="all, delete-orphan")

    projects = relationship(
        "Project",
        back_populates="client",
        cascade="all, delete-orphan"
    )