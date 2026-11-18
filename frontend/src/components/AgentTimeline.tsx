import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  Bot, 
  Cpu, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  RefreshCw, 
  ShieldCheck, 
  Terminal, 
  FileCode2 
} from 'lucide-react';

interface AgentEvent {
  timestamp: number;
  agent_name: string;
  stage: string;
  message: string;
  level: 'info' | 'success' | 'warning' | 'error';
  data?: Record<string, any>;
}

interface AgentTimelineProps {
  jobId: string;
  title?: string;
  autoRefresh?: boolean;
}

export const AgentTimeline: React.FC<AgentTimelineProps> = ({
  jobId,
  title = 'Autonomous Multi-Agent Runtime Timeline',
  autoRefresh = false,
}) => {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const fetchTimeline = async () => {
    if (!jobId) return;
    setLoading(true);
    try {
      const res = await api.get(`/agents/timeline/${jobId}`);
      setEvents(res.data?.events || []);
    } catch (e) {
      console.error('Failed to load agent timeline:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
    if (autoRefresh) {
      const interval = setInterval(fetchTimeline, 3000);
      return () => clearInterval(interval);
    }
  }, [jobId, autoRefresh]);

  const agentIcons: Record<string, any> = {
    ProjectIntelligenceAgent: FileCode2,
    DiagnosisAgent: Terminal,
    RepairAgent: Cpu,
    TestingAgent: CheckCircle2,
    SecurityAgent: ShieldCheck,
    ReviewAgent: Bot,
    Orchestrator: Bot,
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-5 space-y-4 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-zinc-100 uppercase tracking-wider">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-500">
            {events.length} State Transitions
          </span>
          <button
            onClick={fetchTimeline}
            disabled={loading}
            className="p-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Timeline Stream */}
      {events.length === 0 ? (
        <div className="py-8 text-center text-xs text-zinc-600">
          No agent lifecycle events recorded yet for this recovery run.
        </div>
      ) : (
        <div className="relative border-l border-zinc-800/80 ml-3 pl-5 space-y-4 my-2">
          {events.map((evt, idx) => {
            const Icon = agentIcons[evt.agent_name] || Bot;
            const isSuccess = evt.level === 'success';
            const isError = evt.level === 'error';
            const isWarn = evt.level === 'warning';

            const dotBorder = isSuccess
              ? 'border-emerald-500 bg-emerald-950/60 text-emerald-400'
              : isError
              ? 'border-rose-500 bg-rose-950/60 text-rose-400'
              : isWarn
              ? 'border-amber-500 bg-amber-950/60 text-amber-400'
              : 'border-zinc-700 bg-zinc-900 text-zinc-400';

            const timeStr = new Date(evt.timestamp * 1000).toLocaleTimeString();

            return (
              <div key={idx} className="relative group">
                {/* Node Pill */}
                <div
                  className={`absolute -left-[27px] top-0.5 w-4 h-4 rounded-full border flex items-center justify-center ${dotBorder}`}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-current" />
                </div>

                {/* Event Body */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-zinc-200">{evt.agent_name}</span>
                      <span className="text-[10px] text-zinc-500 px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 uppercase">
                        {evt.stage}
                      </span>
                    </div>
                    <span className="text-[10px] text-zinc-600 tabular-nums">{timeStr}</span>
                  </div>

                  <p className="text-xs text-zinc-400 leading-relaxed break-words">{evt.message}</p>

                  {/* Expandable Data */}
                  {evt.data && (
                    <div className="mt-1.5">
                      <button
                        onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                        className="text-[10px] text-zinc-500 hover:text-zinc-300 underline underline-offset-2"
                      >
                        {expandedIndex === idx ? 'Hide Payload' : 'View Payload Data'}
                      </button>
                      {expandedIndex === idx && (
                        <pre className="mt-1.5 p-2 rounded bg-zinc-900/90 border border-zinc-800 text-[10px] text-zinc-300 overflow-x-auto max-h-48">
                          {JSON.stringify(evt.data, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
