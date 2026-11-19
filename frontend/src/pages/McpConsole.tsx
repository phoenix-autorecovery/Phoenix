import React, { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { api } from '../api/client';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { Terminal, Shield, Cpu, RefreshCw, Play, Database, BookOpen, Layers, CheckCircle2, AlertCircle } from 'lucide-react';

interface ToolDef {
  name: string;
  description: string;
  category: 'READ' | 'WRITE' | 'EXECUTE' | 'ADMINISTRATIVE';
  inputSchema: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
  requires_approval: boolean;
}

interface ResourceDef {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}

interface PromptDef {
  name: string;
  description?: string;
  arguments?: { name: string; description?: string; required?: boolean }[];
}

export const McpConsole: React.FC = () => {
  const { user } = useAuth();
  const { success, error } = useToast();
  const [activeTab, setActiveTab] = useState<'tools' | 'resources' | 'prompts' | 'servers'>('tools');
  const [tools, setTools] = useState<ToolDef[]>([]);
  const [resources, setResources] = useState<ResourceDef[]>([]);
  const [prompts, setPrompts] = useState<PromptDef[]>([]);
  const [servers, setServers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Tool execution state
  const [selectedTool, setSelectedTool] = useState<ToolDef | null>(null);
  const [toolArgsJson, setToolArgsJson] = useState<string>('{}');
  const [toolResult, setToolResult] = useState<any>(null);
  const [executing, setExecuting] = useState(false);

  // Resource read state
  const [selectedUri, setSelectedUri] = useState<string>('phoenix://system/health');
  const [resourceContent, setResourceContent] = useState<string | null>(null);
  const [readingResource, setReadingResource] = useState(false);

  const fetchMcpData = async () => {
    setLoading(true);
    try {
      const [toolsRes, resRes, promptsRes, serversRes] = await Promise.all([
        api.get('/mcp/tools'),
        api.get('/mcp/resources'),
        api.get('/mcp/prompts'),
        api.get('/mcp/servers'),
      ]);
      setTools(toolsRes.data || []);
      setResources(resRes.data || []);
      setPrompts(promptsRes.data || []);
      setServers(serversRes.data || []);
      if (toolsRes.data?.length > 0 && !selectedTool) {
        setSelectedTool(toolsRes.data[0]);
        // Default sample args
        const defaultArgs: Record<string, string> = {};
        const props = toolsRes.data[0].inputSchema?.properties || {};
        Object.keys(props).forEach((k) => {
          defaultArgs[k] = 'example_id';
        });
        setToolArgsJson(JSON.stringify(defaultArgs, null, 2));
      }
    } catch (e: any) {
      error(e.response?.data?.detail || 'Failed to fetch MCP registry metadata.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMcpData();
  }, []);

  const handleSelectTool = (tool: ToolDef) => {
    setSelectedTool(tool);
    setToolResult(null);
    const defaultArgs: Record<string, string> = {};
    const props = tool.inputSchema?.properties || {};
    Object.keys(props).forEach((k) => {
      defaultArgs[k] = k === 'format' ? 'technical' : 'sample_id';
    });
    setToolArgsJson(JSON.stringify(defaultArgs, null, 2));
  };

  const handleExecuteTool = async () => {
    if (!selectedTool) return;
    setExecuting(true);
    setToolResult(null);
    try {
      let parsedArgs = {};
      try {
        parsedArgs = JSON.parse(toolArgsJson);
      } catch (e) {
        error('Invalid JSON arguments format.');
        setExecuting(false);
        return;
      }

      const res = await api.post('/mcp/tools/call', {
        name: selectedTool.name,
        arguments: parsedArgs,
      });
      setToolResult(res.data);
      if (res.data?.isError) {
        error(res.data.content?.[0]?.text || 'Tool returned error.', 'MCP Execution Warning');
      } else {
        success(`Executed ${selectedTool.name} successfully.`, 'MCP Call Passed');
      }
    } catch (e: any) {
      const msg = e.response?.data?.detail || 'Execution failed';
      setToolResult({ isError: true, content: [{ text: msg }] });
      error(msg, 'Execution Failed');
    } finally {
      setExecuting(false);
    }
  };

  const handleReadResource = async (uri: string) => {
    setSelectedUri(uri);
    setReadingResource(true);
    try {
      const res = await api.get(`/mcp/resources/read?uri=${encodeURIComponent(uri)}`);
      const contents = res.data?.contents || [];
      const text = contents[0]?.text || 'No content';
      setResourceContent(text);
      success(`Read ${uri}`, 'Resource Retrieved');
    } catch (e: any) {
      setResourceContent(JSON.stringify(e.response?.data || { error: 'Failed to read resource' }, null, 2));
      error(e.response?.data?.detail || 'Could not read resource.');
    } finally {
      setReadingResource(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-zinc-950 overflow-y-auto">
      <Navbar
        title="Model Context Protocol (MCP) Console"
        subtitle="Universal tool execution gateway, resource reader, and prompt templates"
      />

      {user?.role !== 'admin' ? (
        <div className="p-12 text-center rounded-2xl bg-zinc-900 border border-zinc-800 max-w-lg mx-auto space-y-4 my-16">
          <div className="w-12 h-12 rounded-xl bg-orange-500/10 text-orange-400 mx-auto flex items-center justify-center">
            <Shield className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-zinc-200">Administrator Access Required</h3>
          <p className="text-xs text-zinc-400 leading-relaxed font-mono">
            Model Context Protocol (MCP) server dispatch, external agent connectors, and raw tool execution are restricted to Administrators.
          </p>
          <span className="inline-block text-[11px] font-mono px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
            Current Role: <strong className="text-orange-400 uppercase">{user?.role}</strong>
          </span>
        </div>
      ) : (
        <div className="p-8 max-w-7xl mx-auto w-full space-y-6">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-zinc-500 uppercase tracking-widest">Protocol Core 2026-07-28</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/50 font-mono">
                  Stateless Gateway
                </span>
              </div>
              <h1 className="text-xl font-medium tracking-tight text-zinc-100 mt-1">
                Model Context Protocol (MCP) Console
              </h1>
              <p className="text-xs text-zinc-400 mt-1 max-w-2xl font-mono">
                Interoperability bridge exposing PHOENIX AST analysis, deterministic sandbox execution, and cryptographic governance to external AI models and IDE clients.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={fetchMcpData}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                Sync Registry
              </button>
            </div>
          </div>

        {/* Tab Selector */}
        <div className="flex items-center gap-1 border-b border-zinc-800/80 pb-px">
          {[
            { id: 'tools', label: `Tools (${tools.length})`, icon: Cpu },
            { id: 'resources', label: `Resources (${resources.length})`, icon: Database },
            { id: 'prompts', label: `Prompts (${prompts.length})`, icon: BookOpen },
            { id: 'servers', label: `Connected MCP Servers (${servers.length})`, icon: Layers },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs font-mono transition-colors border-b-2 -mb-px ${
                  active
                    ? 'border-zinc-200 text-zinc-100 font-medium'
                    : 'border-transparent text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* TAB 1: TOOLS EXPLORER */}
        {activeTab === 'tools' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Tool List */}
            <div className="lg:col-span-5 space-y-2">
              <div className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-2">Registered Capabilities</div>
              <div className="space-y-1.5 max-h-[600px] overflow-y-auto pr-1">
                {tools.map((t) => {
                  const isSelected = selectedTool?.name === t.name;
                  const catColor =
                    t.category === 'ADMINISTRATIVE'
                      ? 'text-rose-400 border-rose-900/50 bg-rose-950/20'
                      : t.category === 'EXECUTE'
                      ? 'text-amber-400 border-amber-900/50 bg-amber-950/20'
                      : t.category === 'WRITE'
                      ? 'text-blue-400 border-blue-900/50 bg-blue-950/20'
                      : 'text-zinc-400 border-zinc-800 bg-zinc-900/50';

                  return (
                    <button
                      key={t.name}
                      onClick={() => handleSelectTool(t)}
                      className={`w-full text-left p-3 rounded-lg border transition-all text-xs font-mono ${
                        isSelected
                          ? 'border-zinc-600 bg-zinc-900/90 text-zinc-100 shadow-md'
                          : 'border-zinc-800/80 bg-zinc-950 hover:bg-zinc-900/40 text-zinc-400'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-semibold text-zinc-200">{t.name}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase ${catColor}`}>
                          {t.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-500 line-clamp-2 leading-relaxed">
                        {t.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Tool Playground & Execution Output */}
            <div className="lg:col-span-7 space-y-4">
              {selectedTool ? (
                <div className="p-5 rounded-lg border border-zinc-800 bg-zinc-950 space-y-4">
                  <div className="flex items-start justify-between border-b border-zinc-800 pb-3">
                    <div>
                      <div className="text-sm font-mono font-medium text-zinc-100">{selectedTool.name}</div>
                      <div className="text-xs text-zinc-400 font-mono mt-0.5">{selectedTool.description}</div>
                    </div>
                    {selectedTool.requires_approval && (
                      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-amber-950/40 text-amber-400 border border-amber-800/50 font-mono">
                        <Shield className="w-3 h-3" /> Requires Cryptographic Approval
                      </span>
                    )}
                  </div>

                  {/* Arguments JSON Input */}
                  <div>
                    <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-1.5">
                      <span>Parameters (JSON arguments)</span>
                      <span className="text-[10px] text-zinc-500">
                        Required: {selectedTool.inputSchema?.required?.join(', ') || 'None'}
                      </span>
                    </div>
                    <textarea
                      value={toolArgsJson}
                      onChange={(e) => setToolArgsJson(e.target.value)}
                      rows={5}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded p-2.5 text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-600 transition-colors"
                      placeholder={'{\n  "project_id": "..."\n}'}
                    />
                  </div>

                  {/* Dispatch Button */}
                  <div className="flex justify-end">
                    <button
                      onClick={handleExecuteTool}
                      disabled={executing}
                      className="flex items-center gap-2 px-4 py-2 rounded text-xs font-mono font-medium bg-zinc-100 hover:bg-white text-zinc-950 transition-colors disabled:opacity-50"
                    >
                      <Play className={`w-3.5 h-3.5 fill-current ${executing ? 'animate-pulse' : ''}`} />
                      {executing ? 'Dispatching...' : 'Dispatch MCP Tool Call'}
                    </button>
                  </div>

                  {/* Tool Execution Result View */}
                  {toolResult && (
                    <div className="border-t border-zinc-800 pt-3 space-y-2">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="text-zinc-400">Response Payload</span>
                        {toolResult.isError ? (
                          <span className="flex items-center gap-1 text-rose-400">
                            <AlertCircle className="w-3 h-3" /> Error
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-emerald-400">
                            <CheckCircle2 className="w-3 h-3" /> 200 OK
                          </span>
                        )}
                      </div>
                      <pre className="p-3 bg-zinc-900/90 rounded border border-zinc-800 text-[11px] font-mono text-zinc-300 overflow-x-auto max-h-72">
                        {toolResult.content?.[0]?.text || JSON.stringify(toolResult, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-12 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800 rounded-lg">
                  Select a tool from the left list to inspect schema and execute.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: RESOURCES EXPLORER */}
        {activeTab === 'resources' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 space-y-2">
              <div className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-2">Exposed URI Resources</div>
              {resources.map((r) => (
                <button
                  key={r.uri}
                  onClick={() => handleReadResource(r.uri)}
                  className={`w-full text-left p-3 rounded-lg border transition-all text-xs font-mono ${
                    selectedUri === r.uri
                      ? 'border-zinc-600 bg-zinc-900/90 text-zinc-100 shadow-md'
                      : 'border-zinc-800/80 bg-zinc-950 hover:bg-zinc-900/40 text-zinc-400'
                  }`}
                >
                  <div className="font-semibold text-zinc-200 mb-0.5">{r.name}</div>
                  <div className="text-[11px] text-zinc-500 break-all">{r.uri}</div>
                  <div className="text-[10px] text-zinc-600 mt-1">{r.description}</div>
                </button>
              ))}
            </div>

            <div className="lg:col-span-7">
              <div className="p-5 rounded-lg border border-zinc-800 bg-zinc-950 space-y-3">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                  <div className="text-xs font-mono text-zinc-300 font-medium break-all">{selectedUri}</div>
                  <button
                    onClick={() => handleReadResource(selectedUri)}
                    disabled={readingResource}
                    className="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${readingResource ? 'animate-spin' : ''}`} /> Refresh
                  </button>
                </div>
                <pre className="p-3 bg-zinc-900 rounded border border-zinc-800 text-[11px] font-mono text-zinc-300 overflow-x-auto max-h-96">
                  {resourceContent || 'Click any resource on the left to read its contents.'}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: PROMPTS */}
        {activeTab === 'prompts' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {prompts.map((p) => (
              <div key={p.name} className="p-5 rounded-lg border border-zinc-800 bg-zinc-950 space-y-2">
                <div className="text-xs font-mono font-semibold text-zinc-200">{p.name}</div>
                <div className="text-xs text-zinc-400 font-mono leading-relaxed">{p.description}</div>
                <div className="pt-2 border-t border-zinc-900 text-[11px] font-mono text-zinc-500">
                  Arguments: {p.arguments?.map((a) => a.name).join(', ') || 'None'}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* TAB 4: EXTERNAL SERVERS */}
        {activeTab === 'servers' && (
          <div className="space-y-4">
            <div className="text-xs font-mono text-zinc-400">
              External MCP servers connected to PHOENIX Client with least-privilege boundary enforcement:
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {servers.map((s) => (
                <div key={s.id} className="p-5 rounded-lg border border-zinc-800 bg-zinc-950 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-medium text-zinc-200">{s.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded border border-emerald-900/50 bg-emerald-950/20 text-emerald-400 font-mono">
                      {s.status}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-zinc-500">
                    ID: <code className="text-zinc-400">{s.id}</code>
                  </div>
                  <div className="text-[11px] font-mono text-zinc-500">
                    Allowed Risk Tiers: {s.allowed_categories?.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      )}
    </div>
  );
};
