import React from 'react';

interface ActionButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'success' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
}

export const ActionButton: React.FC<ActionButtonProps> = ({
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  loading = false,
  children,
  className = '',
  disabled,
  ...props
}) => {
  const sizeClasses = {
    xs: 'px-2.5 py-1 text-[11px] gap-1 rounded-[6px]',
    sm: 'px-3 py-1.5 text-xs gap-1.5 rounded-[8px]',
    md: 'px-4 py-2 text-xs sm:text-sm gap-2 rounded-[10px]',
    lg: 'px-5 py-2.5 text-sm gap-2.5 rounded-[12px]',
  }[size];

  const variantClasses = {
    primary:
      'bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] font-bold shadow-ap-mint border border-transparent transition-all',
    secondary:
      'bg-[#F4F2FB] hover:bg-white text-[#3B1D5E] border border-[#E6E2F0] shadow-sm font-medium transition-all',
    outline:
      'bg-transparent hover:bg-[#E0F8FA] text-[#0D6553] border border-[#1DE9C0] font-semibold transition-all',
    danger:
      'bg-[#DC2626] hover:bg-[#B91C1C] text-white font-semibold shadow-sm transition-all',
    success:
      'bg-[#059669] hover:bg-[#047857] text-white font-semibold shadow-sm transition-all',
    ghost:
      'bg-transparent hover:bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] font-medium transition-all',
  }[variant];

  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-sans font-semibold transition-all duration-150 select-none disabled:opacity-50 disabled:pointer-events-none ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {loading ? (
        <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin shrink-0" />
      ) : (
        icon && iconPosition === 'left' && <span className="shrink-0">{icon}</span>
      )}
      {children}
      {!loading && icon && iconPosition === 'right' && <span className="shrink-0">{icon}</span>}
    </button>
  );
};
