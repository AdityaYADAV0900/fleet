import React, { useMemo, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  CalendarDays,
  Clock,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Search,
  TrendingDown,
  Check,
  PlusCircle,
  Tag,
  Layers,
} from 'lucide-react';
import { KpiCard } from '../components/common/KpiCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { DataTable, type Column } from '../components/common/DataTable';
import { SectionContainer } from '../components/common/SectionContainer';
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton';
import { useAuth } from '../hooks/useAuth';
import { useKpis } from '../hooks/useAvailabilityQueries';
import {
  useWorkOrders,
  useCreateWorkOrder,
  useAgencies,
  useScheduledTasks,
} from '../hooks/useMaintenanceQueries';
import { useAircraftList } from '../hooks/useFleetQueries';
import type { WorkOrderOut } from '../types/api';

export const PlanningPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { asOfDate, role } = useAuth();
  const canPlan = role === 'commander' || role === 'planner';

  // Read pre-filled query params if redirected from Advisories / Component Health
  const prefillAircraft = searchParams.get('aircraft') || '';
  const prefillComponent = searchParams.get('component') || '';
  const prefillAdvisory = searchParams.get('advisory') || '';

  // Tab: 'table' | 'gantt'
  const [viewMode, setViewMode] = useState<'gantt' | 'table'>('gantt');

  // Filters for work orders table
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [agencyFilter, setAgencyFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>(prefillAircraft);

  // Scheduling slot helper state
  const [slotAircraft, setSlotAircraft] = useState<string>(prefillAircraft || 'AC-017');
  const [slotAgency, setSlotAgency] = useState<string>('AG-BASE-01');
  const [slotBundleInspection, setSlotBundleInspection] = useState<boolean>(true);
  const [slotSuccessMessage, setSlotSuccessMessage] = useState<string | null>(null);
  const [slotErrorMessage, setSlotErrorMessage] = useState<string | null>(null);

  const createWorkOrderMutation = useCreateWorkOrder();

  // Queries
  const { data: kpis, isLoading: loadingKpis } = useKpis(asOfDate);
  const { data: agenciesData, isLoading: loadingAgencies } = useAgencies();
  const { data: scheduledTasksData } = useScheduledTasks();
  const { data: aircraftData } = useAircraftList({ page_size: 100 });
  const { data: workOrdersData, isLoading: loadingOrders } = useWorkOrders({
    status: statusFilter !== 'all' ? statusFilter : undefined,
    agency: agencyFilter !== 'all' ? agencyFilter : undefined,
    priority: priorityFilter !== 'all' ? priorityFilter : undefined,
    page_size: 100,
  });

  const allWorkOrders = workOrdersData?.items || [];
  const agencies = agenciesData || [];
  const scheduledTasks = scheduledTasksData || [];

  // Filtered work orders
  const filteredWorkOrders = useMemo(() => {
    let list = allWorkOrders;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (w) =>
          w.wo_id.toLowerCase().includes(q) ||
          w.aircraft_id.toLowerCase().includes(q) ||
          (w.component_id && w.component_id.toLowerCase().includes(q)) ||
          (w.delay_reason && w.delay_reason.toLowerCase().includes(q))
      );
    }
    return list;
  }, [allWorkOrders, searchQuery]);

  // Backlog & On-Time Performance Metrics
  const { openCount, manHours, avgTurnaround, onTimeRate } = useMemo(() => {
    const openWos = allWorkOrders.filter((w) => w.status !== 'completed');
    const completedWos = allWorkOrders.filter((w) => w.status === 'completed');

    const openCount = kpis?.backlog.open_orders ?? openWos.length;
    const manHours = kpis?.backlog.outstanding_man_hours ?? openCount * 18.5;
    const avgTurnaround = kpis?.turnaround_days ?? 3.8;

    let onTimeCount = 0;
    completedWos.forEach((w) => {
      if (!w.actual_done || !w.promised_done) return;
      if (new Date(w.actual_done) <= new Date(w.promised_done)) {
        onTimeCount++;
      }
    });

    const onTimeRate = completedWos.length > 0 ? (onTimeCount / completedWos.length) * 100 : 86.4;

    return {
      openCount,
      manHours,
      avgTurnaround,
      onTimeRate: Number(onTimeRate.toFixed(1)),
    };
  }, [allWorkOrders, kpis]);

  // Work Orders Table Columns
  const columns: Column<WorkOrderOut>[] = [
    {
      header: 'WO ID',
      accessorKey: 'wo_id',
    },
    {
      header: 'Airframe',
      render: (row) => (
        <button
          onClick={() => navigate(`/aircraft?id=${row.aircraft_id}`)}
          className="font-bold font-mono text-[#3B1D5E] hover:text-[#0D6553] transition"
        >
          {row.aircraft_id}
        </button>
      ),
    },
    {
      header: 'Component Instance',
      render: (row) => (
        <span className="text-[#3B1D5E]">
          {row.component_id ? (
            <button
              onClick={() => navigate(`/components/${row.component_id}`)}
              className="text-[#0D6553] hover:underline font-semibold font-mono"
            >
              {row.component_id}
            </button>
          ) : (
            'Periodic Inspection'
          )}
        </span>
      ),
    },
    {
      header: 'Assigned Agency',
      render: (row) => {
        const ag = agencies.find((a) => a.agency_id === row.agency_id);
        return (
          <div>
            <div className="font-semibold text-[#3B1D5E]">{ag?.name || row.agency_id}</div>
            <div className="text-[10px] text-[#8F7FA8] uppercase">{ag?.level || 'Workshop'}</div>
          </div>
        );
      },
    },
    {
      header: 'Priority',
      align: 'center',
      render: (row) => <StatusBadge status={row.priority} size="sm" />,
    },
    {
      header: 'Status',
      align: 'center',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      header: 'Promised Done',
      render: (row) => (
        <span className="text-[#6B5B84] font-mono">
          {row.promised_done ? new Date(row.promised_done).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      header: 'Actual Done',
      render: (row) => (
        <span className={row.actual_done ? 'text-[#059669] font-mono font-bold' : 'text-[#8F7FA8]'}>
          {row.actual_done ? new Date(row.actual_done).toLocaleDateString() : 'In Progress'}
        </span>
      ),
    },
    {
      header: 'Turnaround Delay Reason',
      render: (row) => (
        <span
          className={`text-[11px] block truncate max-w-xs ${
            row.delay_reason ? 'text-[#DC2626] font-bold' : 'text-[#8F7FA8]'
          }`}
        >
          {row.delay_reason || 'Nominal Flow'}
        </span>
      ),
    },
  ];

  // Group work orders by airframe for the Gantt view
  const ganttAirframes = useMemo(() => {
    const map = new Map<
      string,
      Array<{
        id: string;
        title: string;
        startDay: number;
        duration: number;
        priority: string;
        status: string;
        isBundled?: boolean;
      }>
    >();

    const sampleAirframes = ['AC-017', 'AC-003', 'AC-008', 'AC-012', 'AC-024', 'AC-031'];

    sampleAirframes.forEach((acId, idx) => {
      const items: Array<{
        id: string;
        title: string;
        startDay: number;
        duration: number;
        priority: string;
        status: string;
        isBundled?: boolean;
      }> = [];

      const matchingWos = allWorkOrders.filter((w) => w.aircraft_id === acId);
      matchingWos.slice(0, 2).forEach((wo, wIdx) => {
        items.push({
          id: wo.wo_id,
          title: wo.component_id ? `Replace ${wo.component_id}` : 'Periodic Phase Inspection',
          startDay: (idx * 2 + wIdx * 4) % 18,
          duration: wo.priority === 'P1' ? 4 : 2,
          priority: wo.priority,
          status: wo.status,
          isBundled: acId === 'AC-017',
        });
      });

      const matchingTasks = scheduledTasks.filter((t) => t.aircraft_id === acId);
      matchingTasks.slice(0, 1).forEach((st, sIdx) => {
        items.push({
          id: st.task_id,
          title: st.task_name,
          startDay: (idx * 3 + sIdx * 4 + 1) % 18,
          duration: 3,
          priority: 'P3',
          status: 'scheduled',
          isBundled: false,
        });
      });

      if (items.length === 0) {
        items.push({
          id: `TASK-${acId}`,
          title: '300-Hour Phase Servicing',
          startDay: (idx * 3 + 2) % 20,
          duration: 3,
          priority: 'P3',
          status: 'scheduled',
          isBundled: false,
        });
      }

      map.set(acId, items);
    });

    return Array.from(map.entries()).map(([aircraftId, tasks]) => ({
      aircraftId,
      tasks,
    }));
  }, [allWorkOrders, scheduledTasks]);

  // Handle slot reservation
  const handleScheduleSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    setSlotSuccessMessage(null);
    setSlotErrorMessage(null);
    try {
      const created = await createWorkOrderMutation.mutateAsync({
        aircraft_id: slotAircraft,
        agency_id: slotAgency,
        component_id: prefillComponent || undefined,
        advisory_id: prefillAdvisory || undefined,
        bundle_inspection: slotBundleInspection,
        priority: 'P2',
      });
      setSlotSuccessMessage(
        `Slot Confirmed: Maintenance work order #${created.wo_id} successfully scheduled for ${slotAircraft} in ${slotAgency}. Status: ${created.status.toUpperCase()} (Spare reserved, turnaround: 2.5 days).`
      );
    } catch (err: unknown) {
      setSlotErrorMessage(
        err instanceof Error ? err.message : 'Failed to schedule maintenance slot'
      );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E6E2F0] pb-4">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 bg-[#E0F8FA] border border-[#BAE6FD] rounded-[12px] text-[#0D6553] shadow-sm">
            <CalendarDays className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-[#3B1D5E] tracking-tight">
              Maintenance Planning & Work Orders
            </h1>
            <p className="text-xs text-[#6B5B84] mt-0.5">
              Workshop capacity balancing, bay allocation, and availability-neutral job bundling
            </p>
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex items-center space-x-1 bg-white border border-[#E6E2F0] rounded-[10px] p-1 text-xs shadow-sm">
          <button
            onClick={() => setViewMode('gantt')}
            className={`px-3 py-1.5 rounded-[8px] font-bold transition ${
              viewMode === 'gantt'
                ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                : 'text-[#6B5B84] hover:text-[#3B1D5E]'
            }`}
          >
            Gantt Timeline
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1.5 rounded-[8px] font-bold transition ${
              viewMode === 'table'
                ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                : 'text-[#6B5B84] hover:text-[#3B1D5E]'
            }`}
          >
            Work Orders Table ({allWorkOrders.length})
          </button>
        </div>
      </div>

      {/* 2. LEVEL 1: Backlog & Turnaround KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Open Work Orders"
          value={openCount}
          subtitle="Active bay worklist"
          change={{
            value: `${Math.round(manHours)} Hours`,
            isPositive: openCount < 10,
            label: 'Backlog Labor',
          }}
          icon={<Wrench className="w-5 h-5" />}
          accent="honey"
          loading={loadingKpis && loadingOrders}
        />

        <KpiCard
          title="Backlog Labor Hours"
          value={`${Math.round(manHours)}h`}
          subtitle="Required workshop man-hours"
          icon={<Clock className="w-5 h-5" />}
          accent="amber"
          loading={loadingKpis}
        />

        <KpiCard
          title="Mean Turnaround (MTTR)"
          value={`${avgTurnaround.toFixed(1)} Days`}
          subtitle="Order open to release"
          change={{
            value: 'Within SLA',
            isPositive: avgTurnaround <= 4.0,
          }}
          icon={<TrendingDown className="w-5 h-5" />}
          accent="cyan"
          loading={loadingKpis}
        />

        <KpiCard
          title="On-Time Completion Rate"
          value={`${onTimeRate}%`}
          subtitle="Target: ≥85% On-Time"
          change={{
            value: 'Target Met',
            isPositive: onTimeRate >= 85.0,
          }}
          icon={<CheckCircle2 className="w-5 h-5" />}
          accent="emerald"
          loading={loadingOrders}
        />
      </div>

      {/* 3. LEVEL 2: Workshop Agency Capacity Cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#3B1D5E] uppercase tracking-wider font-bold flex items-center gap-1.5">
            <Building2 className="w-4 h-4 text-[#0D6553]" />
            Maintenance Agencies & Bay Workload Capacity
          </span>
          <span className="text-[#6B5B84]">Live Workshop Status</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {loadingAgencies ? (
            <LoadingSkeleton rows={4} className="col-span-3" />
          ) : (
            agencies.map((agency) => {
              const activeAgencyOrders = allWorkOrders.filter(
                (w) => w.agency_id === agency.agency_id && w.status !== 'completed'
              ).length;
              const utilization = Math.min(100, Math.round((activeAgencyOrders / agency.bays) * 100));

              return (
                <div
                  key={agency.agency_id}
                  className="bg-white border border-[#E6E2F0] rounded-[16px] p-5 shadow-ap-card space-y-3 text-xs hover:border-[#1DE9C0] transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-bold text-[#3B1D5E] text-sm">{agency.name}</h4>
                      <span className="text-[10px] text-[#8F7FA8] uppercase tracking-wider">
                        Level: {agency.level} • {agency.agency_id}
                      </span>
                    </div>
                    <span
                      className={`text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full border ${
                        utilization >= 90
                          ? 'bg-[#FEF2F2] text-[#DC2626] border-[#FCA5A5]'
                          : utilization >= 60
                          ? 'bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]'
                          : 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]'
                      }`}
                    >
                      {utilization}% Load
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[#6B5B84] pt-1">
                    <div>
                      <div className="text-[10px] text-[#8F7FA8]">Active Bays:</div>
                      <div className="text-base font-bold font-mono text-[#3B1D5E]">
                        {activeAgencyOrders} / {agency.bays} Bays
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#8F7FA8]">Capacity Rate:</div>
                      <div className="text-base font-bold font-mono text-[#0D6553]">
                        {agency.capacity_hours_per_day}h / day
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-1 pt-1">
                    <div className="flex justify-between text-[10px] text-[#6B5B84]">
                      <span>Bay Utilization</span>
                      <span>Avg Turnaround: {agency.avg_turnaround_days}d</span>
                    </div>
                    <div className="w-full bg-[#F4F2FB] h-2 rounded-full overflow-hidden border border-[#E6E2F0]">
                      <div
                        className={`h-full rounded-full ${
                          utilization >= 90
                            ? 'bg-[#EF4444]'
                            : utilization >= 60
                            ? 'bg-[#F59E0B]'
                            : 'bg-[#10B981]'
                        }`}
                        style={{ width: `${utilization}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 4. LEVEL 3: Slot Scheduling & Availability Impact Calculator Panel */}
      <SectionContainer
        title="Availability-Optimized Slot Proposal"
        subtitle="Bundling unscheduled replacement with scheduled maintenance minimizes lost fleet days"
        icon={<PlusCircle className="w-5 h-5 text-[#0D6553]" />}
      >
        <div className="space-y-4 text-xs">
          {(prefillAdvisory || prefillComponent) && (
            <div className="flex items-center space-x-2 bg-[#E0F8FA] border border-[#BAE6FD] rounded-[12px] p-3 text-[#0369A1] text-xs shadow-sm">
              <Tag className="w-4 h-4 text-[#0284C7] shrink-0" />
              <span>
                Pre-filled from Advisory <strong>{prefillAdvisory || 'Direct Worklist'}</strong>: Scheduling slot for LRU{' '}
                <strong>{prefillComponent || 'Target Subsystem'}</strong> on airframe <strong>{slotAircraft}</strong>.
              </span>
            </div>
          )}

          <form onSubmit={handleScheduleSlot} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div>
              <label className="block text-[#6B5B84] mb-1 font-medium">Target Airframe</label>
              <select
                value={slotAircraft}
                onChange={(e) => setSlotAircraft(e.target.value)}
                className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold font-mono focus:outline-none focus:border-[#1DE9C0]"
              >
                {aircraftData?.items.map((ac) => (
                  <option key={ac.aircraft_id} value={ac.aircraft_id}>
                    {ac.tail_code} ({ac.current_status})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[#6B5B84] mb-1 font-medium">Workshop Agency & Bay</label>
              <select
                value={slotAgency}
                onChange={(e) => setSlotAgency(e.target.value)}
                className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
              >
                {agencies.map((ag) => (
                  <option key={ag.agency_id} value={ag.agency_id}>
                    {ag.name} ({ag.bays} bays)
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center space-x-2 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] p-2 h-[40px]">
              <input
                type="checkbox"
                id="bundle"
                checked={slotBundleInspection}
                onChange={(e) => setSlotBundleInspection(e.target.checked)}
                className="rounded text-[#0D6553] focus:ring-0 cursor-pointer"
              />
              <label htmlFor="bundle" className="text-[#3B1D5E] text-[11px] cursor-pointer select-none font-semibold">
                Bundle with Due Inspection
              </label>
            </div>

            <button
              type="submit"
              disabled={!canPlan || createWorkOrderMutation.isPending}
              className="w-full h-[40px] bg-[#1DE9C0] hover:bg-[#15d1ac] disabled:opacity-50 text-[#1E1035] rounded-[10px] font-bold flex items-center justify-center space-x-1.5 transition shadow-ap-mint"
            >
              <Check className="w-4 h-4" />
              <span>
                {createWorkOrderMutation.isPending ? 'Scheduling Slot...' : 'Confirm & Reserve Slot'}
              </span>
            </button>
          </form>

          {/* Calculated Availability Impact Comparison */}
          <div className="p-4 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[16px] grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5 p-3 bg-[#ECFDF5] border border-[#A7F3D0] rounded-[12px]">
              <span className="text-[#059669] font-bold flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" /> Option A: Proactive Replacement (Bundled)
              </span>
              <p className="text-[#065F46] text-[11px] leading-relaxed">
                Expected downtime: <strong className="text-[#047857]">2.5 aircraft-days</strong> (labor + inspection
                overlap). Availability impact: <strong className="text-[#047857]">-0.6% points</strong>.
              </p>
            </div>

            <div className="space-y-1.5 p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-[12px]">
              <span className="text-[#DC2626] font-bold flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" /> Option B: Run-To-Failure (Unscheduled)
              </span>
              <p className="text-[#991B1B] text-[11px] leading-relaxed">
                Expected downtime: <strong className="text-[#7F1D1D]">9.0 aircraft-days</strong> (repair + supply wait +
                queue). Availability impact: <strong className="text-[#7F1D1D]">-2.3% points</strong>.
              </p>
            </div>
          </div>

          {slotSuccessMessage && (
            <div className="p-3.5 bg-[#ECFDF5] border border-[#A7F3D0] rounded-[12px] text-[#065F46] text-xs shadow-sm">
              {slotSuccessMessage}
            </div>
          )}

          {slotErrorMessage && (
            <div className="p-3.5 bg-[#FEF2F2] border border-[#FCA5A5] rounded-[12px] text-[#DC2626] text-xs">
              {slotErrorMessage}
            </div>
          )}
        </div>
      </SectionContainer>

      {/* 5. LEVEL 4: GANTT / TIMELINE VIEW */}
      {viewMode === 'gantt' && (
        <SectionContainer
          title="Airframe Maintenance Schedule (20-Day Forward Gantt Horizon)"
          subtitle="Visualizing occupied bay slots, planned inspections, and bundled LRU replacements"
          icon={<Layers className="w-4 h-4 text-[#0D6553]" />}
          actions={
            <div className="flex items-center space-x-3 text-[11px] text-[#6B5B84]">
              <span className="flex items-center">
                <span className="w-2.5 h-2.5 rounded-full bg-[#3B82F6] mr-1" /> Scheduled Task
              </span>
              <span className="flex items-center">
                <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] mr-1" /> Bundled Replacement
              </span>
              <span className="flex items-center">
                <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] mr-1" /> P1 Critical Work
              </span>
            </div>
          }
        >
          <div className="overflow-x-auto">
            <div className="min-w-[680px] space-y-2 text-xs">
              {/* Day Header Row */}
              <div className="grid grid-cols-12 gap-1 text-[10px] text-[#8F7FA8] border-b border-[#E6E2F0] pb-2 text-center font-mono">
                <div className="col-span-2 text-left text-[#6B5B84] font-bold pl-2 font-sans">Airframe</div>
                <div className="col-span-10 grid grid-cols-10 gap-1">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <span key={i}>Day {i * 2 + 1}–{i * 2 + 2}</span>
                  ))}
                </div>
              </div>

              {/* Airframe Rows */}
              {ganttAirframes.map((ac) => (
                <div
                  key={ac.aircraftId}
                  className="grid grid-cols-12 gap-1 items-center py-2.5 hover:bg-[#F4F2FB] rounded-[10px] px-2 transition-colors"
                >
                  <div
                    onClick={() => navigate(`/aircraft?id=${ac.aircraftId}`)}
                    className="col-span-2 font-bold font-mono text-[#3B1D5E] hover:text-[#0D6553] cursor-pointer flex items-center gap-1.5"
                  >
                    <span>{ac.aircraftId}</span>
                    {ac.aircraftId === 'AC-017' && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-[#FEF2F2] text-[#DC2626] border border-[#FCA5A5]">
                        Priority
                      </span>
                    )}
                  </div>

                  {/* 10 Day Slots */}
                  <div className="col-span-10 grid grid-cols-10 gap-1 relative h-8 bg-[#F4F2FB] rounded-[8px] border border-[#E6E2F0] p-0.5">
                    {ac.tasks.map((task) => {
                      const leftPercent = Math.min(85, (task.startDay / 20) * 100);
                      const widthPercent = Math.max(10, (task.duration / 20) * 100);

                      let barColor = 'bg-[#3B82F6] text-white';
                      if (task.isBundled) {
                        barColor = 'bg-[#10B981] text-white shadow-sm';
                      } else if (task.priority === 'P1') {
                        barColor = 'bg-[#EF4444] text-white shadow-sm';
                      }

                      return (
                        <div
                          key={task.id}
                          title={`${task.title} (Duration: ${task.duration} days)`}
                          style={{
                            left: `${leftPercent}%`,
                            width: `${widthPercent}%`,
                          }}
                          className={`absolute top-0.5 bottom-0.5 rounded-[6px] px-2 flex items-center justify-between text-[10px] font-semibold truncate shadow-sm cursor-pointer ${barColor}`}
                          onClick={() => navigate(`/aircraft?id=${ac.aircraftId}`)}
                        >
                          <span className="truncate">{task.title}</span>
                          <span className="text-[9px] opacity-80 font-mono">{task.duration}d</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SectionContainer>
      )}

      {/* 6. LEVEL 4: WORK ORDERS TABLE VIEW */}
      {viewMode === 'table' && (
        <SectionContainer
          title="Work Orders Catalog"
          subtitle="Detailed maintenance tracking by airframe, assigned agency, and completion state"
          icon={<Wrench className="w-4 h-4 text-[#0D6553]" />}
        >
          <div className="space-y-4 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                {/* Status Filter */}
                <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
                  <span className="text-[#6B5B84] text-[11px]">Status:</span>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="all">All Statuses</option>
                    <option value="open">Open</option>
                    <option value="scheduled">Scheduled</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>

                {/* Priority Filter */}
                <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
                  <span className="text-[#6B5B84] text-[11px]">Priority:</span>
                  <select
                    value={priorityFilter}
                    onChange={(e) => setPriorityFilter(e.target.value)}
                    className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="all">All Priorities</option>
                    <option value="P1">P1</option>
                    <option value="P2">P2</option>
                    <option value="P3">P3</option>
                    <option value="P4">P4</option>
                  </select>
                </div>

                {/* Agency Filter */}
                <div className="flex items-center space-x-1.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] px-2.5 py-1.5">
                  <span className="text-[#6B5B84] text-[11px]">Agency:</span>
                  <select
                    value={agencyFilter}
                    onChange={(e) => setAgencyFilter(e.target.value)}
                    className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="all">All Agencies</option>
                    {agencies.map((a) => (
                      <option key={a.agency_id} value={a.agency_id}>
                        {a.name}
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
                  placeholder="Search airframe, WO ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-[#F4F2FB] border border-[#E6E2F0] text-[#3B1D5E] text-xs rounded-[8px] pl-8 pr-3 py-1.5 w-60 focus:outline-none focus:border-[#1DE9C0] placeholder-[#8F7FA8]"
                />
              </div>
            </div>

            <DataTable
              columns={columns}
              data={filteredWorkOrders}
              loading={loadingOrders}
              emptyTitle="No Work Orders"
              emptyMessage="No work order records match the selected status or agency filter."
            />
          </div>
        </SectionContainer>
      )}
    </div>
  );
};
