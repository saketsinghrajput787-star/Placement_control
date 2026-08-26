import React from 'react';
import { useOperations } from '../../store/operationsStore';
import { Card } from '../../components/common/Card';
import { MetricCard } from '../../components/common/MetricCard';
import { BottleneckRadar } from '../../components/analytics/BottleneckRadar';
import { BarChart3, DoorOpen, Activity, Users, Building2, TrendingUp } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const { analytics, scheduleVersion } = useOperations();
  const metrics = scheduleVersion?.metrics || analytics;

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <h2 className="text-xl font-bold text-sand-900 tracking-tight">OPERATIONS TELEMETRY & CAPACITY ANALYTICS</h2>
        <p className="text-xs text-sand-600 mt-1">
          Quantitative utilization breakdown of campus physical rooms, corporate panels, and student contention
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Room Utilization"
          value={`${(metrics?.room_utilization_pct || 0).toFixed(1)}%`}
          icon={<DoorOpen className="w-4 h-4" />}
          status="primary"
          trend="20 Active Rooms"
        />
        <MetricCard
          label="Panel Utilization"
          value={`${(metrics?.panel_utilization_pct || 0).toFixed(1)}%`}
          icon={<Activity className="w-4 h-4" />}
          status="primary"
          trend="40 Active Panels"
        />
        <MetricCard
          label="Schedule Stability"
          value={`${(metrics?.schedule_stability || 100).toFixed(1)}%`}
          icon={<TrendingUp className="w-4 h-4" />}
          status="healthy"
          trend="Zero Overlaps"
        />
        <MetricCard
          label="Risk Assessment"
          value={analytics?.current_risk_level || 'LOW'}
          icon={<BarChart3 className="w-4 h-4" />}
          status={analytics?.current_risk_level === 'CRITICAL' ? 'critical' : 'healthy'}
        />
      </div>

      {/* Radar & Resource Utilization Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <BottleneckRadar
            bottlenecks={analytics?.bottlenecks || []}
            roomUtil={metrics?.room_utilization_pct || 0}
            panelUtil={metrics?.panel_utilization_pct || 0}
          />
        </div>

        <div className="lg:col-span-2 space-y-6">
          {/* Top Utilized Panels */}
          <Card title="Recruiter Panel Saturation Rankings" subtitle="Individual panel load across 12 daily time slots">
            <div className="space-y-3">
              {(analytics?.top_utilized_panels || []).map((panel, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-sand-800">{panel.name}</span>
                    <span className="font-mono text-sand-900">{panel.utilization_pct}% ({panel.used_slots}/12 slots)</span>
                  </div>
                  <div className="w-full bg-sand-200 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full ${
                        panel.utilization_pct >= 90
                          ? 'bg-status-critical'
                          : panel.utilization_pct >= 75
                          ? 'bg-status-warning'
                          : 'bg-forest-700'
                      }`}
                      style={{ width: `${panel.utilization_pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Top Utilized Rooms */}
          <Card title="Campus Interview Room Utilization" subtitle="Block A and Block B physical infrastructure occupancy">
            <div className="space-y-3">
              {(analytics?.top_utilized_rooms || []).map((room, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-sand-800">{room.name}</span>
                    <span className="font-mono text-sand-900">{room.utilization_pct}% ({room.used_slots}/12 slots)</span>
                  </div>
                  <div className="w-full bg-sand-200 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full ${
                        room.utilization_pct >= 90
                          ? 'bg-status-critical'
                          : room.utilization_pct >= 75
                          ? 'bg-status-warning'
                          : 'bg-forest-700'
                      }`}
                      style={{ width: `${room.utilization_pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
