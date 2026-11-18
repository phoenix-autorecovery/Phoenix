#!/usr/bin/env python3
"""
PHOENIX End-to-End Demo Seed Script
Creates a sample production-grade project ('Phoenix Core Billing Engine')
with a realistic financial calculation bug and automated unit tests.
Executes automated defect detection, Groq LLM diagnosis, candidate patch generation,
and isolated sandbox verification.
"""

import io
import zipfile
import httpx
import time

def run_seed():
    print("==================================================")
    print("       PHOENIX End-to-End Showcase Seeder         ")
    print("==================================================")
    
    client = httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=60.0)

    # 1. Authenticate as Admin
    print("[1/5] Authenticating as Administrator...")
    login_res = client.post("/auth/token", data={"username": "admin@phoenix.io", "password": "phoenix123"})
    if login_res.status_code != 200:
        print(f"[!] Authentication failed: {login_res.text}")
        return
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[+] Successfully authenticated as admin@phoenix.io")

    # 2. Package sample billing engine repository
    print("[2/5] Creating in-memory project archive (Financial Billing Engine)...")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("calculator.py", '''"""
Phoenix Core Billing Engine - Transaction Processing
"""

def calculate_total(items):
    """Calculates cumulative total of transactions."""
    total = 0
    for item in items:
        total += item
    return total

def calculate_discount(amount, percent):
    """Calculates discounted amount."""
    if amount < 0 or percent < 0:
        raise ValueError("Amount and percent must be non-negative.")
    return round(amount * (1.0 - percent / 100.0), 2)
''')
        zf.writestr("test_calc.py", '''from calculator import calculate_total, calculate_discount

def test_calculate_total_valid_numbers():
    assert calculate_total([100, 250, 75]) == 425

def test_calculate_discount_valid():
    assert calculate_discount(200, 15) == 170.0

def test_calculate_total_none_fallback():
    # Simulates null transaction payload from external webhook
    assert calculate_total(None) == 0
''')
        zf.writestr("requirements.txt", "pytest>=8.0.0\n")
        zf.writestr("README.md", "# Phoenix Core Billing Engine\nAutonomous transaction and billing ledger service.\n")
    buf.seek(0)

    # 3. Ingest project
    print("[3/5] Ingesting project via Secure Workspace Manager...")
    ingest_res = client.post(
        "/ingestion/zip",
        headers=headers,
        data={"name": "Phoenix Core Billing Engine"},
        files={"file": ("billing_engine.zip", buf.getvalue(), "application/zip")}
    )
    if ingest_res.status_code != 200:
        print(f"[!] Ingestion failed: {ingest_res.text}")
        return
    project = ingest_res.json()
    print(f"[+] Project Ingested: {project['name']} (ID: {project['id']})")

    # 4. Trigger Autonomous Defect Detection & Auto-Pilot
    print("[4/5] Running Autonomous Auto-Pilot (Detection -> Groq Diagnosis -> Sandbox Verification)...")
    start_time = time.time()
    pilot_res = client.post(
        f"/projects/{project['id']}/auto-pilot",
        headers=headers,
        json={"auto_apply": True, "override_model": "llama-3.1-70b-versatile"}
    )
    elapsed = time.time() - start_time
    
    if pilot_res.status_code != 200:
        print(f"[!] Auto-Pilot failed: {pilot_res.text}")
        return
    result = pilot_res.json()

    print(f"[+] Status: {result.get('status').upper()} in {elapsed:.2f}s")
    print(f"[+] Model Used: {result.get('model_used')}")
    print(f"[+] Defect Detected: {result.get('incident_title')}")
    print(f"[+] Patch Hash: {result.get('patch_hash')}")
    print(f"[+] Workspace Auto-Modified: {result.get('workspace_modified')}")

    # 5. Summary
    print("[5/5] Verification Complete!")
    print("==================================================")
    print("SHOWCASE READY!")
    print(f"Open Dashboard: http://127.0.0.1:5173/projects/{project['id']}")
    print("Login with: admin@phoenix.io / phoenix123")
    print("==================================================")

if __name__ == "__main__":
    run_seed()
