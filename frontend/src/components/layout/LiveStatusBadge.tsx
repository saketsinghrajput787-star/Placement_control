import React from 'react';
import { useOperations } from '../../store/operationsStore';

export const LiveStatusBadge: React.FC = () => {
  const { isLiveConnected, lastSyncTime } = useOperations();

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-sand-200/60 border border-sand-300 shadow-xs">
      {isLiveConnected ? (
        <>
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-600"></span>
          </span>
          <span className="text-emerald-900 font-bold tracking-wide">● LIVE</span>
          <span className="text-sand-600 text-[10px] hidden sm:inline">({lastSyncTime})</span>
        </>
      ) : (
        <>
          <span className="inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
          <span className="text-amber-900 font-bold tracking-wide">○ OFFLINE</span>
          <span className="text-sand-600 text-[10px] hidden sm:inline">Reconnecting...</span>
        </>
      )}
    </div>
  );
};
