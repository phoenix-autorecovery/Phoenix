from fastapi import status

def test_approval_cryptographic_binding(client, dev_token, sample_buggy_zip):
    # Setup project and repair
    ingest_resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Approval Security App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    project_id = ingest_resp.json()["id"]

    inc_resp = client.post(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"project_id": project_id, "title": "Test Defect"}
    )
    incident_id = inc_resp.json()["id"]

    client.post(f"/api/v1/incidents/{incident_id}/diagnose", headers={"Authorization": f"Bearer {dev_token}"})
    repair_resp = client.post("/api/v1/repairs", headers={"Authorization": f"Bearer {dev_token}"}, json={"incident_id": incident_id})
    repair_data = repair_resp.json()
    repair_id = repair_data["id"]
    correct_patch_hash = repair_data["patch_hash"]

    # Attempt approval with tampered patch hash -> must be rejected
    tampered_resp = client.post(
        f"/api/v1/approvals/{repair_id}/approve",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"patch_hash": "deadbeef1234567890abcdef1234567890abcdef1234567890abcdef12345678", "notes": "Hacked approval"}
    )
    assert tampered_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Integrity check failed" in tampered_resp.json()["detail"]

    # Approval with correct patch hash -> succeeds
    valid_resp = client.post(
        f"/api/v1/approvals/{repair_id}/approve",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"patch_hash": correct_patch_hash, "notes": "Verified candidate diff"}
    )
    assert valid_resp.status_code == status.HTTP_200_OK
    assert valid_resp.json()["status"] == "approved"

def test_cross_tenant_isolation(client, dev_token, other_token, sample_buggy_zip):
    # Dev User creates project
    ingest_resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Dev User Private Project"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    project_id = ingest_resp.json()["id"]

    # Other User attempts to access it -> must be rejected with 403 Forbidden
    other_resp = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert other_resp.status_code == status.HTTP_403_FORBIDDEN

def test_delivery_blocked_without_prior_approval(client, dev_token, sample_buggy_zip):
    # Setup project and repair
    ingest_resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Unapproved Delivery App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    project_id = ingest_resp.json()["id"]

    inc_resp = client.post(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"project_id": project_id, "title": "Crash Defect"}
    )
    incident_id = inc_resp.json()["id"]
    client.post(f"/api/v1/incidents/{incident_id}/diagnose", headers={"Authorization": f"Bearer {dev_token}"})
    repair_resp = client.post("/api/v1/repairs", headers={"Authorization": f"Bearer {dev_token}"}, json={"incident_id": incident_id})
    repair_id = repair_resp.json()["id"]

    # Attempt to trigger Pull Request without approval -> must fail
    pr_resp = client.post(
        f"/api/v1/repairs/{repair_id}/pull-request",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"title": "Premature PR"}
    )
    assert pr_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Explicit reviewer approval is required" in pr_resp.json()["detail"]

def test_auditor_permissions_and_restrictions(client, dev_token, auditor_token, sample_buggy_zip):
    # Dev creates project & repair
    ingest_resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Audited App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    assert ingest_resp.status_code == status.HTTP_200_OK
    project_id = ingest_resp.json()["id"]

    inc_resp = client.post(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"project_id": project_id, "title": "Auditor Visible Issue"}
    )
    incident_id = inc_resp.json()["id"]
    client.post(f"/api/v1/incidents/{incident_id}/diagnose", headers={"Authorization": f"Bearer {dev_token}"})
    repair_resp = client.post("/api/v1/repairs", headers={"Authorization": f"Bearer {dev_token}"}, json={"incident_id": incident_id})
    repair_id = repair_resp.json()["id"]
    patch_hash = repair_resp.json()["patch_hash"]

    # 1. Auditor CAN read projects, audit events, and metrics
    proj_resp = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {auditor_token}"})
    assert proj_resp.status_code == status.HTTP_200_OK

    audit_resp = client.get("/api/v1/audit-events", headers={"Authorization": f"Bearer {auditor_token}"})
    assert audit_resp.status_code == status.HTTP_200_OK

    metrics_resp = client.get("/api/v1/monitoring/metrics", headers={"Authorization": f"Bearer {auditor_token}"})
    assert metrics_resp.status_code == status.HTTP_200_OK

    # 2. Auditor CANNOT ingest new projects
    ingest_fail = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {auditor_token}"},
        data={"name": "Auditor Illegal App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    assert ingest_fail.status_code == status.HTTP_403_FORBIDDEN

    # 3. Auditor CANNOT approve candidate repairs
    approve_fail = client.post(
        f"/api/v1/approvals/{repair_id}/approve",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"patch_hash": patch_hash, "notes": "Auditor attempting approval"}
    )
    assert approve_fail.status_code == status.HTTP_403_FORBIDDEN

    # 4. Auditor CANNOT trigger repair generation
    repair_fail = client.post(
        "/api/v1/repairs",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"incident_id": incident_id}
    )
    assert repair_fail.status_code == status.HTTP_403_FORBIDDEN

def test_reviewer_permissions_and_restrictions(client, dev_token, reviewer_token, sample_buggy_zip):
    # Dev creates project & repair
    ingest_resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Reviewer Review App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    project_id = ingest_resp.json()["id"]

    inc_resp = client.post(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"project_id": project_id, "title": "Reviewer Inspect Defect"}
    )
    incident_id = inc_resp.json()["id"]
    client.post(f"/api/v1/incidents/{incident_id}/diagnose", headers={"Authorization": f"Bearer {dev_token}"})
    repair_resp = client.post("/api/v1/repairs", headers={"Authorization": f"Bearer {dev_token}"}, json={"incident_id": incident_id})
    repair_id = repair_resp.json()["id"]
    patch_hash = repair_resp.json()["patch_hash"]

    # 1. Reviewer CAN view developer's project across tenant boundary
    proj_resp = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert proj_resp.status_code == status.HTTP_200_OK

    # 2. Reviewer CAN approve the candidate repair
    approve_resp = client.post(
        f"/api/v1/approvals/{repair_id}/approve",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"patch_hash": patch_hash, "notes": "LGTM by quality reviewer"}
    )
    assert approve_resp.status_code == status.HTTP_200_OK
    assert approve_resp.json()["status"] == "approved"

    # 3. Reviewer CANNOT modify system settings
    settings_fail = client.post(
        "/api/v1/settings",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"sandbox_timeout_seconds": 999}
    )
    assert settings_fail.status_code == status.HTTP_403_FORBIDDEN
