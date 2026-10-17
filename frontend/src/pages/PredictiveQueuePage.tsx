import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Play,
  CheckCircle,
  XCircle,
  ArrowRight,
  ShieldAlert,
  RefreshCw,
  Search,
  CheckSquare,
  Square,
  Package,
} from 'lucide-react';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton';
import { EmptyState } from '../components/feedback/EmptyState';
import { useAuth } from '../hooks/useAuth';
import {
  useAdvisories,
  useUpdateAdvisory,
  useRunEngine,
  usePredictions,
} from '../hooks/useEngineQueries';
import { useSystems, useAircraftList } from '../hooks/useFleetQueries';
import type { EngineRunSummaryOut } from '../types/api';

export const PredictiveQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const { role, asOfDate } = useAuth();
  const canAction = role === 'commander' || role === 'planner';

  // Filters
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('proposed');
  const [spareFilter, setSpareFilter] = useState<string>('all');
  const [systemFilter, setSystemFilter] = useState<string>('all');
  const [aircraftFilter, setAircraftFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 25;

  // Selection for bulk actions
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Modal states
  const [dismissTarget, setDismissTarget] = useState<{ id?: string; bulk?: boolean } | null>(null);
  const [dismissReason, setDismissReason] = useState<string>('');
  const [engineModalOpen, setEngineModalOpen] = useState<boolean>(false);
  const [engineAsOf, setEngineAsOf] = useState<string>(asOfDate || '');
  const [engineAircraft, setEngineAircraft] = useState<string>('');
  const [engineResult, setEngineResult] = useState<EngineRunSummaryOut | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Queries & Mutations
  const { data: advisoriesData, isLoading: loadingAdvisories, refetch } = useAdvisories({
    priority: priorityFilter !== 'all' ? priorityFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    spare_status: spareFilter !== 'all' ? spareFilter : undefined,
    aircraft_id: aircraftFilter !== 'all' ? aircraftFilter : undefined,
    as_of_date: asOfDate || undefined,
    page: currentPage,
    page_size: pageSize,
  });

  const { data: predictionsData } = usePredictions({ page_size: 200, as_of_date: asOfDate || undefined });
  const { data: systemsData } = useSystems();
  const { data: aircraftData } = useAircraftList({ page_size: 100 });

  const updateMutation = useUpdateAdvisory();
  const runEngineMutation = useRunEngine();

  // Prediction lookup map for fast RUL / risk display
  const predictionsMap = useMemo(() => {
    const map = new Map<string, { risk_14d: number; rul_p50: number }>();
    predictionsData?.items.forEach((p) => {
      map.set(p.component_id, { risk_14d: p.risk_14d, rul_p50: p.rul_p50 });
    });
    return map;
  }, [predictionsData]);

  // Client-side search and system filter
  const items = useMemo(() => {
    if (!advisoriesData?.items) return [];
    let list = advisoriesData.items;

    if (systemFilter !== 'all') {
      list = list.filter((a) => a.system_name?.toLowerCase().includes(systemFilter.toLowerCase()));
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (a) =>
          a.component_name?.toLowerCase().includes(q) ||
          a.component_id.toLowerCase().includes(q) ||
          a.tail_code?.toLowerCase().includes(q) ||
          a.action.toLowerCase().includes(q)
      );
    }

    return list;
  }, [advisoriesData, systemFilter, searchQuery]);

  // Checkbox multi-select helpers
  const allCurrentSelected = items.length > 0 && items.every((item) => selectedIds.has(item.advisory_id));

  const toggleSelectAll = () => {
    if (allCurrentSelected) {
      setSelectedIds(new Set());
    } else {
      const next = new Set<string>();
      items.forEach((item) => next.add(item.advisory_id));
      setSelectedIds(next);
    }
  };

  const toggleSelectOne = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  // Actions
  const handleSingleAccept = async (id: string) => {
    setActionError(null);
    try {
      await updateMutation.mutateAsync({ id, payload: { status: 'accepted' } });
      selectedIds.delete(id);
      setSelectedIds(new Set(selectedIds));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Accept failed');
    }
  };

  const handleBulkAccept = async () => {
    setActionError(null);
    try {
      for (const id of Array.from(selectedIds)) {
        await updateMutation.mutateAsync({ id, payload: { status: 'accepted' } });
      }
      setSelectedIds(new Set());
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Bulk accept failed');
    }
  };

  const handleDismissSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dismissReason.trim()) return;
    setActionError(null);

    try {
      if (dismissTarget?.bulk) {
        for (const id of Array.from(selectedIds)) {
          await updateMutation.mutateAsync({
            id,
            payload: { status: 'dismissed', reason: dismissReason.trim() },
          });
        }
        setSelectedIds(new Set());
      } else if (dismissTarget?.id) {
        await updateMutation.mutateAsync({
          id: dismissTarget.id,
          payload: { status: 'dismissed', reason: dismissReason.trim() },
        });
      }
      setDismissTarget(null);
      setDismissReason('');
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Dismissal failed');
    }
  };

  const handleRunEngineSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEngineResult(null);
    setActionError(null);

    try {
      const res = await runEngineMutation.mutateAsync({
        as_of_date: engineAsOf || undefined,
        aircraft_id: engineAircraft || undefined,
      });
      setEngineResult(res);
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Scoring engine run failed');
    }
  };

  const p1Count = useMemo(() => items.filter((a) => a.priority === 'P1').length, [items]);
  const p2Count = useMemo(() => items.filter((a) => a.priority === 'P2').length, [items]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E6E2F0] pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-[#FEF2F2] border border-[#FCA5A5] rounded-[12px] text-[#DC2626] shadow-sm">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-[#3B1D5E] tracking-tight flex items-center gap-2">
                Predictive Maintenance Queue
              </h1>
              <p className="text-xs text-[#6B5B84] mt-0.5">
                Priority-ranked risk worklist generated from ML inference, failure rules, and spares stock
              </p>
            </div>
          </div>
        </div>

        {/* Header Right Actions */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => refetch()}
            disabled={loadingAdvisories}
            className="p-2 bg-white border border-[#E6E2F0] hover:bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] rounded-[10px] text-xs transition shadow-sm"
            title="Refresh Queue"
          >
            <RefreshCw className={`w-4 h-4 ${loadingAdvisories ? 'animate-spin' : ''}`} />
          </button>

          {canAction && (
            <button
              onClick={() => {
                setEngineResult(null);
                setEngineModalOpen(true);
              }}
              className="py-2 px-4 bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] rounded-[10px] text-xs font-bold flex items-center space-x-1.5 transition shadow-ap-mint"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Trigger Scoring Engine</span>
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="p-3.5 bg-[#FEF2F2] border border-[#FCA5A5] rounded-[12px] text-xs text-[#DC2626]">
          {actionError}
        </div>
      )}

      {/* 2. LEVEL 1: Queue Status Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5 text-xs">
        <div className="p-4 bg-white border border-[#E6E2F0] rounded-[16px] shadow-ap-card flex items-center justify-between">
          <div>
            <div className="text-[10px] text-[#DC2626] uppercase font-bold tracking-wider">P1 Critical Queue</div>
            <div className="text-2xl font-bold font-mono text-[#3B1D5E] mt-1">{p1Count}</div>
          </div>
          <span className="w-3 h-3 rounded-full bg-[#EF4444] animate-ping" />
        </div>

        <div className="p-4 bg-white border border-[#E6E2F0] rounded-[16px] shadow-ap-card flex items-center justify-between">
          <div>
            <div className="text-[10px] text-[#D97706] uppercase font-bold tracking-wider">P2 High Queue</div>
            <div className="text-2xl font-bold font-mono text-[#3B1D5E] mt-1">{p2Count}</div>
          </div>
          <span className="w-3 h-3 rounded-full bg-[#F59E0B]" />
        </div>

        <div className="p-4 bg-white border border-[#E6E2F0] rounded-[16px] shadow-ap-card flex items-center justify-between">
          <div>
            <div className="text-[10px] text-[#6B5B84] uppercase font-bold tracking-wider">Selected Items</div>
            <div className="text-2xl font-bold font-mono text-[#0D6553] mt-1">{selectedIds.size}</div>
          </div>
          <CheckSquare className="w-5 h-5 text-[#0D6553]" />
        </div>

        <div className="p-4 bg-white border border-[#E6E2F0] rounded-[16px] shadow-ap-card flex items-center justify-between">
          <div>
            <div className="text-[10px] text-[#6B5B84] uppercase font-bold tracking-wider">Total In Filter</div>
            <div className="text-2xl font-bold font-mono text-[#3B1D5E] mt-1">{advisoriesData?.total ?? 0}</div>
          </div>
          <Package className="w-5 h-5 text-[#8F7FA8]" />
        </div>
      </div>

      {/* 3. LEVEL 2: Filters & Search Strip */}
      <div className="p-4 bg-white border border-[#E6E2F0] rounded-[16px] space-y-3 text-xs shadow-ap-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {/* Priority Filter */}
            <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
              <span className="text-[#6B5B84] text-[11px]">Priority:</span>
              <select
                value={priorityFilter}
                onChange={(e) => {
                  setPriorityFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
              >
                <option value="all">All Priorities</option>
                <option value="P1">P1 — Critical Grounding</option>
                <option value="P2">P2 — High Urgency</option>
                <option value="P3">P3 — Watch Window</option>
                <option value="P4">P4 — Routine Deferred</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
              <span className="text-[#6B5B84] text-[11px]">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
              >
                <option value="all">All Statuses</option>
                <option value="proposed">Proposed (Action Needed)</option>
                <option value="accepted">Accepted</option>
                <option value="scheduled">Scheduled</option>
                <option value="completed">Completed</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>

            {/* Functional System Filter */}
            <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
              <span className="text-[#6B5B84] text-[11px]">System:</span>
              <select
                value={systemFilter}
                onChange={(e) => setSystemFilter(e.target.value)}
                className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
              >
                <option value="all">All Systems</option>
                {systemsData?.map((s) => (
                  <option key={s.system_id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Spare Status Filter */}
            <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
              <span className="text-[#6B5B84] text-[11px]">Spare:</span>
              <select
                value={spareFilter}
                onChange={(e) => {
                  setSpareFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
              >
                <option value="all">All Stock</option>
                <option value="in_stock">In Stock</option>
                <option value="low_stock">Low Stock</option>
                <option value="out_of_stock">Out of Stock</option>
              </select>
            </div>

            {/* Airframe Filter */}
            <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
              <span className="text-[#6B5B84] text-[11px]">Airframe:</span>
              <select
                value={aircraftFilter}
                onChange={(e) => {
                  setAircraftFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-transparent text-[#3B1D5E] font-semibold font-mono focus:outline-none cursor-pointer"
              >
                <option value="all">All Fleet</option>
                {aircraftData?.items.map((ac) => (
                  <option key={ac.aircraft_id} value={ac.aircraft_id}>
                    {ac.tail_code}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#8F7FA8] absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search component, action..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#F4F2FB] border border-[#E6E2F0] text-[#3B1D5E] text-xs rounded-[8px] pl-8 pr-3 py-1.5 w-60 focus:outline-none focus:border-[#1DE9C0] placeholder-[#8F7FA8]"
            />
          </div>
        </div>

        {/* Bulk Action Bar (when selected) */}
        {selectedIds.size > 0 && canAction && (
          <div className="pt-2.5 border-t border-[#E6E2F0] flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <span className="text-[#0D6553] font-bold">
              {selectedIds.size} advisories selected for bulk operation
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleBulkAccept}
                disabled={updateMutation.isPending}
                className="py-1.5 px-3 bg-[#059669] hover:bg-[#047857] text-white rounded-[8px] font-bold flex items-center gap-1 transition shadow-sm"
              >
                <CheckCircle className="w-3.5 h-3.5" /> Accept Selected ({selectedIds.size})
              </button>
              <button
                onClick={() => setDismissTarget({ bulk: true })}
                disabled={updateMutation.isPending}
                className="py-1.5 px-3 bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] border border-[#FCA5A5] rounded-[8px] font-bold flex items-center gap-1 transition"
              >
                <XCircle className="w-3.5 h-3.5" /> Dismiss Selected ({selectedIds.size})
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 4. LEVEL 3: Advisories Data Table */}
      <div className="overflow-x-auto rounded-[20px] border border-[#E6E2F0] bg-white shadow-ap-card">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[#E6E2F0] bg-[#F4F2FB] text-[#6B5B84] uppercase text-[11px] tracking-wider select-none font-semibold">
              <th className="py-3 px-3 w-10 text-center">
                <button
                  onClick={toggleSelectAll}
                  className="text-[#6B5B84] hover:text-[#3B1D5E] transition"
                  title="Toggle Select All"
                >
                  {allCurrentSelected ? (
                    <CheckSquare className="w-4 h-4 text-[#0D6553]" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                </button>
              </th>
              <th className="py-3 px-3 text-center">Priority</th>
              <th className="py-3 px-4">Airframe</th>
              <th className="py-3 px-4">Component & System</th>
              <th className="py-3 px-4">Recommended Action</th>
              <th className="py-3 px-3 text-right">Risk (14d)</th>
              <th className="py-3 px-3 text-right">RUL (P50)</th>
              <th className="py-3 px-3 text-center">Spare</th>
              <th className="py-3 px-3 text-right">Downtime</th>
              <th className="py-3 px-3 text-center">Status</th>
              <th className="py-3 px-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E6E2F0] text-[#3B1D5E]">
            {loadingAdvisories ? (
              <tr>
                <td colSpan={11} className="py-8">
                  <LoadingSkeleton rows={6} />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={11} className="py-12">
                  <EmptyState
                    title="No Advisories Found"
                    message="No predictive maintenance advisories match the current filter criteria."
                  />
                </td>
              </tr>
            ) : (
              items.map((advisory) => {
                const isSelected = selectedIds.has(advisory.advisory_id);
                const pred = predictionsMap.get(advisory.component_id);
                const riskVal = pred?.risk_14d;
                const rulVal = pred?.rul_p50;

                return (
                  <tr
                    key={advisory.advisory_id}
                    className={`transition-all duration-150 ${
                      isSelected ? 'bg-[#E6FCF7]' : 'hover:bg-[#FBF9FE]'
                    }`}
                  >
                    {/* Checkbox */}
                    <td className="py-3 px-3 text-center">
                      <button
                        onClick={() => toggleSelectOne(advisory.advisory_id)}
                        className="text-[#8F7FA8] hover:text-[#3B1D5E] transition"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-[#0D6553]" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                    </td>

                    {/* Priority */}
                    <td className="py-3 px-3 text-center">
                      <StatusBadge status={advisory.priority} size="sm" />
                    </td>

                    {/* Airframe */}
                    <td className="py-3 px-4">
                      <button
                        onClick={() => navigate(`/aircraft?id=${advisory.aircraft_id}`)}
                        className="font-bold font-mono text-[#3B1D5E] hover:text-[#0D6553] transition"
                      >
                        {advisory.tail_code || advisory.aircraft_id}
                      </button>
                    </td>

                    {/* Component */}
                    <td className="py-3 px-4">
                      <div>
                        <button
                          onClick={() => navigate(`/components/${advisory.component_id}`)}
                          className="font-semibold text-[#3B1D5E] hover:text-[#0D6553] transition text-left"
                        >
                          {advisory.component_name || advisory.component_id}
                        </button>
                        <div className="text-[10px] text-[#8F7FA8]">{advisory.system_name}</div>
                      </div>
                    </td>

                    {/* Action */}
                    <td className="py-3 px-4">
                      <span className="text-[#3B1D5E] font-medium flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 shrink-0 text-[#D97706]" />
                        {advisory.action}
                      </span>
                    </td>

                    {/* Risk */}
                    <td className="py-3 px-3 text-right font-bold font-mono">
                      <span
                        className={
                          (riskVal ?? 0) >= 0.5
                            ? 'text-[#DC2626]'
                            : (riskVal ?? 0) >= 0.2
                            ? 'text-[#D97706]'
                            : 'text-[#6B5B84]'
                        }
                      >
                        {riskVal !== undefined ? `${(riskVal * 100).toFixed(0)}%` : '—'}
                      </span>
                    </td>

                    {/* RUL */}
                    <td className="py-3 px-3 text-right font-bold font-mono">
                      <span
                        className={
                          (rulVal ?? 99) <= 14
                            ? 'text-[#DC2626]'
                            : (rulVal ?? 99) <= 30
                            ? 'text-[#D97706]'
                            : 'text-[#3B1D5E]'
                        }
                      >
                        {rulVal !== undefined ? `${Math.round(rulVal)}d` : '—'}
                      </span>
                    </td>

                    {/* Spare */}
                    <td className="py-3 px-3 text-center">
                      <StatusBadge status={advisory.spare_status || 'in_stock'} size="sm" />
                    </td>

                    {/* Expected Downtime */}
                    <td className="py-3 px-3 text-right text-[#6B5B84] font-mono font-bold">
                      {advisory.expected_downtime_days ? `${advisory.expected_downtime_days}d` : '—'}
                    </td>

                    {/* Status */}
                    <td className="py-3 px-3 text-center">
                      <StatusBadge status={advisory.status} size="sm" />
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center space-x-1.5">
                        {canAction && advisory.status === 'proposed' && (
                          <>
                            <button
                              onClick={() => handleSingleAccept(advisory.advisory_id)}
                              disabled={updateMutation.isPending}
                              className="p-1 px-2.5 bg-[#ECFDF5] hover:bg-[#059669] text-[#059669] hover:text-white rounded-[8px] border border-[#A7F3D0] text-[10px] font-bold transition"
                              title="Accept Advisory"
                            >
                              Accept
                            </button>

                            <button
                              onClick={() =>
                                navigate(
                                  `/planning?aircraft=${advisory.aircraft_id}&component=${advisory.component_id}&advisory=${advisory.advisory_id}`
                                )
                              }
                              className="p-1 px-2.5 bg-[#E0F8FA] hover:bg-[#1DE9C0] text-[#0D6553] hover:text-[#1E1035] rounded-[8px] border border-[#1DE9C0]/40 text-[10px] font-bold transition shadow-sm"
                              title="Schedule Work Order"
                            >
                              Schedule
                            </button>

                            <button
                              onClick={() => setDismissTarget({ id: advisory.advisory_id })}
                              className="p-1 px-1.5 bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] border border-[#FCA5A5] rounded-[8px] text-[10px] transition"
                              title="Dismiss with reason"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}

                        <button
                          onClick={() => navigate(`/components/${advisory.component_id}`)}
                          className="p-1 px-1.5 text-[#8F7FA8] hover:text-[#0D6553] transition"
                          title="View Telemetry Evidence"
                        >
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* 5. LEVEL 4: Pagination Footer */}
      {advisoriesData && advisoriesData.total_pages > 1 && (
        <div className="flex items-center justify-between px-2 text-xs text-[#6B5B84]">
          <div>
            Page <span className="font-bold text-[#3B1D5E]">{advisoriesData.page}</span> of{' '}
            <span className="font-bold text-[#3B1D5E]">{advisoriesData.total_pages}</span> ({advisoriesData.total}{' '}
            advisories)
          </div>
          <div className="flex space-x-1.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="px-3 py-1 rounded-[8px] border border-[#E6E2F0] bg-white hover:bg-[#F4F2FB] text-[#3B1D5E] disabled:opacity-40 shadow-sm"
            >
              Prev
            </button>
            <button
              onClick={() => setCurrentPage((p) => p + 1)}
              disabled={currentPage >= advisoriesData.total_pages}
              className="px-3 py-1 rounded-[8px] border border-[#E6E2F0] bg-white hover:bg-[#F4F2FB] text-[#3B1D5E] disabled:opacity-40 shadow-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* MODAL 1: Dismissal Audit Reason Modal */}
      {dismissTarget && (
        <div className="fixed inset-0 bg-[#3B1D5E]/30 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleDismissSubmit}
            className="bg-white border border-[#E6E2F0] rounded-[20px] p-6 max-w-md w-full shadow-ap-floating space-y-4 text-xs"
          >
            <div className="flex items-center space-x-2 text-[#DC2626]">
              <ShieldAlert className="w-5 h-5" />
              <h3 className="font-bold text-sm text-[#3B1D5E]">
                Override & Dismissal Justification
              </h3>
            </div>
            <p className="text-[#6B5B84]">
              {dismissTarget.bulk
                ? `You are dismissing ${selectedIds.size} selected advisories. An audit justification is required by fleet decision rules:`
                : `You are dismissing advisory #${dismissTarget.id}. Enter an engineering justification:`}
            </p>
            <textarea
              required
              rows={3}
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              placeholder="e.g. Visual inspection performed; component confirmed nominal with zero play; sensor drift documented."
              className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] p-2.5 text-[#3B1D5E] focus:outline-none focus:border-[#1DE9C0] placeholder-[#8F7FA8]"
            />
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setDismissTarget(null)}
                className="px-3 py-1.5 bg-[#F4F2FB] hover:bg-white text-[#6B5B84] rounded-[8px] font-bold border border-[#E6E2F0]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!dismissReason.trim() || updateMutation.isPending}
                className="px-3.5 py-1.5 bg-[#DC2626] hover:bg-[#B91C1C] text-white rounded-[8px] font-bold shadow-sm"
              >
                Confirm Dismissal
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 2: Batch Scoring Engine Trigger Modal */}
      {engineModalOpen && (
        <div className="fixed inset-0 bg-[#3B1D5E]/30 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-6 max-w-lg w-full shadow-ap-floating space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-[#E6E2F0] pb-3">
              <div className="flex items-center space-x-2 text-[#0D6553]">
                <Play className="w-5 h-5 fill-current" />
                <h3 className="font-bold text-sm text-[#3B1D5E]">
                  Execute Predictive Maintenance Scoring Engine
                </h3>
              </div>
              <button
                onClick={() => setEngineModalOpen(false)}
                className="text-[#8F7FA8] hover:text-[#3B1D5E]"
              >
                ✕
              </button>
            </div>

            <p className="text-[#6B5B84] leading-relaxed">
              Triggers the scoring engine to evaluate rolling flight telemetry,
              infer failure risk and RUL models, synthesize prioritization rules, and generate updated advisories.
            </p>

            <form onSubmit={handleRunEngineSubmit} className="space-y-4">
              <div>
                <label className="block text-[#6B5B84] mb-1 font-semibold">Reference Date (as_of_date)</label>
                <input
                  type="date"
                  value={engineAsOf}
                  onChange={(e) => setEngineAsOf(e.target.value)}
                  className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] focus:outline-none focus:border-[#1DE9C0]"
                />
                <span className="text-[10px] text-[#8F7FA8] mt-1 block">
                  Leave blank to score against latest flight telemetry date.
                </span>
              </div>

              <div>
                <label className="block text-[#6B5B84] mb-1 font-semibold">Target Airframe (Optional)</label>
                <select
                  value={engineAircraft}
                  onChange={(e) => setEngineAircraft(e.target.value)}
                  className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] focus:outline-none focus:border-[#1DE9C0] cursor-pointer"
                >
                  <option value="">Full Fleet (All Airframes)</option>
                  {aircraftData?.items.map((ac) => (
                    <option key={ac.aircraft_id} value={ac.aircraft_id}>
                      {ac.tail_code} ({ac.type_code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Execution Summary Report */}
              {engineResult && (
                <div className="p-3.5 bg-[#E6FCF7] border border-[#1DE9C0]/50 rounded-[12px] space-y-1.5 text-[11px] text-[#0D6553] shadow-sm">
                  <div className="font-bold flex items-center gap-1.5 text-[#0D6553]">
                    <CheckCircle className="w-4 h-4 text-[#0D6553]" />
                    Engine Run Complete ({engineResult.duration_seconds.toFixed(2)}s)
                  </div>
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1 pt-1 text-[#3B1D5E]">
                    <div>Components Scored: <strong>{engineResult.components_scored}</strong></div>
                    <div>Predictions Logged: <strong>{engineResult.predictions_recorded}</strong></div>
                    <div>Advisories Raised: <strong>{engineResult.advisories_generated}</strong></div>
                    <div>P1 / P2 Critical: <strong className="text-[#DC2626]">{engineResult.p1_count} / {engineResult.p2_count}</strong></div>
                  </div>
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-2 border-t border-[#E6E2F0]">
                <button
                  type="button"
                  onClick={() => setEngineModalOpen(false)}
                  className="px-3.5 py-1.5 bg-[#F4F2FB] hover:bg-white text-[#6B5B84] rounded-[8px] font-semibold border border-[#E6E2F0]"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={runEngineMutation.isPending}
                  className="px-4 py-1.5 bg-[#1DE9C0] hover:bg-[#15d1ac] disabled:opacity-50 text-[#1E1035] rounded-[8px] font-bold flex items-center gap-1.5 shadow-ap-mint"
                >
                  {runEngineMutation.isPending ? 'Scoring Fleet...' : 'Run Scoring Job'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
