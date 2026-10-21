from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LLMProvider(ABC):
    @abstractmethod
    def generate_chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        """Generates a text completion given chat messages."""
        pass

    @abstractmethod
    def check_capabilities(self) -> Dict[str, Any]:
        """Verifies connection and active model support."""
        pass
