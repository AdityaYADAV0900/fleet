import React from 'react';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  subtitle,
  badge,
  actions,
  children,
  className = '',
}) => {
  return (
    <div
      className={`bg-[#111721] border border-[#252D39] rounded-xl p-5 sm:p-6 shadow-card transition-all duration-200 hover:border-[#343F50] flex flex-col justify-between ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-[#252D39]">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-xs sm:text-sm font-bold font-mono uppercase tracking-wider text-[#F5F7FA]">
              {title}
            </h3>
            {badge}
          </div>
          {subtitle && (
            <p className="text-xs text-[#9AA6B5] font-sans mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex items-center space-x-2 shrink-0 self-end sm:self-center">
            {actions}
          </div>
        )}
      </div>

      <div className="w-full flex-1">{children}</div>
    </div>
  );
};
