import React, { useState } from 'react';
import { X, AlertTriangle, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { Project } from '../types';

interface NewIncidentModalProps {
  isOpen: boolean;
  projects: Project[];
  preselectedProjectId?: string;
  onClose: () => void;
  onSuccess: (incidentId: string) => void;
}

export const NewIncidentModal: React.FC<NewIncidentModalProps> = ({
  isOpen,
  projects,
  preselectedProjectId,
  onClose,
  onSuccess
}) => {
  const [projectId, setProjectId] = useState(preselectedProjectId || (projects[0]?.id || ''));
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [stackTrace, setStackTrace] = useState('');
  const [severity, setSeverity] = useState<'critical' | 'high' | 'medium' | 'low'>('high');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) {
      setError('Please select a project.');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await api.post('/incidents', {
        project_id: projectId,
        title: title.trim(),
        description: description.trim() || undefined,
        stack_trace: stackTrace.trim() || undefined,
        severity
      });
      onSuccess(res.data.id);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register incident.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-5 h-5 text-orange-400" />
            <h3 className="text-base font-bold text-slate-100">Investigate New Software Incident</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Target Project</label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-orange-500 focus:outline-none"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.detected_language || 'Project'})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Incident Title</label>
              <input
                type="text"
                required
                placeholder="e.g. TypeError: NoneType object is not iterable in compute()"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-orange-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value as any)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-orange-500 focus:outline-none"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Description (Optional)</label>
            <textarea
              rows={2}
              placeholder="Context or reproduction steps..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs focus:border-orange-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Stack Trace / Test Error Log</label>
            <textarea
              rows={5}
              placeholder="Paste stack trace, pytest failure log, or console output..."
              value={stackTrace}
              onChange={(e) => setStackTrace(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 font-mono text-xs focus:border-orange-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-500 mt-1">The diagnosis engine will parse error signatures and correlate source files.</p>
          </div>

          <div className="pt-2 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-lg text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white flex items-center gap-2 shadow-lg shadow-orange-600/20 disabled:opacity-50"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{loading ? 'Submitting Incident...' : 'Start Investigation'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
