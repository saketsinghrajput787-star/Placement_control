import React from 'react';
import { BottleneckItem } from '../../types';
import { Badge } from '../common/Badge';
import { Activity, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface BottleneckRadarProps {
  bottlenecks: BottleneckItem[];
  roomUtil: number;
  panelUtil: number;
}

export const BottleneckRadar: React.FC<BottleneckRadarProps> = ({
  bottlenecks,
  roomUtil,
  panelUtil,
}) => {
  const getProgressColor = (pct: number) => {
    if (pct >= 90) return 'bg-status-critical';
    if (pct >= 75) return 'bg-status-warning';
    return 'bg-forest-700';
  };

  return (
    <div className="bg-white border border-sand-300 rounded-lg p-5 shadow-sm space-y-5">
      <div className="flex items-center justify-between border-b border-sand-200 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-forest-700" />
          <h3 className="text-sm font-bold text-sand-900">Capacity & Bottleneck Radar</h3>
        </div>
        <span className="text-xs text-sand-500 font-mono">Live Saturation</span>
      </div>

      {/* Capacity Progress Bars */}
      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-xs font-semibold mb-1">
            <span className="text-sand-700">Interview Panel Capacity</span>
            <span className="font-mono text-sand-900">{panelUtil}%</span>
          </div>
          <div className="w-full bg-sand-200 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${getProgressColor(panelUtil)}`}
              style={{ width: `${Math.min(100, panelUtil)}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs font-semibold mb-1">
            <span className="text-sand-700">Campus Room Saturation</span>
            <span className="font-mono text-sand-900">{roomUtil}%</span>
          </div>
          <div className="w-full bg-sand-200 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${getProgressColor(roomUtil)}`}
              style={{ width: `${Math.min(100, roomUtil)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Detected Bottleneck Alerts */}
      <div className="pt-2 border-t border-sand-200 space-y-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-sand-600 block">
          Predicted High-Pressure Windows
        </span>
        {bottlenecks.length === 0 ? (
          <p className="text-xs text-sand-500 italic py-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-status-healthy" />
            No critical resource bottlenecks predicted for active schedule.
          </p>
        ) : (
          bottlenecks.slice(0, 3).map((b, i) => (
            <div
              key={i}
              className="p-3 rounded-md bg-sand-50 border border-sand-300 flex items-start justify-between gap-3 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-forest-800">{b.time_window}</span>
                  <span className="font-semibold text-sand-900">{b.entity_name}</span>
                </div>
                <p className="text-sand-600">{b.reason}</p>
                <p className="text-sand-500 italic">Action: {b.suggested_action}</p>
              </div>
              <Badge variant={b.risk_level === 'CRITICAL' ? 'critical' : 'warning'} size="sm">
                {b.risk_level}
              </Badge>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
