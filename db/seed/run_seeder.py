# db/seed/run_seeder.py
import logging
from sqlalchemy.orm import Session
from ..db import SessionLocal                 # relative import from db/db.py
from .project_seeder import ProjectSeeder     # relative import in seed package

logging.basicConfig(level=logging.INFO)

def main():
    # SQLAlchemy 2.x style: context manager ensures close()
    with SessionLocal() as db:
        seeder = ProjectSeeder(db)
        seeder.seed(num_projects=5)

if __name__ == "__main__":
    main()
