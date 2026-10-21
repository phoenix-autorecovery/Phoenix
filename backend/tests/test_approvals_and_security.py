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
