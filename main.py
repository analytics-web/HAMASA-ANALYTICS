from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from api import auth, client, client_user, project, project_categories, project_collaborators, project_media_categories, project_media_sources, project_ml, project_report, project_report_avenues, project_report_consultations, project_report_times, dashboard
from api import hamasa_user
from db.db import SessionLocal
from models.base import Base
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
import logging
from fastapi.openapi.utils import get_openapi


from utils.project_helpers import seed_report_consultations, seed_report_times


logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

origins = ["*"]

# ✔ Docs & OpenAPI under /api/*
app = FastAPI(
    title="Hamasa Analytics",
    description="Hamasa Analytics Backend APIs",
    version="1.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication and user management"}
    ],
)


# ✔ Request logger middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request: {request.method} {request.url} Headers: {request.headers}")
    response = await call_next(request)
    return response


# ✔ Custom OpenAPI security schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["servers"] = [{"url": "/api"}]

    # JWT security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Apply Bearer auth (except login & refresh)
    public_paths = [
        "/hamasa-api/v1/auth/login",
        "/hamasa-api/v1/auth/refresh-token"
    ]

    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if path not in public_paths:
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ✔ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✔ Startup: redis + seeding + rate limiter
@app.on_event("startup")
async def startup_event():
    redis_connection = redis.from_url(
        "redis://localhost:6379/0",
        encoding="utf-8",
        decode_responses=True
    )

    db = SessionLocal()
    seed_report_times(db)
    seed_report_consultations(db)
    db.close()

    await FastAPILimiter.init(redis_connection)


@app.on_event("shutdown")
async def shutdown_event():
    await FastAPILimiter.close()


# ✔ Routers
app.include_router(auth.router, prefix="/hamasa-api/v1", tags=["Auth"])
app.include_router(client.router, prefix="/hamasa-api/v1", tags=["Clients"])
app.include_router(client_user.router, prefix="/hamasa-api/v1", tags=["Client Users"])
app.include_router(hamasa_user.router, prefix="/hamasa-api/v1", tags=["Hamasa Users"])
app.include_router(project_categories.router, prefix="/hamasa-api/v1", tags=["Project Categories"])
app.include_router(project_media_categories.router, prefix="/hamasa-api/v1", tags=["Project Media Categories"])
app.include_router(project_media_sources.router, prefix="/hamasa-api/v1", tags=["Project Media Sources"])
app.include_router(project_collaborators.router, prefix="/hamasa-api/v1", tags=["Project Collaborators"])
app.include_router(project_report_avenues.router, prefix="/hamasa-api/v1", tags=["Project Report Avenues"])
app.include_router(project_report_times.router, prefix="/hamasa-api/v1", tags=["Project Report Times"])
app.include_router(project_report_consultations.router, prefix="/hamasa-api/v1", tags=["Project Report Consultations"])
app.include_router(project_ml.router, prefix="/hamasa-api/v1", tags=["Project Machine Learning"])
app.include_router(project.router, prefix="/hamasa-api/v1", tags=["Projects"])
app.include_router(project_report.router, prefix="/hamasa-api/v1", tags=["Project Reports"])
app.include_router(dashboard.router, prefix="/hamasa-api/v1", tags=["Dashboard"])

