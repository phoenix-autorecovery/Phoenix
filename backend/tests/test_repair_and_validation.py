from fastapi import status

def test_full_autonomous_repair_flow(client, dev_token, sample_buggy_zip):
    # 1. Ingest sample project
    ingest_resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "End-to-End Buggy App"},
        files={"file": ("app.zip", sample_buggy_zip, "application/zip")}
    )
    assert ingest_resp.status_code == status.HTTP_200_OK
    project_id = ingest_resp.json()["id"]

    # 2. Inspect project profile
    prof_resp = client.get(
        f"/api/v1/projects/{project_id}/profile",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert prof_resp.status_code == status.HTTP_200_OK
    assert prof_resp.json()["detected_language"] == "Python"

    # 3. Create incident with stack trace
    inc_resp = client.post(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={
            "project_id": project_id,
            "title": "TypeError: 'NoneType' object is not iterable in calculate_total",
            "stack_trace": """Traceback (most recent call last):
  File "test_calc.py", line 8, in test_calculate_total_none
    assert calculate_total(None) == 0
  File "calculator.py", line 3, in calculate_total
    for item in items:
TypeError: 'NoneType' object is not iterable""",
            "severity": "high"
        }
    )
    assert inc_resp.status_code == status.HTTP_200_OK
    incident_id = inc_resp.json()["id"]

    # 4. Trigger AI Diagnosis
    diag_resp = client.post(
        f"/api/v1/incidents/{incident_id}/diagnose",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert diag_resp.status_code == status.HTTP_200_OK
    diag_data = diag_resp.json()
    assert diag_data["confidence_score"] > 0.6
    assert "root_cause_hypothesis" in diag_data

    # 5. Trigger Repair Job
    repair_resp = client.post(
        "/api/v1/repairs",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"incident_id": incident_id}
    )
    assert repair_resp.status_code == status.HTTP_200_OK
    repair_data = repair_resp.json()
    assert repair_data["patch_hash"] is not None
    assert len(repair_data["candidate_patches"]) > 0

    # 6. Verify validation was executed in disposable sandbox
    assert len(repair_data["validation_runs"]) > 0
    val_run = repair_data["validation_runs"][0]
    assert val_run["overall_status"] in ["passed", "failed", "inconclusive"]

    # 7. Download patch artifact
    repair_id = repair_data["id"]
    patch_artifact_resp = client.get(
        f"/api/v1/repairs/{repair_id}/artifact?artifact_type=patch",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert patch_artifact_resp.status_code == status.HTTP_200_OK
    assert "calculator.py" in patch_artifact_resp.text
