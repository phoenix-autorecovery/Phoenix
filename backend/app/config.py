import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "PHOENIX Autonomous Software Recovery Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security & Auth
    SECRET_KEY: str = "phoenix-super-secret-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'phoenix.db'}"
    
    # Workspace & Storage Paths
    STORAGE_DIR: Path = BASE_DIR / "data" / "storage"
    WORKSPACES_DIR: Path = BASE_DIR / "data" / "workspaces"
    SANDBOX_DIR: Path = BASE_DIR / "data" / "sandboxes"
    ARTIFACTS_DIR: Path = BASE_DIR / "data" / "artifacts"
    
    # Ingestion Limits
    MAX_ARCHIVE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_UNCOMPRESSED_SIZE_BYTES: int = 250 * 1024 * 1024  # 250 MB
    MAX_FILE_COUNT: int = 15000
    
    # Sandbox Execution Limits
    SANDBOX_TIMEOUT_SECONDS: int = 60
    SANDBOX_MAX_MEMORY_MB: int = 1024
    SANDBOX_NETWORK_ISOLATED: bool = True
    DOCKER_AVAILABLE: bool = False
    
    # Groq / LLM Settings
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_PROVIDER: str = "groq"
    LLM_TIMEOUT_SECONDS: int = 45
    LLM_MAX_RETRIES: int = 3
    
    # GitHub Integration
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_APP_ID: Optional[str] = None
    GITHUB_APP_PRIVATE_KEY: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure critical data directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
settings.SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
