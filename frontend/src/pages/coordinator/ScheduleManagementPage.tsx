import React from 'react';
import { useOperations } from '../../store/operationsStore';
import { TimelineView } from '../../components/schedule/TimelineView';
import { Button } from '../../components/common/Button';
import { RefreshCw, Download } from 'lucide-react';

export const ScheduleManagementPage: React.FC = () => {
  const { scheduleVersion, generateSchedule, isLoading } = useOperations();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <div>
          <h2 className="text-xl font-bold text-sand-900 tracking-tight">SCHEDULE MANAGEMENT & TIMETABLE</h2>
          <p className="text-xs text-sand-600 mt-1">
            Global interactive interview schedule with real-time room and panel allocation filters
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
            onClick={generateSchedule}
            isLoading={isLoading}
          >
            Re-solve Optimization
          </Button>
        </div>
      </div>

      <TimelineView interviews={scheduleVersion?.interviews || []} />
    </div>
  );
};
