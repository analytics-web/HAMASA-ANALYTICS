from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from api import auth, client, project
from db import engine
from api import hamasa_user
from models.base import Base
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from contextlib import asynccontextmanager
import logging
# from sentry_sdk.integrations.fastapi import FastAPIIntegration


logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# sentry_sdk.init(
#     dsn=os.getenv("SENTRY_DSN"),
#     integrations=[FastAPIIntegration()],
#     traces_sample_rate=1.0
# )


origins = ["*"]




app = FastAPI(
    title= "Hamasa Analytics",
    description="Hamasa Analytics Backend Apis",
    version="1.0",
    openapi_tags=[
        {"name": "Auth", "description":"Authentication and user management"}
    ],
    extra={
        "security": [
            {"BearerAuth":[]}
        ]
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],         # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],         # Allow all headers
)

@app.on_event("startup")
async def startup_event():
    # Initialize Redis connection
    redis_connection = redis.from_url(
        "redis://localhost:6379/0",
        encoding="utf-8",
        decode_responses=True
    )
    # Initialize FastAPILimiter
    await FastAPILimiter.init(redis_connection)

@app.on_event("shutdown")
async def shutdown_event():
    # Close Redis connection
    await FastAPILimiter.close()

@app.get("/")
def root():
    return {"message": "Api is running"}


app.include_router(auth.router, prefix="/hamasa-api/v1", tags=["Auth"])
app.include_router(client.router, prefix="/hamasa-api/v1", tags=["Clients"])
app.include_router(hamasa_user.router, prefix="/hamasa-api/v1", tags=["Users"])
app.include_router(project.router, prefix="/hamasa-api/v1", tags=["Projects"])