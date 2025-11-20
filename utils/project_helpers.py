
from sqlalchemy.orm import Session

from models.project import MediaCategory
from schemas.project import *



def get_category_by_name(db: Session, category_enum: ProjectMediaCategory):
    return db.query(MediaCategory).filter(
        MediaCategory.name.ilike(category_enum.value),
        MediaCategory.is_deleted == False
    ).first()
