import React from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle2, ArrowRight } from 'lucide-react';

interface AlertBannerProps {
  type?: 'critical' | 'warning' | 'info' | 'success';
  title?: string;
  message: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({
  type = 'warning',
  title,
  message,
  action,
  className = '',
}) => {
  const styles = {
    critical: {
      bg: 'bg-[#FEF2F2] border-[#FECACA] text-[#DC2626]',
      badge: 'bg-[#FEE2E2] text-[#DC2626] border-[#FECACA]',
      icon: <ShieldAlert className="w-4 h-4 text-[#DC2626] shrink-0" />,
      btn: 'text-[#DC2626] hover:text-[#991B1B]',
    },
    warning: {
      bg: 'bg-[#FFFBEB] border-[#FDE68A] text-[#D97706]',
      badge: 'bg-[#FEF3C7] text-[#D97706] border-[#FDE68A]',
      icon: <AlertTriangle className="w-4 h-4 text-[#D97706] shrink-0" />,
      btn: 'text-[#D97706] hover:text-[#92400E]',
    },
    info: {
      bg: 'bg-[#E0F8FA] border-[#B6EFF4] text-[#0E7490]',
      badge: 'bg-[#CCFBF1] text-[#0E7490] border-[#99F6E4]',
      icon: <AlertTriangle className="w-4 h-4 text-[#0E7490] shrink-0" />,
      btn: 'text-[#0E7490] hover:text-[#155E75]',
    },
    success: {
      bg: 'bg-[#ECFDF5] border-[#A7F3D0] text-[#059669]',
      badge: 'bg-[#D1FAE5] text-[#059669] border-[#A7F3D0]',
      icon: <CheckCircle2 className="w-4 h-4 text-[#059669] shrink-0" />,
      btn: 'text-[#059669] hover:text-[#065F46]',
    },
  }[type];

  return (
    <div
      className={`rounded-[16px] border p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-ap-sm ${styles.bg} ${className}`}
    >
      <div className="flex items-center space-x-2.5">
        {styles.icon}
        {title && (
          <span className={`font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border text-[10px] ${styles.badge}`}>
            {title}
          </span>
        )}
        <div className="text-xs leading-normal font-medium">{message}</div>
      </div>

      {action && (
        <button
          onClick={action.onClick}
          className={`text-[11px] underline flex items-center gap-1 font-semibold shrink-0 self-end sm:self-center ${styles.btn}`}
        >
          <span>{action.label}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
