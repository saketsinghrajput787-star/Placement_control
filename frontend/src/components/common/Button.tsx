import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-150 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed';

  const variantStyles = {
    primary: 'bg-forest-700 hover:bg-forest-800 text-white shadow-sm focus:ring-forest-600',
    secondary: 'bg-sand-200 hover:bg-sand-300 text-sand-900 focus:ring-sand-400',
    accent: 'bg-amber-500 hover:bg-amber-600 text-white shadow-sm focus:ring-amber-400',
    danger: 'bg-status-critical hover:bg-red-700 text-white shadow-sm focus:ring-red-500',
    ghost: 'bg-transparent hover:bg-sand-200 text-sand-800 focus:ring-sand-400',
    outline: 'bg-transparent border border-sand-300 hover:bg-sand-100 text-sand-800 focus:ring-forest-600',
  };

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  };

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-1.5" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children}
    </button>
  );
};
