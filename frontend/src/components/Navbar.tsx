import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, Activity } from 'lucide-react';
import { api } from '../api/client';

interface NavbarProps {
  title: string;
  subtitle?: string;
  actionButton?: React.ReactNode;
}

export const Navbar: React.FC<NavbarProps> = ({ title, subtitle, actionButton }) => {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    api.get('/health')
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, []);

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/40 backdrop-blur px-8 flex items-center justify-between sticky top-0 z-20">
      <div>
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          {title}
        </h2>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>

      <div className="flex items-center space-x-4">
        {/* Verification Engine Status Pill */}
        <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/80 text-xs">
          <Activity className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 font-mono">Sandbox:</span>
          {healthy === true ? (
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" /> Isolated
            </span>
          ) : (
            <span className="flex items-center gap-1 text-rose-400 font-medium">
              <ShieldAlert className="w-3.5 h-3.5" /> Offline
            </span>
          )}
        </div>

        {actionButton}
      </div>
    </header>
  );
};
