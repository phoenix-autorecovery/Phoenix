import React, { useState } from 'react';
import { Copy, Check, Download, FileCode2 } from 'lucide-react';

interface DiffViewerProps {
  diff: string;
  patchHash?: string;
  filesModified?: string[];
  repairJobId?: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diff, patchHash, filesModified, repairJobId }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(diff);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = diff.split('\n');

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-2xl">
      {/* Diff Header */}
      <div className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <FileCode2 className="w-5 h-5 text-orange-400" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200">Candidate Patch Diff</span>
              {filesModified && filesModified.length > 0 && (
                <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                  {filesModified.join(', ')}
                </span>
              )}
            </div>
            {patchHash && (
              <p className="text-[10px] font-mono text-slate-500">
                SHA-256: <span className="text-slate-400">{patchHash}</span>
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Diff'}</span>
          </button>
          
          {repairJobId && (
            <a
              href={`http://localhost:8000/api/v1/repairs/${repairJobId}/artifact?artifact_type=patch`}
              download
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-orange-600 hover:bg-orange-500 text-white transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download .patch</span>
            </a>
          )}
        </div>
      </div>

      {/* Diff Code View */}
      <div className="p-4 font-mono text-xs overflow-x-auto leading-relaxed max-h-[500px]">
        {lines.map((line, idx) => {
          let lineClass = 'text-slate-400';
          let bgClass = 'hover:bg-slate-900/50';

          if (line.startsWith('+++') || line.startsWith('---')) {
            lineClass = 'text-slate-300 font-bold';
            bgClass = 'bg-slate-900/80';
          } else if (line.startsWith('@@')) {
            lineClass = 'text-cyan-400 font-semibold';
            bgClass = 'bg-cyan-950/20';
          } else if (line.startsWith('+')) {
            lineClass = 'text-emerald-400';
            bgClass = 'bg-emerald-950/30';
          } else if (line.startsWith('-')) {
            lineClass = 'text-rose-400';
            bgClass = 'bg-rose-950/30';
          }

          return (
            <div key={idx} className={`px-2 py-0.5 rounded flex items-start space-x-4 ${bgClass}`}>
              <span className="w-8 select-none text-right text-slate-600 shrink-0 font-mono text-[10px]">
                {idx + 1}
              </span>
              <pre className={`flex-1 overflow-x-visible ${lineClass}`}>
                {line || ' '}
              </pre>
            </div>
          );
        })}
      </div>
    </div>
  );
};
