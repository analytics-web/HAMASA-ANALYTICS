# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# from dotenv import load_dotenv
# import os
# from sqlalchemy.engine import make_url

# load_dotenv()


# DATABASE_URL = os.getenv("DATABASE_URL")

# url = make_url(DATABASE_URL)
# print(url.render_as_string(hide_password=True))

# if not DATABASE_URL:
#     raise ValueError("DATABASE_URL not found in .env file")
# engine = create_engine(DATABASE_URL, echo=False)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()



from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from dotenv import load_dotenv
import logging
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
APP_ENV = os.getenv("APP_ENV", "development")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

# Safe DB URL for logging
url = make_url(DATABASE_URL)

if APP_ENV == "development":
    engine = create_engine(DATABASE_URL, echo=True)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.info(f"🔧 [DEV] Connecting to DB: {url.render_as_string(hide_password=True)}")
else:
    engine = create_engine(DATABASE_URL, echo=False)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.info(f"🚀 [PROD] Connecting to DB: {url.render_as_string(hide_password=True)}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
