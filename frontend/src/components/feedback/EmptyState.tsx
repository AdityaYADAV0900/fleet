import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Records Found',
  message = 'There is currently no telemetry, advisory, or log data matching the selected criteria.',
  icon,
  action,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-[#F4F2FB]/60 border border-dashed border-[#E6E2F0] rounded-[20px] my-3">
      <div className="p-3 bg-white text-[#7C3AED] rounded-[14px] mb-3 border border-[#E6E2F0] shadow-ap-sm">
        {icon || <Inbox className="w-6 h-6" />}
      </div>
      <h3 className="text-sm font-semibold text-[#3B1D5E] tracking-tight">{title}</h3>
      <p className="text-xs text-[#6B5B84] mt-1 max-w-sm">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 px-4 py-2 bg-[#1DE9C0] hover:bg-[#18D4AD] text-[#3B1D5E] font-semibold rounded-[10px] text-xs transition shadow-sm"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};
