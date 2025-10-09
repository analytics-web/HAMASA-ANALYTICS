from enum import Enum
from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM
from sqlalchemy.orm import relationship
import uuid
from models.base import Base


class ClientUser(Base):
    __tablename__ = "client_users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("client.id", ondelete="CASCADE"),
        nullable=False
    )
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=True)  # optional: client-specific roles

    # Relationship
    client = relationship("Client", back_populates="users")
    
    projects = relationship(
        "Project",
        secondary="project_collaborators",
        back_populates="collaborators"
    )