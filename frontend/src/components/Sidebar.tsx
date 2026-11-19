import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderGit2, 
  AlertTriangle, 
  Wrench, 
  CheckCircle2, 
  ScrollText, 
  Settings, 
  LogOut,
  Flame,
  Terminal,
  Eye,
  Code2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useMode } from '../context/ModeContext';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const { mode, toggleMode } = useMode();

  // Role-specific streamlined navigation: non-admins only see what they need
  const allNavItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard, roles: ['admin', 'developer', 'reviewer', 'auditor'] },
    { to: '/projects', label: 'Projects', icon: FolderGit2, roles: ['admin', 'developer', 'reviewer', 'auditor'] },
    { to: '/incidents', label: 'Incidents', icon: AlertTriangle, roles: ['admin', 'developer', 'reviewer', 'auditor'] },
    { to: '/repairs', label: 'Repairs & Diffs', icon: Wrench, roles: ['admin', 'developer', 'reviewer', 'auditor'] },
    { to: '/approvals', label: 'Approvals Gate', icon: CheckCircle2, roles: ['admin', 'developer', 'reviewer'] },
    { to: '/mcp', label: 'MCP & Agents', icon: Terminal, roles: ['admin'] },
    { to: '/audit', label: 'Audit Trail', icon: ScrollText, roles: ['admin', 'auditor'] },
    { to: '/settings', label: 'Settings', icon: Settings, roles: ['admin'] },
  ];

  const userRole = user?.role || 'developer';
  const navItems = allNavItems.filter((item) => item.roles.includes(userRole));

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen sticky top-0 select-none">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-orange-600 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
          <Flame className="w-6 h-6 text-white animate-pulse" />
        </div>
        <div>
          <h1 className="font-extrabold text-lg text-white tracking-wider flex items-center gap-1.5">
            PHOENIX
            <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30">
              v1.0
            </span>
          </h1>
          <p className="text-xs text-slate-400 font-mono">Autonomous Recovery</p>
        </div>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-orange-500/20 to-orange-500/5 text-orange-400 border-l-4 border-orange-500'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </div>
            </NavLink>
          );
        })}
      </nav>

      {/* Mode Switcher Pill - Admin Only to keep UI simple for everyone else */}
      {userRole === 'admin' && (
        <div className="px-3 pb-3">
          <button
            onClick={toggleMode}
            className={`w-full p-2.5 rounded-xl border flex items-center justify-between text-xs transition-all ${
              mode === 'simple'
                ? 'bg-amber-500/10 border-amber-500/20 text-amber-300 hover:bg-amber-500/20'
                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20 font-mono'
            }`}
            title="Click to toggle between Simple Executive View and Dev Inspector Mode (⌘D)"
          >
            <div className="flex items-center gap-2">
              {mode === 'simple' ? <Eye className="w-4 h-4 text-amber-400" /> : <Code2 className="w-4 h-4 text-emerald-400" />}
              <span className="font-semibold">{mode === 'simple' ? 'Simple Mode' : 'Dev Mode Active'}</span>
            </div>
            <span className="text-[10px] opacity-75 underline">Switch</span>
          </button>
        </div>
      )}

      {/* User Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 truncate">
            <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-orange-400 border border-slate-700">
              {user?.full_name?.charAt(0) || user?.email?.charAt(0).toUpperCase()}
            </div>
            <div className="truncate">
              <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name || user?.email}</p>
              <span className={`inline-block text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold uppercase ${
                user?.role === 'admin'
                  ? 'bg-orange-500/20 text-orange-400 border-orange-500/30'
                  : user?.role === 'reviewer'
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                  : user?.role === 'auditor'
                  ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                  : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
              }`}>
                {user?.role}
              </span>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log out"
            className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-md transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
