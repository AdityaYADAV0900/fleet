import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { LoadingSkeleton } from '../feedback/LoadingSkeleton';
import { EmptyState } from '../feedback/EmptyState';

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  render?: (row: T, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  pagination?: {
    currentPage: number;
    totalPages: number;
    totalItems: number;
    pageSize: number;
    onPageChange: (page: number) => void;
  };
  maxHeight?: string;
  className?: string;
}

export function DataTable<T extends object>({
  columns,
  data,
  loading = false,
  emptyTitle,
  emptyMessage,
  onRowClick,
  pagination,
  maxHeight,
  className = '',
}: DataTableProps<T>): React.JSX.Element {
  if (loading) {
    return <LoadingSkeleton rows={5} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState title={emptyTitle} message={emptyMessage} />;
  }

  return (
    <div className={`w-full flex flex-col space-y-3 ${className}`}>
      <div
        className="overflow-x-auto rounded-[20px] border border-[#E6E2F0] bg-white shadow-ap-card"
        style={maxHeight ? { maxHeight, overflowY: 'auto' } : undefined}
      >
        <table className="w-full text-left text-xs border-collapse">
          <thead className="sticky top-0 z-10 bg-[#F4F2FB]">
            <tr className="border-b border-[#E6E2F0] text-[#6B5B84] uppercase text-[11px] font-semibold tracking-wider select-none">
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className={`py-3.5 px-4 ${
                    col.align === 'right'
                      ? 'text-right'
                      : col.align === 'center'
                      ? 'text-center'
                      : 'text-left'
                  } ${col.className || ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#EDE9F5] font-mono text-[#3B1D5E]">
            {data.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                onClick={() => onRowClick && onRowClick(row)}
                className={`transition-all duration-150 ${
                  onRowClick
                    ? 'cursor-pointer hover:bg-[#FBF9FE]'
                    : 'hover:bg-[#FBF9FE]/60'
                }`}
              >
                {columns.map((col, colIdx) => (
                  <td
                    key={colIdx}
                    className={`py-3.5 px-4 ${
                      col.align === 'right'
                        ? 'text-right'
                        : col.align === 'center'
                        ? 'text-center'
                        : 'text-left'
                    } ${col.className || ''}`}
                  >
                    {col.render
                      ? col.render(row, rowIdx)
                      : col.accessorKey
                      ? String((row as Record<string, unknown>)[col.accessorKey as string] ?? '—')
                      : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pagination && pagination.totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 px-2 text-xs font-mono text-[#6B5B84]">
          <div>
            Showing page <span className="font-bold text-[#3B1D5E]">{pagination.currentPage}</span> of{' '}
            <span className="font-bold text-[#3B1D5E]">{pagination.totalPages}</span> ({pagination.totalItems} items)
          </div>
          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => pagination.onPageChange(pagination.currentPage - 1)}
              disabled={pagination.currentPage <= 1}
              className="p-1.5 rounded-[10px] border border-[#E6E2F0] bg-white hover:bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] disabled:opacity-30 disabled:pointer-events-none transition shadow-sm"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-3 py-1 font-bold text-[#059669] bg-[#E6FCF7] rounded-[10px] border border-[#A3F5E4]">
              {pagination.currentPage}
            </span>
            <button
              onClick={() => pagination.onPageChange(pagination.currentPage + 1)}
              disabled={pagination.currentPage >= pagination.totalPages}
              className="p-1.5 rounded-[10px] border border-[#E6E2F0] bg-white hover:bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] disabled:opacity-30 disabled:pointer-events-none transition shadow-sm"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
