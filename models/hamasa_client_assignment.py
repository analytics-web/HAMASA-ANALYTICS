from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM
from sqlalchemy.orm import relationship
import uuid
from models.base import Base




class HamasaUserClientAssignment(Base):
    __tablename__ = "hamasa_user_client_assignments"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True,
        default=uuid.uuid4, 
        unique=True,
        nullable=False,
    )

    hamasa_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("hamasa_users.id", ondelete="CASCADE"),
        nullable=False
    )

    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("client.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Ensure a user cannot be assigned to the same client more than once
    __table_args__ = (
        UniqueConstraint("hamasa_user_id", "client_id", name="uq_hamasa_user_client"),
    )

    # Relationships
    hamasa_user = relationship("HamasaUser", back_populates="client_assignments")
    client = relationship("Client", back_populates="hamasa_assignments")
