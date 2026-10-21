# PHOENIX — Enterprise System Architecture & Security Design

## 1. System Overview

PHOENIX is an enterprise-grade autonomous software maintenance and recovery platform. It provides a secure, deterministic verification pipeline for AI-proposed code repairs.

### Architectural Invariant
> **The AI proposes changes; deterministic tools verify them; explicit authorization controls where those changes go.**

---

## 2. Updated Technology Stack (Supabase-First)

| Component | Technology | Role & Boundary |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Developer dashboard, diff inspection, approvals gate |
| **Backend API** | Python, FastAPI, Pydantic | Ingestion validation, workflow orchestration, policy enforcement |
| **Primary Database** | Supabase PostgreSQL | Relational schema, transactional integrity, foreign keys |
| **Authentication** | Supabase Auth + JWT | User identity, organization RBAC, token verification |
| **File & Artifact Storage**| Supabase Storage | Private buckets for project archives, generated `.patch` diffs |
| **Vector Retrieval** | pgvector in Supabase | Code snippet & past incident semantic similarity search |
| **Real-time Dashboard** | Supabase Realtime | WebSocket notifications for live job status & incident states |
| **Background Jobs** | Redis + Celery / Queue | Durable task state machine, retries, timeout enforcement |
| **AI Inference** | Groq API Adapter | Bounded context diagnosis & minimal patch plan generation |
| **Isolated Execution** | Disposable Sandboxes / Docker | Non-root, environment-scrubbed test runs (pytest, npm test) |
| **Delivery & SCM** | Git & GitHub App / PAT | Author of repair branches & Pull Requests (Never default branch) |

---

## 3. Layered Architecture

```
+-------------------------------------------------------------------------------+
| Layer 1: Ingestion Interfaces                                                |
| - Public / Authorized GitHub Repo (Git shallow clone / tree fetch)             |
| - ZIP Archive Upload (ZIP-Slip protected, bomb-limited, secret-scanned)       |
| - Local Folder Companion CLI (Manifest-driven, .gitignore-compliant)          |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Layer 2: Secure Workspace Manager                                             |
| - Project Root Detection · Language/Framework Identification                 |
| - Secret & Credential Inspection · Base Snapshot Fingerprinting              |
| - Working Copy Isolation (Original source is immutable)                       |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Layer 3: Backend Orchestration & Policy Engine                                |
| - FastAPI REST API & Supabase Realtime WebSocket notifications                |
| - Durable Job State Machine (Queued -> Ingesting -> Diagnosing -> Repairing    |
|                              -> Validating -> Awaiting Approval -> Delivered) |
| - RBAC (Admin, Developer, Reviewer, Auditor)                                  |
| - Deterministic Policy Gates (Evidence thresholds, required test passing)     |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Layer 4: Software Intelligence & LLM Adapter                                  |
| - Stack Trace Parser & Error Fingerprinting                                  |
| - Source Retrieval (AST / grep / pgvector semantic search)                    |
| - Provider-Independent Model Adapter (Groq API + Verified Catalogue + Mock)  |
| - Structured Repair Plan Generator (Bounded context, minimal patch size)      |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Layer 5: Isolated Verification Sandbox                                        |
| - Disposable Sandbox (Temp working copy, scrubbed env, restricted paths)      |
| - Deterministic Test Execution (pytest, npm test, etc.)                      |
| - Static Analysis & Security Scanning (Semgrep / Ruff / pattern scanning)     |
| - Cryptographic Patch Hash Binding (SHA-256 of candidate diff)                |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Layer 6: Controlled Delivery & Approvals                                      |
| - Unified Diff Inspection & Reviewer Sign-Off                                |
| - Invalidation of approval if target commit or patch hash changes            |
| - Downloadable Patch (.patch) & Repaired Project ZIP                          |
| - Authorized GitHub Branch & Pull Request Creation (Never push to main)      |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Supabase Managed Infrastructure                                               |
| - Supabase PostgreSQL (Transactional records, relations, audit events)        |
| - Supabase Auth (Identity verification, token validation)                     |
| - Supabase Storage (Private buckets: phoenix-archives, phoenix-artifacts)     |
| - Supabase Realtime (Live job state broadcast to dashboard)                   |
| - Row-Level Security (Strict tenant & organization isolation)                 |
+-------------------------------------------------------------------------------+
```

---

## 4. Supabase PostgreSQL Schema & Security Policies

The schema migration is located in [`supabase/migrations/20261021_init_phoenix_schema.sql`](file:///c:/Users/srich_7kke41v/Desktop/Phoenix/supabase/migrations/20261021_init_phoenix_schema.sql):

- **profiles**: Linked to `auth.users(id)` with roles: `admin`, `developer`, `reviewer`, `auditor`.
- **projects**: Workspace records with `content_fingerprint`, `root_path`, `health_status`.
- **project_snapshots**: Manifest and file count tracking.
- **incidents**: Incident records, error signatures, severity, status.
- **diagnoses**: Root cause hypothesis, confidence score, evidence, affected files.
- **repair_jobs**: State machine tracking, patch hash, base commit SHA, retry counts.
- **candidate_patches**: Unified diffs, modified files list, SHA-256 patch hash.
- **validation_runs**: Exit codes, duration, test logs, security scan findings.
- **approvals**: Reviewer decisions cryptographically bound to `(patch_hash, base_commit)`.
- **pull_requests**: Branch names and PR URLs.
- **audit_events**: Immutable action logs with correlation IDs.
- **code_embeddings**: pgvector `vector(1536)` table with ivfflat index.

### Row-Level Security (RLS) Boundaries:
- `projects`: Users can view/modify only projects matching `user_id = auth.uid()` or role `admin`.
- `incidents` & `repair_jobs`: Filtered by project ownership.
- `approvals`: Only users with role `reviewer` or `admin` can create or update approval decisions.
- `audit_events`: Viewable by event owner or role `auditor`/`admin`.

---

## 5. Threat Model and Trust Boundaries

| Threat / Risk | Mitigation Strategy |
| :--- | :--- |
| **ZIP Slip / Path Traversal** | Normalized absolute path resolution; verify all unzipped paths remain inside the target working directory. Symlinks are rejected. |
| **Archive Bombs** | Max archive size limit (50MB compressed, 250MB uncompressed), max file count (15,000 files), decompression ratio monitoring. |
| **Untrusted Repository Execution** | Code is never automatically executed upon ingestion. Verification commands run inside isolated sandboxes with strict execution timeouts, restricted environment variables, and non-shell vector calls. |
| **Prompt Injection** | Project files, READMEs, and issue descriptions are treated as untrusted strings wrapped in rigid JSON schema templates. Model output cannot execute arbitrary host shell commands. |
| **Secret Leakage** | Pre-ingestion regex scanning detects API keys, tokens, and private keys. Environment scrubbing ensures credentials never leak to execution processes. |
| **Unauthorized Git Push** | Read-only by default. Creating branches and pull requests requires explicit user authorization and GitHub PAT/App token. Phoenix never pushes directly to default branches. |
| **Approval Tampering** | Approvals are strictly cryptographically bound to `(patch_hash, base_commit_sha)`. Any alteration to the patch or repository invalidates pending or granted approvals. |
| **Cross-Tenant Access** | Every project, incident, repair job, and audit log is isolated by tenant/user ID and enforced via PostgreSQL RLS and API middleware. |
