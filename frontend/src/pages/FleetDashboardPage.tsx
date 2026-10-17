import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  Plane,
  AlertTriangle,
  Package,
  ArrowRight,
  ShieldAlert,
  Filter,
  CheckCircle2,
  TrendingUp,
  Clock,
  Sparkles,
  Layers,
  Wrench,
} from 'lucide-react';
import { KpiCard } from '../components/common/KpiCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { DataTable, type Column } from '../components/common/DataTable';
import { TimeSeriesChart } from '../components/common/TimeSeriesChart';
import { Heatgrid, type HeatgridCell } from '../components/common/Heatgrid';
import { SectionContainer } from '../components/common/SectionContainer';
import { useAuth } from '../hooks/useAuth';
import { useKpis, useFleetSummary, useAvailabilityTrend } from '../hooks/useAvailabilityQueries';
import { useFleetTwin } from '../hooks/useTwinQueries';
import { useAdvisories, useAlerts } from '../hooks/useEngineQueries';
import { useWorkOrders } from '../hooks/useMaintenanceQueries';
import { useSystems } from '../hooks/useFleetQueries';
import type { AdvisoryOut, WorkOrderOut } from '../types/api';

export const FleetDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { asOfDate } = useAuth();

  // Filters state
  const [selectedBase, setSelectedBase] = useState<string>('all');
  const [selectedSystem, setSelectedSystem] = useState<string>('all');

  // API Queries
  const { data: summary, isLoading: loadingSummary } = useFleetSummary(asOfDate);
  const { data: kpis, isLoading: loadingKpis } = useKpis(asOfDate);
  const { data: trendData, isLoading: loadingTrend } = useAvailabilityTrend(30, asOfDate);
  const { data: fleetTwin, isLoading: loadingTwin } = useFleetTwin(asOfDate);
  const { data: systemsData } = useSystems();
  const { data: topAdvisories, isLoading: loadingAdvisories } = useAdvisories({
    status: 'proposed',
    page_size: 10,
  });
  const { data: upcomingOrders, isLoading: loadingOrders } = useWorkOrders({
    page_size: 8,
  });
  const { data: alertsData } = useAlerts({ acknowledged: false, page_size: 3 });

  // 1. Prepare Availability Trend Series with Forecast Shading
  const { trendSeries, forecastStart } = useMemo(() => {
    if (!trendData || !trendData.points || trendData.points.length === 0) {
      return { trendSeries: [], forecastStart: undefined };
    }

    const actualOrP50: Array<[string, number]> = [];
    const p10Data: Array<[string, number]> = [];
    const p90Data: Array<[string, number]> = [];
    let firstForecastDate: string | undefined = undefined;

    trendData.points.forEach((pt) => {
      actualOrP50.push([pt.date, Number(pt.avail.toFixed(1))]);
      if (pt.is_forecast) {
        if (!firstForecastDate) firstForecastDate = pt.date;
        if (pt.p10 !== null) p10Data.push([pt.date, Number(pt.p10.toFixed(1))]);
        if (pt.p90 !== null) p90Data.push([pt.date, Number(pt.p90.toFixed(1))]);
      }
    });

    const series: Array<{
      name: string;
      data: Array<[string, number]>;
      color: string;
      area?: boolean;
      dashed?: boolean;
    }> = [
      {
        name: 'Availability (Median Ao)',
        data: actualOrP50,
        color: '#0D6553',
        area: true,
      },
    ];

    if (p90Data.length > 0) {
      series.push({
        name: 'P90 (Optimistic)',
        data: p90Data,
        color: '#10B981',
        area: false,
        dashed: true,
      });
    }

    if (p10Data.length > 0) {
      series.push({
        name: 'P10 (Stress Lower)',
        data: p10Data,
        color: '#EF4444',
        area: false,
        dashed: true,
      });
    }

    return { trendSeries: series, forecastStart: firstForecastDate };
  }, [trendData]);

  // 2. Prepare Heatgrid Matrix Cells
  const heatgridCells: HeatgridCell[] = useMemo(() => {
    if (!fleetTwin || !fleetTwin.aircraft) return [];

    const cells: HeatgridCell[] = [];
    const systemsList = systemsData || [
      { system_id: 'sys-1', name: 'Propulsion' },
      { system_id: 'sys-2', name: 'Hydraulics' },
      { system_id: 'sys-3', name: 'Electrical' },
      { system_id: 'sys-4', name: 'Landing gear' },
      { system_id: 'sys-5', name: 'Avionics' },
      { system_id: 'sys-6', name: 'Fuel' },
      { system_id: 'sys-7', name: 'Environmental (ECS)' },
    ];

    fleetTwin.aircraft.forEach((ac) => {
      systemsList.forEach((sys) => {
        if (selectedSystem !== 'all' && !sys.name.toLowerCase().includes(selectedSystem.toLowerCase())) {
          return;
        }

        const isDriverSystem = ac.driver_component?.system_name.toLowerCase().includes(sys.name.toLowerCase());
        const healthIndex = isDriverSystem && ac.driver_component ? ac.driver_component.health_index : ac.health_index;
        const status = isDriverSystem && ac.driver_component ? ac.driver_component.state : ac.state;

        cells.push({
          aircraftId: ac.aircraft_id,
          tailCode: ac.tail_code,
          systemId: sys.system_id,
          systemName: sys.name,
          healthIndex: Number(healthIndex.toFixed(1)),
          status,
          driverComponent: isDriverSystem ? ac.driver_component?.component_name : undefined,
        });
      });
    });

    return cells;
  }, [fleetTwin, systemsData, selectedSystem]);

  // 3. Advisory Table Columns
  const advisoryColumns: Column<AdvisoryOut>[] = [
    {
      header: 'Priority',
      align: 'center',
      render: (row) => <StatusBadge status={row.priority} size="sm" />,
    },
    {
      header: 'Airframe',
      render: (row) => (
        <span className="font-mono font-bold text-[#3B1D5E] hover:text-[#0D6553] cursor-pointer">
          {row.tail_code || row.aircraft_id}
        </span>
      ),
    },
    {
      header: 'System / Component',
      render: (row) => (
        <div>
          <div className="text-[#3B1D5E] font-semibold">{row.component_name || row.component_id}</div>
          <div className="text-[11px] text-[#8F7FA8]">{row.system_name || 'System'}</div>
        </div>
      ),
    },
    {
      header: 'Recommended Action',
      render: (row) => (
        <span className="text-[#3B1D5E] font-medium flex items-center gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 text-[#D97706]" />
          {row.action}
        </span>
      ),
    },
    {
      header: 'Spares',
      align: 'center',
      render: (row) => <StatusBadge status={row.spare_status || 'in_stock'} size="sm" />,
    },
    {
      header: 'Loss (Days)',
      align: 'right',
      render: (row) => (
        <span className="text-[#6B5B84] font-mono font-bold">
          {row.expected_downtime_days ? `${row.expected_downtime_days}d` : '—'}
        </span>
      ),
    },
    {
      header: 'Inspect',
      align: 'center',
      render: (row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/components/${row.component_id}`);
          }}
          className="p-1 px-2.5 text-[11px] bg-[#E0F8FA] hover:bg-[#1DE9C0] text-[#0D6553] hover:text-[#1E1035] font-semibold rounded-[8px] border border-[#1DE9C0]/40 transition shadow-sm"
        >
          View Evidence
        </button>
      ),
    },
  ];

  // 4. Upcoming Work Orders Table Columns
  const workOrderColumns: Column<WorkOrderOut>[] = [
    {
      header: 'WO ID',
      render: (row) => <span className="text-[#6B5B84] font-mono">{row.wo_id}</span>,
    },
    {
      header: 'Airframe',
      render: (row) => <span className="text-[#3B1D5E] font-mono font-bold">{row.aircraft_id}</span>,
    },
    {
      header: 'Agency / Bay',
      render: (row) => <span className="text-[#6B5B84]">{row.agency_id}</span>,
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
      header: 'Delay Reason',
      render: (row) => (
        <span className="text-[#DC2626] text-[11px] truncate max-w-[140px] block">
          {row.delay_reason || 'Nominal execution'}
        </span>
      ),
    },
  ];

  const downtime = kpis?.downtime_by_cause;
  const stateBreakdown = summary?.by_state || {};

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Alerts Banner Strip */}
      {alertsData && alertsData.items.length > 0 && (
        <div className="bg-[#FEF2F2] border border-[#FCA5A5] rounded-[16px] p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-[#991B1B] shadow-sm">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-[#DC2626] animate-pulse flex-shrink-0" />
            <span className="font-bold uppercase text-[#B91C1C]">Operational Alert:</span>
            <span className="truncate max-w-2xl text-[#7F1D1D] font-medium">{alertsData.items[0].message}</span>
          </div>
          <button
            onClick={() => navigate('/advisories')}
            className="text-[11px] text-[#B91C1C] hover:text-[#7F1D1D] underline flex items-center gap-1 font-bold flex-shrink-0"
          >
            Review Queue ({alertsData.total}) <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* 2. Top Header & Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E6E2F0] pb-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-[#3B1D5E] tracking-tight flex items-center gap-2">
            <Activity className="w-6 h-6 text-[#0D6553]" />
            Fleet Operational Cockpit
          </h1>
          <p className="text-xs text-[#6B5B84] mt-0.5">
            Integrated fleet availability, degradation signals, and turnaround bottlenecks
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <div className="flex items-center space-x-1.5 bg-white border border-[#E6E2F0] rounded-[10px] px-3 py-1.5 shadow-sm">
            <Filter className="w-3.5 h-3.5 text-[#0D6553]" />
            <span className="text-[#6B5B84]">System:</span>
            <select
              value={selectedSystem}
              onChange={(e) => setSelectedSystem(e.target.value)}
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

          <div className="flex items-center space-x-1.5 bg-white border border-[#E6E2F0] rounded-[10px] px-3 py-1.5 shadow-sm">
            <Plane className="w-3.5 h-3.5 text-[#0D6553]" />
            <span className="text-[#6B5B84]">Base:</span>
            <select
              value={selectedBase}
              onChange={(e) => setSelectedBase(e.target.value)}
              className="bg-transparent text-[#3B1D5E] font-semibold focus:outline-none cursor-pointer"
            >
              <option value="all">All Squadrons</option>
              <option value="Base-North">Base-North (Forward)</option>
              <option value="Base-South">Base-South (Main)</option>
            </select>
          </div>
        </div>
      </div>

      {/* 3. LEVEL 1: Primary KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Fleet Availability (Ao)"
          value={`${(summary?.availability_pct ?? kpis?.fleet_availability_pct ?? 0).toFixed(1)}%`}
          subtitle="Target: ≥75% Serviceable Fleet"
          change={{
            value: '74.2% in 30d',
            isPositive: false,
            label: 'Forecast Trend',
          }}
          icon={<Activity className="w-5 h-5" />}
          accent="honey"
          loading={loadingSummary && loadingKpis}
          onClick={() => navigate('/scenarios')}
        />

        <KpiCard
          title="Airframes by Status"
          value={`${summary?.serviceable_count ?? '—'}/${summary?.total_aircraft ?? '40'}`}
          subtitle={`${stateBreakdown['Unscheduled Repair'] || 0} unscheduled • ${stateBreakdown['Awaiting Spares'] || 0} supply hold`}
          change={{
            value: `${Math.round(((summary?.serviceable_count ?? 32) / (summary?.total_aircraft ?? 40)) * 100)}%`,
            isPositive: true,
            label: 'Ready rate',
          }}
          icon={<Plane className="w-5 h-5" />}
          accent="emerald"
          loading={loadingSummary}
          onClick={() => navigate('/aircraft')}
        />

        <KpiCard
          title="P1/P2 Active Advisories"
          value={`${(summary?.open_p1 || 0) + (summary?.open_p2 || 0)}`}
          subtitle={`${summary?.open_p1 || 0} Critical P1 • ${summary?.open_p2 || 0} High P2`}
          change={{
            value: 'Action Required',
            isPositive: false,
          }}
          icon={<AlertTriangle className="w-5 h-5" />}
          accent="rose"
          loading={loadingSummary}
          onClick={() => navigate('/advisories')}
        />

        <KpiCard
          title="Spares at Risk & Backlog"
          value={`${summary?.parts_at_risk || 0} Parts`}
          subtitle={`${kpis?.backlog.open_orders || summary?.backlog.open_orders || 0} Work Orders (${Math.round(kpis?.backlog.outstanding_man_hours || 0)} hrs)`}
          change={{
            value: `${kpis?.spare_fill_rate_pct ? kpis.spare_fill_rate_pct.toFixed(0) : 94}%`,
            isPositive: true,
            label: 'Fill Rate',
          }}
          icon={<Package className="w-5 h-5" />}
          accent="amber"
          loading={loadingSummary && loadingKpis}
          onClick={() => navigate('/spares')}
        />
      </div>

      {/* 4. LEVEL 2: Charts Row: Availability Trend + Downtime by Cause */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Availability Trend Line Chart (2 Cols) */}
        <div className="lg:col-span-2 bg-white border border-[#E6E2F0] rounded-[20px] p-5 sm:p-6 shadow-ap-card flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-3 border-b border-[#E6E2F0]">
            <div>
              <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#3B1D5E] flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#0D6553]" />
                Fleet Availability Timeline & 30-Day Forward Projection
              </h3>
              <p className="text-xs text-[#6B5B84] mt-0.5">
                Historical observed availability with P10/P50/P90 forward projection band
              </p>
            </div>
            {forecastStart && (
              <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#E0F8FA] border border-[#1DE9C0]/50 text-[#0D6553] font-semibold">
                Forecast from: {forecastStart}
              </span>
            )}
          </div>

          <TimeSeriesChart
            height={260}
            series={trendSeries}
            forecastStartDate={forecastStart}
            yAxisLabel="Availability %"
            yAxisMin={50}
            yAxisMax={100}
            loading={loadingTrend}
          />
        </div>

        {/* Downtime by Cause Stacked / Breakdown (1 Col) */}
        <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-5 sm:p-6 shadow-ap-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-3 border-b border-[#E6E2F0]">
              <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#3B1D5E] flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-[#0D6553]" />
                Downtime Loss Breakdown
              </h3>
            </div>
            <p className="text-xs text-[#6B5B84] mb-4">
              Cumulative aircraft-days lost by operational root cause
            </p>

            <div className="space-y-3.5 text-xs">
              <div>
                <div className="flex justify-between text-[#6B5B84] mb-1">
                  <span>Scheduled Inspections</span>
                  <span className="font-mono font-bold text-[#3B1D5E]">
                    {downtime ? `${downtime.scheduled_days}d (${downtime.scheduled_pct.toFixed(0)}%)` : '—'}
                  </span>
                </div>
                <div className="w-full bg-[#F4F2FB] h-2 rounded-full overflow-hidden border border-[#E6E2F0]">
                  <div
                    className="bg-[#1DE9C0] h-full rounded-full"
                    style={{ width: `${downtime?.scheduled_pct || 40}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[#6B5B84] mb-1">
                  <span>Unscheduled Repairs</span>
                  <span className="font-mono font-bold text-[#D97706]">
                    {downtime ? `${downtime.unscheduled_days}d (${downtime.unscheduled_pct.toFixed(0)}%)` : '—'}
                  </span>
                </div>
                <div className="w-full bg-[#F4F2FB] h-2 rounded-full overflow-hidden border border-[#E6E2F0]">
                  <div
                    className="bg-[#F59E0B] h-full rounded-full"
                    style={{ width: `${downtime?.unscheduled_pct || 25}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[#6B5B84] mb-1">
                  <span>Supply Wait (Stockout)</span>
                  <span className="font-mono font-bold text-[#DC2626]">
                    {downtime ? `${downtime.supply_wait_days}d (${downtime.supply_wait_pct.toFixed(0)}%)` : '—'}
                  </span>
                </div>
                <div className="w-full bg-[#F4F2FB] h-2 rounded-full overflow-hidden border border-[#E6E2F0]">
                  <div
                    className="bg-[#EF4444] h-full rounded-full"
                    style={{ width: `${downtime?.supply_wait_pct || 20}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[#6B5B84] mb-1">
                  <span>Workshop / Bay Queue</span>
                  <span className="font-mono font-bold text-[#2563EB]">
                    {downtime ? `${downtime.agency_wait_days}d (${downtime.agency_wait_pct.toFixed(0)}%)` : '—'}
                  </span>
                </div>
                <div className="w-full bg-[#F4F2FB] h-2 rounded-full overflow-hidden border border-[#E6E2F0]">
                  <div
                    className="bg-[#3B82F6] h-full rounded-full"
                    style={{ width: `${downtime?.agency_wait_pct || 15}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#E6E2F0] flex items-center justify-between text-xs text-[#6B5B84]">
            <span>Total Lost Days:</span>
            <span className="font-mono font-bold text-[#3B1D5E] text-sm">
              {downtime ? `${downtime.total_downtime_days} Days` : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* 5. LEVEL 3: Aircraft × System Health Heat-Grid */}
      <Heatgrid
        cells={heatgridCells}
        loading={loadingTwin}
        onCellClick={(aircraftId) => {
          navigate(`/aircraft?id=${aircraftId}`);
        }}
      />

      {/* 6. LEVEL 4: Before / After Impact Summary Card */}
      <SectionContainer
        title="Integrated Maintenance & Availability Outcomes"
        subtitle="Demonstrating quantified outcomes: availability uplift, downtime reduction, and zero AOG spares"
        icon={<Sparkles className="w-5 h-5 text-[#0D6553]" />}
        badge={
          <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#E0F8FA] text-[#0369A1] border border-[#BAE6FD] uppercase font-bold">
            Fleet Benchmark
          </span>
        }
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div className="bg-[#F4F2FB] border border-[#E6E2F0] rounded-[16px] p-4 space-y-1.5 shadow-sm">
            <div className="text-[#6B5B84] text-[11px] flex items-center gap-1.5 font-medium">
              <TrendingUp className="w-4 h-4 text-[#059669]" />
              <span>Availability Uplift</span>
            </div>
            <div className="text-xl font-bold font-mono text-[#059669]">+7.8% Uplift</div>
            <p className="text-[11px] text-[#6B5B84] leading-relaxed">
              Fleet readiness elevated from ~74.2% (reactive baseline) to ~82.0% continuous availability.
            </p>
          </div>

          <div className="bg-[#F4F2FB] border border-[#E6E2F0] rounded-[16px] p-4 space-y-1.5 shadow-sm">
            <div className="text-[#6B5B84] text-[11px] flex items-center gap-1.5 font-medium">
              <Clock className="w-4 h-4 text-[#D97706]" />
              <span>Downtime Reduction</span>
            </div>
            <div className="text-xl font-bold font-mono text-[#D97706]">-6.5 Days / Defect</div>
            <p className="text-[11px] text-[#6B5B84] leading-relaxed">
              Proactive bundled bay slot requires 2.5d vs 9.0d run-to-failure unscheduled grounding.
            </p>
          </div>

          <div className="bg-[#F4F2FB] border border-[#E6E2F0] rounded-[16px] p-4 space-y-1.5 shadow-sm">
            <div className="text-[#6B5B84] text-[11px] flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-4 h-4 text-[#2563EB]" />
              <span>Advance Early Warning</span>
            </div>
            <div className="text-xl font-bold font-mono text-[#2563EB]">19 Days Lead-Time</div>
            <p className="text-[11px] text-[#6B5B84] leading-relaxed">
              Sustained telemetry anomaly flags deteriorating pump ~19 days prior to functional failure.
            </p>
          </div>

          <div className="bg-[#F4F2FB] border border-[#E6E2F0] rounded-[16px] p-4 space-y-1.5 shadow-sm">
            <div className="text-[#6B5B84] text-[11px] flex items-center gap-1.5 font-medium">
              <Package className="w-4 h-4 text-[#0D6553]" />
              <span>Supply Risk Avoidance</span>
            </div>
            <div className="text-xl font-bold font-mono text-[#0D6553]">Zero Spares AOG</div>
            <p className="text-[11px] text-[#6B5B84] leading-relaxed">
              Integrated logistics triggers 45-day lead-time procurement before depot stockout.
            </p>
          </div>
        </div>
      </SectionContainer>

      {/* 7. LEVEL 5: Lower Tables Row: Top Risk Advisories + Upcoming Work Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Advisories Table */}
        <SectionContainer
          title="Top Priority Maintenance Advisories"
          subtitle="Proposed predictive alerts awaiting engineering disposition"
          icon={<ShieldAlert className="w-4 h-4 text-[#0D6553]" />}
          actions={
            <button
              onClick={() => navigate('/advisories')}
              className="text-xs text-[#0D6553] hover:underline font-bold flex items-center gap-1"
            >
              <span>Full Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          }
        >
          <DataTable
            columns={advisoryColumns}
            data={topAdvisories?.items || []}
            loading={loadingAdvisories}
            emptyTitle="No Active Advisories"
            emptyMessage="All airframe subsystems are operating within nominal thresholds."
            onRowClick={(row) => navigate(`/components/${row.component_id}`)}
          />
        </SectionContainer>

        {/* Upcoming Work Orders */}
        <SectionContainer
          title="Active & Upcoming Work Orders"
          subtitle="Scheduled bay operations and workshop maintenance backlog"
          icon={<Wrench className="w-4 h-4 text-[#0D6553]" />}
          actions={
            <button
              onClick={() => navigate('/planning')}
              className="text-xs text-[#0D6553] hover:underline font-bold flex items-center gap-1"
            >
              <span>Planning Board</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          }
        >
          <DataTable
            columns={workOrderColumns}
            data={upcomingOrders?.items || []}
            loading={loadingOrders}
            emptyTitle="No Active Work Orders"
            emptyMessage="No open work orders currently scheduled in maintenance bays."
            onRowClick={() => navigate('/planning')}
          />
        </SectionContainer>
      </div>
    </div>
  );
};
