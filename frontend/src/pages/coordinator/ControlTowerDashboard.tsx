import React from 'react';
import { useOperations } from '../../store/operationsStore';
import { MetricCard } from '../../components/common/MetricCard';
import { Button } from '../../components/common/Button';
import { TimelineView } from '../../components/schedule/TimelineView';
import { ConflictList } from '../../components/schedule/ConflictList';
import { BottleneckRadar } from '../../components/analytics/BottleneckRadar';
import {
  Users,
  Building2,
  DoorOpen,
  CalendarCheck,
  ShieldCheck,
  Activity,
  GitPullRequestDraft,
  ShieldAlert,
  UploadCloud,
  GitCompare,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const ControlTowerDashboard: React.FC = () => {
  const { scheduleVersion, analytics, conflicts, setIsDisruptionModalOpen, setIsDiffModalOpen, generateSchedule, isLoading } =
    useOperations();
  const navigate = useNavigate();

  const metrics = scheduleVersion?.metrics || analytics;
  const scheduledCount = (scheduleVersion?.interviews && scheduleVersion.interviews.length > 0) 
    ? scheduleVersion.interviews.length 
    : (metrics?.scheduled_interviews || analytics?.scheduled_interviews || 0);

  return (
    <div className="space-y-6">
      
      {/* Top Operations Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-sand-900 tracking-tight">LIVE PLACEMENT CONTROL TOWER</h2>
            <span className="text-xs bg-forest-100 text-forest-800 font-mono px-2 py-0.5 rounded font-semibold">
              DAY 1 • LIVE SYNCHRONIZED
            </span>
          </div>
          <p className="text-xs text-sand-600 mt-1">
            Real-time constraint satisfaction, live event detection, automated replanning, and multi-portal telemetry
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            icon={<UploadCloud className="w-4 h-4 text-forest-700" />}
            onClick={() => navigate('/coordinator/import')}
          >
            [ + Upload Document ]
          </Button>

          <Button
            variant="outline"
            size="sm"
            icon={<GitCompare className="w-4 h-4 text-forest-700" />}
            onClick={() => setIsDiffModalOpen(true)}
          >
            Schedule Diff
          </Button>

          <Button
            variant="accent"
            size="sm"
            icon={<ShieldAlert className="w-4 h-4" />}
            onClick={() => setIsDisruptionModalOpen(true)}
          >
            Simulate Disruption
          </Button>

          <Button
            variant="primary"
            size="sm"
            icon={<GitPullRequestDraft className="w-4 h-4" />}
            onClick={() => navigate('/coordinator/replanning')}
          >
            Replanning Engine
          </Button>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <MetricCard
          label="Students"
          value={analytics?.total_students ?? metrics?.total_students ?? 0}
          icon={<Users className="w-3.5 h-3.5" />}
          status="primary"
        />
        <MetricCard
          label="Companies"
          value={analytics?.total_companies ?? metrics?.total_companies ?? 0}
          icon={<Building2 className="w-3.5 h-3.5" />}
          status="primary"
        />
        <MetricCard
          label="Rooms"
          value={analytics?.total_rooms ?? metrics?.total_rooms ?? 0}
          icon={<DoorOpen className="w-3.5 h-3.5" />}
          status="primary"
        />
        <MetricCard
          label="Panels"
          value={analytics?.total_panels ?? metrics?.total_panels ?? 0}
          icon={<Activity className="w-3.5 h-3.5" />}
          status="primary"
        />
        <MetricCard
          label="Scheduled"
          value={scheduledCount}
          icon={<CalendarCheck className="w-3.5 h-3.5" />}
          status="healthy"
          subValue="100% Feasible"
        />
        <MetricCard
          label="Conflicts"
          value={conflicts.length}
          icon={<ShieldCheck className="w-3.5 h-3.5" />}
          status={conflicts.length > 0 ? 'critical' : 'healthy'}
        />
        <MetricCard
          label="Stability"
          value={`${(metrics?.schedule_stability || 100).toFixed(1)}%`}
          icon={<GitPullRequestDraft className="w-3.5 h-3.5" />}
          status="healthy"
        />
        <MetricCard
          label="Risk Level"
          value={metrics?.bottleneck_risk_level || analytics?.current_risk_level || 'LOW'}
          icon={<Activity className="w-3.5 h-3.5" />}
          status={
            metrics?.bottleneck_risk_level === 'CRITICAL'
              ? 'critical'
              : metrics?.bottleneck_risk_level === 'HIGH'
              ? 'critical'
              : metrics?.bottleneck_risk_level === 'MEDIUM'
              ? 'warning'
              : 'healthy'
          }
        />
      </div>

      {/* Middle Grid: Radar & Conflict Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <BottleneckRadar
            bottlenecks={analytics?.bottlenecks || []}
            roomUtil={metrics?.room_utilization_pct || 0}
            panelUtil={metrics?.panel_utilization_pct || 0}
          />
        </div>

        <div className="lg:col-span-2">
          <ConflictList conflicts={conflicts} />
        </div>
      </div>

      {/* Live Schedule Timeline */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-sand-900">Live Campus Schedule Matrix</h3>
          <span className="text-xs text-sand-500 font-mono">
            {scheduleVersion?.interviews?.length || 0} active assignments
          </span>
        </div>
        <TimelineView interviews={scheduleVersion?.interviews || []} />
      </div>
    </div>
  );
};
