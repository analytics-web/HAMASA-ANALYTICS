import uuid
from sqlalchemy import JSON, UUID, Column, DateTime, ForeignKey, Integer, func
from models.base import Base
from sqlalchemy.orm import relationship


class MLAnalysisResult(Base):
    __tablename__ = "ml_analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    row_number = Column(Integer, nullable=False)     # order of the row
    data = Column(JSON, nullable=False)              # entire CSV row as dict
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="ml_results")






