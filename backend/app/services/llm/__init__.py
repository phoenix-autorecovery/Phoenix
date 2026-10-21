import os
from backend.app.config import settings
from backend.app.services.llm.base import LLMProvider
from backend.app.services.llm.groq import GroqProvider
from backend.app.services.llm.mock import MockLLMProvider

def get_llm_provider() -> LLMProvider:
    if settings.GROQ_API_KEY:
        return GroqProvider()
    return MockLLMProvider()

__all__ = ["LLMProvider", "GroqProvider", "MockLLMProvider", "get_llm_provider"]
