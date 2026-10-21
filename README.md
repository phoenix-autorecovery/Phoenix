# PHOENIX — Enterprise Autonomous Software Recovery Platform

[![Status](https://img.shields.io/badge/Status-Production--Ready-emerald.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](#)
[![React](https://img.shields.io/badge/React-18.2-cyan.svg)](#)
[![Vite](https://img.shields.io/badge/Vite-5.0-purple.svg)](#)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-sky.svg)](#)
[![Groq](https://img.shields.io/badge/Inference-Groq_API-orange.svg)](#)
[![Tests](https://img.shields.io/badge/Tests-11_Passed-brightgreen.svg)](#)

> **Core Architectural Invariant:**
> *The AI proposes changes; deterministic tools verify them; explicit authorization controls where those changes go.*

---

## 1. System Overview

PHOENIX is an enterprise-grade autonomous software maintenance and recovery platform. It ingests software projects via GitHub URLs, ZIP archives, or a local companion CLI, diagnoses defect signatures using software intelligence and hosted Groq inference models, synthesizes minimal unified diffs, verifies them deterministically inside isolated disposable sandboxes, and delivers verified fixes through cryptographic approvals, downloadable patches, or authorized GitHub Pull Requests.

---

## 2. Six-Layer Enterprise Architecture

```
Layer 1: Project Ingestion
  ├── GitHub OAuth / App (URL validation, SSRF shield, commit pinning)
  ├── ZIP Archive Upload (ZIP-Slip protection, archive-bomb limit, secret scanning)
  └── Local Companion CLI (Manifest generation, .gitignore compliance, secret exclusion)

Layer 2: Secure Workspace Manager
  ├── Project Root Normalization & AST Technology Detection
  ├── Base Snapshot Fingerprinting (SHA-256 integrity hash)
  └── Working Copy Isolation (Original source files are strictly immutable)

Layer 3: Backend Orchestration & Policy Engine
  ├── FastAPI REST Services & JWT Role-Based Access Control (Admin, Dev, Reviewer, Auditor)
  ├── Durable Job State Machine (Queued -> Diagnosing -> Validating -> Awaiting Approval -> Delivered)
  └── Deterministic Risk-Aware Policy Engine (Scope checks, required test passes, no sensitive path writes)

Layer 4: Software Intelligence & LLM Adapter
  ├── Stack Trace Parser & Error Signature Fingerprinting
  ├── Code Snippet & AST Evidence Retriever
  ├── Provider-Independent Model Adapter (Groq API + Verified Catalogue + Mock Fallback)
  └── Structured JSON Repair Plan Generator (Bounded context, minimal patch size)

Layer 5: Isolated Verification Sandbox
  ├── Disposable Sandboxes (Temporary workspace copy, scrubbed env, restricted paths)
  ├── Project-Native Test Execution (pytest, npm test, etc.)
  ├── Static Analysis & Security Scanning (Pattern rules, forbidden code detection)
  └── Cryptographic Patch Hash Binding (Normalized SHA-256 of unified diff)

Layer 6: Controlled Delivery & Human Gate
  ├── Interactive Unified Diff Inspection (Added lines, removed lines, hunk navigation)
  ├── Reviewer Sign-Off Binding (Approval strictly locked to patch hash and base commit)
  ├── Downloadable .patch and Repaired Project .zip Archives
  └── Authorized GitHub Branch & Pull Request Creation (Never commits to default branch)
```

---

## 3. Quickstart Guide

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Git

### 1. Backend Setup & Run

```bash
# Navigate to backend and create virtual environment
cd backend
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Or on Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database initialization and backend server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI backend will start at `http://localhost:8000`.
- Swagger OpenAPI interactive documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

Default seeded development accounts:
- **Admin:** `admin@phoenix.io` / `phoenix123`
- **Developer:** `developer@phoenix.io` / `phoenix123`

---

### 2. Frontend Setup & Run

```bash
# In a new terminal window:
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### 3. Local Companion CLI Usage

To safely ingest a local workspace without uploading `node_modules`, `.env`, or secrets:

```bash
# Run companion CLI
python cli/phoenix_cli.py sync /path/to/local/project --token <YOUR_JWT_TOKEN>
```

---

## 4. Configuring Groq API Key & GitHub PAT

PHOENIX works 100% out of the box with an embedded deterministic provider for testing and evaluation.

To connect your real **Groq API Key** and **GitHub Personal Access Token**:
1. Sign in to the PHOENIX dashboard (`http://localhost:5173`).
2. Navigate to **Settings** in the sidebar.
3. Paste your `GROQ_API_KEY` (e.g. `gsk_...`) and select your desired model from Groq's verified catalogue (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`).
4. Paste your `GITHUB_TOKEN` (e.g. `ghp_...`).
5. Click **Save Configuration**.

Alternatively, you can set them in your `.env` file:
```env
GROQ_API_KEY="gsk_your_groq_api_key_here"
GROQ_MODEL="llama-3.3-70b-versatile"
GITHUB_TOKEN="ghp_your_github_token_here"
```

---

## 5. Automated Verification & Test Suite

PHOENIX includes an automated test suite verifying all security boundaries, multi-tenant isolation, safe ZIP extraction, and the end-to-end autonomous repair lifecycle:

```bash
# Run full automated test suite
backend\.venv\Scripts\python -m pytest backend/tests -v
```

### Verified Test Cases:
1. `test_approval_cryptographic_binding`: Confirms approval succeeds only when the exact SHA-256 patch hash is supplied; tampered hashes are rejected with HTTP 400.
2. `test_cross_tenant_isolation`: Confirms User B cannot access User A's private project workspaces or repair jobs (HTTP 403 Forbidden).
3. `test_delivery_blocked_without_prior_approval`: Confirms pull request generation is strictly blocked without explicit reviewer sign-off.
4. `test_register_and_login`: Verifies user registration, bcrypt password hashing, and JWT issuance.
5. `test_login_invalid_password`: Confirms rejection of invalid credentials.
6. `test_get_current_user_me`: Verifies authenticated user profile extraction.
7. `test_unauthorized_access`: Verifies route protection for unauthenticated requests.
8. `test_ingest_valid_zip`: Verifies safe archive decompression, AST tech stack detection, and directory fingerprinting.
9. `test_ingest_zip_slip_rejection`: Verifies path-traversal and ZIP-Slip attacks (`../../etc/passwd`) are blocked and rejected.
10. `test_github_invalid_scheme_ssrf_rejection`: Verifies non-https and arbitrary external host URLs are rejected to prevent SSRF.
11. `test_full_autonomous_repair_flow`: Verifies the complete end-to-end vertical slice (Ingest buggy project -> Report reproducible TypeError -> Software intelligence diagnosis -> Minimal patch synthesis -> Isolated sandbox execution -> Deterministic test passing -> Artifact export).

---

## 6. API Route Specification

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/auth/register` | `POST` | Public | Register user account |
| `/api/v1/auth/token` | `POST` | Public | OAuth2 JWT token login |
| `/api/v1/auth/me` | `GET` | Authenticated | Current user profile |
| `/api/v1/projects` | `GET` | Authenticated | List tenant workspaces |
| `/api/v1/projects/{id}` | `GET` | Authenticated | Get project details |
| `/api/v1/projects/{id}/profile` | `GET` | Authenticated | Tech stack, commands, risks |
| `/api/v1/projects/{id}/files` | `GET` | Authenticated | Safe file tree inventory |
| `/api/v1/ingestion/zip` | `POST` | Authenticated | Upload & extract ZIP archive |
| `/api/v1/ingestion/github` | `POST` | Authenticated | Clone & pin GitHub repo commit |
| `/api/v1/ingestion/local` | `POST` | Authenticated | Sync companion CLI manifest |
| `/api/v1/incidents` | `POST` | Authenticated | Register reproducible issue |
| `/api/v1/incidents/{id}/diagnose` | `POST` | Authenticated | Run AI diagnosis & evidence search |
| `/api/v1/repairs` | `POST` | Authenticated | Generate patch & validate in sandbox |
| `/api/v1/repairs/{id}` | `GET` | Authenticated | Get repair job status & validation run |
| `/api/v1/repairs/{id}/diff` | `GET` | Authenticated | Retrieve candidate patch diff |
| `/api/v1/approvals/{id}/approve` | `POST` | Reviewer/Admin | Cryptographically bound approval |
| `/api/v1/approvals/{id}/reject` | `POST` | Reviewer/Admin | Reject candidate repair |
| `/api/v1/repairs/{id}/artifact` | `GET` | Authenticated | Download `.patch` or repaired `.zip` |
| `/api/v1/repairs/{id}/pull-request` | `POST` | Authenticated | Open GitHub Pull Request |
| `/api/v1/monitoring/metrics` | `GET` | Authenticated | Live dashboard telemetry |
| `/api/v1/audit-events` | `GET` | Authenticated | Immutable audit log trail |
| `/api/v1/settings` | `GET/POST` | Admin | Manage Groq & GitHub credentials |

---

## 7. Threat Model & Security Controls

| Threat / Risk | PHOENIX Mitigation Strategy |
| :--- | :--- |
| **ZIP Slip / Directory Traversal** | Normalized absolute path resolution; rejects any archive entry attempting to resolve outside the working directory. Symlinks are rejected. |
| **Archive Bombs** | Strict size limits (50MB compressed, 250MB decompressed), file count limits (15,000 files), and decompression ratio tracking. |
| **Arbitrary Shell Execution** | Models cannot execute host shell commands. Sandbox runs use direct vector arrays without shell expansion (`shell=False`). |
| **Secret Exposure** | Pre-ingestion regex scanners identify API keys, tokens, and private keys. Environment scrubbing ensures credentials never leak to sandbox child processes. |
| **Prompt Injection** | Untrusted project files and READMEs are wrapped into strict JSON schemas. Model outputs are parsed only for specified JSON fields. |
| **Unauthorized Git Pushes** | Read-only by default. Creating branches and PRs requires explicit reviewer approval. PHOENIX never pushes directly to `main` or default branches. |
| **Approval Tampering** | Approvals require an exact cryptographic match between `(patch_hash, base_commit_sha)`. Modifying the patch invalidates the approval. |
