import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FolderGit2, 
  AlertTriangle, 
  Wrench, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight, 
  Plus, 
  Activity,
  ShieldCheck,
  Zap,
  Cpu,
  Terminal,
  Code2,
  Lock,
  Layers,
  Sparkles,
  FileCode,
  Eye
} from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { ImportProjectModal } from '../components/ImportProjectModal';
import { api } from '../api/client';
import { subscribeToRepairJobs, subscribeToIncidents } from '../api/supabase';
import { DashboardMetrics } from '../types';
import { useMode } from '../context/ModeContext';
import { useAuth } from '../context/AuthContext';

export const Dashboard: React.FC = () => {
  const { mode } = useMode();
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  const fetchMetrics = async () => {
    try {
      const res = await api.get('/monitoring/metrics');
      setMetrics(res.data);
    } catch (e) {
      console.error('Failed to load metrics:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000); // polling fallback

    // Supabase Realtime live subscriptions
    const unsubRepairs = subscribeToRepairJobs(() => fetchMetrics());
    const unsubIncidents = subscribeToIncidents(() => fetchMetrics());

    return () => {
      clearInterval(interval);
      unsubRepairs();
      unsubIncidents();
    };
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title="Autonomous Recovery Dashboard"
        subtitle={
          mode === 'simple'
            ? 'Executive overview of workspace health, automated recovery, and release approvals'
            : 'Real-time software telemetry, automated diagnoses, and deterministic verification gates'
        }
        actionButton={
          (user?.role === 'admin' || user?.role === 'developer') ? (
            <button
              onClick={() => setIsImportOpen(true)}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-600/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Import Workspace</span>
            </button>
          ) : undefined
        }
      />

      <main className="flex-1 p-8 space-y-8 max-w-7xl w-full mx-auto">
        {/* HERO BANNER: Admin gets dev/simple controls; other roles get clean status */}
        {user?.role === 'admin' ? (
          mode === 'simple' ? (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-500/10 via-orange-500/5 to-slate-900 border border-amber-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30 shrink-0">
                  <Eye className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-amber-200 uppercase tracking-wider">Simple Executive Mode Active</h4>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Complex terminal output, AST diagnostics, and raw traces are condensed into plain-English business health indicators.
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700 shrink-0">
                Toggle via top-right (⌘D)
              </span>
            </div>
          ) : (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-slate-900 to-slate-900 border border-emerald-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm font-mono">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shrink-0">
                  <Code2 className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-emerald-300 uppercase tracking-wider">Developer & Telemetry Mode Active</h4>
                  <p className="text-xs text-slate-300 mt-0.5 font-sans">
                    Raw OpenTelemetry spans, Groq inference latency, AST security filters, and deterministic test traces enabled.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                className="text-[11px] px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/30 transition-all shrink-0 flex items-center gap-1.5"
              >
                <Terminal className="w-3 h-3" />
                <span>{showRawJson ? 'Hide Raw JSON' : 'Inspect Raw Metrics JSON'}</span>
              </button>
            </div>
          )
        ) : (
          <div className="p-4 rounded-2xl bg-gradient-to-r from-orange-500/10 via-slate-900 to-slate-900 border border-orange-500/20 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30 shrink-0">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">Autonomous Workspace Protection</h4>
                <p className="text-xs text-slate-300 mt-0.5">
                  Continuously monitoring code health, verifying candidate repairs in isolated sandboxes, and securing delivery.
                </p>
              </div>
            </div>
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shrink-0 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" /> All Systems Active
            </span>
          </div>
        )}

        {/* DEV MODE RAW JSON VIEWER - Admin Only */}
        {user?.role === 'admin' && mode === 'dev' && showRawJson && (
          <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>GET /monitoring/metrics (Realtime Telemetry Payload)</span>
              <span className="text-emerald-400">HTTP 200 OK</span>
            </div>
            <pre className="p-4 rounded-xl bg-slate-950 font-mono text-xs text-emerald-300/90 max-h-60 overflow-y-auto leading-relaxed border border-slate-800">
              {JSON.stringify(metrics, null, 2)}
            </pre>
          </div>
        )}

        {/* KPI Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">
                {mode === 'simple' ? 'Monitored Workspaces' : 'Active Projects'}
              </span>
              <FolderGit2 className="w-4 h-4 text-orange-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.total_projects || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {mode === 'simple' ? 'under 24/7 protection' : 'workspaces'}
              </span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">
                {mode === 'simple' ? 'Software Defects' : 'Open Incidents'}
              </span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.open_incidents || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {mode === 'simple' ? 'requiring resolution' : 'under investigation'}
              </span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">
                {mode === 'simple' ? 'Verified Fixes' : 'Active Recovery Jobs'}
              </span>
              <Wrench className="w-4 h-4 text-blue-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.active_jobs || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {mode === 'simple' ? 'tested in isolation' : 'sandboxed'}
              </span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">
                {mode === 'simple' ? 'Release Sign-Offs' : 'Pending Approvals'}
              </span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.pending_approvals || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {mode === 'simple' ? 'ready to deploy' : 'awaiting sign-off'}
              </span>
            </div>
          </div>
        </div>

        {/* DEV MODE LIVE TELEMETRY TELEGRAPH - Admin Only */}
        {user?.role === 'admin' && mode === 'dev' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="flex items-center gap-1.5 text-orange-400 font-semibold">
                  <Cpu className="w-4 h-4" /> Groq Engine
                </span>
                <span className="text-emerald-400">ONLINE</span>
              </div>
              <p className="text-slate-200">LLaMA 3.1 70B & Qwen 2.5 32B</p>
              <div className="flex justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800">
                <span>Inference Latency: ~380ms</span>
                <span>Context: 128k</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="flex items-center gap-1.5 text-blue-400 font-semibold">
                  <Layers className="w-4 h-4" /> Sandbox Host
                </span>
                <span className="text-emerald-400">READY</span>
              </div>
              <p className="text-slate-200">Isolated Workspaces (tmpfs)</p>
              <div className="flex justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800">
                <span>Execution Timeout: 60s</span>
                <span>Security: Zip-Slip Proof</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                  <Lock className="w-4 h-4" /> Policy Guardian
                </span>
                <span className="text-emerald-400">ENFORCED</span>
              </div>
              <p className="text-slate-200">Cryptographic SHA-256 Hashes</p>
              <div className="flex justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800">
                <span>AST Injection Check: Active</span>
                <span>Veto Rate: 0%</span>
              </div>
            </div>
          </div>
        )}

        {/* Auto-Pilot Highlight Banner */}
        <div className="p-5 rounded-2xl bg-gradient-to-r from-orange-950/40 via-slate-900 to-slate-900 border border-orange-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-orange-600/20 text-orange-400 border border-orange-500/30">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white">
                  {mode === 'simple'
                    ? 'Autonomous Self-Healing Protection Active'
                    : 'Autonomous Error Detection & Self-Healing Engine'}
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 font-bold uppercase">
                  {mode === 'simple' ? 'AI Auto-Pilot' : 'Groq LLaMA 3.1 & Qwen'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {mode === 'simple'
                  ? 'Phoenix automatically spots bugs in your repositories, synthesizes tested solutions, and prepares 1-click approvals.'
                  : 'Workspaces automatically scan for failing tests and syntax regressions, synthesize high-precision repairs with Groq, verify in sandboxes, and self-heal automatically.'}
              </p>
            </div>
          </div>
          <Link
            to="/projects"
            className="shrink-0 px-4 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white flex items-center gap-1.5 shadow-lg shadow-orange-600/20 transition-all"
          >
            <span>{mode === 'simple' ? 'Browse Workspaces' : 'View Monitored Projects'}</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Operational Grid: Architecture Principle & Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content: Principle & Verification Engine */}
          <div className="lg:col-span-2 space-y-6">
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2 rounded-lg bg-orange-500/10 text-orange-400">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {mode === 'simple' ? 'Guaranteed Safety Standards' : 'Guaranteed Architectural Principle'}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">
                    {mode === 'simple' ? 'No bad code ever reaches your branches' : 'Deterministic verification before release'}
                  </p>
                </div>
              </div>
              <p className="text-xs leading-relaxed text-slate-300">
                {mode === 'simple'
                  ? 'All fixes generated by Phoenix are verified against strict automated test suites inside disposable sandboxes before you see them. You maintain complete human authority over every patch delivered to your repositories.'
                  : 'In PHOENIX, the AI proposes changes; deterministic tools verify them; and explicit authorization controls where those changes go. Candidate repairs are executed solely inside disposable isolated sandboxes with strict resource limits and environment scrubbing. No changes are written to the default Git branch without reviewer sign-off.'}
              </p>
              <div className="mt-6 grid grid-cols-3 gap-4 pt-4 border-t border-slate-800/80 text-center">
                <div>
                  <span className="text-[11px] font-mono text-slate-400 uppercase">Input Gate</span>
                  <p className="text-xs font-semibold text-slate-200 mt-0.5">ZIP-Slip & SSRF Shield</p>
                </div>
                <div>
                  <span className="text-[11px] font-mono text-slate-400 uppercase">Execution</span>
                  <p className="text-xs font-semibold text-slate-200 mt-0.5">Isolated Disposable Sandbox</p>
                </div>
                <div>
                  <span className="text-[11px] font-mono text-slate-400 uppercase">Sign-Off</span>
                  <p className="text-xs font-semibold text-slate-200 mt-0.5">Cryptographic Patch Binding</p>
                </div>
              </div>
            </div>

            {/* Quick Links */}
            <div className="grid grid-cols-2 gap-4">
              <Link
                to="/projects"
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all group flex items-center justify-between"
              >
                <div>
                  <h4 className="text-sm font-semibold text-slate-200 group-hover:text-orange-400 transition-colors">
                    {mode === 'simple' ? 'Workspace Explorer' : 'Workspace Explorer'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {mode === 'simple' ? 'Check project health and start auto-repair' : 'Browse tech stacks & dependencies'}
                  </p>
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-orange-400 transition-colors" />
              </Link>
              <Link
                to="/approvals"
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all group flex items-center justify-between"
              >
                <div>
                  <h4 className="text-sm font-semibold text-slate-200 group-hover:text-orange-400 transition-colors">
                    {mode === 'simple' ? 'Pending Release Gate' : 'Human Review Gate'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {mode === 'simple' ? 'Review & approve verified patches' : 'Inspect verified diffs & reports'}
                  </p>
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-orange-400 transition-colors" />
              </Link>
            </div>
          </div>

          {/* Right Column: Live Audit Activity */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-orange-400" />
                {mode === 'simple' ? 'Recent Recovery Activity' : 'Live Audit Trail'}
              </h3>
              <Link to="/audit" className="text-xs text-orange-400 hover:text-orange-300 font-medium">
                View all
              </Link>
            </div>

            <div className="flex-1 space-y-3.5 overflow-y-auto max-h-[420px]">
              {loading ? (
                <p className="text-xs text-slate-500">Loading audit records...</p>
              ) : metrics?.recent_audits.length === 0 ? (
                <p className="text-xs text-slate-500">No events recorded yet.</p>
              ) : (
                metrics?.recent_audits.map((ev) => (
                  <div key={ev.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs">
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="font-mono font-semibold text-orange-400">
                        {mode === 'simple'
                          ? ev.action.replace(/_/g, ' ').toUpperCase()
                          : ev.action}
                      </span>
                      <span className="text-slate-500 font-mono flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(ev.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate">
                      {mode === 'simple' ? (
                        <span>Verified event on <strong className="text-slate-200">{ev.resource_type}</strong></span>
                      ) : (
                        <span>
                          Resource: <span className="text-slate-300">{ev.resource_type}</span>{' '}
                          {ev.resource_id && <span className="font-mono text-slate-500">({ev.resource_id.slice(0, 8)})</span>}
                        </span>
                      )}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>

      <ImportProjectModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onSuccess={fetchMetrics}
      />
    </div>
  );
};
