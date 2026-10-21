import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.user import User
from backend.app.core.security import get_password_hash
from backend.app.api import auth, projects, ingestion, incidents, repairs, approvals, delivery, audit, settings as settings_api

# Configure root logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phoenix.main")

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-Grade Autonomous Software Recovery & Deterministic Verification Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health & Readiness checks
@app.get("/health", tags=["Observability"])
def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database": "connected"
    }

@app.get("/ready", tags=["Observability"])
def readiness_check():
    return {
        "status": "ready",
        "storage_ready": settings.STORAGE_DIR.exists(),
        "workspaces_ready": settings.WORKSPACES_DIR.exists(),
        "sandboxes_ready": settings.SANDBOX_DIR.exists()
    }

# Seed default accounts on startup
@app.on_event("startup")
def seed_default_accounts():
    db = SessionLocal()
    try:
        charan = db.query(User).filter(User.email == "charan@phoenix.io").first()
        if not charan:
            charan = User(
                email="charan@phoenix.io",
                hashed_password=get_password_hash("charan123"),
                full_name="Charan",
                role="admin"
            )
            db.add(charan)
            logger.info("Seeded administrator account: charan@phoenix.io")

        admin = db.query(User).filter(User.email == "admin@phoenix.io").first()
        if not admin:
            admin = User(
                email="admin@phoenix.io",
                hashed_password=get_password_hash("phoenix123"),
                full_name="PHOENIX Administrator",
                role="admin"
            )
            db.add(admin)
            logger.info("Seeded default admin account: admin@phoenix.io")

        dev = db.query(User).filter(User.email == "developer@phoenix.io").first()
        if not dev:
            dev = User(
                email="developer@phoenix.io",
                hashed_password=get_password_hash("phoenix123"),
                full_name="Phoenix Developer",
                role="developer"
            )
            db.add(dev)
            logger.info("Seeded default developer account: developer@phoenix.io")

        db.commit()
    finally:
        db.close()

# Mount API routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(ingestion.router, prefix=settings.API_V1_STR)
app.include_router(incidents.router, prefix=settings.API_V1_STR)
app.include_router(repairs.router, prefix=settings.API_V1_STR)
app.include_router(approvals.router, prefix=settings.API_V1_STR)
app.include_router(delivery.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(settings_api.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
