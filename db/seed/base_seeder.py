# db/seed/base_seeder.py
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class BaseSeeder:
    def __init__(self, db: Session):
        self.db = db

    def find_or_create(self, model, defaults=None, **filters):
        """
        Look up by `filters`. If not found, create with {**filters, **defaults}.
        - `filters`: columns used to uniquely identify the row (passed to filter_by).
        - `defaults`: extra fields set only when creating a new row.
        """
        instance = self.db.query(model).filter_by(**filters).first()
        if instance:
            return instance

        payload = {**(defaults or {}), **filters}
        instance = model(**payload)
        self.db.add(instance)
        try:
            # Commit is fine here; you can use flush() instead if you batch commits
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            # Try to fetch again in case a concurrent insert happened
            existing = self.db.query(model).filter_by(**filters).first()
            if existing:
                return existing
            raise
        else:
            self.db.refresh(instance)
        return instance
