import json
from typing import Dict, Any, List
from backend.app.config import settings
from backend.app.services.llm.base import LLMProvider

class MockLLMProvider(LLMProvider):
    def __init__(self, model: str = None):
        self.model = model or settings.GROQ_MODEL

    def check_capabilities(self) -> Dict[str, Any]:
        return {
            "available": True,
            "active_model": self.model,
            "model_in_catalogue": True,
            "models": settings.SUPPORTED_GROQ_MODELS
        }

    def generate_chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        prompt_text = " ".join([m.get("content", "") for m in messages])
        
        # If prompt is asking for repair plan / patch
        if "REPAIR_PLAN_SCHEMA" in prompt_text:
            return json.dumps({
                "hypothesized_cause": "Unhandled None argument in calculate_total causes TypeError.",
                "intended_behavior": "Gracefully treat None or empty input as 0.0 total.",
                "files_to_modify": ["calculator.py"],
                "patch": "--- a/calculator.py\n+++ b/calculator.py\n@@ -1,4 +1,6 @@\n def calculate_total(items):\n+    if items is None:\n+        items = []\n     total = 0\n     for item in items:\n",
                "expected_test_outcomes": ["test_calculate_total_none passes without TypeError"],
                "potential_side_effects": "None. Input signature and valid outputs remain unchanged.",
                "security_considerations": "Prevents denial-of-service crash via unhandled input."
            })

        # Otherwise diagnosis schema
        return json.dumps({
            "root_cause_hypothesis": "The calculate_total function crashes when items is None or empty due to an unhandled TypeError during iteration.",
            "confidence_score": 0.92,
            "evidence": [
                {"type": "stack_trace", "observation": "TypeError: 'NoneType' object is not iterable at calculator.py:3"},
                {"type": "code_inspection", "observation": "Missing default empty list or defensive None check before loop."}
            ],
            "relevant_files": [
                {"path": "calculator.py", "lines": [1, 5], "reason": "Function definition and unhandled iteration"}
            ],
            "suggested_action": "Add defensive check 'if items is None: items = []' before the loop.",
            "is_repair_safe": True
        })
