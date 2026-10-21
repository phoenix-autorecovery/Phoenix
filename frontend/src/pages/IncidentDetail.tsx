import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  AlertTriangle, 
  Wrench, 
  FileCode2, 
  ArrowLeft, 
  Loader2, 
  BrainCircuit, 
  CheckCircle2, 
  ShieldAlert,
  Terminal,
  Activity
} from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { api } from '../api/client';
import { Incident } from '../types';

export const IncidentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);
  const [repairing, setRepairing] = useState(false);

  const fetchIncident = async () => {
    try {
      const res = await api.get(`/incidents/${id}`);
      setIncident(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncident();
  }, [id]);

  const handleDiagnose = async () => {
    setDiagnosing(true);
    try {
      await api.post(`/incidents/${id}/diagnose`);
      await fetchIncident();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Diagnosis failed.');
    } finally {
      setDiagnosing(false);
    }
  };

  const handleGenerateRepair = async () => {
    setRepairing(true);
    try {
      const res = await api.post('/repairs', { incident_id: id });
      navigate(`/repairs/${res.data.id}`);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Repair generation failed.');
      setRepairing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-slate-950 text-slate-500 gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
        <span>Loading incident telemetry...</span>
      </div>
    );
  }

  if (!incident) {
    return <div className="flex-1 p-8 text-center text-slate-400">Incident not found.</div>;
  }

  const latestDiagnosis = incident.diagnoses?.[incident.diagnoses.length - 1];

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title={incident.title}
        subtitle={`Incident ID: ${incident.id}`}
        actionButton={
          <div className="flex items-center space-x-3">
            <Link
              to={`/projects/${incident.project_id}`}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Workspace</span>
            </Link>

            {!latestDiagnosis ? (
              <button
                onClick={handleDiagnose}
                disabled={diagnosing}
                className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-600/20 disabled:opacity-50 transition-all"
              >
                {diagnosing ? <Loader2 className="w-4 h-4 animate-spin" /> : <BrainCircuit className="w-4 h-4" />}
                <span>{diagnosing ? 'Analyzing Stack...' : 'Run Software Intelligence'}</span>
              </button>
            ) : (
              <button
                onClick={handleGenerateRepair}
                disabled={repairing}
                className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 disabled:opacity-50 transition-all"
              >
                {repairing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4" />}
                <span>{repairing ? 'Generating & Validating...' : 'Generate Candidate Repair'}</span>
              </button>
            )}
          </div>
        }
      />

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-8">
        {/* Incident Summary Card */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-orange-500/10 text-orange-400 border border-orange-500/20">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">{incident.title}</h3>
                <p className="text-xs font-mono text-slate-500">Error Signature: {incident.error_signature}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                Severity: {incident.severity}
              </span>
              <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/30 uppercase">
                Status: {incident.status}
              </span>
            </div>
          </div>

          {incident.description && (
            <p className="text-xs text-slate-300">{incident.description}</p>
          )}

          {/* Stack trace display */}
          {incident.stack_trace && (
            <div className="space-y-1.5 pt-2">
              <span className="text-xs font-mono text-slate-400">Observed Stack Trace:</span>
              <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-xs text-rose-300/90 overflow-x-auto leading-relaxed">
                {incident.stack_trace}
              </pre>
            </div>
          )}
        </div>

        {/* Software Intelligence & Diagnosis Section */}
        {latestDiagnosis ? (
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center space-x-3">
                <BrainCircuit className="w-5 h-5 text-orange-400" />
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Structured AI Diagnostic Report</h3>
                  <p className="text-xs font-mono text-slate-500">
                    Model: {latestDiagnosis.model_used || 'Groq Adapter'} · Time: {new Date(latestDiagnosis.created_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                  Confidence: {(latestDiagnosis.confidence_score * 100).toFixed(0)}%
                </span>
                {latestDiagnosis.is_repair_safe ? (
                  <span className="text-xs font-mono px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    Repair Safe
                  </span>
                ) : (
                  <span className="text-xs font-mono px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Human Review Required
                  </span>
                )}
              </div>
            </div>

            {/* Root cause hypothesis */}
            <div className="space-y-1.5">
              <h4 className="text-xs font-mono uppercase text-slate-400">Root-Cause Hypothesis</h4>
              <p className="text-sm text-slate-200 leading-relaxed p-4 rounded-xl bg-slate-950 border border-slate-800 font-sans">
                {latestDiagnosis.root_cause_hypothesis}
              </p>
            </div>

            {/* Evidence & Relevant Files */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h4 className="text-xs font-mono uppercase text-slate-400">Supporting Evidence</h4>
                <div className="space-y-2">
                  {latestDiagnosis.evidence?.map((ev, i) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs text-slate-300">
                      <span className="text-[10px] font-mono text-orange-400 uppercase mr-2">[{ev.type}]</span>
                      {ev.observation}
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-mono uppercase text-slate-400">Correlated Source Locations</h4>
                <div className="space-y-2">
                  {latestDiagnosis.relevant_files?.map((rf, i) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs flex items-center justify-between">
                      <div className="flex items-center space-x-2 truncate">
                        <FileCode2 className="w-4 h-4 text-orange-400 shrink-0" />
                        <span className="font-mono text-slate-200 truncate">{rf.path}</span>
                      </div>
                      {rf.lines?.length > 0 && (
                        <span className="text-[11px] font-mono text-slate-500 shrink-0">
                          Lines: {rf.lines.join('-')}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="pt-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={handleGenerateRepair}
                disabled={repairing}
                className="px-6 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-2 shadow-lg shadow-emerald-600/20 disabled:opacity-50 transition-all"
              >
                {repairing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4" />}
                <span>{repairing ? 'Synthesizing & Validating Patch...' : 'Synthesize Candidate Patch & Verify'}</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <BrainCircuit className="w-12 h-12 text-orange-400 mx-auto" />
            <h3 className="text-base font-bold text-slate-200">Incident Needs Software Intelligence Diagnosis</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
              Run PHOENIX's automated diagnosis engine to parse error patterns, search project files, and formulate a verifiable root-cause hypothesis.
            </p>
            <button
              onClick={handleDiagnose}
              disabled={diagnosing}
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white inline-flex items-center gap-2 shadow-lg shadow-orange-600/20 transition-all"
            >
              {diagnosing && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{diagnosing ? 'Diagnosing...' : 'Start Diagnosis'}</span>
            </button>
          </div>
        )}
      </main>
    </div>
  );
};
