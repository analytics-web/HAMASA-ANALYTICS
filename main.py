from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from api import auth, client, client_user, project, project_categories, project_collaborators, project_media_categories, project_media_sources, project_ml, project_report_avenues, project_report_consultations, project_report_times, project_thematic_areas
from db import engine
from api import hamasa_user
from db.db import SessionLocal
from models.base import Base
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from contextlib import asynccontextmanager
import logging
from fastapi.openapi.utils import get_openapi

from utils.project_helpers import seed_report_consultations, seed_report_times
# from sentry_sdk.integrations.fastapi import FastAPIIntegration


logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



origins = ["*"]




app = FastAPI(
    title= "Hamasa Analytics",
    description="Hamasa Analytics Backend Apis",
    version="1.1.0",
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
    allow_methods=["*"],         
    allow_headers=["*"],         
)

@app.on_event("startup")
async def startup_event():
    # Initialize Redis connection
    redis_connection = redis.from_url(
        "redis://localhost:6379/0",
        encoding="utf-8",
        decode_responses=True
    )

    db = SessionLocal()
    seed_report_times(db)
    seed_report_consultations(db)
    db.close()
    # Initialize FastAPILimiter
    await FastAPILimiter.init(redis_connection)

@app.on_event("shutdown")
async def shutdown_event():
    # Close Redis connection
    await FastAPILimiter.close()

# @app.get("/")
# def root():
#     return {"message": "Api is running"}


app.include_router(auth.router, prefix="/hamasa-api/v1", tags=["Auth"])
app.include_router(client.router, prefix="/hamasa-api/v1", tags=["Clients"])
app.include_router(client_user.router, prefix="/hamasa-api/v1", tags=["Client Users "])
app.include_router(hamasa_user.router, prefix="/hamasa-api/v1", tags=["Hamasa Users"])
app.include_router(project_categories.router, prefix="/hamasa-api/v1", tags=["Project Categories"])
# app.include_router(project_thematic_areas.router, prefix="/hamasa-api/v1", tags=["Project Thematic Areas"])
app.include_router(project_media_categories.router, prefix="/hamasa-api/v1", tags=["Project Media Categories"])
app.include_router(project_media_sources.router, prefix="/hamasa-api/v1", tags=["Project Media Sources"])
# app.include_router(project_report_avenues.router, prefix="/hamasa-api/v1", tags=["Project Report Avenues"])
# app.include_router(project_report_times.router, prefix="/hamasa-api/v1", tags=["Projects Report Times"])
# app.include_router(project_report_consultations.router, prefix="/hamasa-api/v1", tags=["Project Report Consultations"])
app.include_router(project_collaborators.router, prefix="/hamasa-api/v1", tags=["Project Collaborators"])
app.include_router(project_ml.router, prefix="/hamasa-api/v1", tags=["Project Machine Learning"])
app.include_router(project.router, prefix="/hamasa-api/v1", tags=["Projects"])
