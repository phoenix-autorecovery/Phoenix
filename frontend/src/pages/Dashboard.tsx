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
  ShieldCheck
} from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { ImportProjectModal } from '../components/ImportProjectModal';
import { api } from '../api/client';
import { DashboardMetrics } from '../types';

export const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [isImportOpen, setIsImportOpen] = useState(false);

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
    const interval = setInterval(fetchMetrics, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title="Autonomous Recovery Dashboard"
        subtitle="Real-time software telemetry, automated diagnoses, and deterministic verification gates"
        actionButton={
          <button
            onClick={() => setIsImportOpen(true)}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Import Workspace</span>
          </button>
        }
      />

      <main className="flex-1 p-8 space-y-8 max-w-7xl w-full mx-auto">
        {/* KPI Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">Active Projects</span>
              <FolderGit2 className="w-4 h-4 text-orange-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.total_projects || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">workspaces</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">Open Incidents</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.open_incidents || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">under investigation</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">Active Recovery Jobs</span>
              <Wrench className="w-4 h-4 text-blue-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.active_jobs || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">sandboxed</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-medium uppercase tracking-wider">Pending Approvals</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-4 flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-white">
                {loading ? '-' : metrics?.pending_approvals || 0}
              </span>
              <span className="text-xs text-slate-500 font-mono">awaiting sign-off</span>
            </div>
          </div>
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
                  <h3 className="text-sm font-bold text-white">Guaranteed Architectural Principle</h3>
                  <p className="text-xs text-slate-400 font-mono">Deterministic verification before release</p>
                </div>
              </div>
              <p className="text-xs leading-relaxed text-slate-300">
                In PHOENIX, the AI proposes changes; deterministic tools verify them; and explicit authorization controls where those changes go. Candidate repairs are executed solely inside disposable isolated sandboxes with strict resource limits and environment scrubbing. No changes are written to the default Git branch without reviewer sign-off.
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
                    Workspace Explorer
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">Browse tech stacks & dependencies</p>
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-orange-400 transition-colors" />
              </Link>
              <Link
                to="/approvals"
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all group flex items-center justify-between"
              >
                <div>
                  <h4 className="text-sm font-semibold text-slate-200 group-hover:text-orange-400 transition-colors">
                    Human Review Gate
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">Inspect verified diffs & reports</p>
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
                Live Audit Trail
              </h3>
              <Link to="/audit" className="text-xs text-orange-400 hover:text-orange-300 font-medium">
                View all
              </Link>
            </div>

            <div className="flex-1 space-y-3.5 overflow-y-auto max-h-[420px]">
              {loading ? (
                <p className="text-xs text-slate-500">Loading audit records...</p>
              ) : metrics?.recent_audits.length === 0 ? (
                <p className="text-xs text-slate-500">No audit events recorded yet.</p>
              ) : (
                metrics?.recent_audits.map((ev) => (
                  <div key={ev.id} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs">
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="font-mono font-semibold text-orange-400">{ev.action}</span>
                      <span className="text-slate-500 font-mono flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(ev.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate">
                      Resource: <span className="text-slate-300">{ev.resource_type}</span>{' '}
                      {ev.resource_id && <span className="font-mono text-slate-500">({ev.resource_id.slice(0, 8)})</span>}
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
