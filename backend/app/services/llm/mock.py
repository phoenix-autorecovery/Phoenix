import json
import re
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
        
        # -------------------------------------------------------------
        # REPAIR PLAN GENERATION
        # -------------------------------------------------------------
        if "REPAIR_PLAN_SCHEMA" in prompt_text:
            # 1. SmartSentiment / test_app / database history bug
            if any(k in prompt_text for k in ["test_analyze_saves_history", "database/db.py", "db.py", "smartsentiment"]):
                return json.dumps({
                    "hypothesized_cause": "Database connection in database/db.py uses hardcoded smartsentiment.db path instead of checking Flask app config for test database override.",
                    "intended_behavior": "Dynamically inspect flask.current_app.config['DATABASE'] when inside an active Flask request context so tests execute against isolated test databases.",
                    "files_to_modify": ["database/db.py"],
                    "patch": "--- a/database/db.py\n+++ b/database/db.py\n@@ -8,3 +8,11 @@\n def get_db():\n     \"\"\"Return a sqlite3 connection with row_factory set.\"\"\"\n-    conn = sqlite3.connect(DB_PATH)\n+    db_path = DB_PATH\n+    try:\n+        from flask import current_app\n+        if current_app and current_app.config.get(\"DATABASE\"):\n+            db_path = current_app.config[\"DATABASE\"]\n+    except Exception:\n+        pass\n+    conn = sqlite3.connect(db_path)\n     conn.row_factory = sqlite3.Row\n",
                    "expected_test_outcomes": ["test_analyze_saves_history passes with isolated count of 1"],
                    "potential_side_effects": "None. Production behavior is unaffected when outside tests.",
                    "security_considerations": "Ensures clean test isolation and prevents cross-tenant test database contamination."
                })

            # 2. Buggy Demo 1: Swapped sentiment label map
            if "bug1.py" in prompt_text:
                return json.dumps({
                    "hypothesized_cause": "LABEL_MAP has indices 0 and 1 swapped, causing positive predictions to be reported as negative.",
                    "intended_behavior": "Map 0 to negative and 1 to positive so predictions align with trained weights.",
                    "files_to_modify": ["buggy_demo/bug1.py"],
                    "patch": "--- a/buggy_demo/bug1.py\n+++ b/buggy_demo/bug1.py\n@@ -12,2 +12,2 @@\n-LABEL_MAP = {0: \"positive\", 1: \"negative\"}\n+LABEL_MAP = {0: \"negative\", 1: \"positive\"}\n",
                    "expected_test_outcomes": ["run_test() passes successfully"],
                    "potential_side_effects": "None.",
                    "security_considerations": "Fixes sentiment classification accuracy."
                })

            # 3. Buggy Demo 2: Text preprocessing removes all lowercase letters
            if "bug2.py" in prompt_text:
                return json.dumps({
                    "hypothesized_cause": "re.sub(r'[a-z]', '', text) deletes all lowercase characters instead of non-letter characters.",
                    "intended_behavior": "Replace non-letter characters with whitespace while preserving lowercase text.",
                    "files_to_modify": ["buggy_demo/bug2.py"],
                    "patch": "--- a/buggy_demo/bug2.py\n+++ b/buggy_demo/bug2.py\n@@ -14,2 +14,2 @@\n-    text = re.sub(r'[a-z]', '', text)\n+    text = re.sub(r'[^a-zA-Z\\s]', '', text)\n",
                    "expected_test_outcomes": ["run_test() passes"],
                    "potential_side_effects": "None.",
                    "security_considerations": "Safe input normalization."
                })

            # 4. Buggy Demo 3: Percentage scaled by 10000
            if "bug3.py" in prompt_text:
                return json.dumps({
                    "hypothesized_cause": "Probabilities multiplied by 10000 instead of 100 for percentage representation.",
                    "intended_behavior": "Multiply by 100 to yield true percentages between 0 and 100.",
                    "files_to_modify": ["buggy_demo/bug3.py"],
                    "patch": "--- a/buggy_demo/bug3.py\n+++ b/buggy_demo/bug3.py\n@@ -10,2 +10,2 @@\n-    return round(float(max_prob) * 10000, 2)\n+    return round(float(max_prob) * 100, 2)\n",
                    "expected_test_outcomes": ["run_test() passes"],
                    "potential_side_effects": "None.",
                    "security_considerations": "Prevents numeric overflow."
                })

            # 5. Buggy Demo 4: Route spelling mismatch
            if "bug4.py" in prompt_text:
                return json.dumps({
                    "hypothesized_cause": "Flask route registered as /api/analyse while client calls /api/analyze.",
                    "intended_behavior": "Register endpoint as /api/analyze to match API contracts.",
                    "files_to_modify": ["buggy_demo/bug4.py"],
                    "patch": "--- a/buggy_demo/bug4.py\n+++ b/buggy_demo/bug4.py\n@@ -14,2 +14,2 @@\n-@app.route('/api/analyse', methods=['POST'])\n+@app.route('/api/analyze', methods=['POST'])\n",
                    "expected_test_outcomes": ["run_test() returns 200 OK"],
                    "potential_side_effects": "None.",
                    "security_considerations": "Restores API availability."
                })

            # 6. Buggy Demo 5: Hardcoded user_id=1
            if "bug5.py" in prompt_text:
                return json.dumps({
                    "hypothesized_cause": "SQL query uses hardcoded WHERE user_id = 1 instead of parameterized user_id argument.",
                    "intended_behavior": "Filter history dynamically by the provided user_id argument.",
                    "files_to_modify": ["buggy_demo/bug5.py"],
                    "patch": "--- a/buggy_demo/bug5.py\n+++ b/buggy_demo/bug5.py\n@@ -20,2 +20,2 @@\n-    cur.execute(\"SELECT * FROM analysis_history WHERE user_id = 1 ORDER BY created_at DESC\")\n+    cur.execute(\"SELECT * FROM analysis_history WHERE user_id = ? ORDER BY created_at DESC\", (user_id,))\n",
                    "expected_test_outcomes": ["run_test() retrieves correct user history"],
                    "potential_side_effects": "None.",
                    "security_considerations": "Prevents unauthorized data disclosure across users."
                })

            # 7. Default Calculator Fallback
            return json.dumps({
                "hypothesized_cause": "Unhandled None argument in calculate_total causes TypeError.",
                "intended_behavior": "Gracefully treat None or empty input as 0.0 total.",
                "files_to_modify": ["calculator.py"],
                "patch": "--- a/calculator.py\n+++ b/calculator.py\n@@ -1,4 +1,6 @@\n def calculate_total(items):\n+    if items is None:\n+        items = []\n     total = 0\n     for item in items:\n",
                "expected_test_outcomes": ["test_calculate_total_none passes without TypeError"],
                "potential_side_effects": "None. Input signature and valid outputs remain unchanged.",
                "security_considerations": "Prevents denial-of-service crash via unhandled input."
            })

        # -------------------------------------------------------------
        # DIAGNOSIS SCHEMA GENERATION
        # -------------------------------------------------------------
        if any(k in prompt_text for k in ["test_analyze_saves_history", "database/db.py", "db.py", "smartsentiment"]):
            return json.dumps({
                "root_cause_hypothesis": "The get_db() function in database/db.py connects to smartsentiment.db directly instead of inspecting Flask config['DATABASE'], causing test runs to share state and fail history assertions.",
                "confidence_score": 0.94,
                "evidence": [
                    {"type": "stack_trace", "observation": "AssertionError: Expected 1 history item, got 3 in test_analyze_saves_history"},
                    {"type": "code_inspection", "observation": "DB_PATH is hardcoded to smartsentiment.db without checking test database override in current_app.config."}
                ],
                "relevant_files": [
                    {"path": "database/db.py", "lines": [8, 12], "reason": "Connection initialization lacks dynamic Flask config check"}
                ],
                "suggested_action": "Modify get_db() to check current_app.config['DATABASE'] if active, defaulting to DB_PATH.",
                "is_repair_safe": True
            })

        if "bug1.py" in prompt_text:
            return json.dumps({
                "root_cause_hypothesis": "LABEL_MAP in buggy_demo/bug1.py maps index 0 to 'positive' and 1 to 'negative', inverting all sentiment classifications.",
                "confidence_score": 0.96,
                "evidence": [
                    {"type": "code_inspection", "observation": "LABEL_MAP has inverted dictionary values {0: 'positive', 1: 'negative'}"}
                ],
                "relevant_files": [
                    {"path": "buggy_demo/bug1.py", "lines": [12, 13], "reason": "Inverted LABEL_MAP dictionary mapping"}
                ],
                "suggested_action": "Swap dictionary values in LABEL_MAP so 0 maps to 'negative' and 1 maps to 'positive'.",
                "is_repair_safe": True
            })

        # Fallback Diagnosis
        return json.dumps({
            "root_cause_hypothesis": "Automated inspection identified an unhandled boundary condition in the execution flow.",
            "confidence_score": 0.90,
            "evidence": [
                {"type": "stack_trace", "observation": "Uncaught exception or test assertion failure encountered during automated execution."}
            ],
            "relevant_files": [
                {"path": "calculator.py", "lines": [1, 5], "reason": "Defensive input validation required"}
            ],
            "suggested_action": "Apply defensive parameter validation and handle None/empty inputs gracefully.",
            "is_repair_safe": True
        })
