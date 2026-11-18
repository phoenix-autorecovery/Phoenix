import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  Terminal, 
  Cpu, 
  FolderGit2, 
  CheckCircle2, 
  FileText, 
  Settings as SettingsIcon, 
  Zap, 
  ShieldCheck, 
  Eye, 
  SlidersHorizontal,
  X
} from 'lucide-react';
import { useMode } from '../context/ModeContext';
import { useToast } from '../context/ToastContext';
import { api } from '../api/client';

interface CommandItem {
  id: string;
  title: string;
  subtitle: string;
  category: 'Navigation' | 'Mode' | 'AI Model' | 'Actions';
  icon: React.ReactNode;
  action: () => void;
  shortcut?: string;
}

export const CommandPalette: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { mode, setMode, toggleMode } = useMode();
  const { success, error } = useToast();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const switchModel = async (modelName: string) => {
    try {
      await api.post('/settings/models', { model: modelName });
      success(`Switched inference model to ${modelName}`, 'Model Reconfigured');
      onClose();
    } catch (e: any) {
      error(e.response?.data?.detail || 'Model switch failed.', 'Model Error');
    }
  };

  const commands: CommandItem[] = [
    {
      id: 'toggle-mode',
      title: mode === 'simple' ? 'Switch to Dev / Inspector Mode' : 'Switch to Simple Executive View',
      subtitle: mode === 'simple' ? 'Reveal raw terminal streams, AST diagnostics, and token metrics' : 'Simplify view for non-technical overview',
      category: 'Mode',
      icon: <SlidersHorizontal className="w-4 h-4 text-zinc-400" />,
      shortcut: '⌘D',
      action: () => {
        toggleMode();
        onClose();
      }
    },
    {
      id: 'nav-dashboard',
      title: 'Go to Recovery Dashboard',
      subtitle: 'Overview of system telemetry, active sandboxes, and verification gates',
      category: 'Navigation',
      icon: <Terminal className="w-4 h-4 text-zinc-400" />,
      action: () => {
        navigate('/');
        onClose();
      }
    },
    {
      id: 'nav-projects',
      title: 'View Workspaces & Projects',
      subtitle: 'Browse all ingested repositories and monitored software roots',
      category: 'Navigation',
      icon: <FolderGit2 className="w-4 h-4 text-zinc-400" />,
      action: () => {
        navigate('/projects');
        onClose();
      }
    },
    {
      id: 'nav-approvals',
      title: 'Review Cryptographic Approvals',
      subtitle: 'Inspect sign-offs bound to candidate patch SHA-256 hashes',
      category: 'Navigation',
      icon: <ShieldCheck className="w-4 h-4 text-zinc-400" />,
      action: () => {
        navigate('/approvals');
        onClose();
      }
    },
    {
      id: 'nav-audit',
      title: 'Immutable Audit Trail',
      subtitle: 'Inspect tamper-evident system ledger of every autonomous repair action',
      category: 'Navigation',
      icon: <FileText className="w-4 h-4 text-zinc-400" />,
      action: () => {
        navigate('/audit');
        onClose();
      }
    },
    {
      id: 'nav-mcp',
      title: 'MCP Protocol & Agent Console',
      subtitle: 'Inspect Model Context Protocol tools, run JSON-RPC gateway calls, and view prompts',
      category: 'Navigation',
      icon: <Terminal className="w-4 h-4 text-emerald-400" />,
      action: () => {
        navigate('/mcp');
        onClose();
      }
    },
    {
      id: 'nav-settings',
      title: 'Platform Settings & Secrets',
      subtitle: 'Configure Groq API tokens, GitHub App credentials, and sandbox quotas',
      category: 'Navigation',
      icon: <SettingsIcon className="w-4 h-4 text-zinc-400" />,
      action: () => {
        navigate('/settings');
        onClose();
      }
    },
    {
      id: 'model-llama31',
      title: 'Switch Engine to Groq LLaMA 3.1 70B',
      subtitle: 'High-capability multi-file root-cause reasoning and candidate synthesis',
      category: 'AI Model',
      icon: <Cpu className="w-4 h-4 text-emerald-400" />,
      action: () => switchModel('llama-3.1-70b-versatile')
    },
    {
      id: 'model-qwen',
      title: 'Switch Engine to Groq Qwen 2.5 Coder 32B',
      subtitle: 'Specialized high-precision programming and unified diff code repair',
      category: 'AI Model',
      icon: <Cpu className="w-4 h-4 text-blue-400" />,
      action: () => switchModel('qwen-2.5-coder-32b')
    }
  ];

  const filtered = commands.filter((c) =>
    c.title.toLowerCase().includes(query.toLowerCase()) ||
    c.subtitle.toLowerCase().includes(query.toLowerCase()) ||
    c.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + (filtered.length || 1)) % (filtered.length || 1));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      e.preventDefault();
      filtered[selectedIndex].action();
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-24 p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-xl bg-zinc-950 border border-zinc-800 rounded-lg shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-zinc-800 gap-3">
          <Search className="w-4 h-4 text-zinc-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search actions..."
            className="w-full bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none font-sans"
          />
          <button 
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-xs px-1.5 py-0.5 rounded border border-zinc-800 font-mono"
          >
            ESC
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-zinc-500 font-mono">
              No matching commands found.
            </div>
          ) : (
            filtered.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-md cursor-pointer text-xs transition-colors ${
                    isSelected ? 'bg-zinc-900 text-zinc-100' : 'text-zinc-400 hover:bg-zinc-900/50 hover:text-zinc-200'
                  }`}
                >
                  <div className="flex items-center gap-3 truncate">
                    <span className="shrink-0">{item.icon}</span>
                    <div className="truncate">
                      <p className="font-medium text-zinc-200 truncate">{item.title}</p>
                      <p className="text-[11px] text-zinc-500 truncate">{item.subtitle}</p>
                    </div>
                  </div>
                  {item.shortcut && (
                    <span className="shrink-0 font-mono text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded border border-zinc-700">
                      {item.shortcut}
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer Navigation Hints */}
        <div className="px-4 py-2 border-t border-zinc-900 bg-zinc-950/60 flex items-center justify-between text-[11px] text-zinc-500 font-mono">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span className="text-[10px] text-zinc-400">PHOENIX Command Interface</span>
        </div>
      </div>
    </div>
  );
};
