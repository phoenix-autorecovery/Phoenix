import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Wrench, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Download, 
  GitPullRequest, 
  ShieldCheck, 
  ShieldAlert, 
  ArrowLeft,
  Loader2,
  Terminal,
  FileCode2,
  AlertCircle
} from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { DiffViewer } from '../components/DiffViewer';
import { api } from '../api/client';
import { subscribeToRepairJobs } from '../api/supabase';
import { RepairJob } from '../types';

export const RepairWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<RepairJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [notes, setNotes] = useState('');
  const [prCreated, setPrCreated] = useState<string | null>(null);

  const fetchJob = async () => {
    try {
      const res = await api.get(`/repairs/${id}`);
      setJob(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJob();

    // Supabase Realtime subscription for instant job state transition
    const unsub = subscribeToRepairJobs((payload) => {
      if (payload.new && payload.new.id === id) {
        fetchJob();
      }
    });

    return () => unsub();
  }, [id]);

  const handleApprove = async () => {
    if (!job || !job.patch_hash) return;
    setActionLoading(true);
    try {
      await api.post(`/approvals/${job.id}/approve`, {
        patch_hash: job.patch_hash,
        notes: notes.trim() || undefined
      });
      await fetchJob();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Approval failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!job || !job.patch_hash) return;
    setActionLoading(true);
    try {
      await api.post(`/approvals/${job.id}/reject`, {
        patch_hash: job.patch_hash,
        notes: notes.trim() || 'Rejected by reviewer'
      });
      await fetchJob();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Rejection failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreatePR = async () => {
    if (!job) return;
    setActionLoading(true);
    try {
      const res = await api.post(`/repairs/${job.id}/pull-request`, {
        title: `fix(phoenix): autonomous repair for incident ${job.incident_id.slice(0, 8)}`,
        target_branch: 'main'
      });
      setPrCreated(res.data.pr_url || res.data.branch_name);
      await fetchJob();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Pull request creation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-slate-950 text-slate-500 gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
        <span>Loading repair workspace...</span>
      </div>
    );
  }

  if (!job) {
    return <div className="flex-1 p-8 text-center text-slate-400">Repair job not found.</div>;
  }

  const latestPatch = job.candidate_patches?.[job.candidate_patches.length - 1];
  const latestValidation = job.validation_runs?.[job.validation_runs.length - 1];
  const latestApproval = job.approvals?.[job.approvals.length - 1];

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title="Repair Verification & Delivery Workspace"
        subtitle={`Repair Job: ${job.id}`}
        actionButton={
          <div className="flex items-center space-x-3">
            <Link
              to={`/incidents/${job.incident_id}`}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Incident</span>
            </Link>

            <a
              href={`http://localhost:8000/api/v1/repairs/${job.id}/artifact?artifact_type=zip`}
              download
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors border border-slate-700"
            >
              <Download className="w-4 h-4 text-orange-400" />
              <span>Download Repaired ZIP</span>
            </a>
          </div>
        }
      />

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-8">
        {/* State Banner */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-xl bg-orange-500/10 text-orange-400 border border-orange-500/20">
              <Wrench className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-base font-bold text-slate-100">Status: {job.status.toUpperCase()}</h3>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  Retry #{job.retry_count} / {job.max_retries}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Patch Hash: <span className="text-orange-400">{job.patch_hash || 'Pending synthesis'}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {job.status === 'awaiting_approval' && (
              <span className="text-xs font-mono px-3 py-1.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5">
                <Clock className="w-4 h-4" /> Awaiting Human Sign-Off
              </span>
            )}
            {job.status === 'approved' && (
              <span className="text-xs font-mono px-3 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" /> Approved for Delivery
              </span>
            )}
            {job.status === 'delivered' && (
              <span className="text-xs font-mono px-3 py-1.5 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/30 flex items-center gap-1.5">
                <GitPullRequest className="w-4 h-4" /> Delivered via Pull Request
              </span>
            )}
          </div>
        </div>

        {/* Diff Viewer */}
        {latestPatch ? (
          <DiffViewer
            diff={latestPatch.patch_content}
            patchHash={latestPatch.patch_hash}
            filesModified={latestPatch.files_modified}
            repairJobId={job.id}
          />
        ) : (
          <div className="p-8 text-center rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-500">
            No candidate patch generated.
          </div>
        )}

        {/* Validation Report & Policy Evaluation */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Validation Runs */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-orange-400" />
                Isolated Verification Report
              </h4>
              {latestValidation && (
                <span
                  className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-full ${
                    latestValidation.overall_status === 'passed'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}
                >
                  {latestValidation.overall_status.toUpperCase()}
                </span>
              )}
            </div>

            {latestValidation ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono">
                    <span className="text-slate-500">Exit Code:</span> {latestValidation.exit_code}
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono">
                    <span className="text-slate-500">Execution Time:</span> {latestValidation.duration_ms} ms
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-xs font-mono text-slate-400">Sandbox Test Logs:</span>
                  <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 max-h-48 overflow-y-auto leading-relaxed">
                    {latestValidation.test_output || 'No output recorded.'}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Validation has not completed yet.</p>
            )}
          </div>

          {/* Human Review Gate / Approval Decision */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col justify-between space-y-4">
            <div>
              <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
                <CheckCircle2 className="w-4 h-4 text-orange-400" />
                Cryptographic Approval Gate
              </h4>
              <p className="text-xs text-slate-400 mt-3 leading-relaxed">
                Approvals are bound directly to SHA-256 patch hash <code className="text-orange-400 font-mono">{job.patch_hash?.slice(0, 16)}...</code>. Any change to the source repository or diff immediately invalidates this sign-off.
              </p>

              {latestApproval && (
                <div className="mt-4 p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1 font-mono">
                  <p className="text-slate-400">Decision: <span className="text-emerald-400 font-bold uppercase">{latestApproval.status}</span></p>
                  <p className="text-slate-500">Reviewer ID: {latestApproval.user_id}</p>
                  {latestApproval.reviewer_notes && <p className="text-slate-300">Notes: "{latestApproval.reviewer_notes}"</p>}
                </div>
              )}
            </div>

            {/* Decision Controls */}
            {job.status === 'awaiting_approval' && (
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <input
                  type="text"
                  placeholder="Reviewer inspection notes (optional)..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs focus:border-orange-500 focus:outline-none"
                />
                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleReject}
                    disabled={actionLoading}
                    className="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800/80 transition-colors"
                  >
                    Reject Patch
                  </button>
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition-all flex items-center justify-center gap-2"
                  >
                    {actionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    <span>Approve Candidate Patch</span>
                  </button>
                </div>
              </div>
            )}

            {job.status === 'approved' && (
              <div className="pt-3 border-t border-slate-800 space-y-3">
                <p className="text-xs text-emerald-400 font-medium">Patch approved. You can now open a GitHub Pull Request.</p>
                <button
                  onClick={handleCreatePR}
                  disabled={actionLoading}
                  className="w-full py-2.5 rounded-xl text-xs font-bold bg-orange-600 hover:bg-orange-500 text-white flex items-center justify-center gap-2 shadow-lg shadow-orange-600/20"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4" />}
                  <span>Open GitHub Pull Request</span>
                </button>
              </div>
            )}

            {prCreated && (
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
                Pull request initiated: <span className="font-mono text-white">{prCreated}</span>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
