import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.session import engine, Base
import app.models  # Ensure all models are registered

from sqlalchemy import inspect, text

def auto_migrate_schema(engine):
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        with engine.connect() as conn:
            for table in tables:
                columns = [c["name"] for c in inspector.get_columns(table)]
                if "placement_session_id" not in columns and table not in ["alembic_version"]:
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN placement_session_id VARCHAR(36)"))
                        conn.commit()
                        print(f"Auto-migrated {table}: added placement_session_id column.")
                    except Exception as e:
                        print(f"Migration note for {table}: {e}")
    except Exception as exc:
        print(f"Auto-migration warning: {exc}")

# Create tables and auto-migrate existing tables on startup
Base.metadata.create_all(bind=engine)
auto_migrate_schema(engine)

# Ensure default placement session exists and bind unassigned records
from app.db.session import SessionLocal
from app.api.deps import get_or_create_active_session
with SessionLocal() as _db:
    try:
        active_sess = get_or_create_active_session(_db)
        sid = active_sess.id
        with engine.connect() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            for t in tables:
                cols = [c["name"] for c in inspector.get_columns(t)]
                if "placement_session_id" in cols:
                    try:
                        conn.execute(text(f"UPDATE {t} SET placement_session_id = :sid WHERE placement_session_id IS NULL OR placement_session_id = ''"), {"sid": sid})
                        conn.commit()
                    except Exception:
                        pass
    except Exception as e:
        print(f"Session init warning: {e}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("placement_control_tower")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Deterministic Live Placement Operations & Minimal-Disruption Control Tower with AI Copilot.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"(http://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.students import router as students_router
from app.api.v1.companies import router as companies_router
from app.api.v1.rooms import router as rooms_router
from app.api.v1.panels import router as panels_router
from app.api.v1.shortlists import router as shortlists_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.conflicts import router as conflicts_router
from app.api.v1.disruptions import router as disruptions_router
from app.api.v1.replanning import router as replanning_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.ai import router as ai_router
from app.api.v1.documents import router as documents_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.websockets import router as websockets_router
from app.api.v1.operations import router as operations_router

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(students_router, prefix=settings.API_V1_STR)
app.include_router(companies_router, prefix=settings.API_V1_STR)
app.include_router(rooms_router, prefix=settings.API_V1_STR)
app.include_router(panels_router, prefix=settings.API_V1_STR)
app.include_router(shortlists_router, prefix=settings.API_V1_STR)
app.include_router(schedule_router, prefix=settings.API_V1_STR)
app.include_router(conflicts_router, prefix=settings.API_V1_STR)
app.include_router(disruptions_router, prefix=settings.API_V1_STR)
app.include_router(replanning_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(interviews_router, prefix=settings.API_V1_STR)
app.include_router(operations_router, prefix=settings.API_V1_STR)
app.include_router(websockets_router)

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}

@app.get("/", tags=["system"])
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.method} {request.url}: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response
