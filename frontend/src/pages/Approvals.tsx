import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Clock, ArrowRight, ShieldCheck, Loader2 } from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { api } from '../api/client';
import { Approval } from '../types';

export const Approvals: React.FC = () => {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/approvals')
      .then((res) => setApprovals(res.data))
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title="Human Review & Approval Gate"
        subtitle="Policy enforcement: deterministic cryptographic sign-off required before repository delivery"
      />

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-6">
        {loading ? (
          <div className="flex items-center justify-center p-16 text-slate-500 gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
            <span>Loading approval queue...</span>
          </div>
        ) : approvals.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 max-w-md mx-auto space-y-3">
            <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto" />
            <h3 className="text-base font-bold text-slate-200">No Pending Approvals</h3>
            <p className="text-xs text-slate-400">
              When AI candidate repairs pass deterministic validation, they will appear here for human reviewer sign-off.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {approvals.map((appr) => (
              <div
                key={appr.id}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-3">
                    <span
                      className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-full ${
                        appr.status === 'approved'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : appr.status === 'rejected'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}
                    >
                      {appr.status.toUpperCase()}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      Repair ID: {appr.repair_job_id.slice(0, 8)}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-slate-400 truncate">
                    Patch Hash: <span className="text-orange-400">{appr.patch_hash}</span>
                  </p>
                  {appr.reviewer_notes && (
                    <p className="text-xs text-slate-300">Notes: "{appr.reviewer_notes}"</p>
                  )}
                </div>

                <Link
                  to={`/repairs/${appr.repair_job_id}`}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                >
                  <span>Inspect Diff</span>
                  <ArrowRight className="w-3.5 h-3.5 text-orange-400" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};
