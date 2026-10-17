import React from 'react';

interface SectionContainerProps {
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  elevated?: boolean;
  glow?: boolean;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  padding?: 'sm' | 'md' | 'lg' | 'none';
}

export const SectionContainer: React.FC<SectionContainerProps> = ({
  title,
  subtitle,
  icon,
  badge,
  actions,
  children,
  className = '',
  elevated = false,
  glow = false,
  collapsible = false,
  defaultCollapsed = false,
  padding = 'md',
}) => {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

  const paddingClasses = {
    none: '',
    sm: 'p-3.5 sm:p-4',
    md: 'p-5 sm:p-6',
    lg: 'p-6 sm:p-8',
  }[padding];

  const baseBg = elevated ? 'bg-[#F4F2FB]' : 'bg-white';
  const glowClass = glow ? 'border-[#C9A2F5]/60 shadow-ap-floating' : 'border-[#E6E2F0] shadow-ap-card';

  return (
    <section
      className={`rounded-[20px] border ${baseBg} ${glowClass} transition-all duration-200 relative overflow-hidden ${className}`}
    >
      {/* Header if specified */}
      {(title || actions || icon || badge) && (
        <div
          className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 sm:px-6 py-4 border-b border-[#EDE9F5] ${
            collapsible ? 'cursor-pointer select-none' : ''
          }`}
          onClick={collapsible ? () => setIsCollapsed(!isCollapsed) : undefined}
        >
          <div className="flex items-center space-x-3">
            {icon && (
              <div className="p-2 rounded-[10px] bg-[#F4EBFF] border border-[#E5D0FA] text-[#7C3AED] flex items-center justify-center shrink-0">
                {icon}
              </div>
            )}
            <div>
              <div className="flex items-center space-x-2">
                {title && (
                  <h3 className="text-sm sm:text-base font-semibold text-[#3B1D5E] tracking-tight">
                    {title}
                  </h3>
                )}
                {badge}
              </div>
              {subtitle && (
                <p className="text-xs text-[#6B5B84] font-normal mt-0.5 leading-normal">
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          <div
            className="flex items-center space-x-2 shrink-0 self-end sm:self-center"
            onClick={(e) => e.stopPropagation()}
          >
            {actions}
            {collapsible && (
              <button
                type="button"
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="p-1 rounded-[8px] text-[#6B5B84] hover:text-[#3B1D5E] hover:bg-[#F4F2FB] transition"
                title={isCollapsed ? 'Expand Section' : 'Collapse Section'}
              >
                <svg
                  className={`w-4 h-4 transform transition-transform duration-200 ${
                    isCollapsed ? '-rotate-90' : 'rotate-0'
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      {!isCollapsed && <div className={paddingClasses}>{children}</div>}
    </section>
  );
};
