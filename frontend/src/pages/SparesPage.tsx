import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import {
  Package,
  AlertTriangle,
  Clock,
  TrendingUp,
  Search,
  CheckCircle2,
  Truck,
  ArrowUpRight,
  ExternalLink,
  History,
  ShieldAlert,
  Layers,
} from 'lucide-react';
import { KpiCard } from '../components/common/KpiCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { DataTable, type Column } from '../components/common/DataTable';
import { SectionContainer } from '../components/common/SectionContainer';
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton';
import { EmptyState } from '../components/feedback/EmptyState';
import { useAuth } from '../hooks/useAuth';
import {
  useInventory,
  useSpareParts,
  useInventoryTransactions,
} from '../hooks/useSparesQueries';
import { useAdvisories } from '../hooks/useEngineQueries';
import type { InventoryTransactionOut, SparePartOut } from '../types/api';

interface MergedPartRow {
  part_number: string;
  description: string;
  criticality: number;
  unit_cost: number;
  lead_time_days: number;
  reorder_level: number;
  on_hand: number;
  reserved: number;
  available_net: number;
  on_order: number;
  demand_30d: number;
  min_rul_days: number | null;
  status: 'short' | 'at_risk' | 'ok';
  has_lead_time_shortfall: boolean;
  affected_airframes: string[];
}

export const SparesPage: React.FC = () => {
  const navigate = useNavigate();
  const { asOfDate } = useAuth();

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'short' | 'at_risk' | 'ok'>('all');
  const [selectedLocation, setSelectedLocation] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<'inventory' | 'transactions'>('inventory');

  // Queries
  const { data: partsData, isLoading: loadingParts } = useSpareParts();
  const { data: inventoryData, isLoading: loadingInventory } = useInventory({
    location_id: selectedLocation !== 'all' ? selectedLocation : undefined,
    page_size: 150,
  });
  const { data: advisoriesData, isLoading: loadingAdvisories } = useAdvisories({
    as_of_date: asOfDate || undefined,
    page_size: 100,
  });
  const { data: transactionsData, isLoading: loadingTxns } = useInventoryTransactions({
    page_size: 50,
  });

  const rawParts = partsData || [];
  const inventoryItems = inventoryData?.items || [];
  const advisories = advisoriesData?.items || [];
  const transactions = transactionsData?.items || [];

  // Locations list for filter dropdown
  const locations = useMemo(() => {
    const locSet = new Set<string>();
    inventoryItems.forEach((item) => {
      if (item.location_id) locSet.add(item.location_id);
    });
    return Array.from(locSet).sort();
  }, [inventoryItems]);

  // Merge Parts + Inventory Aggregations + ML Predicted Demand & RUL
  const mergedParts = useMemo<MergedPartRow[]>(() => {
    const stockMap = new Map<
      string,
      { on_hand: number; reserved: number; on_order: number }
    >();

    inventoryItems.forEach((inv) => {
      const existing = stockMap.get(inv.part_number) || {
        on_hand: 0,
        reserved: 0,
        on_order: 0,
      };
      existing.on_hand += inv.on_hand;
      existing.reserved += inv.reserved;
      existing.on_order += inv.on_order;
      stockMap.set(inv.part_number, existing);
    });

    const demandMap = new Map<
      string,
      { demand: number; minRul: number | null; airframes: Set<string> }
    >();

    advisories.forEach((adv) => {
      const expl = adv.explanation || {};
      const spareInfo = (expl.spare_info as Record<string, unknown>) || {};
      const pn = (spareInfo.part_number as string) || '';
      const rul = typeof expl.rul_p50 === 'number' ? expl.rul_p50 : null;

      if (pn) {
        const cur = demandMap.get(pn) || {
          demand: 0,
          minRul: null,
          airframes: new Set<string>(),
        };
        cur.demand += 1;
        if (rul !== null) {
          if (cur.minRul === null || rul < cur.minRul) {
            cur.minRul = rul;
          }
        }
        if (adv.aircraft_id) cur.airframes.add(adv.aircraft_id);
        demandMap.set(pn, cur);
      }
    });

    return rawParts.map((p) => {
      const stock = stockMap.get(p.part_number) || {
        on_hand: 0,
        reserved: 0,
        on_order: 0,
      };
      const demandInfo = demandMap.get(p.part_number) || {
        demand: 0,
        minRul: null,
        airframes: new Set<string>(),
      };

      const available_net = Math.max(0, stock.on_hand - stock.reserved);
      const demand_30d = Math.max(demandInfo.demand, stock.reserved > 0 ? stock.reserved : 0);
      const min_rul_days = demandInfo.minRul;

      const has_lead_time_shortfall =
        min_rul_days !== null && p.lead_time_days > min_rul_days;

      const is_stock_short = available_net < demand_30d;

      let status: 'short' | 'at_risk' | 'ok' = 'ok';
      if (has_lead_time_shortfall || is_stock_short) {
        status = 'short';
      } else if (stock.on_hand <= p.reorder_level) {
        status = 'at_risk';
      }

      return {
        part_number: p.part_number,
        description: p.description,
        criticality: p.criticality,
        unit_cost: p.unit_cost,
        lead_time_days: p.lead_time_days,
        reorder_level: p.reorder_level,
        on_hand: stock.on_hand,
        reserved: stock.reserved,
        available_net,
        on_order: stock.on_order,
        demand_30d,
        min_rul_days,
        status,
        has_lead_time_shortfall,
        affected_airframes: Array.from(demandInfo.airframes),
      };
    });
  }, [rawParts, inventoryItems, advisories]);

  // Filtered rows for data table
  const filteredRows = useMemo(() => {
    return mergedParts.filter((item) => {
      if (statusFilter !== 'all' && item.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesPn = item.part_number.toLowerCase().includes(q);
        const matchesDesc = item.description.toLowerCase().includes(q);
        const matchesAc = item.affected_airframes.some((ac) => ac.toLowerCase().includes(q));
        if (!matchesPn && !matchesDesc && !matchesAc) return false;
      }
      return true;
    });
  }, [mergedParts, statusFilter, searchQuery]);

  // Overall KPIs
  const { totalParts, shortCount, totalOnHand, totalOnOrder } = useMemo(() => {
    let shorts = 0;
    let onHand = 0;
    let onOrder = 0;

    mergedParts.forEach((p) => {
      if (p.status === 'short') shorts++;
      onHand += p.on_hand;
      onOrder += p.on_order;
    });

    return {
      totalParts: mergedParts.length,
      shortCount: shorts,
      totalOnHand: onHand,
      totalOnOrder: onOrder,
    };
  }, [mergedParts]);

  // Critical Shortfall Alerts list
  const criticalShortfalls = useMemo(() => {
    return mergedParts.filter((p) => p.has_lead_time_shortfall || p.status === 'short');
  }, [mergedParts]);

  // Table Columns for Inventory
  const columns: Column<MergedPartRow>[] = [
    {
      header: 'Part Number',
      accessorKey: 'part_number',
      render: (row) => (
        <div>
          <span className="font-bold font-mono text-[#3B1D5E]">{row.part_number}</span>
          <div className="text-[10px] text-[#8F7FA8]">Tier {row.criticality}</div>
        </div>
      ),
    },
    {
      header: 'Description',
      render: (row) => (
        <div className="max-w-xs">
          <p className="text-[#3B1D5E] text-xs truncate font-semibold" title={row.description}>
            {row.description}
          </p>
          {row.affected_airframes.length > 0 && (
            <div className="flex items-center space-x-1 mt-0.5">
              <span className="text-[10px] text-[#8F7FA8]">Demand:</span>
              {row.affected_airframes.map((ac) => (
                <button
                  key={ac}
                  onClick={() => navigate(`/aircraft?id=${ac}`)}
                  className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#E0F8FA] text-[#0369A1] hover:underline border border-[#BAE6FD] font-bold"
                >
                  {ac}
                </button>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      header: 'On Hand',
      align: 'right',
      render: (row) => (
        <span className="font-mono font-bold text-[#3B1D5E]">{row.on_hand}</span>
      ),
    },
    {
      header: 'Reserved',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono font-bold ${
            row.reserved > 0 ? 'text-[#D97706]' : 'text-[#8F7FA8]'
          }`}
        >
          {row.reserved}
        </span>
      ),
    },
    {
      header: 'Net Available',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono font-bold ${
            row.available_net === 0 ? 'text-[#DC2626]' : 'text-[#059669]'
          }`}
        >
          {row.available_net}
        </span>
      ),
    },
    {
      header: 'On Order',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono ${
            row.on_order > 0 ? 'text-[#2563EB] font-bold' : 'text-[#8F7FA8]'
          }`}
        >
          {row.on_order}
        </span>
      ),
    },
    {
      header: 'Lead Time',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono ${
            row.has_lead_time_shortfall ? 'text-[#DC2626] font-bold' : 'text-[#6B5B84]'
          }`}
        >
          {row.lead_time_days}d
        </span>
      ),
    },
    {
      header: '30d Demand',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono font-bold ${
            row.demand_30d > row.available_net ? 'text-[#DC2626]' : 'text-[#3B1D5E]'
          }`}
        >
          {row.demand_30d}
        </span>
      ),
    },
    {
      header: 'Reorder Lvl',
      align: 'right',
      render: (row) => <span className="font-mono text-[#8F7FA8]">{row.reorder_level}</span>,
    },
    {
      header: 'Status',
      align: 'center',
      render: (row) => {
        if (row.status === 'short') {
          return <StatusBadge status="short" size="sm" />;
        }
        if (row.status === 'at_risk') {
          return <StatusBadge status="at risk" size="sm" />;
        }
        return <StatusBadge status="ok" size="sm" />;
      },
    },
  ];

  // Table Columns for Inventory Transactions
  const txnColumns: Column<InventoryTransactionOut>[] = [
    {
      header: 'Txn ID',
      accessorKey: 'txn_id',
    },
    {
      header: 'Part Number',
      render: (row) => <span className="font-mono font-bold text-[#3B1D5E]">{row.part_number}</span>,
    },
    {
      header: 'Date & Time',
      render: (row) => (
        <span className="text-[#6B5B84] font-mono">{new Date(row.date).toLocaleString()}</span>
      ),
    },
    {
      header: 'Movement Type',
      align: 'center',
      render: (row) => {
        const isIssue = row.type === 'issue';
        return (
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-bold uppercase ${
              isIssue
                ? 'bg-[#FEF2F2] text-[#DC2626] border border-[#FCA5A5]'
                : 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]'
            }`}
          >
            {row.type}
          </span>
        );
      },
    },
    {
      header: 'Quantity',
      align: 'right',
      render: (row) => (
        <span
          className={`font-mono font-bold ${
            row.type === 'issue' ? 'text-[#DC2626]' : 'text-[#059669]'
          }`}
        >
          {row.type === 'issue' ? `-${row.qty}` : `+${row.qty}`}
        </span>
      ),
    },
    {
      header: 'Associated Work Order',
      render: (row) => (
        <span className="font-mono text-[#0D6553]">
          {row.work_order_id ? (
            <button
              onClick={() => navigate('/planning')}
              className="hover:underline flex items-center gap-1 font-bold"
            >
              {row.work_order_id}
              <ArrowUpRight className="w-3 h-3 opacity-70" />
            </button>
          ) : (
            '—'
          )}
        </span>
      ),
    },
  ];

  const isLoading = loadingParts || loadingInventory || loadingAdvisories;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E6E2F0] pb-4">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 bg-[#E0F8FA] border border-[#BAE6FD] rounded-[12px] text-[#0D6553] shadow-sm">
            <Package className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-[#3B1D5E] tracking-tight">
              Spares & Inventory Intelligence
            </h1>
            <p className="text-xs text-[#6B5B84] mt-0.5">
              Connecting predictive wear horizons, procurement lead times, and multi-echelon stock
            </p>
          </div>
        </div>

        {/* View / Location Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Location Selector */}
          <div className="flex items-center space-x-1.5 bg-white border border-[#E6E2F0] rounded-[10px] px-3 py-1.5 text-xs shadow-sm">
            <span className="text-[#6B5B84]">Warehouse:</span>
            <select
              value={selectedLocation}
              onChange={(e) => setSelectedLocation(e.target.value)}
              className="bg-transparent text-[#3B1D5E] font-bold focus:outline-none cursor-pointer"
            >
              <option value="all">All Locations (Consolidated)</option>
              {locations.map((loc) => (
                <option key={loc} value={loc}>
                  {loc}
                </option>
              ))}
            </select>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center space-x-1 bg-white border border-[#E6E2F0] rounded-[10px] p-1 text-xs shadow-sm">
            <button
              onClick={() => setActiveTab('inventory')}
              className={`px-3 py-1.5 rounded-[8px] font-bold transition ${
                activeTab === 'inventory'
                  ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                  : 'text-[#6B5B84] hover:text-[#3B1D5E]'
              }`}
            >
              Stock Status
            </button>
            <button
              onClick={() => setActiveTab('transactions')}
              className={`px-3 py-1.5 rounded-[8px] font-bold transition ${
                activeTab === 'transactions'
                  ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                  : 'text-[#6B5B84] hover:text-[#3B1D5E]'
              }`}
            >
              Material Movements
            </button>
          </div>
        </div>
      </div>

      {/* 2. LEVEL 1: Key Inventory & Supply Risk KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Tracked Catalog Parts"
          value={totalParts}
          subtitle="Critical LRUs & Assemblies"
          icon={<Package className="w-5 h-5" />}
          accent="honey"
          loading={isLoading}
        />

        <KpiCard
          title="Supply Shortfall Risks"
          value={shortCount}
          subtitle="Lead Time > RUL or Stockout"
          change={{
            value: shortCount > 0 ? 'Urgent PO Req.' : 'Protected',
            isPositive: shortCount === 0,
            label: 'Risk State',
          }}
          icon={<ShieldAlert className="w-5 h-5" />}
          accent="rose"
          loading={isLoading}
        />

        <KpiCard
          title="Total Physical On-Hand"
          value={totalOnHand}
          subtitle="Units across base & depot"
          icon={<CheckCircle2 className="w-5 h-5" />}
          accent="emerald"
          loading={isLoading}
        />

        <KpiCard
          title="On-Order Pipeline"
          value={totalOnOrder}
          subtitle="Incoming purchase deliveries"
          icon={<Truck className="w-5 h-5" />}
          accent="cyan"
          loading={isLoading}
        />
      </div>

      {/* 3. LEVEL 2: Critical Supply Shortfall Warning Banners */}
      {criticalShortfalls.length > 0 && (
        <div className="space-y-3">
          {criticalShortfalls.map((sf) => (
            <div
              key={sf.part_number}
              className="bg-[#FEF2F2] border border-[#FCA5A5] rounded-[16px] p-4 sm:p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="flex items-start space-x-3.5">
                <div className="p-2 bg-white border border-[#FCA5A5] rounded-[10px] text-[#DC2626] shrink-0 mt-0.5 shadow-sm">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs uppercase font-bold px-2.5 py-0.5 rounded-full bg-[#DC2626] text-white tracking-wider">
                      Supply Shortfall Alert
                    </span>
                    <span className="text-sm font-bold text-[#3B1D5E]">
                      P/N {sf.part_number} — {sf.description}
                    </span>
                  </div>

                  <p className="text-xs text-[#991B1B] leading-relaxed">
                    {sf.has_lead_time_shortfall ? (
                      <>
                        Lead time (<strong className="text-[#3B1D5E] font-mono">{sf.lead_time_days} days</strong>) exceeds
                        predicted component remaining life (
                        <strong className="text-[#DC2626] font-mono">
                          RUL ~{sf.min_rul_days ? sf.min_rul_days.toFixed(1) : '12'} days
                        </strong>
                        ). Available unreserved stock: <strong className="text-[#3B1D5E] font-mono">{sf.available_net}</strong>{' '}
                        unit(s). Grounding will occur unless immediate emergency PO expediting is triggered.
                      </>
                    ) : (
                      <>
                        Projected 30-day demand (<strong className="text-[#3B1D5E] font-mono">{sf.demand_30d} units</strong>)
                        exceeds available net stock (<strong className="text-[#DC2626] font-mono">{sf.available_net} units</strong>).
                        Reorder threshold breached.
                      </>
                    )}
                  </p>

                  {sf.affected_airframes.length > 0 && (
                    <div className="flex items-center space-x-2 text-[11px] text-[#6B5B84] pt-0.5">
                      <span>Degrading Airframe(s):</span>
                      {sf.affected_airframes.map((ac) => (
                        <span key={ac} className="text-[#0D6553] font-bold font-mono">
                          {ac}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-2 shrink-0 self-end md:self-center">
                {sf.affected_airframes.length > 0 && (
                  <button
                    onClick={() => navigate(`/aircraft?id=${sf.affected_airframes[0]}`)}
                    className="px-3.5 py-1.5 rounded-[8px] bg-white hover:bg-[#F4F2FB] text-[#3B1D5E] text-xs font-bold flex items-center space-x-1.5 transition border border-[#E6E2F0] shadow-sm"
                  >
                    <span>View Airframe</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  onClick={() =>
                    navigate(
                      `/planning?aircraft=${sf.affected_airframes[0] || ''}&component=${
                        sf.part_number
                      }`
                    )
                  }
                  className="px-3.5 py-1.5 rounded-[8px] bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] text-xs font-bold flex items-center space-x-1.5 transition shadow-ap-mint"
                >
                  <span>Schedule Replacement</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 4. LEVEL 3: Visualizations: Demand vs Stock & Lead Time vs RUL */}
      {activeTab === 'inventory' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Demand vs Stock Bars */}
          <SectionContainer
            title="Demand vs. Stock Analysis (Critical LRUs)"
            subtitle="Comparison of available on-hand stock against 30-day wear demand"
            icon={<TrendingUp className="w-4 h-4 text-[#0D6553]" />}
            badge={<span className="text-[10px] text-[#6B5B84] font-mono">Top 8 Catalog Parts</span>}
          >
            <DemandVsStockChart parts={mergedParts.slice(0, 8)} loading={isLoading} />
          </SectionContainer>

          {/* Chart 2: Lead Time vs RUL Scatter Plot */}
          <SectionContainer
            title="Lead Time vs. Remaining Useful Life (RUL)"
            subtitle="Supply Risk Horizon: Parts plotted above the line (LT > RUL) cause grounding"
            icon={<Clock className="w-4 h-4 text-[#DC2626]" />}
            badge={<span className="text-[10px] text-[#DC2626] font-bold">Risk Zone: LT &gt; RUL</span>}
          >
            <LeadTimeVsRulScatterChart
              advisories={advisories}
              parts={rawParts}
              loading={isLoading}
              onSelectAirframe={(acId) => navigate(`/aircraft?id=${acId}`)}
            />
          </SectionContainer>
        </div>
      )}

      {/* 5. LEVEL 4: Inventory Stock Table & Filter Controls */}
      {activeTab === 'inventory' && (
        <SectionContainer
          title="Spare Parts Inventory Catalog"
          subtitle="Multi-echelon stock levels, reserved allocation, procurement pipelines, and lead time constraints"
          icon={<Layers className="w-4 h-4 text-[#0D6553]" />}
        >
          <div className="space-y-4 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-3">
              {/* Left Filter Buttons */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[#6B5B84] text-[11px]">Filter Status:</span>
                <button
                  onClick={() => setStatusFilter('all')}
                  className={`px-3 py-1 rounded-[8px] text-[11px] font-bold transition ${
                    statusFilter === 'all'
                      ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                      : 'bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] border border-[#E6E2F0]'
                  }`}
                >
                  All ({mergedParts.length})
                </button>
                <button
                  onClick={() => setStatusFilter('short')}
                  className={`px-3 py-1 rounded-[8px] text-[11px] font-bold transition ${
                    statusFilter === 'short'
                      ? 'bg-[#FEF2F2] text-[#DC2626] border border-[#FCA5A5]'
                      : 'bg-[#F4F2FB] text-[#6B5B84] hover:text-[#DC2626] border border-[#E6E2F0]'
                  }`}
                >
                  Shortfall ({mergedParts.filter((p) => p.status === 'short').length})
                </button>
                <button
                  onClick={() => setStatusFilter('at_risk')}
                  className={`px-3 py-1 rounded-[8px] text-[11px] font-bold transition ${
                    statusFilter === 'at_risk'
                      ? 'bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]'
                      : 'bg-[#F4F2FB] text-[#6B5B84] hover:text-[#D97706] border border-[#E6E2F0]'
                  }`}
                >
                  At Risk ({mergedParts.filter((p) => p.status === 'at_risk').length})
                </button>
                <button
                  onClick={() => setStatusFilter('ok')}
                  className={`px-3 py-1 rounded-[8px] text-[11px] font-bold transition ${
                    statusFilter === 'ok'
                      ? 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]'
                      : 'bg-[#F4F2FB] text-[#6B5B84] hover:text-[#059669] border border-[#E6E2F0]'
                  }`}
                >
                  Nominal ({mergedParts.filter((p) => p.status === 'ok').length})
                </button>
              </div>

              {/* Right Search Input */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-[#8F7FA8] absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Search part, description, airframe..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-[#F4F2FB] border border-[#E6E2F0] text-[#3B1D5E] text-xs rounded-[8px] pl-8 pr-3 py-1.5 w-64 focus:outline-none focus:border-[#1DE9C0] placeholder-[#8F7FA8]"
                />
              </div>
            </div>

            <DataTable
              columns={columns}
              data={filteredRows}
              loading={isLoading}
              emptyTitle="No Parts Match Filter"
              emptyMessage="No spare part records match the selected status or keyword search."
            />
          </div>
        </SectionContainer>
      )}

      {/* 6. LEVEL 5: Material Movements / Transactions Tab */}
      {activeTab === 'transactions' && (
        <SectionContainer
          title="Recent Warehouse Material Movements"
          subtitle="Audit log of issues, receipts, and returns connected to work orders"
          icon={<History className="w-4 h-4 text-[#0D6553]" />}
        >
          {loadingTxns ? (
            <LoadingSkeleton rows={5} />
          ) : transactions.length === 0 ? (
            <EmptyState
              title="No Movement Transactions"
              message="No inventory issue or receipt records found."
            />
          ) : (
            <DataTable columns={txnColumns} data={transactions} />
          )}
        </SectionContainer>
      )}
    </div>
  );
};

// ----------------------------------------------------
// Subcomponent: Demand vs Stock Grouped Bar Chart
// ----------------------------------------------------
interface DemandVsStockChartProps {
  parts: MergedPartRow[];
  loading?: boolean;
}

const DemandVsStockChart: React.FC<DemandVsStockChartProps> = ({ parts, loading = false }) => {
  const chartRef = React.useRef<HTMLDivElement | null>(null);
  const chartInstance = React.useRef<echarts.EChartsType | null>(null);

  React.useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' });
    }
    const chart = chartInstance.current;

    if (loading || parts.length === 0) {
      chart.showLoading({ color: '#1DE9C0', maskColor: 'rgba(255, 255, 255, 0.85)' });
      return;
    }
    chart.hideLoading();

    const categories = parts.map((p) => p.part_number);
    const onHandData = parts.map((p) => p.on_hand);
    const reservedData = parts.map((p) => p.reserved);
    const onOrderData = parts.map((p) => p.on_order);
    const demandData = parts.map((p) => p.demand_30d);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#FFFFFF',
        borderColor: '#E6E2F0',
        textStyle: { color: '#3B1D5E', fontSize: 11 },
      },
      legend: {
        data: ['On-Hand', 'Reserved', 'On-Order', '30d Demand'],
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
        data: categories,
        axisLine: { lineStyle: { color: '#E6E2F0' } },
        axisLabel: {
          color: '#6B5B84',
          fontSize: 10,
          fontFamily: 'monospace',
          interval: 0,
          rotate: 20,
        },
      },
      yAxis: {
        type: 'value',
        name: 'Units',
        nameTextStyle: { color: '#8F7FA8', fontSize: 10 },
        splitLine: { lineStyle: { color: '#F4F2FB', type: 'dashed' } },
        axisLabel: { color: '#8F7FA8', fontSize: 10 },
      },
      series: [
        {
          name: 'On-Hand',
          type: 'bar',
          data: onHandData,
          itemStyle: { color: '#10B981', borderRadius: [4, 4, 0, 0] },
          barGap: '12%',
        },
        {
          name: 'Reserved',
          type: 'bar',
          data: reservedData,
          itemStyle: { color: '#F59E0B', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: 'On-Order',
          type: 'bar',
          data: onOrderData,
          itemStyle: { color: '#3B82F6', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '30d Demand',
          type: 'bar',
          data: demandData,
          itemStyle: { color: '#EF4444', borderRadius: [4, 4, 0, 0] },
        },
      ],
    };

    chart.setOption(option, true);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [parts, loading]);

  return <div ref={chartRef} className="w-full h-72" />;
};

// ----------------------------------------------------
// Subcomponent: Lead Time vs RUL Scatter Plot
// ----------------------------------------------------
interface LeadTimeVsRulScatterProps {
  advisories: Array<{
    aircraft_id?: string | null;
    component_id: string;
    explanation?: Record<string, unknown> | null;
  }>;
  parts: SparePartOut[];
  loading?: boolean;
  onSelectAirframe?: (aircraftId: string) => void;
}

const LeadTimeVsRulScatterChart: React.FC<LeadTimeVsRulScatterProps> = ({
  advisories,
  parts,
  loading = false,
  onSelectAirframe,
}) => {
  const chartRef = React.useRef<HTMLDivElement | null>(null);
  const chartInstance = React.useRef<echarts.EChartsType | null>(null);

  React.useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' });
    }
    const chart = chartInstance.current;

    if (loading) {
      chart.showLoading({ color: '#1DE9C0', maskColor: 'rgba(255, 255, 255, 0.85)' });
      return;
    }
    chart.hideLoading();

    const partsMap = new Map(parts.map((p) => [p.part_number, p]));

    const highRiskPoints: Array<[number, number, string, string, string]> = [];
    const safePoints: Array<[number, number, string, string, string]> = [];

    advisories.forEach((adv) => {
      const expl = adv.explanation || {};
      const spareInfo = (expl.spare_info as Record<string, unknown>) || {};
      const pn = (spareInfo.part_number as string) || '';
      const p = partsMap.get(pn);
      const rul = typeof expl.rul_p50 === 'number' ? expl.rul_p50 : null;

      if (p && rul !== null && rul > 0) {
        const item: [number, number, string, string, string] = [
          Number(rul.toFixed(1)),
          p.lead_time_days,
          adv.aircraft_id || 'Airframe',
          adv.component_id,
          pn,
        ];

        if (p.lead_time_days > rul) {
          highRiskPoints.push(item);
        } else {
          safePoints.push(item);
        }
      }
    });

    const maxVal = 70;

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: '#FFFFFF',
        borderColor: '#E6E2F0',
        textStyle: { color: '#3B1D5E', fontSize: 11 },
        formatter: (params: unknown) => {
          const p = params as {
            data: [number, number, string, string, string];
            seriesName: string;
          };
          const [rul, lt, ac, cmp, pn] = p.data;
          const isRisk = lt > rul;
          return `
            <div>
              <div style="font-weight: bold; color: ${isRisk ? '#DC2626' : '#059669'}; margin-bottom: 4px;">
                ${isRisk ? 'CRITICAL SUPPLY SHORTFALL' : 'NOMINAL SUPPLY HORIZON'}
              </div>
              <div>Airframe: <strong>${ac}</strong></div>
              <div>Component: <strong>${cmp}</strong></div>
              <div>Spare Part: <strong>${pn}</strong></div>
              <div style="margin-top: 4px; border-top: 1px solid #E6E2F0; padding-top: 4px;">
                Procurement Lead Time: <strong>${lt} days</strong><br/>
                Predicted Component RUL: <strong>${rul} days</strong>
              </div>
              <div style="color: ${isRisk ? '#DC2626' : '#059669'}; margin-top: 4px; font-weight: bold;">
                ${
                  isRisk
                    ? `Procurement exceeds remaining life by ${(lt - rul).toFixed(1)} days!`
                    : `Safe margin: ${(rul - lt).toFixed(1)} days buffer`
                }
              </div>
            </div>
          `;
        },
      },
      legend: {
        data: ['Shortfall Risk (LT > RUL)', 'Safe Buffer (LT ≤ RUL)'],
        textStyle: { color: '#6B5B84', fontSize: 10 },
        top: 0,
        right: 10,
      },
      grid: {
        left: '4%',
        right: '4%',
        bottom: '4%',
        top: '18%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: 'Predicted RUL (Days)',
        nameLocation: 'middle',
        nameGap: 24,
        nameTextStyle: { color: '#8F7FA8', fontSize: 10 },
        min: 0,
        max: maxVal,
        splitLine: { lineStyle: { color: '#F4F2FB', type: 'dashed' } },
        axisLabel: { color: '#8F7FA8', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        name: 'Lead Time (Days)',
        nameTextStyle: { color: '#8F7FA8', fontSize: 10 },
        min: 0,
        max: maxVal,
        splitLine: { lineStyle: { color: '#F4F2FB', type: 'dashed' } },
        axisLabel: { color: '#8F7FA8', fontSize: 10 },
      },
      series: [
        {
          name: 'Critical Horizon (LT = RUL)',
          type: 'line',
          data: [
            [0, 0],
            [maxVal, maxVal],
          ],
          symbol: 'none',
          lineStyle: {
            color: '#EF4444',
            type: 'dashed',
            width: 1.5,
          },
          tooltip: { show: false },
        },
        {
          name: 'Safe Buffer (LT ≤ RUL)',
          type: 'scatter',
          data: safePoints,
          symbolSize: 10,
          itemStyle: {
            color: '#10B981',
          },
        },
        {
          name: 'Shortfall Risk (LT > RUL)',
          type: 'scatter',
          data: highRiskPoints,
          symbolSize: 14,
          itemStyle: {
            color: '#EF4444',
            borderColor: '#FFFFFF',
            borderWidth: 1.5,
          },
        },
      ],
    };

    chart.setOption(option, true);

    chart.off('click');
    chart.on('click', (params: unknown) => {
      const p = params as { data?: [number, number, string, string, string] };
      if (p.data && p.data[2] && onSelectAirframe) {
        onSelectAirframe(p.data[2]);
      }
    });

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [advisories, parts, loading, onSelectAirframe]);

  return <div ref={chartRef} className="w-full h-72 cursor-pointer" />;
};
