export interface User {
  id: string;
  email: string;
  full_name?: string;
  role: 'admin' | 'developer' | 'reviewer' | 'auditor';
  is_active: boolean;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  input_type: 'github' | 'zip' | 'local';
  source_url?: string;
  content_fingerprint?: string;
  detected_language?: string;
  detected_framework?: string;
  root_path: string;
  health_status: 'healthy' | 'degraded' | 'critical' | 'unknown';
  created_at: string;
  updated_at: string;
}

export interface ProjectProfile {
  name: string;
  detected_language: string;
  detected_framework: string;
  dependency_files: string[];
  test_commands: string[];
  lint_commands: string[];
  file_count: number;
  total_size_bytes: number;
  health_status: string;
  risks_identified: string[];
}

export interface Incident {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  raw_log?: string;
  stack_trace?: string;
  error_signature?: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'detected' | 'diagnosing' | 'diagnosed' | 'repairing' | 'resolved' | 'closed';
  diagnoses: Diagnosis[];
  created_at: string;
  updated_at: string;
}

export interface Diagnosis {
  id: string;
  incident_id: string;
  root_cause_hypothesis: string;
  confidence_score: number;
  evidence: { type: string; observation: string }[];
  relevant_files: { path: string; lines: number[]; reason: string }[];
  suggested_action?: string;
  is_repair_safe: boolean;
  model_used?: string;
  created_at: string;
}

export interface CandidatePatch {
  id: string;
  repair_job_id: string;
  patch_content: string;
  diff_summary?: string;
  files_modified: string[];
  patch_hash: string;
  created_at: string;
}

export interface ValidationRun {
  id: string;
  repair_job_id: string;
  candidate_patch_id: string;
  overall_status: 'passed' | 'failed' | 'inconclusive' | 'skipped';
  exit_code: number;
  duration_ms: number;
  test_output?: string;
  security_findings: { rule: string; severity: string; message: string; line?: string }[];
  ran_at: string;
}

export interface Approval {
  id: string;
  repair_job_id: string;
  candidate_patch_id: string;
  user_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'invalidated';
  patch_hash: string;
  base_commit?: string;
  reviewer_notes?: string;
  decided_at?: string;
  created_at: string;
}

export interface PullRequestRecord {
  id: string;
  repair_job_id: string;
  repository_url: string;
  branch_name: string;
  pr_number?: number;
  pr_url?: string;
  status: string;
  created_at: string;
}

export interface RepairJob {
  id: string;
  incident_id: string;
  project_id: string;
  status: 'queued' | 'generating' | 'validating' | 'awaiting_approval' | 'approved' | 'rejected' | 'delivered' | 'failed';
  retry_count: number;
  max_retries: number;
  patch_hash?: string;
  base_commit?: string;
  repair_plan?: {
    hypothesized_cause?: string;
    intended_behavior?: string;
    files_to_modify?: string[];
    patch?: string;
    expected_test_outcomes?: string[];
    potential_side_effects?: string;
    security_considerations?: string;
  };
  error_message?: string;
  candidate_patches: CandidatePatch[];
  validation_runs: ValidationRun[];
  approvals: Approval[];
  pull_requests: PullRequestRecord[];
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  correlation_id?: string;
  ip_address?: string;
  details?: Record<string, any>;
  created_at: string;
}

export interface DashboardMetrics {
  total_projects: number;
  active_jobs: number;
  open_incidents: number;
  resolved_incidents: number;
  pending_approvals: number;
  recent_audits: AuditEvent[];
}

export interface SystemSettings {
  groq_configured: boolean;
  groq_model: string;
  github_configured: boolean;
  sandbox_timeout_seconds: number;
  sandbox_network_isolated: boolean;
  docker_available: boolean;
  available_models: string[];
}
