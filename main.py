from fastapi import FastAPI, Request
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
from fastapi.openapi.utils import get_openapi
# from sentry_sdk.integrations.fastapi import FastAPIIntegration


logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



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


# Middleware to log requests for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request: {request.method} {request.url} Headers: {request.headers}")
    response = await call_next(request)
    return response

# Custom OpenAPI schema for Bearer token
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    # Apply BearerAuth only to specific routes (optional; remove for global)
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if path not in ["/hamasa-api/v1/auth/login", "/hamasa-api/v1/auth/refresh-token"]:  # Public endpoints
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


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
app.include_router(hamasa_user.router, prefix="/hamasa-api/v1", tags=["Hamasa Users"])
app.include_router(project.router, prefix="/hamasa-api/v1", tags=["Projects"])