import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md', className = '' }) => {
  const norm = (status || '').toLowerCase().trim();

  let colorClasses = 'bg-[#F4F2FB] text-[#6B5B84] border-[#E6E2F0]';

  if (
    norm.includes('available') ||
    norm === 'serviceable' ||
    norm === 'ok' ||
    norm === 'completed' ||
    norm === 'accepted' ||
    norm === 'nominal'
  ) {
    colorClasses = 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]';
  } else if (norm.includes('scheduled') || norm === 'watch' || norm === 'in_stock') {
    colorClasses = 'bg-[#EEF2FF] text-[#4F46E5] border-[#C7D2FE]';
  } else if (
    norm.includes('unscheduled') ||
    norm.includes('repair') ||
    norm === 'high' ||
    norm === 'p2' ||
    norm === 'low_stock' ||
    norm === 'degraded' ||
    norm === 'at risk' ||
    norm === 'warning'
  ) {
    colorClasses = 'bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]';
  } else if (
    norm.includes('spares') ||
    norm.includes('workshop') ||
    norm.includes('agency') ||
    norm === 'critical' ||
    norm === 'p1' ||
    norm === 'out_of_stock' ||
    norm === 'short' ||
    norm === 'failed'
  ) {
    colorClasses = 'bg-[#FEF2F2] text-[#DC2626] border-[#FECACA]';
  } else if (norm === 'p3') {
    colorClasses = 'bg-[#E0F8FA] text-[#0E7490] border-[#B6EFF4]';
  } else if (norm === 'p4' || norm === 'dismissed' || norm === 'low') {
    colorClasses = 'bg-[#F4F2FB] text-[#6B5B84] border-[#E6E2F0]';
  }

  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-[9px]',
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm font-semibold',
  }[size];

  return (
    <span
      className={`inline-flex items-center font-semibold font-mono rounded-full border uppercase tracking-wider select-none ${sizeClasses} ${colorClasses} ${className}`}
    >
      {status}
    </span>
  );
};
