import React, { useState, useEffect } from 'react';
import { useOperations } from '../../store/operationsStore';
import { apiClient } from '../../api/client';

export const ScheduleVersionHistoryDrawer: React.FC = () => {
  const { isHistoryDrawerOpen, setIsHistoryDrawerOpen, setIsDiffModalOpen } = useOperations();
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (isHistoryDrawerOpen) {
      setLoading(true);
      apiClient.get('/schedule/versions')
        .then(res => setVersions(res.data))
        .catch(err => console.error('Failed to load schedule versions', err))
        .finally(() => setLoading(false));
    }
  }, [isHistoryDrawerOpen]);

  if (!isHistoryDrawerOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-sand-900/40 backdrop-blur-xs">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-sand-300 animate-in slide-in-from-right duration-200">
        
        {/* Header */}
        <div className="p-6 bg-sand-100 border-b border-sand-200 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-black text-sand-900">Schedule Version History</h3>
            <p className="text-xs text-sand-500 mt-0.5">Audit log of all generated & replanned versions</p>
          </div>
          <button
            onClick={() => setIsHistoryDrawerOpen(false)}
            className="p-2 rounded-xl text-sand-400 hover:text-sand-700 hover:bg-sand-200 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Versions List */}
        <div className="p-6 overflow-y-auto flex-1 space-y-3">
          {loading ? (
            <div className="p-8 text-center text-sand-500 font-medium text-xs">Loading version history...</div>
          ) : versions.length === 0 ? (
            <div className="p-8 text-center text-sand-500 font-medium text-xs">No schedule versions found.</div>
          ) : (
            versions.map((v, idx) => (
              <div
                key={v.id}
                className="p-4 rounded-2xl border border-sand-200 bg-sand-50/60 hover:bg-sand-100/80 transition-colors flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-black text-forest-800 text-sm">Schedule Version {v.version_number}</span>
                    {idx === 0 && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-sand-500 mt-1">
                    Created: {v.created_at ? new Date(v.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'N/A'}
                  </div>
                  <div className="text-xs font-semibold text-sand-700 mt-1">
                    Stability Score: {v.stability_score}%
                  </div>
                </div>

                <button
                  onClick={() => {
                    setIsHistoryDrawerOpen(false);
                    setIsDiffModalOpen(true);
                  }}
                  className="px-3 py-1.5 rounded-xl text-xs font-bold bg-forest-800 text-white hover:bg-forest-900 transition-colors shadow-xs"
                >
                  View Diff
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-sand-100 border-t border-sand-200 flex justify-end">
          <button
            onClick={() => setIsHistoryDrawerOpen(false)}
            className="px-5 py-2 rounded-xl text-xs font-bold bg-sand-200 text-sand-800 hover:bg-sand-300 transition-colors"
          >
            Close History
          </button>
        </div>
      </div>
    </div>
  );
};
