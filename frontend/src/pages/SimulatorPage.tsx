import React, { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import * as echarts from 'echarts';
import {
  Sliders,
  Play,
  RotateCcw,
  AlertTriangle,
  BookmarkPlus,
  Trash2,
  Layers,
  Wrench,
  Package,
  TrendingUp,
  TrendingDown,
  Clock,
  History,
} from 'lucide-react';
import { KpiCard } from '../components/common/KpiCard';
import { SectionContainer } from '../components/common/SectionContainer';
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton';
import { EmptyState } from '../components/feedback/EmptyState';
import { useAuth } from '../hooks/useAuth';
import {
  useRunScenario,
  useScenarioHistory,
} from '../hooks/useAvailabilityQueries';
import { useAircraftList } from '../hooks/useFleetQueries';
import { useSpareParts } from '../hooks/useSparesQueries';
import type { ScenarioRunOut } from '../types/api';

type ScenarioType =
  | 'schedule_maintenance'
  | 'spare_unavailable'
  | 'early_vs_run_to_failure'
  | 'extra_capacity';

interface ScenarioComparisonItem {
  id: string;
  name: string;
  type: ScenarioType;
  params: Record<string, unknown>;
  horizon_days: number;
  runs: number;
  seed: number;
  baseline_p50: number;
  scenario_p50: number;
  avail_delta_pct: number;
  days_lost_delta: number;
  stockout_prob: number;
  by_cause_delta: Record<string, number>;
}

const formatScenarioType = (type: string) => {
  switch (type) {
    case 'early_vs_run_to_failure':
      return 'Proactive Replacement vs RTF';
    case 'spare_unavailable':
      return 'Supply Shortfall & Stockout Stress';
    case 'schedule_maintenance':
      return 'Scheduled Bay Maintenance';
    case 'extra_capacity':
      return 'Bay Capacity Expansion';
    default:
      return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
};

export const SimulatorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { role } = useAuth();
  const canSimulate = role === 'commander' || role === 'planner';

  // Read URL query params for what-if pre-fills
  const prefillAircraft = searchParams.get('aircraft') || '';
  const prefillPart = searchParams.get('part') || '';
  const prefillTypeParam = searchParams.get('type') as ScenarioType | null;

  // Form State
  const initialType: ScenarioType =
    prefillTypeParam || (prefillPart ? 'spare_unavailable' : 'early_vs_run_to_failure');
  const [scenarioType, setScenarioType] = useState<ScenarioType>(initialType);
  const [horizonDays, setHorizonDays] = useState<number>(30);
  const [simulationRuns, setSimulationRuns] = useState<number>(100);
  const [randomSeed, setRandomSeed] = useState<number>(42);

  // Type-specific parameters
  // 1. schedule_maintenance
  const [schedAircraft, setSchedAircraft] = useState<string>(prefillAircraft || 'AC-017');
  const [schedStartDay, setSchedStartDay] = useState<number>(5);
  const [schedDurationDays, setSchedDurationDays] = useState<number>(3);

  // 2. spare_unavailable
  const [sparePartNumber, setSparePartNumber] = useState<string>(prefillPart || 'HYD-114');
  const [spareStockOverride, setSpareStockOverride] = useState<number>(0);
  const [spareLeadTimeDays, setSpareLeadTimeDays] = useState<number>(45);

  // 3. early_vs_run_to_failure
  const [earlyAircraft, setEarlyAircraft] = useState<string>(prefillAircraft || 'AC-017');
  const [earlyReplaceDay, setEarlyReplaceDay] = useState<number>(3);
  const [earlyDurationDays, setEarlyDurationDays] = useState<number>(1);

  // 4. extra_capacity
  const [bayIncrease, setBayIncrease] = useState<number>(2);

  // Active Simulation Result & Error
  const [activeResult, setActiveResult] = useState<ScenarioRunOut | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Saved / Pinned Scenarios for Side-by-Side Comparison (Max 3)
  const [pinnedScenarios, setPinnedScenarios] = useState<ScenarioComparisonItem[]>([]);
  const [activeTab, setActiveTab] = useState<'simulator' | 'compare' | 'history'>('simulator');

  // Queries
  const { data: aircraftData } = useAircraftList({ page_size: 100 });
  const { data: partsData } = useSpareParts();
  const { data: scenarioHistory, isLoading: loadingHistory } = useScenarioHistory();
  const runScenarioMutation = useRunScenario();

  const aircraftList = aircraftData?.items || [];
  const partsList = partsData || [];

  // Build params payload based on type
  const buildParams = useMemo(() => {
    switch (scenarioType) {
      case 'schedule_maintenance':
        return {
          aircraft_id: schedAircraft,
          start_day: Number(schedStartDay),
          duration_days: Number(schedDurationDays),
        };
      case 'spare_unavailable':
        return {
          part_number: sparePartNumber,
          stock_override: Number(spareStockOverride),
          lead_time_days: Number(spareLeadTimeDays),
        };
      case 'early_vs_run_to_failure':
        return {
          aircraft_id: earlyAircraft,
          early_replace_day: Number(earlyReplaceDay),
          planned_duration_days: Number(earlyDurationDays),
        };
      case 'extra_capacity':
        return {
          bay_increase: Number(bayIncrease),
        };
      default:
        return {};
    }
  }, [
    scenarioType,
    schedAircraft,
    schedStartDay,
    schedDurationDays,
    sparePartNumber,
    spareStockOverride,
    spareLeadTimeDays,
    earlyAircraft,
    earlyReplaceDay,
    earlyDurationDays,
    bayIncrease,
  ]);

  // Execute Simulation
  const handleExecuteSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (horizonDays < 7 || horizonDays > 90) {
      setValidationError('Horizon must be configured between 7 and 90 days.');
      return;
    }
    if (simulationRuns < 50 || simulationRuns > 500) {
      setValidationError('Simulation iterations must be between 50 and 500 runs.');
      return;
    }

    try {
      const res = await runScenarioMutation.mutateAsync({
        type: scenarioType,
        params: buildParams,
        horizon_days: horizonDays,
        runs: simulationRuns,
        seed: randomSeed,
      });
      setActiveResult(res);
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error ? err.message : 'Simulation failed. Check parameters and try again.';
      setValidationError(errorMsg);
    }
  };

  // Pin Current Run for Comparison
  const handlePinScenario = () => {
    if (!activeResult) return;
    if (pinnedScenarios.length >= 3) {
      setValidationError('Maximum 3 scenarios can be compared side-by-side. Remove one to add this run.');
      return;
    }
    if (pinnedScenarios.some((s) => s.id === activeResult.id)) {
      return;
    }

    const typeLabels: Record<ScenarioType, string> = {
      schedule_maintenance: `Schedule Maint (${activeResult.params.aircraft_id || 'Airframe'})`,
      spare_unavailable: `Spare Outage (${activeResult.params.part_number || 'Part'})`,
      early_vs_run_to_failure: `Proactive vs RTF (${activeResult.params.aircraft_id || 'AC-017'})`,
      extra_capacity: `Capacity (+${activeResult.params.bay_increase || 2} Bays)`,
    };

    const newItem: ScenarioComparisonItem = {
      id: activeResult.id,
      name: typeLabels[activeResult.type as ScenarioType] || activeResult.type,
      type: activeResult.type as ScenarioType,
      params: activeResult.params,
      horizon_days: activeResult.horizon_days,
      runs: activeResult.runs,
      seed: activeResult.seed,
      baseline_p50: activeResult.baseline.availability_p50,
      scenario_p50: activeResult.scenario.availability_p50,
      avail_delta_pct: activeResult.delta.availability_pct_points,
      days_lost_delta: activeResult.delta.aircraft_days_lost,
      stockout_prob: activeResult.scenario.stockout_probability,
      by_cause_delta: activeResult.by_cause || {},
    };

    setPinnedScenarios([...pinnedScenarios, newItem]);
  };

  const handleUnpinScenario = (id: string) => {
    setPinnedScenarios(pinnedScenarios.filter((s) => s.id !== id));
  };

  const [runningTriad, setRunningTriad] = useState<boolean>(false);

  const handleRunDemoTriad = async () => {
    setRunningTriad(true);
    setValidationError(null);
    try {
      const [resBaseline, resProactive, resOutage] = await Promise.all([
        runScenarioMutation.mutateAsync({
          type: 'schedule_maintenance',
          params: { aircraft_id: 'AC-017', start_day: 15, duration_days: 2 },
          horizon_days: 30,
          runs: 100,
          seed: 42,
        }),
        runScenarioMutation.mutateAsync({
          type: 'early_vs_run_to_failure',
          params: { aircraft_id: 'AC-017', replace_day: 3, proactive_duration_days: 1 },
          horizon_days: 30,
          runs: 100,
          seed: 42,
        }),
        runScenarioMutation.mutateAsync({
          type: 'spare_unavailable',
          params: { part_number: 'HYD-114', stock_override: 0, lead_time_days: 60 },
          horizon_days: 30,
          runs: 100,
          seed: 42,
        }),
      ]);

      const toItem = (r: ScenarioRunOut, name: string): ScenarioComparisonItem => ({
        id: r.id,
        name,
        type: r.type as ScenarioType,
        params: r.params,
        horizon_days: r.horizon_days,
        runs: r.runs,
        seed: r.seed,
        baseline_p50: r.baseline.availability_p50,
        scenario_p50: r.scenario.availability_p50,
        avail_delta_pct: r.delta.availability_pct_points,
        days_lost_delta: r.delta.aircraft_days_lost,
        stockout_prob: r.scenario.stockout_probability,
        by_cause_delta: r.by_cause || {},
      });

      setPinnedScenarios([
        toItem(resBaseline, '1. Baseline Schedule'),
        toItem(resProactive, '2. Proactive Replacement'),
        toItem(resOutage, '3. Spare Outage (HYD-114)'),
      ]);
      setActiveResult(resProactive);
      setActiveTab('compare');
    } catch (err: unknown) {
      setValidationError(err instanceof Error ? err.message : 'Failed to run policy benchmark');
    } finally {
      setRunningTriad(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header & Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E6E2F0] pb-4">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 bg-[#E0F8FA] border border-[#BAE6FD] rounded-[12px] text-[#0D6553] shadow-sm">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-[#3B1D5E] tracking-tight">
              Scenario Simulator (What-If Engine)
            </h1>
            <p className="text-xs text-[#6B5B84] mt-0.5">
              Comparative fleet availability & readiness policy simulation
            </p>
          </div>
        </div>

        {/* Action Controls & Tab Toggle */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleRunDemoTriad}
            disabled={!canSimulate || runningTriad || runScenarioMutation.isPending}
            className="px-3.5 py-1.5 bg-[#1DE9C0] hover:bg-[#15d1ac] disabled:opacity-50 text-[#1E1035] rounded-[10px] text-xs font-bold flex items-center space-x-1.5 shadow-ap-mint transition"
            title="Run 3-way policy comparison: Nominal Baseline vs Proactive Replacement vs Supply Shortfall"
          >
            <Layers className="w-3.5 h-3.5 text-[#1E1035]" />
            <span>
              {runningTriad ? 'Simulating Policy Benchmark...' : 'Run Benchmark Policy Comparison'}
            </span>
          </button>

          {/* Tab Controls */}
          <div className="flex items-center space-x-1 bg-white border border-[#E6E2F0] rounded-[10px] p-1 text-xs shadow-sm">
            <button
              onClick={() => setActiveTab('simulator')}
              className={`px-3 py-1.5 rounded-[8px] font-bold transition ${
                activeTab === 'simulator'
                  ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                  : 'text-[#6B5B84] hover:text-[#3B1D5E]'
              }`}
            >
              Run Simulator
            </button>
            <button
              onClick={() => setActiveTab('compare')}
              className={`px-3 py-1.5 rounded-[8px] font-bold transition flex items-center space-x-1.5 ${
                activeTab === 'compare'
                  ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                  : 'text-[#6B5B84] hover:text-[#3B1D5E]'
              }`}
            >
              <span>Compare ({pinnedScenarios.length}/3)</span>
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 py-1.5 rounded-[8px] font-bold transition flex items-center space-x-1.5 ${
                activeTab === 'history'
                  ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                  : 'text-[#6B5B84] hover:text-[#3B1D5E]'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Audit History</span>
            </button>
          </div>
        </div>
      </div>

      {/* Validation or Error Message */}
      {validationError && (
        <div className="p-3.5 bg-[#FEF2F2] border border-[#FCA5A5] rounded-[12px] text-[#DC2626] text-xs flex items-center space-x-2 shadow-sm">
          <AlertTriangle className="w-4 h-4 shrink-0 text-[#DC2626]" />
          <span>{validationError}</span>
        </div>
      )}

      {/* 2. TAB: SIMULATOR */}
      {activeTab === 'simulator' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Configuration Form (5 cols) */}
          <div className="lg:col-span-5">
            <SectionContainer
              title="Scenario Policy Configuration"
              subtitle="Select what-if maintenance, supply, or capacity policy"
              icon={<Wrench className="w-4 h-4 text-[#0D6553]" />}
            >
              <form onSubmit={handleExecuteSimulation} className="space-y-4 text-xs">
                {/* Scenario Type Selection */}
                <div>
                  <label className="block text-[#6B5B84] mb-1.5 font-bold uppercase text-[10px]">
                    Select Policy Type
                  </label>
                  <div className="grid grid-cols-1 gap-2">
                    {[
                      {
                        id: 'early_vs_run_to_failure',
                        label: 'Proactive Early vs Run-to-Failure',
                        desc: 'Compare replacement before wear failure vs unscheduled repair',
                      },
                      {
                        id: 'schedule_maintenance',
                        label: 'Schedule Planned Maintenance',
                        desc: 'Reserve a specific airframe servicing window',
                      },
                      {
                        id: 'spare_unavailable',
                        label: 'Spare Stockout / Supply Delays',
                        desc: 'Simulate critical part stockout and supplier delivery lag',
                      },
                      {
                        id: 'extra_capacity',
                        label: 'Workshop Bay Capacity Expansion',
                        desc: 'Evaluate adding repair bays / extra maintenance shifts',
                      },
                    ].map((item) => (
                      <label
                        key={item.id}
                        className={`flex items-start space-x-2.5 p-3 rounded-[12px] border cursor-pointer transition ${
                          scenarioType === item.id
                            ? 'bg-[#E6FCF7] border-[#1DE9C0] text-[#3B1D5E] shadow-sm'
                            : 'bg-[#F4F2FB] border-[#E6E2F0] text-[#6B5B84] hover:bg-white hover:border-[#1DE9C0]'
                        }`}
                      >
                        <input
                          type="radio"
                          name="scenarioType"
                          value={item.id}
                          checked={scenarioType === item.id}
                          onChange={() => setScenarioType(item.id as ScenarioType)}
                          className="mt-0.5 text-[#0D6553] focus:ring-0"
                        />
                        <div>
                          <div className="font-bold text-[#3B1D5E] text-xs">{item.label}</div>
                          <div className="text-[11px] text-[#6B5B84] leading-tight mt-0.5">
                            {item.desc}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Dynamic Parameter Fields */}
                <div className="p-3.5 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[14px] space-y-3">
                  {scenarioType === 'early_vs_run_to_failure' && (
                    <>
                      <div>
                        <label className="block text-[#6B5B84] mb-1 font-semibold">Target Airframe</label>
                        <select
                          value={earlyAircraft}
                          onChange={(e) => setEarlyAircraft(e.target.value)}
                          className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold font-mono focus:outline-none focus:border-[#1DE9C0]"
                        >
                          {aircraftList.map((ac) => (
                            <option key={ac.aircraft_id} value={ac.aircraft_id}>
                              {ac.tail_code} ({ac.current_status})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[#6B5B84] mb-1 font-semibold">Proactive Day</label>
                          <input
                            type="number"
                            min={1}
                            max={30}
                            value={earlyReplaceDay}
                            onChange={(e) => setEarlyReplaceDay(Number(e.target.value))}
                            className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                          />
                        </div>
                        <div>
                          <label className="block text-[#6B5B84] mb-1 font-semibold">Duration (Days)</label>
                          <input
                            type="number"
                            min={1}
                            max={10}
                            value={earlyDurationDays}
                            onChange={(e) => setEarlyDurationDays(Number(e.target.value))}
                            className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                          />
                        </div>
                      </div>
                    </>
                  )}

                  {scenarioType === 'schedule_maintenance' && (
                    <>
                      <div>
                        <label className="block text-[#6B5B84] mb-1 font-semibold">Target Airframe</label>
                        <select
                          value={schedAircraft}
                          onChange={(e) => setSchedAircraft(e.target.value)}
                          className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold font-mono focus:outline-none focus:border-[#1DE9C0]"
                        >
                          {aircraftList.map((ac) => (
                            <option key={ac.aircraft_id} value={ac.aircraft_id}>
                              {ac.tail_code} ({ac.current_status})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[#6B5B84] mb-1 font-semibold">Planned Start (Day)</label>
                          <input
                            type="number"
                            min={1}
                            max={60}
                            value={schedStartDay}
                            onChange={(e) => setSchedStartDay(Number(e.target.value))}
                            className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                          />
                        </div>
                        <div>
                          <label className="block text-[#6B5B84] mb-1 font-semibold">Service Duration (Days)</label>
                          <input
                            type="number"
                            min={1}
                            max={14}
                            value={schedDurationDays}
                            onChange={(e) => setSchedDurationDays(Number(e.target.value))}
                            className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                          />
                        </div>
                      </div>
                    </>
                  )}

                  {scenarioType === 'spare_unavailable' && (
                    <>
                      <div>
                        <label className="block text-[#6B5B84] mb-1 font-semibold">Critical Part Number</label>
                        <select
                          value={sparePartNumber}
                          onChange={(e) => setSparePartNumber(e.target.value)}
                          className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold font-mono focus:outline-none focus:border-[#1DE9C0]"
                        >
                          {partsList.map((p) => (
                            <option key={p.part_number} value={p.part_number}>
                              {p.part_number} — {p.description.slice(0, 30)}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[#6B5B84] mb-1 font-semibold">Simulated Stock</label>
                          <input
                            type="number"
                            min={0}
                            max={20}
                            value={spareStockOverride}
                            onChange={(e) => setSpareStockOverride(Number(e.target.value))}
                            className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                          />
                        </div>
                        <div>
                          <label className="block text-[#6B5B84] mb-1 font-semibold">Lead Time Delay (Days)</label>
                          <input
                            type="number"
                            min={5}
                            max={90}
                            value={spareLeadTimeDays}
                            onChange={(e) => setSpareLeadTimeDays(Number(e.target.value))}
                            className="w-full bg-white border border-[#E6E2F0] rounded-[10px] p-2 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                          />
                        </div>
                      </div>
                    </>
                  )}

                  {scenarioType === 'extra_capacity' && (
                    <div>
                      <label className="block text-[#6B5B84] mb-1 font-semibold">Additional Workshop Bays</label>
                      <div className="flex items-center space-x-3">
                        <input
                          type="range"
                          min={1}
                          max={6}
                          value={bayIncrease}
                          onChange={(e) => setBayIncrease(Number(e.target.value))}
                          className="w-full accent-[#0D6553] cursor-pointer"
                        />
                        <span className="font-bold text-[#3B1D5E] text-sm w-16 text-right font-mono">
                          +{bayIncrease} Bays
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Simulation Global Engine Parameters */}
                <div className="grid grid-cols-3 gap-2.5 pt-1">
                  <div>
                    <label className="block text-[#6B5B84] text-[10px] mb-1 uppercase font-bold">
                      Horizon (7–90d)
                    </label>
                    <input
                      type="number"
                      min={7}
                      max={90}
                      value={horizonDays}
                      onChange={(e) => setHorizonDays(Number(e.target.value))}
                      className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] p-1.5 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                    />
                  </div>

                  <div>
                    <label className="block text-[#6B5B84] text-[10px] mb-1 uppercase font-bold">
                      Runs (50–500)
                    </label>
                    <input
                      type="number"
                      min={50}
                      max={500}
                      step={25}
                      value={simulationRuns}
                      onChange={(e) => setSimulationRuns(Number(e.target.value))}
                      className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] p-1.5 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                    />
                  </div>

                  <div>
                    <label className="block text-[#6B5B84] text-[10px] mb-1 uppercase font-bold">
                      Seed Key
                    </label>
                    <input
                      type="number"
                      value={randomSeed}
                      onChange={(e) => setRandomSeed(Number(e.target.value))}
                      className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[8px] p-1.5 text-[#3B1D5E] font-bold focus:outline-none focus:border-[#1DE9C0]"
                    />
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={!canSimulate || runScenarioMutation.isPending}
                  className="w-full py-3 bg-[#1DE9C0] hover:bg-[#15d1ac] disabled:opacity-50 text-[#1E1035] rounded-[10px] font-bold flex items-center justify-center space-x-2 transition shadow-ap-mint text-xs"
                >
                  {runScenarioMutation.isPending ? (
                    <>
                      <RotateCcw className="w-4 h-4 animate-spin text-[#1E1035]" />
                      <span>Executing {simulationRuns} Trajectories...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-current" />
                      <span>Run What-If Simulation</span>
                    </>
                  )}
                </button>
              </form>
            </SectionContainer>
          </div>

          {/* Right Column: Simulation Output Dashboard (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            {runScenarioMutation.isPending ? (
              <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-8 text-center space-y-4 shadow-ap-card">
                <RotateCcw className="w-8 h-8 animate-spin text-[#0D6553] mx-auto" />
                <div>
                  <h3 className="text-[#3B1D5E] font-bold text-sm">
                    Simulating {simulationRuns} Parallel Trajectories
                  </h3>
                  <p className="text-[#6B5B84] text-xs mt-1">
                    Evaluating policy counterfactuals over a {horizonDays}-day operational horizon...
                  </p>
                </div>
                <div className="max-w-xs mx-auto bg-[#F4F2FB] h-2 rounded-full overflow-hidden border border-[#E6E2F0]">
                  <div className="bg-[#1DE9C0] h-full w-2/3 animate-pulse" />
                </div>
              </div>
            ) : !activeResult ? (
              <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-12 text-center space-y-3 shadow-ap-card">
                <Sliders className="w-10 h-10 text-[#8F7FA8] mx-auto" />
                <h3 className="text-[#3B1D5E] font-bold text-sm">Ready for Simulation</h3>
                <p className="text-[#6B5B84] text-xs max-w-md mx-auto leading-relaxed">
                  Configure the scenario policy on the left and click &quot;Run What-If Simulation&quot; to compute
                  availability trajectory curves, confidence bands, and aircraft-days delta.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* 1. Delta Metrics Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <KpiCard
                    title="Availability Delta"
                    value={`${activeResult.delta.availability_pct_points >= 0 ? '+' : ''}${
                      activeResult.delta.availability_pct_points
                    }%`}
                    subtitle={`Scenario ${(activeResult.scenario.availability_p50 * 100).toFixed(
                      1
                    )}% vs Base ${(activeResult.baseline.availability_p50 * 100).toFixed(1)}%`}
                    change={{
                      value: `${activeResult.delta.availability_pct_points}% pts`,
                      isPositive: activeResult.delta.availability_pct_points >= 0,
                      label: 'Net Delta',
                    }}
                    icon={
                      activeResult.delta.availability_pct_points >= 0 ? (
                        <TrendingUp className="w-5 h-5" />
                      ) : (
                        <TrendingDown className="w-5 h-5" />
                      )
                    }
                    accent={activeResult.delta.availability_pct_points >= 0 ? 'emerald' : 'rose'}
                  />

                  <KpiCard
                    title="Days Lost Delta"
                    value={`${activeResult.delta.aircraft_days_lost >= 0 ? '+' : ''}${
                      activeResult.delta.aircraft_days_lost
                    }d`}
                    subtitle={`Total: ${activeResult.scenario.aircraft_days_lost.toFixed(1)}d lost`}
                    change={{
                      value:
                        activeResult.delta.aircraft_days_lost <= 0
                          ? 'Capacity Saved'
                          : 'Added Downtime',
                      isPositive: activeResult.delta.aircraft_days_lost <= 0,
                    }}
                    icon={<Clock className="w-5 h-5" />}
                    accent={activeResult.delta.aircraft_days_lost <= 0 ? 'emerald' : 'amber'}
                  />

                  <KpiCard
                    title="Stockout Risk"
                    value={`${(activeResult.scenario.stockout_probability * 100).toFixed(1)}%`}
                    subtitle={`Baseline: ${(activeResult.baseline.stockout_probability * 100).toFixed(
                      1
                    )}%`}
                    change={{
                      value:
                        activeResult.scenario.stockout_probability <= 0.05
                          ? 'Safe Buffer'
                          : 'Supply Constrained',
                      isPositive: activeResult.scenario.stockout_probability <= 0.05,
                    }}
                    icon={<Package className="w-5 h-5" />}
                    accent={activeResult.scenario.stockout_probability <= 0.05 ? 'cyan' : 'rose'}
                  />
                </div>

                {/* 2. Interactive Availability Trajectory Chart */}
                <SectionContainer
                  title="Fleet Availability Projection (Baseline vs. Scenario)"
                  subtitle="P50 trajectory lines with P10–P90 confidence envelope bands"
                  icon={<TrendingUp className="w-4 h-4 text-[#0D6553]" />}
                  actions={
                    <button
                      onClick={handlePinScenario}
                      className="px-3 py-1.5 rounded-[8px] bg-[#E0F8FA] hover:bg-[#1DE9C0] text-[#0D6553] hover:text-[#1E1035] text-xs font-bold flex items-center space-x-1.5 transition shadow-sm border border-[#1DE9C0]/40"
                    >
                      <BookmarkPlus className="w-3.5 h-3.5" />
                      <span>Pin for Comparison</span>
                    </button>
                  }
                >
                  <ScenarioTrendChart result={activeResult} />
                </SectionContainer>

                {/* 3. Downtime Cause Delta Breakdown */}
                <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-4 sm:p-5 shadow-ap-card space-y-3 text-xs">
                  <div className="flex items-center justify-between text-[#6B5B84] border-b border-[#E6E2F0] pb-2.5">
                    <span className="font-bold uppercase tracking-wider text-[11px] flex items-center gap-1.5 text-[#3B1D5E]">
                      <Layers className="w-4 h-4 text-[#0D6553]" />
                      Downtime Impact Breakdown by Cause (Days Delta)
                    </span>
                    <span className="text-[#8F7FA8] text-[10px]">Net Fleet Days</span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-center">
                    <div className="p-3 bg-[#F4F2FB] rounded-[12px] border border-[#E6E2F0]">
                      <div className="text-[10px] text-[#6B5B84] font-semibold">Scheduled Servicing</div>
                      <div
                        className={`text-base font-bold font-mono mt-1 ${
                          (activeResult.by_cause.scheduled || 0) > 0
                            ? 'text-[#D97706]'
                            : 'text-[#059669]'
                        }`}
                      >
                        {(activeResult.by_cause.scheduled || 0) >= 0 ? '+' : ''}
                        {activeResult.by_cause.scheduled || 0}d
                      </div>
                    </div>

                    <div className="p-3 bg-[#F4F2FB] rounded-[12px] border border-[#E6E2F0]">
                      <div className="text-[10px] text-[#6B5B84] font-semibold">Unscheduled Repairs</div>
                      <div
                        className={`text-base font-bold font-mono mt-1 ${
                          (activeResult.by_cause.unscheduled || 0) > 0
                            ? 'text-[#DC2626]'
                            : 'text-[#059669]'
                        }`}
                      >
                        {(activeResult.by_cause.unscheduled || 0) >= 0 ? '+' : ''}
                        {activeResult.by_cause.unscheduled || 0}d
                      </div>
                    </div>

                    <div className="p-3 bg-[#F4F2FB] rounded-[12px] border border-[#E6E2F0]">
                      <div className="text-[10px] text-[#6B5B84] font-semibold">Supply Wait Grounding</div>
                      <div
                        className={`text-base font-bold font-mono mt-1 ${
                          (activeResult.by_cause.supply_wait || 0) > 0
                            ? 'text-[#DC2626]'
                            : 'text-[#059669]'
                        }`}
                      >
                        {(activeResult.by_cause.supply_wait || 0) >= 0 ? '+' : ''}
                        {activeResult.by_cause.supply_wait || 0}d
                      </div>
                    </div>

                    <div className="p-3 bg-[#F4F2FB] rounded-[12px] border border-[#E6E2F0]">
                      <div className="text-[10px] text-[#6B5B84] font-semibold">Agency Queue Wait</div>
                      <div
                        className={`text-base font-bold font-mono mt-1 ${
                          (activeResult.by_cause.agency_wait || 0) > 0
                            ? 'text-[#DC2626]'
                            : 'text-[#059669]'
                        }`}
                      >
                        {(activeResult.by_cause.agency_wait || 0) >= 0 ? '+' : ''}
                        {activeResult.by_cause.agency_wait || 0}d
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. TAB: COMPARE (SIDE-BY-SIDE MATRIX) */}
      {activeTab === 'compare' && (
        <SectionContainer
          title="Multi-Scenario Comparative Decision Matrix"
          subtitle="Side-by-side evaluation of up to 3 simulation runs against baseline readiness"
          icon={<Layers className="w-4 h-4 text-[#0D6553]" />}
          actions={
            pinnedScenarios.length > 0 ? (
              <button
                onClick={() => setPinnedScenarios([])}
                className="px-2.5 py-1 rounded-[8px] bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] border border-[#FCA5A5] text-xs font-bold flex items-center space-x-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear All</span>
              </button>
            ) : undefined
          }
        >
          {pinnedScenarios.length === 0 ? (
            <EmptyState
              title="No Scenarios Pinned for Comparison"
              message="Run a scenario in the Simulator tab and click 'Pin for Comparison' or click 'Run Benchmark Policy Comparison' above to view side-by-side policy trade-offs."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#E6E2F0] bg-[#F4F2FB] text-[#6B5B84] uppercase text-[11px] font-semibold">
                    <th className="py-3 px-4 w-48">Scenario Run</th>
                    <th className="py-3 px-3 text-center">Horizon / Runs</th>
                    <th className="py-3 px-3 text-right">Baseline (Ao)</th>
                    <th className="py-3 px-3 text-right">Scenario (Ao)</th>
                    <th className="py-3 px-3 text-right">Net Delta</th>
                    <th className="py-3 px-3 text-right">Days Lost Delta</th>
                    <th className="py-3 px-3 text-right">Stockout Risk</th>
                    <th className="py-3 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6E2F0] text-[#3B1D5E]">
                  {pinnedScenarios.map((item) => (
                    <tr key={item.id} className="hover:bg-[#FBF9FE] transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#3B1D5E]">
                        <div>{item.name}</div>
                        <div className="text-[10px] text-[#8F7FA8] font-normal">{formatScenarioType(item.type)}</div>
                      </td>
                      <td className="py-3.5 px-3 text-center text-[#6B5B84] font-mono">
                        {item.horizon_days}d / {item.runs} runs
                      </td>
                      <td className="py-3.5 px-3 text-right font-bold text-[#6B5B84] font-mono">
                        {(item.baseline_p50 * 100).toFixed(1)}%
                      </td>
                      <td className="py-3.5 px-3 text-right font-bold text-[#3B1D5E] font-mono">
                        {(item.scenario_p50 * 100).toFixed(1)}%
                      </td>
                      <td
                        className={`py-3.5 px-3 text-right font-bold font-mono ${
                          item.avail_delta_pct >= 0 ? 'text-[#059669]' : 'text-[#DC2626]'
                        }`}
                      >
                        {item.avail_delta_pct >= 0 ? '+' : ''}
                        {item.avail_delta_pct}%
                      </td>
                      <td
                        className={`py-3.5 px-3 text-right font-bold font-mono ${
                          item.days_lost_delta <= 0 ? 'text-[#059669]' : 'text-[#DC2626]'
                        }`}
                      >
                        {item.days_lost_delta >= 0 ? '+' : ''}
                        {item.days_lost_delta}d
                      </td>
                      <td className="py-3.5 px-3 text-right text-[#0D6553] font-bold font-mono">
                        {(item.stockout_prob * 100).toFixed(1)}%
                      </td>
                      <td className="py-3.5 px-3 text-center">
                        <button
                          onClick={() => handleUnpinScenario(item.id)}
                          className="p-1 rounded-[6px] text-[#8F7FA8] hover:text-[#DC2626] transition"
                          title="Remove from comparison"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionContainer>
      )}

      {/* 4. TAB: AUDIT HISTORY */}
      {activeTab === 'history' && (
        <SectionContainer
          title="Historical Simulation Audit Trail"
          subtitle="Persistent audit log of all executed stochastic what-if simulation runs"
          icon={<History className="w-4 h-4 text-[#0D6553]" />}
        >
          {loadingHistory ? (
            <LoadingSkeleton rows={5} />
          ) : !scenarioHistory || scenarioHistory.length === 0 ? (
            <EmptyState
              title="No Simulation History"
              message="No previous scenario simulation runs recorded in the database audit log."
            />
          ) : (
            <div className="overflow-x-auto text-xs">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E6E2F0] bg-[#F4F2FB] text-[#6B5B84] uppercase text-[11px] font-semibold">
                    <th className="py-3 px-4">Run ID</th>
                    <th className="py-3 px-4">Policy Type</th>
                    <th className="py-3 px-3 text-center">Horizon / Runs</th>
                    <th className="py-3 px-3 text-right">Baseline Ao</th>
                    <th className="py-3 px-3 text-right">Scenario Ao</th>
                    <th className="py-3 px-3 text-right">Net Delta</th>
                    <th className="py-3 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6E2F0] text-[#3B1D5E]">
                  {((scenarioHistory || []) as Array<Record<string, unknown>>).map((item) => {
                    const run: ScenarioRunOut = (item.results as ScenarioRunOut) || (item as unknown as ScenarioRunOut);
                    const horizon = run.horizon_days ?? 30;
                    const runsCount = run.runs ?? 100;
                    const baselineAo = run.baseline?.availability_p50 !== undefined ? (run.baseline.availability_p50 * 100).toFixed(1) : '—';
                    const scenarioAo = run.scenario?.availability_p50 !== undefined ? (run.scenario.availability_p50 * 100).toFixed(1) : '—';
                    const deltaPct = run.delta?.availability_pct_points ?? 0;

                    return (
                      <tr key={String(item.id ?? Math.random())} className="hover:bg-[#FBF9FE] transition-colors">
                        <td className="py-3 px-4 text-[#6B5B84] font-mono">{String(item.id ?? '').slice(0, 16)}...</td>
                        <td className="py-3 px-4 font-bold text-[#3B1D5E]">{formatScenarioType(String(item.type ?? ''))}</td>
                        <td className="py-3 px-3 text-center text-[#6B5B84] font-mono">
                          {horizon}d / {runsCount}r
                        </td>
                        <td className="py-3 px-3 text-right font-bold text-[#6B5B84] font-mono">
                          {baselineAo}%
                        </td>
                        <td className="py-3 px-3 text-right font-bold text-[#3B1D5E] font-mono">
                          {scenarioAo}%
                        </td>
                        <td
                          className={`py-3 px-3 text-right font-bold font-mono ${
                            deltaPct >= 0 ? 'text-[#059669]' : 'text-[#DC2626]'
                          }`}
                        >
                          {deltaPct >= 0 ? '+' : ''}
                          {deltaPct}%
                        </td>
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => {
                              if (run.baseline && run.scenario) {
                                setActiveResult(run);
                                setActiveTab('simulator');
                              }
                            }}
                            className="px-2.5 py-1 bg-[#E0F8FA] hover:bg-[#1DE9C0] text-[#0D6553] hover:text-[#1E1035] font-bold rounded-[8px] border border-[#1DE9C0]/40 text-[11px] transition shadow-sm"
                          >
                            View Output
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionContainer>
      )}
    </div>
  );
};

// ----------------------------------------------------
// Subcomponent: Scenario Availability Trend Chart
// ----------------------------------------------------
interface ScenarioTrendChartProps {
  result: ScenarioRunOut;
}

const ScenarioTrendChart: React.FC<ScenarioTrendChartProps> = ({ result }) => {
  const chartRef = React.useRef<HTMLDivElement | null>(null);
  const chartInstance = React.useRef<echarts.EChartsType | null>(null);

  React.useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' });
    }
    const chart = chartInstance.current;

    const daily = result.daily_trend || {};
    const basePts = daily.baseline || [];
    const scnPts = daily.scenario || [];

    const dates = daily.days
      ? daily.days.map((d) => `Day ${d}`)
      : basePts.length > 0
      ? basePts.map((p) => `Day ${p.day}`)
      : Array.from({ length: result.horizon_days || 30 }).map((_, i) => `Day ${i + 1}`);

    const baseP50: number[] = daily.baseline_p50
      ? daily.baseline_p50
      : basePts.length > 0
      ? basePts.map((p) => Number(((p.p50 ?? 0.8) * 100).toFixed(1)))
      : Array.from({ length: dates.length }).map(() => Number((result.baseline.availability_p50 * 100).toFixed(1)));

    const scnP50: number[] = daily.scenario_p50
      ? daily.scenario_p50
      : scnPts.length > 0
      ? scnPts.map((p) => Number(((p.p50 ?? 0.8) * 100).toFixed(1)))
      : Array.from({ length: dates.length }).map(() => Number((result.scenario.availability_p50 * 100).toFixed(1)));

    const scnP10 = daily.scenario_p10
      ? daily.scenario_p10
      : scnPts.length > 0
      ? scnPts.map((p) => (p.p10 !== null && p.p10 !== undefined ? Number((p.p10 * 100).toFixed(1)) : null))
      : Array.from({ length: dates.length }).map(() => Number((result.scenario.availability_p10 * 100).toFixed(1)));

    const scnP90 = daily.scenario_p90
      ? daily.scenario_p90
      : scnPts.length > 0
      ? scnPts.map((p) => (p.p90 !== null && p.p90 !== undefined ? Number((p.p90 * 100).toFixed(1)) : null))
      : Array.from({ length: dates.length }).map(() => Number((result.scenario.availability_p90 * 100).toFixed(1)));

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#FFFFFF',
        borderColor: '#E6E2F0',
        textStyle: { color: '#3B1D5E', fontSize: 11 },
      },
      legend: {
        data: ['Baseline (P50)', 'Scenario (P50)', 'Scenario P90 (Optimistic)', 'Scenario P10 (Stress)'],
        textStyle: { color: '#6B5B84', fontSize: 10 },
        top: 0,
        right: 10,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '18%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#E6E2F0' } },
        axisLabel: { color: '#8F7FA8', fontSize: 10, fontFamily: 'monospace' },
      },
      yAxis: {
        type: 'value',
        name: 'Availability %',
        nameTextStyle: { color: '#8F7FA8', fontSize: 10 },
        min: 40,
        max: 100,
        splitLine: { lineStyle: { color: '#F4F2FB', type: 'dashed' } },
        axisLabel: { color: '#8F7FA8', fontSize: 10 },
      },
      series: [
        {
          name: 'Baseline (P50)',
          type: 'line',
          data: baseP50,
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#8F7FA8', width: 2, type: 'dashed' },
          itemStyle: { color: '#8F7FA8' },
        },
        {
          name: 'Scenario (P50)',
          type: 'line',
          data: scnP50,
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#0D6553', width: 2.5 },
          itemStyle: { color: '#0D6553' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(29, 233, 192, 0.25)' },
              { offset: 1, color: 'rgba(29, 233, 192, 0.0)' },
            ]),
          },
        },
        {
          name: 'Scenario P90 (Optimistic)',
          type: 'line',
          data: scnP90 as (number | null)[],
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#10B981', width: 1.5, type: 'dotted' },
          itemStyle: { color: '#10B981' },
        },
        {
          name: 'Scenario P10 (Stress)',
          type: 'line',
          data: scnP10 as (number | null)[],
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#EF4444', width: 1.5, type: 'dotted' },
          itemStyle: { color: '#EF4444' },
        },
      ] as echarts.SeriesOption[],
    };

    chart.setOption(option, true);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [result]);

  return <div ref={chartRef} className="w-full h-72" />;
};
