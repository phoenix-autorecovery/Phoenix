import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FolderGit2, 
  Plus, 
  Github, 
  Upload, 
  Terminal, 
  Activity, 
  Trash2, 
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Loader2
} from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { ImportProjectModal } from '../components/ImportProjectModal';
import { api } from '../api/client';
import { useToast } from '../context/ToastContext';
import { useMode } from '../context/ModeContext';
import { useAuth } from '../context/AuthContext';
import { Project } from '../types';

export const Projects: React.FC = () => {
  const { mode } = useMode();
  const { user } = useAuth();
  const { success, error } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [isImportOpen, setIsImportOpen] = useState(false);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects');
      setProjects(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to remove project '${name}'? This will delete the isolated workspace.`)) return;
    try {
      await api.delete(`/projects/${id}`);
      setProjects((prev) => prev.filter((p) => p.id !== id));
      success(`Project '${name}' was deleted.`, 'Workspace Removed');
    } catch (e) {
      error('Failed to delete project.', 'Delete Error');
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title="Project Workspaces"
        subtitle="Universal workspace manager for GitHub repos, ZIP archives, and local companion folders"
        actionButton={
          (user?.role === 'admin' || user?.role === 'developer') ? (
            <button
              onClick={() => setIsImportOpen(true)}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-600/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Import Project</span>
            </button>
          ) : undefined
        }
      />

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-6">
        {loading ? (
          <div className="flex items-center justify-center p-16 text-slate-500 gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
            <span className="text-sm">Loading project workspaces...</span>
          </div>
        ) : projects.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 max-w-lg mx-auto space-y-4">
            <div className="w-12 h-12 rounded-xl bg-orange-500/10 text-orange-400 mx-auto flex items-center justify-center">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-200">No Projects Found</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {(user?.role === 'admin' || user?.role === 'developer')
                ? "Connect a GitHub repository URL, upload a software project ZIP, or use the companion CLI to synchronize your local workspace."
                : "No projects have been ingested for review or audit in this workspace yet."}
            </p>
            {(user?.role === 'admin' || user?.role === 'developer') && (
              <button
                onClick={() => setIsImportOpen(true)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white transition-all inline-flex items-center gap-2"
              >
                <Plus className="w-4 h-4" /> Import First Workspace
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((proj) => {
              const SourceIcon = proj.input_type === 'github' ? Github : proj.input_type === 'zip' ? Upload : Terminal;
              return (
                <div
                  key={proj.id}
                  className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col justify-between hover:border-slate-700 transition-all shadow-lg"
                >
                  <div className="space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3 truncate">
                        <div className="p-2.5 rounded-xl bg-slate-800 text-orange-400 border border-slate-700">
                          <SourceIcon className="w-5 h-5" />
                        </div>
                        <div className="truncate">
                          <h4 className="text-sm font-bold text-slate-100 truncate">{proj.name}</h4>
                          <span className="text-[11px] font-mono text-slate-500 uppercase">{proj.input_type}</span>
                        </div>
                      </div>

                      {/* Health Indicator */}
                      {proj.health_status === 'healthy' ? (
                        <span className={`flex items-center gap-1 text-[11px] px-2.5 py-0.5 rounded-full ${
                          mode === 'simple'
                            ? 'bg-emerald-500/10 text-emerald-400 font-medium'
                            : 'bg-emerald-500/10 text-emerald-400 font-mono border border-emerald-500/20'
                        }`}>
                          <ShieldCheck className="w-3 h-3" /> {mode === 'simple' ? 'Protected' : 'Healthy'}
                        </span>
                      ) : (
                        <span className={`flex items-center gap-1 text-[11px] px-2.5 py-0.5 rounded-full ${
                          mode === 'simple'
                            ? 'bg-amber-500/10 text-amber-400 font-medium'
                            : 'bg-amber-500/10 text-amber-400 font-mono border border-amber-500/20'
                        }`}>
                          <ShieldAlert className="w-3 h-3" /> {mode === 'simple' ? 'Needs Fix' : 'Degraded'}
                        </span>
                      )}
                    </div>

                    {proj.description && (
                      <p className="text-xs text-slate-400 line-clamp-2">{proj.description}</p>
                    )}

                    <div className="pt-2 border-t border-slate-800 flex flex-wrap gap-2">
                      {proj.detected_language && (
                        <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                          {proj.detected_language}
                        </span>
                      )}
                      {proj.detected_framework && (
                        <span className="text-[11px] px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 font-mono border border-orange-500/20">
                          {proj.detected_framework}
                        </span>
                      )}
                    </div>

                    {user?.role === 'admin' && mode === 'dev' && proj.content_fingerprint && (
                      <div className="text-[10px] font-mono text-slate-500 truncate pt-1">
                        SHA-256: <span className="text-slate-400">{proj.content_fingerprint.slice(0, 20)}...</span>
                      </div>
                    )}
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
                    {user?.role === 'admin' ? (
                      <button
                        onClick={() => handleDelete(proj.id, proj.name)}
                        title="Delete project workspace"
                        className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    ) : (
                      <span className="text-[11px] text-slate-500 font-medium">Protected Workspace</span>
                    )}

                    <Link
                      to={`/projects/${proj.id}`}
                      className="inline-flex items-center space-x-1.5 text-xs font-semibold text-orange-400 hover:text-orange-300 transition-colors"
                    >
                      <span>{mode === 'simple' ? 'Open Health Portal' : 'Open Workspace'}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      <ImportProjectModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onSuccess={fetchProjects}
      />
    </div>
  );
};
