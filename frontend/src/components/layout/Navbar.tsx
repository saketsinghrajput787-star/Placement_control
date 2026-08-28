import React from 'react';
import { useAuth } from '../../store/authStore';
import { useOperations } from '../../store/operationsStore';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { Bot, RefreshCw, LogOut, ShieldAlert, History, GitCompare, RotateCcw } from 'lucide-react';
import { LiveStatusBadge } from './LiveStatusBadge';
import { NotificationBell } from './NotificationBell';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { 
    scheduleVersion, 
    conflicts, 
    analytics, 
    isCopilotOpen, 
    setIsCopilotOpen, 
    setIsDisruptionModalOpen, 
    setIsDiffModalOpen,
    setIsHistoryDrawerOpen,
    generateSchedule,
    resetSchedule,
    isLoading 
  } = useOperations();

  const riskVariant = analytics?.current_risk_level === 'CRITICAL' ? 'critical' : (analytics?.current_risk_level === 'HIGH' ? 'critical' : (analytics?.current_risk_level === 'MEDIUM' ? 'warning' : 'healthy'));

  return (
    <header className="h-16 bg-white border-b border-sand-300 px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-forest-700 text-white font-bold flex items-center justify-center text-sm tracking-wider shadow-xs">
            PCT
          </div>
          <div>
            <h1 className="text-sm font-bold text-sand-900 leading-tight">LIVE PLACEMENT CONTROL TOWER</h1>
            <p className="text-[11px] text-sand-500 font-mono">University Operations Center • Day 1 (09:00–18:00)</p>
          </div>
        </div>

        <div className="h-6 w-px bg-sand-300 mx-2" />

        <LiveStatusBadge />

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsHistoryDrawerOpen(true)}
            className="flex items-center gap-1 hover:opacity-80 transition-opacity"
            title="View Schedule Version History"
          >
            <Badge variant="neutral" size="sm">
              Version {scheduleVersion?.version_number || 1}
            </Badge>
          </button>
          <Badge variant={riskVariant} size="sm" dot>
            Risk: {analytics?.current_risk_level || 'LOW'}
          </Badge>
          {conflicts.length > 0 && (
            <Badge variant="critical" size="sm" dot>
              {conflicts.length} Conflicts
            </Badge>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => resetSchedule()}
          disabled={isLoading}
          className="px-3 py-1.5 rounded-xl border border-sand-300 text-xs font-bold text-sand-900 bg-sand-100 hover:bg-sand-200 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs active:scale-95 disabled:opacity-50"
          title="Reset All Cancellations & Restore Baseline Schedule"
        >
          <RotateCcw className={`w-3.5 h-3.5 text-forest-700 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{isLoading ? 'Resetting...' : 'Reset Original'}</span>
        </button>

        <button
          onClick={() => setIsDiffModalOpen(true)}
          className="px-3 py-1.5 rounded-xl border border-sand-300 text-xs font-bold text-sand-800 bg-sand-100 hover:bg-sand-200 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
          title="Compare Schedule Versions"
        >
          <GitCompare className="w-3.5 h-3.5 text-forest-700" />
          <span>Diff View</span>
        </button>

        <button
          onClick={() => setIsHistoryDrawerOpen(true)}
          className="p-2 rounded-xl text-sand-600 hover:bg-sand-100 transition-colors"
          title="Schedule Version History"
        >
          <History className="w-4 h-4 text-sand-700" />
        </button>

        <NotificationBell />

        {user?.role === 'COORDINATOR' && (
          <>
            <Button
              variant="outline"
              size="sm"
              icon={<ShieldAlert className="w-4 h-4 text-status-warning" />}
              onClick={() => setIsDisruptionModalOpen(true)}
            >
              Simulate Disruption
            </Button>
            <Button
              variant="secondary"
              size="sm"
              icon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
              onClick={generateSchedule}
              isLoading={isLoading}
            >
              Re-optimize
            </Button>
          </>
        )}

        <Button
          variant={isCopilotOpen ? 'primary' : 'outline'}
          size="sm"
          icon={<Bot className="w-4 h-4 text-forest-700 group-hover:text-white" />}
          onClick={() => setIsCopilotOpen(!isCopilotOpen)}
        >
          AI Decision Copilot
        </Button>

        <div className="h-6 w-px bg-sand-300 mx-1" />

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs font-semibold text-sand-900">{user?.name || user?.email}</p>
            <p className="text-[10px] text-sand-500 uppercase tracking-wider font-mono">{user?.role}</p>
          </div>
          <button
            onClick={logout}
            title="Logout"
            className="p-1.5 text-sand-400 hover:text-sand-700 hover:bg-sand-100 rounded-md transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
