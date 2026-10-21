import io
import zipfile
import pytest
from fastapi import status

def test_ingest_valid_zip(client, dev_token, sample_buggy_zip):
    resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Calculator Project", "description": "Buggy sample project"},
        files={"file": ("calculator.zip", sample_buggy_zip, "application/zip")}
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["name"] == "Calculator Project"
    assert data["input_type"] == "zip"
    assert data["detected_language"] == "Python"
    assert data["content_fingerprint"] is not None

def test_ingest_zip_slip_rejection(client, dev_token):
    # Construct malicious zip with traversal path
    malicious_buf = io.BytesIO()
    with zipfile.ZipFile(malicious_buf, "w") as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0::/root:/bin/bash")
    malicious_buf.seek(0)

    resp = client.post(
        "/api/v1/ingestion/zip",
        headers={"Authorization": f"Bearer {dev_token}"},
        data={"name": "Malicious Zip"},
        files={"file": ("exploit.zip", malicious_buf.getvalue(), "application/zip")}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Path traversal detected" in resp.json()["detail"]

def test_github_invalid_scheme_ssrf_rejection(client, dev_token):
    # Reject http scheme
    resp = client.post(
        "/api/v1/ingestion/github",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"repository_url": "http://github.com/torvalds/linux"}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only valid https://github.com/ URLs are permitted" in resp.json()["detail"]

    # Reject non-github host (SSRF attempt)
    resp2 = client.post(
        "/api/v1/ingestion/github",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={"repository_url": "https://attacker.evil.com/fake/repo"}
    )
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only valid https://github.com/ URLs are permitted" in resp2.json()["detail"]
