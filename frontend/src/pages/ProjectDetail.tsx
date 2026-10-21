import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  FolderGit2, 
  FileCode2, 
  Terminal, 
  AlertTriangle, 
  Plus, 
  ShieldAlert, 
  ShieldCheck, 
  ArrowLeft,
  Loader2,
  FileText
} from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { NewIncidentModal } from '../components/NewIncidentModal';
import { api } from '../api/client';
import { Project, ProjectProfile, Incident } from '../types';

export const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [profile, setProfile] = useState<ProjectProfile | null>(null);
  const [files, setFiles] = useState<{ path: string; size_bytes: number }[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [isNewIncidentOpen, setIsNewIncidentOpen] = useState(false);

  const loadData = async () => {
    try {
      const [projRes, profRes, filesRes, incRes] = await Promise.all([
        api.get(`/projects/${id}`),
        api.get(`/projects/${id}/profile`),
        api.get(`/projects/${id}/files`),
        api.get(`/incidents?project_id=${id}`)
      ]);
      setProject(projRes.data);
      setProfile(profRes.data);
      setFiles(filesRes.data);
      setIncidents(incRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-slate-950 text-slate-500 gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
        <span>Loading workspace telemetry...</span>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex-1 p-8 text-center text-slate-400">
        Project not found.
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title={project.name}
        subtitle={`Workspace ID: ${project.id}`}
        actionButton={
          <div className="flex items-center space-x-3">
            <Link
              to="/projects"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </Link>
            <button
              onClick={() => setIsNewIncidentOpen(true)}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-600/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Report Incident</span>
            </button>
          </div>
        }
      />

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-8">
        {/* Profile Overview Card */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <span className="text-[11px] font-mono uppercase text-slate-500">Tech Stack</span>
            <p className="text-base font-bold text-slate-100 mt-1">
              {profile?.detected_language || 'Unknown'}{' '}
              {profile?.detected_framework && <span className="text-orange-400">({profile.detected_framework})</span>}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-mono uppercase text-slate-500">Files Ingested</span>
            <p className="text-base font-bold text-slate-100 mt-1 font-mono">
              {files.length} files
            </p>
          </div>
          <div>
            <span className="text-[11px] font-mono uppercase text-slate-500">Test Command</span>
            <p className="text-xs font-bold text-slate-100 mt-1 font-mono">
              {profile?.test_commands.length ? profile.test_commands.join(', ') : 'None detected'}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-mono uppercase text-slate-500">Health Assessment</span>
            <div className="mt-1">
              {project.health_status === 'healthy' ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400">
                  <ShieldCheck className="w-4 h-4" /> Healthy
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-400">
                  <ShieldAlert className="w-4 h-4" /> Degraded
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Risks Identified */}
        {profile?.risks_identified && profile.risks_identified.length > 0 && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-2">
            <div className="flex items-center space-x-2 text-amber-400 font-semibold text-xs">
              <AlertTriangle className="w-4 h-4" />
              <span>Project Risks & Hygiene Warnings:</span>
            </div>
            <ul className="list-disc list-inside text-xs text-amber-300/80 space-y-1">
              {profile.risks_identified.map((risk, idx) => (
                <li key={idx}>{risk}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Two Column Layout: Workspace File Tree & Incidents */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* File Inventory */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2 mb-4">
              <FileCode2 className="w-4 h-4 text-orange-400" />
              Workspace File Inventory ({files.length})
            </h3>
            <div className="flex-1 max-h-[400px] overflow-y-auto space-y-1 font-mono text-xs pr-2">
              {files.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-1.5 px-3 rounded-lg hover:bg-slate-800/60 text-slate-300"
                >
                  <span className="truncate">{f.path}</span>
                  <span className="text-[11px] text-slate-600 shrink-0">{(f.size_bytes / 1024).toFixed(1)} KB</span>
                </div>
              ))}
            </div>
          </div>

          {/* Incidents & History */}
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-400" />
                Active & Past Incidents ({incidents.length})
              </h3>
              <button
                onClick={() => setIsNewIncidentOpen(true)}
                className="text-xs text-orange-400 hover:text-orange-300 font-semibold"
              >
                + Investigate Issue
              </button>
            </div>

            <div className="flex-1 max-h-[400px] overflow-y-auto space-y-3 pr-2">
              {incidents.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No incidents registered for this workspace yet.
                </div>
              ) : (
                incidents.map((inc) => (
                  <Link
                    key={inc.id}
                    to={`/incidents/${inc.id}`}
                    className="block p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-100">{inc.title}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20 uppercase">
                        {inc.status}
                      </span>
                    </div>
                    {inc.error_signature && (
                      <p className="text-[11px] font-mono text-slate-400 truncate">
                        Signature: {inc.error_signature}
                      </p>
                    )}
                    <span className="text-[10px] text-slate-500 font-mono">
                      Reported: {new Date(inc.created_at).toLocaleString()}
                    </span>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      </main>

      {project && (
        <NewIncidentModal
          isOpen={isNewIncidentOpen}
          projects={[project]}
          preselectedProjectId={project.id}
          onClose={() => setIsNewIncidentOpen(false)}
          onSuccess={(incId) => {
            loadData();
          }}
        />
      )}
    </div>
  );
};
