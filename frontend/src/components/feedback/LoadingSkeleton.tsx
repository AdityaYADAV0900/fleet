import React from 'react';

interface LoadingSkeletonProps {
  rows?: number;
  className?: string;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ rows = 4, className = '' }) => {
  return (
    <div className={`space-y-3 animate-pulse p-4 ${className}`}>
      <div className="h-4 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] w-1/3 mb-4" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-4">
          <div className="h-3.5 bg-[#F4F2FB] rounded-[6px] w-1/4" />
          <div className="h-3.5 bg-[#EDE9F5] rounded-[6px] w-1/2" />
          <div className="h-3.5 bg-[#F4F2FB] rounded-[6px] w-1/4" />
        </div>
      ))}
    </div>
  );
};

