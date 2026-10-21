-- ==============================================================================
-- PHOENIX — Supabase PostgreSQL Schema & Security Policies
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. User Roles & Profiles (Linked to Supabase Auth)
CREATE TYPE user_role AS ENUM ('admin', 'developer', 'reviewer', 'auditor');

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    role user_role DEFAULT 'developer' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Trigger to create profile when auth.users is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, role)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', new.email),
        COALESCE((new.raw_user_meta_data->>'role')::user_role, 'developer'::user_role)
    )
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email, full_name = EXCLUDED.full_name;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 3. Projects Table
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    input_type TEXT NOT NULL CHECK (input_type IN ('github', 'zip', 'local')),
    source_url TEXT,
    content_fingerprint TEXT,
    detected_language TEXT,
    detected_framework TEXT,
    root_path TEXT NOT NULL,
    health_status TEXT DEFAULT 'unknown' NOT NULL,
    last_analysis_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);

-- 4. Project Snapshots Table
CREATE TABLE IF NOT EXISTS public.project_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE NOT NULL,
    commit_sha TEXT,
    file_count INT DEFAULT 0 NOT NULL,
    total_size_bytes BIGINT DEFAULT 0 NOT NULL,
    manifest_json JSONB NOT NULL,
    storage_path TEXT, -- Reference to Supabase Storage object
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 5. Incidents Table
CREATE TABLE IF NOT EXISTS public.incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    raw_log TEXT,
    stack_trace TEXT,
    error_signature TEXT,
    severity TEXT DEFAULT 'high' NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    status TEXT DEFAULT 'detected' NOT NULL CHECK (status IN ('detected', 'diagnosing', 'diagnosed', 'repairing', 'resolved', 'closed')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incidents_project_id ON public.incidents(project_id);

-- 6. Diagnoses Table
CREATE TABLE IF NOT EXISTS public.diagnoses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES public.incidents(id) ON DELETE CASCADE NOT NULL,
    root_cause_hypothesis TEXT NOT NULL,
    confidence_score FLOAT DEFAULT 0.0 NOT NULL,
    evidence_json JSONB DEFAULT '[]'::jsonb,
    relevant_files_json JSONB DEFAULT '[]'::jsonb,
    suggested_action TEXT,
    is_repair_safe BOOLEAN DEFAULT TRUE NOT NULL,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 7. Repair Jobs Table
CREATE TABLE IF NOT EXISTS public.repair_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES public.incidents(id) ON DELETE CASCADE NOT NULL,
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE NOT NULL,
    status TEXT DEFAULT 'queued' NOT NULL CHECK (status IN ('queued', 'generating', 'validating', 'awaiting_approval', 'approved', 'rejected', 'delivered', 'failed')),
    retry_count INT DEFAULT 0 NOT NULL,
    max_retries INT DEFAULT 3 NOT NULL,
    patch_hash TEXT,
    base_commit TEXT,
    repair_plan_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_repair_jobs_project_id ON public.repair_jobs(project_id);

-- 8. Candidate Patches Table
CREATE TABLE IF NOT EXISTS public.candidate_patches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repair_job_id UUID REFERENCES public.repair_jobs(id) ON DELETE CASCADE NOT NULL,
    patch_content TEXT NOT NULL,
    diff_summary TEXT,
    files_modified_json JSONB DEFAULT '[]'::jsonb,
    patch_hash TEXT NOT NULL,
    storage_path TEXT, -- Reference to Supabase Storage object
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 9. Validation Runs Table
CREATE TABLE IF NOT EXISTS public.validation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repair_job_id UUID REFERENCES public.repair_jobs(id) ON DELETE CASCADE NOT NULL,
    candidate_patch_id UUID REFERENCES public.candidate_patches(id) ON DELETE CASCADE NOT NULL,
    overall_status TEXT NOT NULL CHECK (overall_status IN ('passed', 'failed', 'inconclusive', 'skipped')),
    exit_code INT DEFAULT 0 NOT NULL,
    duration_ms INT DEFAULT 0 NOT NULL,
    test_output TEXT,
    security_findings_json JSONB DEFAULT '[]'::jsonb,
    validation_details_json JSONB DEFAULT '{}'::jsonb,
    ran_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 10. Approvals Table (Cryptographically bound)
CREATE TABLE IF NOT EXISTS public.approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repair_job_id UUID REFERENCES public.repair_jobs(id) ON DELETE CASCADE NOT NULL,
    candidate_patch_id UUID REFERENCES public.candidate_patches(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES public.profiles(id) NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'invalidated')),
    patch_hash TEXT NOT NULL,
    base_commit TEXT,
    reviewer_notes TEXT,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 11. Pull Requests Record Table
CREATE TABLE IF NOT EXISTS public.pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repair_job_id UUID REFERENCES public.repair_jobs(id) ON DELETE CASCADE NOT NULL,
    repository_url TEXT NOT NULL,
    branch_name TEXT NOT NULL,
    pr_number INT,
    pr_url TEXT,
    status TEXT DEFAULT 'created' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 12. Audit Events Table
CREATE TABLE IF NOT EXISTS public.audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    correlation_id TEXT,
    ip_address TEXT,
    details_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_user_id ON public.audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON public.audit_events(created_at DESC);

-- 13. Semantic Retrieval (pgvector)
CREATE TABLE IF NOT EXISTS public.code_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE NOT NULL,
    file_path TEXT NOT NULL,
    chunk_content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ==============================================================================
-- 14. Row-Level Security (RLS) Policies
-- ==============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.diagnoses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repair_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidate_patches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.validation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pull_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.code_embeddings ENABLE ROW LEVEL SECURITY;

-- Profiles: users read own, admins read all
CREATE POLICY "Users can read own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

-- Projects: user can select and manage own projects; admin has full access
CREATE POLICY "Users manage own projects" ON public.projects
    FOR ALL USING (
        auth.uid() = user_id OR
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- Incidents: accessible through project ownership
CREATE POLICY "Users access own project incidents" ON public.incidents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE projects.id = incidents.project_id
            AND (projects.user_id = auth.uid() OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'reviewer')))
        )
    );

-- Repair Jobs: accessible through project ownership or reviewer role
CREATE POLICY "Users access own project repairs" ON public.repair_jobs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE projects.id = repair_jobs.project_id
            AND (projects.user_id = auth.uid() OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'reviewer')))
        )
    );

-- Approvals: reviewers and admins can approve/reject; developers can read
CREATE POLICY "Reviewers manage approvals" ON public.approvals
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'reviewer')
        )
    );

CREATE POLICY "Users view approvals for their repairs" ON public.approvals
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.repair_jobs
            JOIN public.projects ON projects.id = repair_jobs.project_id
            WHERE repair_jobs.id = approvals.repair_job_id AND projects.user_id = auth.uid()
        )
    );

-- Audit Events: users can view own audit events; auditors & admins can view all
CREATE POLICY "Audit event view policy" ON public.audit_events
    FOR SELECT USING (
        user_id = auth.uid() OR
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'auditor'))
    );

-- ==============================================================================
-- 15. Supabase Realtime Publication
-- ==============================================================================
-- Publish live status updates for repair jobs and incidents
ALTER PUBLICATION supabase_realtime ADD TABLE public.repair_jobs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.incidents;
ALTER PUBLICATION supabase_realtime ADD TABLE public.approvals;

-- ==============================================================================
-- 16. Supabase Storage Buckets
-- ==============================================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('phoenix-archives', 'phoenix-archives', false),
       ('phoenix-artifacts', 'phoenix-artifacts', false)
ON CONFLICT (id) DO NOTHING;
