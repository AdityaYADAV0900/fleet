import React from 'react';
import { Filter, RotateCcw } from 'lucide-react';

interface FilterBarProps {
  children: React.ReactNode;
  onReset?: () => void;
  title?: string;
  totalResults?: number;
  className?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  children,
  onReset,
  title = 'Filters',
  totalResults,
  className = '',
}) => {
  return (
    <div
      className={`p-3.5 sm:p-4 bg-white border border-[#E6E2F0] rounded-[20px] shadow-ap-card flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs ${className}`}
    >
      <div className="flex flex-wrap items-center gap-2.5 flex-1">
        <div className="hidden sm:flex items-center space-x-1.5 text-[#3B1D5E] font-semibold tracking-wide pr-3 border-r border-[#EDE9F5]">
          <Filter className="w-3.5 h-3.5 text-[#7C3AED]" />
          <span className="text-[11px] uppercase">{title}</span>
        </div>
        {children}
      </div>

      <div className="flex items-center space-x-3 shrink-0 self-end md:self-center">
        {totalResults !== undefined && (
          <span className="text-[11px] text-[#6B5B84] font-mono">
            Found <strong className="text-[#3B1D5E] font-bold">{totalResults}</strong> records
          </span>
        )}
        {onReset && (
          <button
            onClick={onReset}
            className="px-2.5 py-1.5 rounded-[10px] bg-[#F4F2FB] hover:bg-[#EDE9F5] text-[#6B5B84] hover:text-[#3B1D5E] border border-[#E6E2F0] text-[11px] font-medium flex items-center space-x-1 transition shadow-sm"
            title="Reset Filters"
          >
            <RotateCcw className="w-3 h-3 text-[#7C3AED]" />
            <span>Reset</span>
          </button>
        )}
      </div>
    </div>
  );
};
