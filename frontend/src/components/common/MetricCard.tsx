import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon?: React.ReactNode;
  status?: 'healthy' | 'warning' | 'critical' | 'info' | 'primary';
  trend?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  icon,
  status = 'primary',
  trend,
}) => {
  const statusColors = {
    primary: 'border-l-forest-700 text-forest-800',
    healthy: 'border-l-status-healthy text-status-healthy',
    warning: 'border-l-status-warning text-status-warning',
    critical: 'border-l-status-critical text-status-critical',
    info: 'border-l-status-info text-status-info',
  };

  return (
    <div className={`bg-white border border-sand-300 border-l-4 ${statusColors[status]} rounded-md p-4 shadow-sm flex flex-col justify-between`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-sand-600">{label}</span>
        {icon && <span className="text-sand-500">{icon}</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-sand-900">{value}</span>
        {subValue && <span className="text-xs text-sand-500 font-medium">{subValue}</span>}
      </div>
      {trend && (
        <div className="mt-2 text-xs text-sand-500 flex items-center gap-1">
          <span>{trend}</span>
        </div>
      )}
    </div>
  );
};
