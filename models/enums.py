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
    ml_service = "ml_service"


class ProjectReportStatus(str, Enum):
    unverfied = "Unverified"
    verified = "Verified"
    rejected = "Rejected"


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
    online_media = "Online Media"
    others = "Others"


class ProjectReportAVenues(str,Enum):
    web = "Web"
    mobile = "Mobile"
    

class ProjectReportTimes(str, Enum):
    daily = "Daily"
    weekly = "Weekly"
    monthly = "Monthly"
    quarterly = "Quarterly"
    bi_annually = "Bi-Annually"
    annually = "Annually"


class ProjectReportConsultations(str, Enum):
    daily = "Daily"
    weekly = "Weekly"
    monthly = "Monthly"
    quarterly = "Quarterly"
    bi_annually = "Bi-Annually"
    annually = "Annually"

