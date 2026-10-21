from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.audit import SystemSetting
from backend.app.schemas.settings import SystemSettingsUpdate, SystemSettingsResponse
from backend.app.core.security import require_roles, get_current_user
from backend.app.core.audit import record_audit_event
from backend.app.services.llm.groq import GroqProvider

router = APIRouter(prefix="/settings", tags=["System Settings"])

@router.get("", response_model=SystemSettingsResponse)
def get_settings(current_user: User = Depends(get_current_user)):
    groq_provider = GroqProvider()
    caps = groq_provider.check_capabilities()

    return {
        "groq_configured": bool(settings.GROQ_API_KEY),
        "groq_model": settings.GROQ_MODEL,
        "github_configured": bool(settings.GITHUB_TOKEN),
        "sandbox_timeout_seconds": settings.SANDBOX_TIMEOUT_SECONDS,
        "sandbox_network_isolated": settings.SANDBOX_NETWORK_ISOLATED,
        "docker_available": settings.DOCKER_AVAILABLE,
        "available_models": caps.get("models", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"])
    }

@router.post("", response_model=SystemSettingsResponse)
def update_settings(
    update_in: SystemSettingsUpdate,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    if update_in.groq_api_key is not None:
        settings.GROQ_API_KEY = update_in.groq_api_key.strip() or None
        _upsert_setting(db, "GROQ_API_KEY", settings.GROQ_API_KEY, is_secret="true")

    if update_in.groq_model is not None:
        settings.GROQ_MODEL = update_in.groq_model.strip()
        _upsert_setting(db, "GROQ_MODEL", settings.GROQ_MODEL, is_secret="false")

    if update_in.github_token is not None:
        settings.GITHUB_TOKEN = update_in.github_token.strip() or None
        _upsert_setting(db, "GITHUB_TOKEN", settings.GITHUB_TOKEN, is_secret="true")

    if update_in.sandbox_timeout_seconds is not None:
        settings.SANDBOX_TIMEOUT_SECONDS = update_in.sandbox_timeout_seconds
        _upsert_setting(db, "SANDBOX_TIMEOUT_SECONDS", str(settings.SANDBOX_TIMEOUT_SECONDS), is_secret="false")

    if update_in.sandbox_network_isolated is not None:
        settings.SANDBOX_NETWORK_ISOLATED = update_in.sandbox_network_isolated
        _upsert_setting(db, "SANDBOX_NETWORK_ISOLATED", str(settings.SANDBOX_NETWORK_ISOLATED), is_secret="false")

    record_audit_event(
        db=db,
        action="settings.updated",
        resource_type="system",
        user_id=current_user.id,
        details={"groq_model": settings.GROQ_MODEL, "timeout": settings.SANDBOX_TIMEOUT_SECONDS}
    )

    return get_settings(current_user=current_user)

def _upsert_setting(db: Session, key: str, value: str, is_secret: str = "false"):
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row:
        row = SystemSetting(key=key, value=value, is_secret=is_secret)
        db.add(row)
    else:
        row.value = value
        row.is_secret = is_secret
    db.commit()
