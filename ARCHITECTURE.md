# PHOENIX — Enterprise System Architecture & Security Design

## 1. System Overview

PHOENIX is an enterprise-grade autonomous software maintenance and recovery platform. It provides a secure, deterministic verification pipeline for AI-proposed code repairs.

### Architectural Invariant
> **The AI proposes changes; deterministic tools verify them; explicit authorization controls where those changes go.**

---

## 2. Layered Architecture

```
+-------------------------------------------------------------------------------+
| Layer 1: Ingestion Interfaces                                                |
| - Public / Authorized GitHub Repo (Git shallow clone / tree fetch)             |
| - ZIP Archive Upload (ZIP-Slip protected, bomb-limited, secret-scanned)       |
| - Local Folder Companion CLI (Manifest-driven, ignore-respecting)              |
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
| - FastAPI REST API & WebSocket event stream                                   |
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
| - Source Retrieval (AST / grep / deterministic filtering)                     |
| - Provider-Independent Model Adapter (Groq API + Verified Catalogue + Mock)  |
| - Structured Repair Plan Generator (Bounded context, minimal patch size)      |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Layer 5: Isolated Verification Sandbox                                        |
| - Disposable Sandbox (Temp working copy, scrubbed env, restricted paths)      |
| - Deterministic Test Execution (pytest, npm test, etc.)                      |
| - Static Analysis & Security Scanning (Semgrep / Ruff / ESLint)               |
| - Patch Hash Binding (sha256 of candidate diff)                              |
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
| Shared Enterprise Infrastructure                                              |
| - PostgreSQL (Transactional database, relations, audit events)                |
| - Redis / Durable Job Queue (Async execution, failure recovery)               |
| - Structured Audit Logs (Actor, timestamp, IP, correlation ID, change details)|
+-------------------------------------------------------------------------------+
```

---

## 3. Threat Model and Trust Boundaries

| Threat / Risk | Mitigation Strategy |
| :--- | :--- |
| **ZIP Slip / Path Traversal** | Normalized absolute path resolution; verify all unzipped paths remain inside the target working directory. Symlinks are rejected. |
| **Archive Bombs** | Max archive size limit (50MB compressed, 200MB uncompressed), max file count (10,000 files), decompression ratio monitoring. |
| **Untrusted Repository Execution** | Code is never automatically executed upon ingestion. Verification commands run inside isolated sandboxes with strict execution timeouts, restricted environment variables, and non-shell vector calls. |
| **Prompt Injection** | Project files, READMEs, and issue descriptions are treated as untrusted strings wrapped in rigid JSON schema templates. Model output cannot execute arbitrary host shell commands. |
| **Secret Leakage** | Pre-ingestion regex scanning detects API keys, tokens, and private keys. High-entropy strings are redacted before code is sent to the LLM. Server credentials (Groq keys, GitHub PATs) are stored encrypted or in environment variables and never logged. |
| **Unauthorized Git Push** | Read-only by default. Creating branches and pull requests requires explicit user authorization and GitHub PAT/App token. Phoenix never pushes directly to default branches (e.g. `main` or `master`). |
| **Approval Tampering** | Approvals are strictly cryptographically bound to `(patch_hash, base_commit_sha)`. Any alteration to the patch or repository invalidates pending or granted approvals. |
| **Cross-Tenant Access** | Every project, incident, repair job, and audit log is isolated by tenant/user ID. API middleware enforces tenancy on all route endpoints. |

---

## 4. Database Schema Design (PostgreSQL / SQLite Dual Compatibility)

- **users**: ID, email, hashed_password, full_name, role (`admin`, `developer`, `reviewer`, `auditor`), is_active, created_at.
- **projects**: ID, user_id, name, description, input_type (`github`, `zip`, `local`), source_url, original_fingerprint, detected_language, detected_framework, root_path, created_at, updated_at.
- **project_snapshots**: ID, project_id, commit_sha, file_count, total_size, manifest_json, created_at.
- **incidents**: ID, project_id, title, description, raw_log, stack_trace, error_signature, severity (`critical`, `high`, `medium`, `low`), status (`detected`, `diagnosing`, `diagnosed`, `repairing`, `resolved`, `closed`), created_at.
- **diagnoses**: ID, incident_id, root_cause_hypothesis, confidence_score, evidence_json, relevant_files_json, suggested_action, is_repair_safe, model_used, created_at.
- **repair_jobs**: ID, incident_id, project_id, status (`queued`, `generating`, `validating`, `awaiting_approval`, `approved`, `rejected`, `delivered`, `failed`), retry_count, max_retries, patch_hash, base_commit, repair_plan_json, error_message, created_at, updated_at.
- **candidate_patches**: ID, repair_job_id, patch_content, diff_summary, files_modified_json, patch_hash, created_at.
- **validation_runs**: ID, repair_job_id, candidate_patch_id, overall_status (`passed`, `failed`, `inconclusive`), exit_code, duration_ms, test_output, security_findings_json, ran_at.
- **approvals**: ID, repair_job_id, candidate_patch_id, user_id, status (`pending`, `approved`, `rejected`), patch_hash, base_commit, reviewer_notes, decided_at.
- **pull_requests**: ID, repair_job_id, repository_url, branch_name, pr_number, pr_url, status, created_at.
- **audit_events**: ID, user_id, action, resource_type, resource_id, correlation_id, ip_address, details_json, created_at.
- **system_settings**: ID, key, value_encrypted, is_secret, updated_at.

---

## 5. Model Inference Strategy (Groq Adapter)

1. **Configurable Model**: Default to `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`.
2. **Capability Check**: Dynamic ping to `/models` endpoint to verify model availability.
3. **Structured Outputs**: JSON Schema enforcement for structured diagnosis and repair plans.
4. **Deterministic Mock Mode**: When no Groq API key is configured or when running automated test suites, the `MockLLMProvider` produces syntactically valid, deterministic responses for tests and demonstration.
