from typing import Optional, List
from pydantic import BaseModel

class SystemSettingsUpdate(BaseModel):
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    github_token: Optional[str] = None
    sandbox_timeout_seconds: Optional[int] = None
    sandbox_network_isolated: Optional[bool] = None

class SystemSettingsResponse(BaseModel):
    groq_configured: bool
    groq_model: str
    github_configured: bool
    sandbox_timeout_seconds: int
    sandbox_network_isolated: bool
    docker_available: bool
    available_models: List[str] = []
