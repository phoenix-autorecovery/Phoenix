import React, { useEffect, useState } from 'react';
import { Settings as SettingsIcon, Key, Github, Shield, CheckCircle2, Loader2, Cpu } from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { api } from '../api/client';
import { SystemSettings } from '../types';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  // Form states
  const [groqKey, setGroqKey] = useState('');
  const [groqModel, setGroqModel] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [timeout, setTimeoutSeconds] = useState(60);
  const [networkIsolated, setNetworkIsolated] = useState(true);

  const fetchSettings = async () => {
    try {
      const res = await api.get('/settings');
      setSettings(res.data);
      setGroqModel(res.data.groq_model);
      setTimeoutSeconds(res.data.sandbox_timeout_seconds);
      setNetworkIsolated(res.data.sandbox_network_isolated);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    try {
      const payload: any = {
        groq_model: groqModel,
        sandbox_timeout_seconds: timeout,
        sandbox_network_isolated: networkIsolated
      };
      if (groqKey.trim()) payload.groq_api_key = groqKey.trim();
      if (githubToken.trim()) payload.github_token = githubToken.trim();

      const res = await api.post('/settings', payload);
      setSettings(res.data);
      setGroqKey('');
      setGithubToken('');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to update settings.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title="Platform Configuration & Integrations"
        subtitle="Manage Groq AI model provider, GitHub App/PAT permissions, and execution sandbox limits"
      />

      <main className="flex-1 p-8 max-w-4xl w-full mx-auto space-y-8">
        {loading ? (
          <div className="flex items-center justify-center p-16 text-slate-500 gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
            <span>Loading system configuration...</span>
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-6">
            {success && (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Configuration updated successfully!</span>
              </div>
            )}

            {/* AI Provider Config */}
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4">
              <div className="flex items-center space-x-3 border-b border-slate-800 pb-3">
                <div className="p-2 rounded-lg bg-orange-500/10 text-orange-400">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Groq Model Provider</h3>
                  <p className="text-xs text-slate-400">
                    High-speed LLM inference adapter for structured diagnosis and minimal patch synthesis
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Groq API Key</label>
                  <input
                    type="password"
                    placeholder={settings?.groq_configured ? '•••••••••••••••• (Configured)' : 'gsk_...'}
                    value={groqKey}
                    onChange={(e) => setGroqKey(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono focus:border-orange-500 focus:outline-none"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Status:{' '}
                    {settings?.groq_configured ? (
                      <span className="text-emerald-400 font-semibold">Active & Configured</span>
                    ) : (
                      <span className="text-amber-400 font-semibold">Using Mock Deterministic Provider</span>
                    )}
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Active Model</label>
                  <select
                    value={groqModel}
                    onChange={(e) => setGroqModel(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono focus:border-orange-500 focus:outline-none"
                  >
                    {settings?.available_models.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-500 mt-1">Verified against Groq's active catalogue.</p>
                </div>
              </div>
            </div>

            {/* GitHub PAT / App Config */}
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4">
              <div className="flex items-center space-x-3 border-b border-slate-800 pb-3">
                <div className="p-2 rounded-lg bg-slate-800 text-slate-200">
                  <Github className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">GitHub Integration</h3>
                  <p className="text-xs text-slate-400">
                    Required for creating repair branches and pull requests (Read-only by default)
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Personal Access Token (PAT) / App Token</label>
                <input
                  type="password"
                  placeholder={settings?.github_configured ? '•••••••••••••••• (Configured)' : 'ghp_...'}
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono focus:border-orange-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Requires <code className="text-orange-400">repo</code> scope for branch and PR creation.
                </p>
              </div>
            </div>

            {/* Sandbox Execution Policies */}
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4">
              <div className="flex items-center space-x-3 border-b border-slate-800 pb-3">
                <div className="p-2 rounded-lg bg-slate-800 text-orange-400">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Sandbox Isolation & Resource Limits</h3>
                  <p className="text-xs text-slate-400">
                    Constrains untrusted code execution during deterministic test validation
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Command Execution Timeout</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      min={10}
                      max={300}
                      value={timeout}
                      onChange={(e) => setTimeoutSeconds(parseInt(e.target.value) || 60)}
                      className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono focus:border-orange-500 focus:outline-none"
                    />
                    <span className="text-xs text-slate-400">sec</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">Strict Network Isolation</span>
                    <span className="text-[11px] text-slate-500">Prevent outbound socket calls in sandbox</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={networkIsolated}
                    onChange={(e) => setNetworkIsolated(e.target.checked)}
                    className="w-4 h-4 rounded text-orange-600 focus:ring-orange-500 bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={saving}
                className="px-6 py-2.5 rounded-xl text-xs font-bold bg-orange-600 hover:bg-orange-500 text-white flex items-center gap-2 shadow-lg shadow-orange-600/20 disabled:opacity-50 transition-all"
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>{saving ? 'Applying Configuration...' : 'Save Configuration'}</span>
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
};
