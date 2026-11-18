import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, Activity, Search, Eye, Code2 } from 'lucide-react';
import { api } from '../api/client';
import { useMode } from '../context/ModeContext';

interface NavbarProps {
  title: string;
  subtitle?: string;
  actionButton?: React.ReactNode;
}

export const Navbar: React.FC<NavbarProps> = ({ title, subtitle, actionButton }) => {
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const { mode, setMode } = useMode();

  useEffect(() => {
    api.get('/health')
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, []);

  const triggerCmdK = () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }));
  };

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-4">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2 tracking-tight">
            {title}
          </h2>
          {subtitle && <p className="text-[11px] text-zinc-500 font-mono truncate max-w-md">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Command Palette Trigger */}
        <button
          onClick={triggerCmdK}
          className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800/80 border border-zinc-800 text-zinc-400 text-xs transition-colors"
        >
          <Search className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-zinc-400">Search actions...</span>
          <kbd className="font-mono text-[10px] bg-zinc-800 text-zinc-400 px-1 py-0.2 rounded border border-zinc-700">⌘K</kbd>
        </button>

        {/* Dual-Mode Toggle: Simple View vs Dev Mode */}
        <div className="flex items-center p-0.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs">
          <button
            onClick={() => setMode('simple')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
              mode === 'simple'
                ? 'bg-zinc-800 text-zinc-100 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
            title="Simple View: Non-technical overview of defects and plain-English solutions"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Simple</span>
          </button>
          <button
            onClick={() => setMode('dev')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
              mode === 'dev'
                ? 'bg-zinc-800 text-emerald-400 shadow-sm font-mono'
                : 'text-zinc-400 hover:text-zinc-200 font-mono'
            }`}
            title="Dev Mode: Raw AST, microsecond test logs, unified diff hunks, and Groq token telemetry (⌘D)"
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Dev Mode</span>
          </button>
        </div>

        {/* Sandbox Health Indicator */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-zinc-900/60 border border-zinc-800 text-[11px]">
          <Activity className="w-3 h-3 text-zinc-500" />
          <span className="text-zinc-500 font-mono">Sandbox:</span>
          {healthy === true ? (
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <ShieldCheck className="w-3 h-3" /> Ready
            </span>
          ) : (
            <span className="flex items-center gap-1 text-rose-400 font-medium">
              <ShieldAlert className="w-3 h-3" /> Offline
            </span>
          )}
        </div>

        {actionButton}
      </div>
    </header>
  );
};
