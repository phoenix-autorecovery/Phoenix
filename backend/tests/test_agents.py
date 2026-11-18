"""
Autonomous Multi-Agent Runtime & Specialized Agents Tests
"""
import pytest
from fastapi import status
from backend.app.services.agents.base import AgentContext
from backend.app.services.agents.security_agent import SecurityAgent
from backend.app.models.repair import CandidatePatch


def test_list_specialized_agents(client, dev_token):
    """Test listing available autonomous agents."""
    res = client.get("/api/v1/agents/list")
    assert res.status_code == status.HTTP_200_OK
    agents = res.json()
    assert len(agents) == 6
    agent_ids = [a["id"] for a in agents]
    assert "intelligence" in agent_ids
    assert "diagnosis" in agent_ids
    assert "repair" in agent_ids
    assert "testing" in agent_ids
    assert "security" in agent_ids
    assert "review" in agent_ids


@pytest.mark.asyncio
async def test_security_agent_veto_on_dangerous_injection():
    """Verify that SecurityAgent detects dangerous patterns and triggers a veto."""
    sec_agent = SecurityAgent()
    context = AgentContext(
        project_id="p-1",
        incident_id="i-1",
        job_id="j-1"
    )

    # Malicious candidate diff with eval and os.system
    malicious_diff = """--- a/billing.py
+++ b/billing.py
@@ -10,3 +10,4 @@
 def calculate():
+    eval("__import__('os').system('rm -rf /')")
     return 42
"""
    class MockPatch:
        diff_content = malicious_diff

    context.state["patch"] = MockPatch()
    result = await sec_agent.run(context, db_session=None)

    assert result["security_cleared"] is False
    assert result["security_veto"] is True
    assert result["risk_score"] > 50
    assert len(result["security_findings"]) >= 1


@pytest.mark.asyncio
async def test_security_agent_passes_clean_diff():
    """Verify that SecurityAgent clears benign diff."""
    sec_agent = SecurityAgent()
    context = AgentContext(
        project_id="p-1",
        incident_id="i-1",
        job_id="j-1"
    )

    clean_diff = """--- a/billing.py
+++ b/billing.py
@@ -10,3 +10,4 @@
 def calculate(items=None):
+    if items is None:
+        items = []
     return sum(items)
"""
    class MockPatch:
        diff_content = clean_diff

    context.state["patch"] = MockPatch()
    result = await sec_agent.run(context, db_session=None)

    assert result["security_cleared"] is True
    assert result["security_veto"] is False
    assert result["risk_score"] == 0


def test_multi_agent_execution_and_timeline(client, dev_token, sample_buggy_zip):
    """Test launching the multi-agent runtime on a buggy project and querying its timeline."""
    # 1. Ingest buggy project
    ingest_res = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Multi-Agent Test Project"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    assert ingest_res.status_code == status.HTTP_200_OK
    project_id = ingest_res.json()["id"]

    # 2. Trigger automated scan to detect defect
    scan_res = client.post(
        f"/api/v1/projects/{project_id}/scan",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert scan_res.status_code == status.HTTP_200_OK
    defects = scan_res.json()["defects"]
    assert len(defects) > 0

    # 3. Create incident for defect
    inc_res = client.post(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={
            "project_id": project_id,
            "title": defects[0]["title"],
            "description": "Multi-agent runtime test",
            "stack_trace": defects[0]["stack_trace"],
            "raw_log": defects[0]["raw_log"],
            "severity": defects[0]["severity"]
        }
    )
    assert inc_res.status_code == status.HTTP_200_OK
    incident_id = inc_res.json()["id"]

    # 4. Run Multi-Agent Recovery
    run_res = client.post(
        "/api/v1/agents/run",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={
            "project_id": project_id,
            "incident_id": incident_id,
            "model_name": "llama-3.1-70b-versatile"
        }
    )
    assert run_res.status_code == status.HTTP_200_OK
    run_data = run_res.json()
    job_id = run_data["job_id"]
    assert "status" in run_data
    assert "verdict" in run_data
    assert len(run_data["events"]) >= 6

    # 5. Fetch timeline
    timeline_res = client.get(f"/api/v1/agents/timeline/{job_id}")
    assert timeline_res.status_code == status.HTTP_200_OK
    events = timeline_res.json()["events"]
    assert len(events) >= 6
    agent_names = [e["agent_name"] for e in events]
    assert "ProjectIntelligenceAgent" in agent_names
    assert "DiagnosisAgent" in agent_names
    assert "RepairAgent" in agent_names
    assert "TestingAgent" in agent_names
    assert "SecurityAgent" in agent_names
    assert "ReviewAgent" in agent_names
