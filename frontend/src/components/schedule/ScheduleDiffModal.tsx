import React, { useState, useEffect } from 'react';
import { useOperations } from '../../store/operationsStore';
import { apiClient } from '../../api/client';
import { ScheduleDiffItem } from '../../types';

export const ScheduleDiffModal: React.FC = () => {
  const { isDiffModalOpen, setIsDiffModalOpen, scheduleVersion } = useOperations();
  const [diffData, setDiffData] = useState<any>(null);
  const [filter, setFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (isDiffModalOpen && scheduleVersion?.schedule_version_id) {
      setLoading(true);
      apiClient.get(`/schedule/versions/${scheduleVersion.schedule_version_id}/diff`)
        .then(res => setDiffData(res.data))
        .catch(err => console.error('Failed to load version diff', err))
        .finally(() => setLoading(false));
    }
  }, [isDiffModalOpen, scheduleVersion]);

  if (!isDiffModalOpen) return null;

  const changes: ScheduleDiffItem[] = diffData?.changes || [];
  const filteredChanges = changes.filter(c => {
    if (filter === 'ALL') return true;
    return c.change_type === filter;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-sand-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-3xl border border-sand-300 shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="p-6 bg-sand-100 border-b border-sand-200 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-forest-700">Schedule Change Comparison</span>
            <h3 className="text-xl font-black text-sand-900 flex items-center gap-3 mt-1">
              <span>Version {diffData?.previous_version || 'V1'}</span>
              <span className="text-sand-400">→</span>
              <span className="text-forest-800">Version {diffData?.current_version || 'V2'}</span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                {diffData?.stability_score || 100}% Stability
              </span>
            </h3>
          </div>
          <button
            onClick={() => setIsDiffModalOpen(false)}
            className="p-2 rounded-xl text-sand-400 hover:text-sand-700 hover:bg-sand-200 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Impact Bar */}
        <div className="px-6 py-3 bg-sand-50 border-b border-sand-200 grid grid-cols-4 gap-4 text-center">
          <div className="p-2 rounded-xl bg-amber-50 border border-amber-200">
            <div className="text-xs text-amber-700 font-medium">Moved</div>
            <div className="text-lg font-black text-amber-900">{diffData?.summary?.moved || 0}</div>
          </div>
          <div className="p-2 rounded-xl bg-emerald-50 border border-emerald-200">
            <div className="text-xs text-emerald-700 font-medium">Unchanged</div>
            <div className="text-lg font-black text-emerald-900">{diffData?.summary?.unchanged || 0}</div>
          </div>
          <div className="p-2 rounded-xl bg-rose-50 border border-rose-200">
            <div className="text-xs text-rose-700 font-medium">Cancelled</div>
            <div className="text-lg font-black text-rose-900">{diffData?.summary?.cancelled || 0}</div>
          </div>
          <div className="p-2 rounded-xl bg-blue-50 border border-blue-200">
            <div className="text-xs text-blue-700 font-medium">New</div>
            <div className="text-lg font-black text-blue-900">{diffData?.summary?.new || 0}</div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="px-6 py-3 bg-white border-b border-sand-200 flex items-center gap-2 overflow-x-auto">
          {['ALL', 'MOVED', 'CANCELLED', 'UNCHANGED', 'NEW'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                filter === tab
                  ? 'bg-forest-800 text-white shadow-xs'
                  : 'bg-sand-100 text-sand-700 hover:bg-sand-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Diff Table / List */}
        <div className="p-6 overflow-y-auto flex-1 space-y-3">
          {loading ? (
            <div className="p-12 text-center text-sand-500 font-medium">Loading schedule differences...</div>
          ) : filteredChanges.length === 0 ? (
            <div className="p-12 text-center text-sand-500 font-medium">No schedule changes recorded for this filter.</div>
          ) : (
            filteredChanges.map((c, idx) => (
              <div key={idx} className="p-4 rounded-2xl border border-sand-200 bg-sand-50/50 hover:bg-white transition-colors">
                <div className="flex items-center justify-between gap-4 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sand-900 text-sm">{c.student_code}</span>
                    <span className="text-xs text-sand-500">({c.student_name})</span>
                    <span className="text-xs font-semibold text-sand-700">vs {c.company_name}</span>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    c.change_type === 'MOVED' ? 'bg-amber-100 text-amber-800' :
                    c.change_type === 'CANCELLED' ? 'bg-rose-100 text-rose-800' :
                    c.change_type === 'NEW' ? 'bg-blue-100 text-blue-800' :
                    'bg-emerald-100 text-emerald-800'
                  }`}>
                    {c.change_type}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-white p-3 rounded-xl border border-sand-200 mb-2">
                  <div>
                    <span className="text-sand-400 font-medium uppercase text-[10px] block">BEFORE (Version {diffData?.previous_version || 'V1'})</span>
                    <div className="font-semibold text-sand-800 mt-0.5">
                      {c.old_time || c.old_time_str || 'N/A'} • {c.old_room || c.old_room_code || 'N/A'} • {c.old_panel || c.old_panel_code || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <span className="text-sand-400 font-medium uppercase text-[10px] block">AFTER (Version {diffData?.current_version || 'V2'})</span>
                    <div className="font-bold text-forest-800 mt-0.5">
                      {c.new_time || c.new_time_str || 'N/A'} • {c.new_room || c.new_room_code || 'N/A'} • {c.new_panel || c.new_panel_code || 'N/A'}
                    </div>
                  </div>
                </div>

                {c.reason && (
                  <div className="text-xs text-sand-600 flex items-start gap-1.5">
                    <span className="font-bold text-sand-800">WHY?</span>
                    <span>{c.reason}</span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-sand-100 border-t border-sand-200 flex justify-end">
          <button
            onClick={() => setIsDiffModalOpen(false)}
            className="px-5 py-2 rounded-xl text-xs font-bold bg-sand-200 text-sand-800 hover:bg-sand-300 transition-colors"
          >
            Close Diff View
          </button>
        </div>
      </div>
    </div>
  );
};
