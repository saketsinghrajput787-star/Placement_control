import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'healthy' | 'warning' | 'critical' | 'info' | 'neutral' | 'accent';
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  className = '',
}) => {
  const variantStyles = {
    healthy: 'bg-green-50 text-status-healthy border-green-200',
    warning: 'bg-amber-50 text-status-warning border-amber-200',
    critical: 'bg-red-50 text-status-critical border-red-200',
    info: 'bg-sky-50 text-status-info border-sky-200',
    neutral: 'bg-sand-200 text-sand-800 border-sand-300',
    accent: 'bg-amber-50 text-amber-800 border-amber-200',
  };

  const dotColors = {
    healthy: 'bg-status-healthy',
    warning: 'bg-status-warning',
    critical: 'bg-status-critical',
    info: 'bg-status-info',
    neutral: 'bg-sand-500',
    accent: 'bg-amber-500',
  };

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1 font-medium',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
};
