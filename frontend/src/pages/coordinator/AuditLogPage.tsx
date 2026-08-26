import React, { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import { AuditLogEntry } from '../../types';

export const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    apiClient.get('/audit-logs')
      .then(res => setLogs(res.data))
      .catch(err => console.error('Failed to fetch audit logs', err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="p-6 rounded-3xl bg-sand-100 border border-sand-200">
        <span className="text-xs font-bold uppercase tracking-wider text-forest-700">Operational Compliance & Control</span>
        <h2 className="text-2xl font-black text-sand-900 mt-1">PLACEMENT OPERATIONS AUDIT LOG</h2>
        <p className="text-xs text-sand-600 mt-1">
          Chronological audit trail of all mutations, student cancellations, company delays, data imports, and schedule replanning events.
        </p>
      </div>

      {/* Audit Timeline */}
      <div className="bg-white rounded-3xl border border-sand-300 shadow-xl overflow-hidden p-6 space-y-4">
        {loading ? (
          <div className="p-12 text-center text-sand-500 font-medium text-xs">Loading operational timeline...</div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-sand-400 text-xs">No audit events recorded yet.</div>
        ) : (
          <div className="relative border-l-2 border-sand-200 ml-4 space-y-6">
            {logs.map((log) => (
              <div key={log.id} className="relative pl-6">
                
                {/* Timeline Dot */}
                <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-white shadow-xs ${
                  log.action.includes('CANCEL') ? 'bg-rose-500' :
                  log.action.includes('DELAY') ? 'bg-amber-500' :
                  log.action.includes('IMPORT') ? 'bg-blue-500' : 'bg-emerald-500'
                }`} />

                <div className="p-4 rounded-2xl bg-sand-50/80 border border-sand-200 hover:bg-white transition-colors">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                    <span className="font-bold text-sand-900 text-xs uppercase tracking-wider">{log.action}</span>
                    <span className="text-[10px] font-semibold text-sand-400">
                      {log.created_at ? new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' }) : ''}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-sand-700 font-medium mb-2">
                    <span>User: <strong className="text-sand-900">{log.user_email || log.user_id || 'System'}</strong></span>
                    {log.user_role && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sand-200 text-sand-800">
                        {log.user_role}
                      </span>
                    )}
                    {log.schedule_version_id && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-forest-100 text-forest-800">
                        Schedule Version {log.schedule_version_id.slice(0, 8)}
                      </span>
                    )}
                  </div>

                  {log.reason && (
                    <div className="text-xs text-sand-800 bg-white p-2.5 rounded-xl border border-sand-200 font-medium">
                      Reason / Trigger: {log.reason}
                    </div>
                  )}

                  {log.details && Object.keys(log.details).length > 0 && (
                    <div className="text-[11px] text-sand-600 font-mono mt-2 bg-sand-100/50 p-2 rounded-lg overflow-x-auto">
                      {JSON.stringify(log.details)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
