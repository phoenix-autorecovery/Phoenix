import logging
import httpx
from typing import Dict, Any, List
from backend.app.config import settings
from backend.app.services.llm.base import LLMProvider

logger = logging.getLogger("phoenix.llm.groq")

class GroqProvider(LLMProvider):
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self.max_retries = settings.LLM_MAX_RETRIES

    def check_capabilities(self) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "available": False,
                "error": "GROQ_API_KEY is not configured.",
                "active_model": self.model,
                "models": []
            }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if res.status_code == 200:
                    data = res.json()
                    model_ids = [m["id"] for m in data.get("data", [])]
                    model_valid = self.model in model_ids
                    return {
                        "available": True,
                        "active_model": self.model,
                        "model_in_catalogue": model_valid,
                        "models": model_ids
                    }
                else:
                    return {
                        "available": False,
                        "error": f"Groq API error ({res.status_code}): {res.text}",
                        "active_model": self.model,
                        "models": []
                    }
        except Exception as e:
            logger.error(f"Failed to query Groq models: {e}")
            return {
                "available": False,
                "error": str(e),
                "active_model": self.model,
                "models": []
            }

    def generate_chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        if not self.api_key:
            raise RuntimeError("Cannot invoke GroqProvider: GROQ_API_KEY is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        
        # Enable JSON object enforcement for supported models when requested in prompt
        prompt_text = " ".join([m.get("content", "") for m in messages]).lower()
        if "json" in prompt_text and any(m_family in self.model.lower() for m_family in ["llama-3", "qwen"]):
            payload["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text}"
                        logger.warning(f"Groq API attempt {attempt+1} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Groq API attempt {attempt+1} exception: {e}")

        raise RuntimeError(f"Groq API request failed after {self.max_retries} attempts: {last_error}")
