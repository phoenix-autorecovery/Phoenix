import React, { useState } from 'react';
import { X, Github, Upload, Terminal, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../api/client';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ImportProjectModal: React.FC<ImportModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [tab, setTab] = useState<'github' | 'zip' | 'local'>('github');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);

  if (!isOpen) return null;

  const handleGitHubImport = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post('/ingestion/github', {
        repository_url: repoUrl.trim(),
        branch: branch.trim() || undefined
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to clone repository.');
    } finally {
      setLoading(false);
    }
  };

  const handleZipImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!zipFile) {
      setError('Please select a ZIP file to upload.');
      return;
    }
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('name', projectName || zipFile.name.replace('.zip', ''));
    formData.append('description', projectDesc);
    formData.append('file', zipFile);

    try {
      await api.post('/ingestion/zip', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'ZIP ingestion failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-100">Import Workspace into PHOENIX</h3>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-slate-800 bg-slate-950/40">
          <button
            onClick={() => { setTab('github'); setError(null); }}
            className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
              tab === 'github' ? 'border-orange-500 text-orange-400 bg-slate-900/40' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Github className="w-4 h-4" /> GitHub Repository
          </button>
          <button
            onClick={() => { setTab('zip'); setError(null); }}
            className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
              tab === 'zip' ? 'border-orange-500 text-orange-400 bg-slate-900/40' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Upload className="w-4 h-4" /> ZIP Archive
          </button>
          <button
            onClick={() => { setTab('local'); setError(null); }}
            className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-colors ${
              tab === 'local' ? 'border-orange-500 text-orange-400 bg-slate-900/40' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-4 h-4" /> Local Companion
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {tab === 'github' && (
            <form onSubmit={handleGitHubImport} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">GitHub Repository URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/owner/repository"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-orange-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-500 mt-1">Accepts public repositories or private repos configured with PAT.</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Branch (Optional)</label>
                <input
                  type="text"
                  placeholder="main or master"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-orange-500 focus:outline-none"
                />
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
                  <span>{loading ? 'Ingesting Repository...' : 'Import Repository'}</span>
                </button>
              </div>
            </form>
          )}

          {tab === 'zip' && (
            <form onSubmit={handleZipImport} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Project Name</label>
                <input
                  type="text"
                  placeholder="e.g. My Service"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-orange-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">ZIP Archive File</label>
                <input
                  type="file"
                  accept=".zip"
                  required
                  onChange={(e) => setZipFile(e.target.files ? e.target.files[0] : null)}
                  className="w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-orange-400 hover:file:bg-slate-700 cursor-pointer"
                />
                <p className="text-[11px] text-slate-500 mt-1">Protected by ZIP-Slip scanner and archive-bomb quota limits.</p>
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
                  <span>{loading ? 'Extracting & Scanning...' : 'Upload & Ingest'}</span>
                </button>
              </div>
            </form>
          )}

          {tab === 'local' && (
            <div className="space-y-4 text-xs text-slate-300">
              <p>To safely synchronize a local project without exposing root credentials or arbitrary paths, use the companion CLI:</p>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 font-mono text-[11px] space-y-2">
                <p className="text-slate-500"># 1. Run local companion CLI scan & sync</p>
                <p className="text-orange-400">python cli/phoenix_cli.py sync /path/to/project --token &lt;YOUR_JWT_TOKEN&gt;</p>
              </div>
              <p className="text-slate-400 text-[11px]">
                The CLI respects your <code className="text-orange-300">.gitignore</code> rules, strips private keys and node_modules, and creates an isolated workspace copy.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
