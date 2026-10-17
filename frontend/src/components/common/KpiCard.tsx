import React from 'react';

export interface KpiCardProps {
  title: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  change?: {
    value: number | string;
    isPositive?: boolean;
    label?: string;
  };
  icon?: React.ReactNode;
  accent?: 'honey' | 'blue' | 'emerald' | 'amber' | 'rose' | 'cyan' | 'slate' | 'mint' | 'lilac';
  loading?: boolean;
  onClick?: () => void;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  unit,
  subtitle,
  change,
  icon,
  accent = 'cyan',
  loading = false,
  onClick,
  className = '',
}) => {
  const accentIcons: Record<string, string> = {
    honey: 'bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]',
    amber: 'bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]',
    blue: 'bg-[#EEF2FF] text-[#4F46E5] border-[#C7D2FE]',
    emerald: 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]',
    mint: 'bg-[#E6FCF7] text-[#059669] border-[#A3F5E4]',
    lilac: 'bg-[#F4EBFF] text-[#7C3AED] border-[#E5D0FA]',
    rose: 'bg-[#FEF2F2] text-[#DC2626] border-[#FECACA]',
    cyan: 'bg-[#E0F8FA] text-[#0E7490] border-[#B6EFF4]',
    slate: 'bg-[#F4F2FB] text-[#6B5B84] border-[#E6E2F0]',
  };

  if (loading) {
    return (
      <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-5 shadow-ap-card animate-pulse space-y-3">
        <div className="flex justify-between items-center">
          <div className="h-3.5 bg-[#F4F2FB] rounded w-24" />
          <div className="h-9 w-9 bg-[#F4F2FB] rounded-[10px]" />
        </div>
        <div className="h-8 bg-[#F4F2FB] rounded w-32" />
        <div className="h-3 bg-[#F4F2FB]/70 rounded w-40" />
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={`bg-white border border-[#E6E2F0] rounded-[20px] p-5 shadow-ap-card transition-all duration-200 relative overflow-hidden group ${
        onClick
          ? 'cursor-pointer hover:shadow-ap-floating hover:-translate-y-0.5 hover:border-[#D8D2E5]'
          : 'hover:border-[#D8D2E5]'
      } ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#6B5B84]">
          {title}
        </span>
        {icon && (
          <div
            className={`p-2 rounded-[10px] border flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105 ${
              accentIcons[accent] || accentIcons.cyan
            }`}
          >
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-baseline space-x-1.5 mt-1.5">
        <span className="text-2xl sm:text-3xl font-bold font-mono text-[#3B1D5E] tracking-tight">
          {value}
        </span>
        {unit && <span className="text-xs text-[#6B5B84] font-mono font-medium">{unit}</span>}
      </div>

      <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-[#EDE9F5] text-xs">
        {subtitle && (
          <span className="text-[#6B5B84] truncate text-[11px] font-normal pr-1" title={subtitle}>
            {subtitle}
          </span>
        )}
        {change && (
          <span
            className={`font-mono font-bold text-[11px] shrink-0 ${
              change.isPositive ? 'text-[#059669]' : 'text-[#DC2626]'
            }`}
          >
            {change.isPositive ? '▲' : '▼'} {change.value} {change.label && `(${change.label})`}
          </span>
        )}
      </div>
    </div>
  );
};

// Reusable alias
export const MetricCard = KpiCard;
