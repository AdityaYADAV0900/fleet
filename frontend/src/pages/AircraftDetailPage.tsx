import React, { useMemo, useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Plane,
  Activity,
  Clock,
  Wrench,
  Sliders,
  ArrowRight,
  ShieldAlert,
  Layers,
  TrendingDown,
  History,
} from 'lucide-react';
import { KpiCard } from '../components/common/KpiCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { DataTable, type Column } from '../components/common/DataTable';
import { TimeSeriesChart } from '../components/common/TimeSeriesChart';
import { SvgSchematic, type SystemStatusInfo } from '../components/common/SvgSchematic';
import { SectionContainer } from '../components/common/SectionContainer';
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton';
import { useAuth } from '../hooks/useAuth';
import { useAircraftList, useAircraftDetail } from '../hooks/useFleetQueries';
import { useAircraftTwin } from '../hooks/useTwinQueries';
import { useWorkOrders } from '../hooks/useMaintenanceQueries';
import { useAdvisories } from '../hooks/useEngineQueries';
import type {
  TwinComponentNodeOut,
  TwinMaintenanceEvent,
  WorkOrderOut,
} from '../types/api';

export const AircraftDetailPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { asOfDate } = useAuth();

  // Active airframe ID from URL param or default
  const requestedId = searchParams.get('id') || '';

  // Tabs: 'schematic' | 'twin' | 'orders'
  const [activeTab, setActiveTab] = useState<'schematic' | 'twin' | 'orders'>('schematic');
  const [selectedSystemName, setSelectedSystemName] = useState<string | null>(null);

  // Queries
  const { data: aircraftListData, isLoading: loadingList } = useAircraftList({ page_size: 100 });
  const allAircraft = aircraftListData?.items || [];

  // Default to requested ID or hero aircraft AC-017 or first aircraft
  const activeAircraftId = useMemo(() => {
    if (requestedId && allAircraft.some((a) => a.aircraft_id === requestedId)) {
      return requestedId;
    }
    const hero = allAircraft.find((a) => a.tail_code === 'AC-017' || a.aircraft_id === 'AC-017');
    if (hero) return hero.aircraft_id;
    return allAircraft[0]?.aircraft_id || '';
  }, [requestedId, allAircraft]);

  useEffect(() => {
    if (activeAircraftId && requestedId !== activeAircraftId) {
      setSearchParams({ id: activeAircraftId }, { replace: true });
    }
  }, [activeAircraftId, requestedId, setSearchParams]);

  const { data: aircraftDetail, isLoading: loadingDetail } = useAircraftDetail(activeAircraftId);
  const { data: twinData, isLoading: loadingTwin } = useAircraftTwin(activeAircraftId, asOfDate);
  const { data: workOrdersData, isLoading: loadingOrders } = useWorkOrders({
    aircraft: activeAircraftId,
    page_size: 20,
  });
  const { data: advisoriesData } = useAdvisories({
    aircraft_id: activeAircraftId,
    as_of_date: asOfDate || undefined,
    page_size: 10,
  });

  // Switch aircraft handler
  const handleSelectAircraft = (id: string) => {
    setSearchParams({ id });
    setSelectedSystemName(null);
  };

  // Prepare systems for SVG Schematic
  const schematicSystems: SystemStatusInfo[] = useMemo(() => {
    if (!twinData || !twinData.systems) return [];
    return twinData.systems.map((s) => ({
      name: s.system_name,
      healthIndex: Number(s.health_index.toFixed(1)),
      status: s.state,
      driverComponent: s.driver_component?.component_name,
    }));
  }, [twinData]);

  // Flatten or filter components
  const displayedComponents: TwinComponentNodeOut[] = useMemo(() => {
    if (!twinData || !twinData.systems) return [];
    let list: TwinComponentNodeOut[] = [];
    twinData.systems.forEach((sys) => {
      if (
        !selectedSystemName ||
        sys.system_name.toLowerCase().includes(selectedSystemName.toLowerCase()) ||
        selectedSystemName.toLowerCase().includes(sys.system_name.toLowerCase())
      ) {
        list = list.concat(sys.components);
      }
    });
    // Sort components: lowest health index first (worst performing on top)
    return list.sort((a, b) => a.health_index - b.health_index);
  }, [twinData, selectedSystemName]);

  // Prepare Digital Twin Trajectory Series
  const { trajectorySeries, forecastStart } = useMemo(() => {
    if (!twinData || !twinData.predicted_trajectory || twinData.predicted_trajectory.length === 0) {
      return { trajectorySeries: [], forecastStart: undefined };
    }

    const hiData: Array<[string, number]> = [];
    const riskData: Array<[string, number]> = [];
    let firstForecast: string | undefined = undefined;

    twinData.predicted_trajectory.forEach((pt) => {
      hiData.push([pt.date, Number(pt.health_index.toFixed(1))]);
      if (pt.risk !== null && pt.risk !== undefined) {
        riskData.push([pt.date, Number((pt.risk * 100).toFixed(1))]);
      }
      if (pt.is_forecast && !firstForecast) {
        firstForecast = pt.date;
      }
    });

    const series = [
      {
        name: 'Airframe Health Index',
        data: hiData,
        color: '#0D6553',
        area: true,
      },
      {
        name: 'Failure Risk (%)',
        data: riskData,
        color: '#EF4444',
        area: false,
        dashed: true,
      },
    ];

    return { trajectorySeries: series, forecastStart: firstForecast };
  }, [twinData]);

  // Component Table Columns
  const componentColumns: Column<TwinComponentNodeOut>[] = [
    {
      header: 'Component',
      render: (row) => (
        <div>
          <span className="font-semibold text-[#3B1D5E]">{row.component_name}</span>
          <div className="text-[10px] text-[#8F7FA8] font-mono">
            PN: {row.part_number} • SN: {row.serial_number}
          </div>
        </div>
      ),
    },
    {
      header: 'System',
      accessorKey: 'system_name',
    },
    {
      header: 'Criticality',
      align: 'center',
      render: (row) => (
        <span
          className={`font-mono font-bold text-xs ${
            row.criticality >= 4 ? 'text-[#DC2626]' : row.criticality === 3 ? 'text-[#D97706]' : 'text-[#6B5B84]'
          }`}
        >
          Level {row.criticality}
        </span>
      ),
    },
    {
      header: 'Health Index',
      align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center space-x-1.5">
          <span
            className={`font-mono font-bold text-xs ${
              row.health_index >= 75
                ? 'text-[#059669]'
                : row.health_index >= 50
                ? 'text-[#D97706]'
                : 'text-[#DC2626]'
            }`}
          >
            {row.health_index.toFixed(1)}
          </span>
          <StatusBadge status={row.state} size="sm" />
        </div>
      ),
    },
    {
      header: '14d Risk',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono font-bold ${
            (row.risk ?? 0) >= 0.5 ? 'text-[#DC2626]' : (row.risk ?? 0) >= 0.2 ? 'text-[#D97706]' : 'text-[#6B5B84]'
          }`}
        >
          {row.risk !== null && row.risk !== undefined ? `${(row.risk * 100).toFixed(0)}%` : '—'}
        </span>
      ),
    },
    {
      header: 'RUL (P50)',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono font-bold ${
            (row.rul_p50 ?? 99) <= 14 ? 'text-[#DC2626]' : (row.rul_p50 ?? 99) <= 30 ? 'text-[#D97706]' : 'text-[#3B1D5E]'
          }`}
        >
          {row.rul_p50 !== null && row.rul_p50 !== undefined ? `${Math.round(row.rul_p50)} days` : '—'}
        </span>
      ),
    },
    {
      header: 'Evidence',
      align: 'center',
      render: (row) => (
        <button
          onClick={() => navigate(`/components/${row.component_id}`)}
          className="py-1 px-2.5 bg-[#E0F8FA] hover:bg-[#1DE9C0] text-[#0D6553] hover:text-[#1E1035] rounded-[8px] text-[11px] font-semibold border border-[#1DE9C0]/40 transition flex items-center gap-1 shadow-sm"
        >
          <span>Telemetry</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      ),
    },
  ];

  // Work Order Columns
  const workOrderColumns: Column<WorkOrderOut>[] = [
    {
      header: 'WO ID',
      render: (row) => <span className="font-mono text-[#6B5B84]">{row.wo_id}</span>,
    },
    {
      header: 'Agency / Bay',
      render: (row) => <span className="text-[#3B1D5E] font-semibold">{row.agency_id}</span>,
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
      header: 'Opened',
      render: (row) => <span className="text-[#6B5B84] font-mono">{new Date(row.opened).toLocaleDateString()}</span>,
    },
    {
      header: 'Promised vs Actual',
      render: (row) => (
        <span className="text-[#3B1D5E] font-mono text-[11px]">
          {row.promised_done ? new Date(row.promised_done).toLocaleDateString() : '—'} /{' '}
          {row.actual_done ? new Date(row.actual_done).toLocaleDateString() : 'Pending'}
        </span>
      ),
    },
    {
      header: 'Delay Reason',
      render: (row) => (
        <span className={`text-[11px] ${row.delay_reason ? 'text-[#DC2626] font-semibold' : 'text-[#8F7FA8]'}`}>
          {row.delay_reason || 'On Schedule'}
        </span>
      ),
    },
  ];

  // Maintenance History Columns
  const historyColumns: Column<TwinMaintenanceEvent>[] = [
    {
      header: 'Date',
      render: (row) => <span className="font-mono text-[#6B5B84]">{row.date}</span>,
    },
    {
      header: 'Event Type',
      align: 'center',
      render: (row) => <StatusBadge status={row.event_type} size="sm" />,
    },
    {
      header: 'Action / Description',
      render: (row) => <span className="text-[#3B1D5E]">{row.description}</span>,
    },
    {
      header: 'Status',
      align: 'center',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
  ];

  if (loadingList && !activeAircraftId) {
    return <LoadingSkeleton rows={6} />;
  }

  const driver = twinData?.driver_component;
  const openAdvisoriesCount = advisoriesData?.total || 0;
  const openOrdersCount = workOrdersData?.items.filter((w) => w.status !== 'completed').length || 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Airframe Selector & What-If Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E6E2F0] pb-4">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 bg-[#E0F8FA] border border-[#BAE6FD] rounded-[12px] text-[#0D6553] shadow-sm">
            <Plane className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl md:text-2xl font-bold font-mono text-[#3B1D5E] tracking-tight">
                {twinData?.tail_code || activeAircraftId}
              </h1>
              <span className="text-xs text-[#6B5B84]">
                ({twinData?.type_code || aircraftDetail?.type_code || 'Fleet Airframe'})
              </span>
              {activeAircraftId === 'AC-017' && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#FEF2F2] text-[#DC2626] border border-[#FCA5A5] font-bold">
                  Inspection Priority
                </span>
              )}
            </div>
            <p className="text-xs text-[#6B5B84] mt-0.5">
              Commissioned: {aircraftDetail?.commissioned_date || '2023-01-15'} • Base:{' '}
              {aircraftDetail?.base_id || 'Base-North'}
            </p>
          </div>
        </div>

        {/* Airframe Switcher & What-If Simulation Button */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Airframe Dropdown */}
          <div className="flex items-center space-x-2 bg-white border border-[#E6E2F0] rounded-[10px] px-3 py-1.5 text-xs shadow-sm">
            <span className="text-[#6B5B84]">Switch Airframe:</span>
            <select
              value={activeAircraftId}
              onChange={(e) => handleSelectAircraft(e.target.value)}
              className="bg-transparent text-[#3B1D5E] font-bold font-mono focus:outline-none cursor-pointer"
            >
              {allAircraft.map((ac) => (
                <option key={ac.aircraft_id} value={ac.aircraft_id}>
                  {ac.tail_code} ({ac.current_status})
                </option>
              ))}
            </select>
          </div>

          {/* Launch What-If Simulator Button */}
          <button
            onClick={() => navigate(`/scenarios?aircraft=${activeAircraftId}`)}
            className="py-2 px-4 bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] rounded-[10px] text-xs font-bold flex items-center space-x-1.5 transition shadow-ap-mint"
          >
            <Sliders className="w-4 h-4" />
            <span>Launch What-If Simulator</span>
          </button>
        </div>
      </div>

      {/* 2. LEVEL 1: KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Airframe Health Index"
          value={twinData ? twinData.health_index.toFixed(1) : '—'}
          subtitle={
            twinData?.health_index !== undefined
              ? twinData.health_index >= 75
                ? 'Nominal Serviceability'
                : twinData.health_index >= 50
                ? 'Degraded Subsystem Detected'
                : 'Critical Failure Risk'
              : 'Evaluating...'
          }
          change={{
            value: twinData?.risk ? `${(twinData.risk * 100).toFixed(0)}% Risk` : 'Nominal',
            isPositive: (twinData?.risk ?? 0) < 0.3,
            label: '14d Window',
          }}
          icon={<Activity className="w-5 h-5" />}
          accent={
            (twinData?.health_index ?? 100) >= 75
              ? 'emerald'
              : (twinData?.health_index ?? 100) >= 50
              ? 'amber'
              : 'rose'
          }
          loading={loadingTwin}
        />

        <KpiCard
          title="Operational State"
          value={twinData?.state || aircraftDetail?.current_status || 'Available'}
          subtitle="Decision-Support Availability"
          icon={<Plane className="w-5 h-5" />}
          accent={
            (twinData?.state || '').toLowerCase().includes('available')
              ? 'emerald'
              : (twinData?.state || '').toLowerCase().includes('scheduled')
              ? 'blue'
              : 'rose'
          }
          loading={loadingTwin && loadingDetail}
        />

        <KpiCard
          title="Flight Hours & Cycles"
          value={`${aircraftDetail ? Math.round(aircraftDetail.total_flight_hours) : '—'}h`}
          subtitle={`${aircraftDetail?.total_cycles || 0} Sortie Cycles Complied`}
          change={{
            value: 'Inspection Compliant',
            isPositive: true,
          }}
          icon={<Clock className="w-5 h-5" />}
          accent="blue"
          loading={loadingDetail}
        />

        <KpiCard
          title="Maintenance Backlog"
          value={`${openOrdersCount} Orders`}
          subtitle={`${openAdvisoriesCount} Predictive Advisories Raised`}
          change={{
            value: openAdvisoriesCount > 0 ? `${openAdvisoriesCount} Alerts` : 'Zero Alerts',
            isPositive: openAdvisoriesCount === 0,
          }}
          icon={<Wrench className="w-5 h-5" />}
          accent={openOrdersCount > 0 || openAdvisoriesCount > 0 ? 'amber' : 'slate'}
          loading={loadingOrders}
          onClick={() => setActiveTab('orders')}
        />
      </div>

      {/* 3. Driver Component Alert Banner */}
      {driver && driver.health_index < 75 && (
        <div className="bg-[#FFFBEB] border border-[#FDE68A] rounded-[16px] p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-start space-x-3.5">
            <ShieldAlert className="w-5 h-5 text-[#D97706] animate-pulse mt-0.5 shrink-0" />
            <div>
              <div className="text-xs font-bold uppercase text-[#92400E] tracking-wider">
                Primary Degradation Driver Component Flagged
              </div>
              <p className="text-xs text-[#78350F] mt-0.5 leading-relaxed">
                The airframe&apos;s health index is governed by{' '}
                <strong className="text-[#92400E]">{driver.component_name}</strong> in the{' '}
                <strong className="text-[#92400E]">{driver.system_name}</strong> system (Health Index:{' '}
                <span className="text-[#D97706] font-bold font-mono">{driver.health_index.toFixed(1)}</span>, State:{' '}
                <span className="uppercase text-[#92400E] font-semibold">{driver.state}</span>
                {driver.rul_p50 ? `, RUL: ${Math.round(driver.rul_p50)} days` : ''}).
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate(`/components/${driver.component_id}`)}
            className="py-2 px-4 bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] rounded-[10px] text-xs font-bold flex items-center justify-center space-x-1.5 transition shrink-0 shadow-ap-mint"
          >
            <span>Inspect Evidence</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 4. Tab Navigation Strip */}
      <div className="flex border-b border-[#E6E2F0] text-xs space-x-2">
        <button
          onClick={() => setActiveTab('schematic')}
          className={`py-2.5 px-4 rounded-t-[10px] font-semibold flex items-center space-x-2 transition ${
            activeTab === 'schematic'
              ? 'bg-white text-[#0D6553] border-t-2 border-[#1DE9C0] border-x border-[#E6E2F0]'
              : 'text-[#6B5B84] hover:text-[#3B1D5E] hover:bg-[#F4F2FB]'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Subsystems & Schematic</span>
        </button>

        <button
          onClick={() => setActiveTab('twin')}
          className={`py-2.5 px-4 rounded-t-[10px] font-semibold flex items-center space-x-2 transition ${
            activeTab === 'twin'
              ? 'bg-white text-[#0D6553] border-t-2 border-[#1DE9C0] border-x border-[#E6E2F0]'
              : 'text-[#6B5B84] hover:text-[#3B1D5E] hover:bg-[#F4F2FB]'
          }`}
        >
          <TrendingDown className="w-4 h-4" />
          <span>Digital Twin & Trajectory</span>
        </button>

        <button
          onClick={() => setActiveTab('orders')}
          className={`py-2.5 px-4 rounded-t-[10px] font-semibold flex items-center space-x-2 transition ${
            activeTab === 'orders'
              ? 'bg-white text-[#0D6553] border-t-2 border-[#1DE9C0] border-x border-[#E6E2F0]'
              : 'text-[#6B5B84] hover:text-[#3B1D5E] hover:bg-[#F4F2FB]'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Work Orders ({workOrdersData?.total || 0})</span>
        </button>
      </div>

      {/* 5. Tab Content */}

      {/* TAB 1: Schematic & Functional Systems */}
      {activeTab === 'schematic' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Vector Schematic (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <SvgSchematic
              systems={schematicSystems}
              selectedSystem={selectedSystemName}
              onSelectSystem={(name) => setSelectedSystemName(name === selectedSystemName ? null : name)}
            />

            {/* System Filter Clear Helper */}
            {selectedSystemName && (
              <div className="flex items-center justify-between p-3 bg-[#E0F8FA] border border-[#BAE6FD] rounded-[12px] text-xs text-[#0369A1]">
                <span>
                  Filtering components for: <strong>{selectedSystemName}</strong>
                </span>
                <button
                  onClick={() => setSelectedSystemName(null)}
                  className="text-xs text-[#0D6553] hover:underline font-bold"
                >
                  Show All Systems
                </button>
              </div>
            )}
          </div>

          {/* Right: Functional Component Hierarchy Table (7 cols) */}
          <div className="lg:col-span-7">
            <SectionContainer
              title="Tracked Line Replaceable Units (LRUs)"
              subtitle={`${displayedComponents.length} components installed • Sorted by degradation severity`}
              icon={<Layers className="w-4 h-4 text-[#0D6553]" />}
            >
              <DataTable
                columns={componentColumns}
                data={displayedComponents}
                loading={loadingTwin}
                emptyTitle="No Components"
                emptyMessage="No component instances found matching the selected subsystem filter."
                onRowClick={(row) => navigate(`/components/${row.component_id}`)}
              />
            </SectionContainer>
          </div>
        </div>
      )}

      {/* TAB 2: Digital Twin & Trajectory */}
      {activeTab === 'twin' && (
        <div className="space-y-6">
          {/* Trajectory TimeSeries Chart */}
          <SectionContainer
            title="Degradation Trajectory & Forward Projection"
            subtitle="Health Index decay curve and 14-day failure risk trajectory"
            icon={<TrendingDown className="w-4 h-4 text-[#0D6553]" />}
            badge={
              forecastStart ? (
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#E0F8FA] border border-[#BAE6FD] text-[#0369A1] font-bold">
                  Projection starts: {forecastStart}
                </span>
              ) : undefined
            }
          >
            <TimeSeriesChart
              height={280}
              series={trajectorySeries}
              forecastStartDate={forecastStart}
              yAxisLabel="Metric Score"
              yAxisMin={0}
              yAxisMax={100}
              loading={loadingTwin}
            />
          </SectionContainer>

          {/* Maintenance & Compliance History */}
          <SectionContainer
            title="Digital Twin Maintenance & Inspection Compliance Events"
            subtitle="Historical timeline of physical maintenance, scheduled inspections, and sensor recalibrations"
            icon={<History className="w-4 h-4 text-[#0D6553]" />}
          >
            <DataTable
              columns={historyColumns}
              data={twinData?.maintenance_history || []}
              loading={loadingTwin}
              emptyTitle="No Historical Events Recorded"
              emptyMessage="No inspection or maintenance events recorded in this airframe's digital twin state."
            />
          </SectionContainer>
        </div>
      )}

      {/* TAB 3: Work Orders */}
      {activeTab === 'orders' && (
        <SectionContainer
          title="Work Orders & Turnaround Logistics"
          subtitle="Workshop agency routing, queue wait times, and parts availability constraints"
          icon={<Wrench className="w-4 h-4 text-[#0D6553]" />}
          actions={
            <button
              onClick={() => navigate('/planning')}
              className="text-xs text-[#0D6553] hover:underline font-bold flex items-center gap-1"
            >
              <span>Open Planning Board</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          }
        >
          <DataTable
            columns={workOrderColumns}
            data={workOrdersData?.items || []}
            loading={loadingOrders}
            emptyTitle="No Work Orders"
            emptyMessage="No active or past work orders found for this airframe."
            onRowClick={() => navigate('/planning')}
          />
        </SectionContainer>
      )}
    </div>
  );
};
