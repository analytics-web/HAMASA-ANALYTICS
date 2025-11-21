from sqlalchemy.dialects.postgresql import UUID, ARRAY, ENUM
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from .base import Base

# ------------------- ENUMS ------------------------------------------ #
class ProjectStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    review = "review"
    in_progress = "in_progress"
    active = "active"
    completed = "completed"
    archived = "archived"


class ProjectMediaCategory(str, Enum):
    social_media = "Social Media"
    radio = "Radio"
    tv = "TV"
    print_media = "Print Media"
    others = "Others"