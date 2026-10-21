import io
import zipfile
from fastapi import status

def test_get_and_switch_models(client, admin_token):
    # 1. Get models
    res = client.get("/api/v1/settings/models", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "llama-3.1-70b-versatile" in data["supported_models"]
    assert "qwen-2.5-coder-32b" in data["supported_models"]

    # 2. Switch to Qwen
    switch_res = client.post(
        "/api/v1/settings/models",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"model": "qwen-2.5-coder-32b"}
    )
    assert switch_res.status_code == status.HTTP_200_OK
    assert switch_res.json()["active_model"] == "qwen-2.5-coder-32b"

    # 3. Switch to LLaMA 3.1
    switch_res2 = client.post(
        "/api/v1/settings/models",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"model": "llama-3.1-70b-versatile"}
    )
    assert switch_res2.status_code == status.HTTP_200_OK
    assert switch_res2.json()["active_model"] == "llama-3.1-70b-versatile"

def test_automated_scan_detects_test_failure(client, dev_token, sample_buggy_zip):
    # Ingest project with bug
    ingest_res = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "AutoPilot Test App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    project_id = ingest_res.json()["id"]

    # Automated scan
    scan_res = client.post(
        f"/api/v1/projects/{project_id}/scan",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert scan_res.status_code == status.HTTP_200_OK
    data = scan_res.json()
    assert data["status"] == "issues_detected"
    assert data["defects_count"] >= 1
    assert any("calculate_total" in d["stack_trace"] or "test_calc.py" in d["stack_trace"] for d in data["defects"])

def test_automated_scan_detects_syntax_error(client, dev_token):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("broken.py", "def broken_func(\n    print('unclosed paren'\n")
    buf.seek(0)

    ingest_res = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Syntax Error App"},
        files={"file": ("syntax.zip", buf.getvalue(), "application/zip")}
    )
    project_id = ingest_res.json()["id"]

    scan_res = client.post(
        f"/api/v1/projects/{project_id}/scan",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert scan_res.status_code == status.HTTP_200_OK
    data = scan_res.json()
    assert data["status"] == "issues_detected"
    assert any(d["type"] == "syntax_error" for d in data["defects"])

def test_full_autonomous_self_healing_cycle(client, dev_token, sample_buggy_zip):
    # Ingest project with bug
    ingest_res = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "AutoHeal Self-Repairing App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    project_id = ingest_res.json()["id"]

    # Trigger Autonomous Auto-Pilot
    pilot_res = client.post(
        f"/api/v1/projects/{project_id}/auto-pilot",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"auto_apply": True, "override_model": "qwen-2.5-coder-32b"}
    )
    assert pilot_res.status_code == status.HTTP_200_OK
    data = pilot_res.json()
    assert data["status"] == "healed"
    assert data["model_used"] == "qwen-2.5-coder-32b"
    assert data["workspace_modified"] is True
    assert "calculator.py" in data["patch_diff"]

    # Re-scan project workspace to confirm zero remaining defects
    post_scan = client.post(
        f"/api/v1/projects/{project_id}/scan",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert post_scan.status_code == status.HTTP_200_OK
    assert post_scan.json()["defects_count"] == 0
    assert post_scan.json()["status"] == "healthy"
