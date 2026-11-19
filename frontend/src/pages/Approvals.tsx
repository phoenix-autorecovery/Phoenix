import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ArrowRight, 
  ShieldCheck, 
  Loader2, 
  FileCode2, 
  AlertTriangle,
  RefreshCw,
  FolderKanban,
  Check,
  X
} from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { api } from '../api/client';
import { Approval } from '../types';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export const Approvals: React.FC = () => {
  const { user } = useAuth();
  const { success, error } = useToast();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [notesState, setNotesState] = useState<{ [id: string]: string }>({});

  const fetchApprovals = () => {
    setLoading(true);
    api.get('/approvals')
      .then((res) => setApprovals(res.data))
      .catch((e) => {
        console.error(e);
        error('Failed to load approvals queue.', 'Network Error');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleApprove = async (appr: Approval) => {
    const notes = notesState[appr.id] || 'Cryptographically verified and approved by human reviewer.';
    setActionLoading(appr.id);
    try {
      await api.post(`/approvals/${appr.repair_job_id}/approve`, {
        patch_hash: appr.patch_hash,
        notes: notes
      });
      success('Cryptographic approval registered. Patch applied to project workspace.', 'Patch Approved');
      fetchApprovals();
    } catch (e: any) {
      error(e.response?.data?.detail || 'Approval failed.', 'Approval Error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (appr: Approval) => {
    const notes = notesState[appr.id] || 'Candidate patch rejected by reviewer.';
    setActionLoading(appr.id);
    try {
      await api.post(`/approvals/${appr.repair_job_id}/reject`, {
        patch_hash: appr.patch_hash,
        notes: notes
      });
      success('Candidate patch rejected.', 'Patch Rejected');
      fetchApprovals();
    } catch (e: any) {
      error(e.response?.data?.detail || 'Rejection failed.', 'Rejection Error');
    } finally {
      setActionLoading(null);
    }
  };

  const pendingApprovals = approvals.filter((a) => a.status === 'pending');
  const resolvedApprovals = approvals.filter((a) => a.status !== 'pending');

  const canDecide = user?.role === 'admin' || user?.role === 'reviewer' || user?.role === 'developer';

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950 text-slate-100">
      <Navbar
        title="Human Review & Cryptographic Approval Gate"
        subtitle="Policy enforcement: deterministic cryptographic sign-off required before repository delivery"
        actionButton={
          <button
            onClick={fetchApprovals}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-orange-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Queue</span>
          </button>
        }
      />

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-8">
        {loading ? (
          <div className="flex items-center justify-center p-16 text-slate-500 gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
            <span>Loading approvals queue...</span>
          </div>
        ) : (
          <>
            {/* SECTION 1: PENDING APPROVAL REQUESTS */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Clock className="w-5 h-5 text-amber-400" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                    Pending Approval Requests ({pendingApprovals.length})
                  </h3>
                </div>
                {pendingApprovals.length > 0 && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
                    Requires Human Action
                  </span>
                )}
              </div>

              {pendingApprovals.length === 0 ? (
                <div className="p-10 text-center rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3">
                  <ShieldCheck className="w-10 h-10 text-emerald-400 mx-auto" />
                  <h4 className="text-sm font-bold text-slate-200">No Pending Approvals</h4>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    When candidate repairs pass deterministic isolated verification, they will queue here for human review and cryptographic SHA-256 sign-off.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {pendingApprovals.map((appr) => (
                    <div
                      key={appr.id}
                      className="p-6 rounded-2xl bg-slate-900 border border-amber-500/30 shadow-lg shadow-amber-950/20 space-y-4 transition-all hover:border-amber-500/50"
                    >
                      {/* Top Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                            AWAITING APPROVAL
                          </span>
                          {appr.project_name && (
                            <span className="flex items-center gap-1 text-xs text-slate-300 font-medium">
                              <FolderKanban className="w-3.5 h-3.5 text-slate-500" />
                              {appr.project_name}
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-mono text-slate-400">
                          Queued: {new Date(appr.created_at).toLocaleString()}
                        </span>
                      </div>

                      {/* Incident & Fix Details */}
                      <div className="space-y-2">
                        {appr.incident_title && (
                          <h4 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                            <span>Defect:</span>
                            <span className="text-orange-400 font-mono text-xs">{appr.incident_title}</span>
                          </h4>
                        )}
                        <p className="text-xs text-slate-300 leading-relaxed">
                          <strong>Intended Fix:</strong> {appr.diff_summary || 'Verified autonomous repair candidate ready for application.'}
                        </p>
                        <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs font-mono">
                          <div className="truncate">
                            <span className="text-slate-500 mr-2">SHA-256 Patch Hash:</span>
                            <span className="text-emerald-400">{appr.patch_hash}</span>
                          </div>
                          <Link
                            to={`/repairs/${appr.repair_job_id}`}
                            className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1 shrink-0 ml-4 font-sans font-medium"
                          >
                            <span>Inspect Full Diff</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>

                      {/* Reviewer Note Input & Action Buttons */}
                      {canDecide ? (
                        <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
                          <input
                            type="text"
                            placeholder="Optional reviewer notes for audit log..."
                            value={notesState[appr.id] || ''}
                            onChange={(e) =>
                              setNotesState({ ...notesState, [appr.id]: e.target.value })
                            }
                            className="flex-1 w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:border-orange-500 focus:outline-none"
                          />
                          <div className="flex items-center space-x-2 w-full sm:w-auto shrink-0">
                            <button
                              onClick={() => handleReject(appr)}
                              disabled={actionLoading === appr.id}
                              className="flex-1 sm:flex-none px-4 py-2 rounded-xl text-xs font-semibold bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 transition-colors flex items-center justify-center gap-1.5"
                            >
                              <X className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>
                            <button
                              onClick={() => handleApprove(appr)}
                              disabled={actionLoading === appr.id}
                              className="flex-1 sm:flex-none px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/40 transition-all flex items-center justify-center gap-1.5"
                            >
                              {actionLoading === appr.id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Check className="w-3.5 h-3.5" />
                              )}
                              <span>Accept & Approve</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800 text-xs text-purple-400 font-mono">
                          Auditor role view: sign-offs are restricted to Reviewers and System Administrators.
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* SECTION 2: RESOLVED APPROVALS HISTORY */}
            {resolvedApprovals.length > 0 && (
              <div className="space-y-4 pt-4 border-t border-slate-800">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-5 h-5 text-slate-400" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                    Decision Audit History ({resolvedApprovals.length})
                  </h3>
                </div>

                <div className="space-y-3">
                  {resolvedApprovals.map((appr) => (
                    <div
                      key={appr.id}
                      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center space-x-3">
                          <span
                            className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-full ${
                              appr.status === 'approved'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : appr.status === 'rejected'
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                            }`}
                          >
                            {appr.status.toUpperCase()}
                          </span>
                          {appr.project_name && (
                            <span className="text-xs text-slate-400 font-medium">
                              Project: <strong className="text-slate-200">{appr.project_name}</strong>
                            </span>
                          )}
                          <span className="text-xs font-mono text-slate-500">
                            Repair: {appr.repair_job_id.slice(0, 8)}
                          </span>
                        </div>
                        <p className="text-xs font-mono text-slate-400 truncate max-w-xl">
                          Patch SHA-256: <span className="text-orange-400">{appr.patch_hash}</span>
                        </p>
                        {appr.reviewer_notes && (
                          <p className="text-xs text-slate-300 italic">Notes: "{appr.reviewer_notes}"</p>
                        )}
                        {appr.decided_at && (
                          <p className="text-[11px] text-slate-500 font-mono">
                            Decided at: {new Date(appr.decided_at).toLocaleString()}
                          </p>
                        )}
                      </div>

                      <Link
                        to={`/repairs/${appr.repair_job_id}`}
                        className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors shrink-0"
                      >
                        <span>Inspect Diff</span>
                        <ArrowRight className="w-3.5 h-3.5 text-orange-400" />
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
};
