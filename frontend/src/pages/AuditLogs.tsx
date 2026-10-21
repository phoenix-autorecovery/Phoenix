import React, { useEffect, useState } from 'react';
import { ScrollText, Clock, Search, Loader2 } from 'lucide-react';
import { Navbar } from '../components/Navbar';
import { api } from '../api/client';
import { AuditEvent } from '../types';

export const AuditLogs: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    api.get('/audit-events?limit=100')
      .then((res) => setEvents(res.data))
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const filtered = events.filter((e) =>
    e.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.resource_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (e.resource_id && e.resource_id.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-slate-950">
      <Navbar
        title="Enterprise Audit Trail"
        subtitle="Immutable records of workspace imports, diagnostic queries, patch generations, and deliveries"
      />

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="relative w-80">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Filter by action or resource..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-orange-500"
            />
          </div>
          <span className="text-xs text-slate-500 font-mono">
            Showing {filtered.length} audit events
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center p-16 text-slate-500 gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
            <span>Loading audit trail...</span>
          </div>
        ) : (
          <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 font-mono text-[11px] text-slate-400">
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Resource</th>
                  <th className="py-3 px-4">Resource ID</th>
                  <th className="py-3 px-4">Correlation ID</th>
                  <th className="py-3 px-4 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {filtered.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 text-orange-400 font-semibold">{ev.action}</td>
                    <td className="py-3 px-4 text-slate-400">{ev.resource_type}</td>
                    <td className="py-3 px-4 text-slate-500 truncate max-w-[120px]">
                      {ev.resource_id ? ev.resource_id.slice(0, 8) : '-'}
                    </td>
                    <td className="py-3 px-4 text-slate-600 truncate max-w-[120px]">
                      {ev.correlation_id ? ev.correlation_id.slice(0, 8) : '-'}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-500">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
};
