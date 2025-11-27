import uuid
from sqlalchemy import UUID, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from models.base import Base
from models.enums import ProjectStatus
from sqlalchemy.orm import relationship


class ProjectProgress(Base):
    __tablename__ = "project_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    stage_no = Column(Integer, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("hamasa_users.id"), nullable=False)

    previous_status = Column(Enum(ProjectStatus), nullable=True)
    current_status = Column(Enum(ProjectStatus), nullable=False)

    action = Column(String(255))
    comment = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="project_progress")
