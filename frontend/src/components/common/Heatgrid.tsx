import React, { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { LoadingSkeleton } from '../feedback/LoadingSkeleton';

export interface HeatgridCell {
  aircraftId: string;
  tailCode: string;
  systemId: string;
  systemName: string;
  healthIndex: number;
  status: string;
  driverComponent?: string;
}

interface HeatgridProps {
  cells: HeatgridCell[];
  onCellClick?: (aircraftId: string, systemId?: string) => void;
  loading?: boolean;
}

const SYSTEMS_ORDER = [
  'Propulsion',
  'Hydraulics',
  'Electrical',
  'Landing gear',
  'Avionics',
  'Fuel',
  'Environmental (ECS)',
];

export const Heatgrid: React.FC<HeatgridProps> = ({ cells, onCellClick, loading = false }) => {
  const [filterQuery, setFilterQuery] = useState('');

  // Extract unique systems and aircraft
  const { systems, aircraftList, matrix } = useMemo(() => {
    const sysSet = new Set<string>();
    const acMap = new Map<string, string>(); // id -> tail
    const cellMap = new Map<string, HeatgridCell>(); // `${ac}_${sys}` -> cell

    cells.forEach((c) => {
      sysSet.add(c.systemName);
      acMap.set(c.aircraftId, c.tailCode);
      cellMap.set(`${c.aircraftId}_${c.systemName}`, c);
    });

    // Sort systems according to standard order if present
    const sortedSystems = Array.from(sysSet).sort((a, b) => {
      const idxA = SYSTEMS_ORDER.indexOf(a);
      const idxB = SYSTEMS_ORDER.indexOf(b);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return a.localeCompare(b);
    });

    const sortedAircraft = Array.from(acMap.entries())
      .map(([id, tail]) => ({ id, tail }))
      .sort((a, b) => a.tail.localeCompare(b.tail));

    return {
      systems: sortedSystems,
      aircraftList: sortedAircraft,
      matrix: cellMap,
    };
  }, [cells]);

  const filteredAircraft = useMemo(() => {
    if (!filterQuery) return aircraftList;
    const q = filterQuery.toLowerCase();
    return aircraftList.filter((ac) => ac.tail.toLowerCase().includes(q) || ac.id.toLowerCase().includes(q));
  }, [aircraftList, filterQuery]);

  if (loading) {
    return <LoadingSkeleton rows={8} />;
  }

  const getCellColor = (hi: number | undefined) => {
    if (hi === undefined) return 'bg-[#F4F2FB] border-[#E6E2F0] text-[#BAAFC9]';
    if (hi >= 75) return 'bg-[#ECFDF5] hover:bg-[#D1FAE5] border-[#A7F3D0] text-[#059669] font-bold';
    if (hi >= 50) return 'bg-[#FFFBEB] hover:bg-[#FEF3C7] border-[#FDE68A] text-[#D97706] font-bold';
    return 'bg-[#FEF2F2] hover:bg-[#FEE2E2] border-[#FECACA] text-[#DC2626] font-bold';
  };

  return (
    <div className="w-full flex flex-col space-y-3 bg-white border border-[#E6E2F0] rounded-[20px] p-5 shadow-ap-card">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#EDE9F5] pb-4">
        <div>
          <h3 className="text-sm sm:text-base font-semibold text-[#3B1D5E] tracking-tight">
            Fleet System Readiness Heat-Grid
          </h3>
          <p className="text-xs text-[#6B5B84] mt-0.5">
            Click any cell to inspect airframe telemetry and subsystem components
          </p>
        </div>

        {/* Legend & Filter */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-3 text-[10px] font-mono text-[#6B5B84]">
            <span className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#059669] inline-block mr-1" /> ≥75 (Nominal)
            </span>
            <span className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#D97706] inline-block mr-1" /> 50–74 (Degraded)
            </span>
            <span className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#DC2626] inline-block mr-1" /> &lt;50 (Critical)
            </span>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#6B5B84] absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Filter tail..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="bg-[#F4F2FB] border border-[#E6E2F0] text-[#3B1D5E] text-xs font-mono rounded-[10px] pl-7 pr-2.5 py-1.5 w-32 focus:outline-none focus:border-[#7C3AED] focus:bg-white"
            />
          </div>
        </div>
      </div>

      {/* Heatgrid Matrix */}
      <div className="overflow-x-auto max-h-[380px] overflow-y-auto pr-1">
        <table className="w-full border-collapse text-left text-xs font-mono">
          <thead className="sticky top-0 bg-[#F4F2FB] z-10">
            <tr className="border-b border-[#E6E2F0] text-[11px] text-[#6B5B84] select-none">
              <th className="py-2.5 px-3 font-bold w-24">Airframe</th>
              {systems.map((sys) => (
                <th key={sys} className="py-2.5 px-2 text-center font-semibold truncate max-w-[100px]" title={sys}>
                  {sys.replace('Environmental (ECS)', 'ECS').replace('Landing gear', 'Landing Gear')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#EDE9F5]">
            {filteredAircraft.map((ac) => (
              <tr key={ac.id} className="hover:bg-[#FBF9FE] transition-colors">
                <td
                  onClick={() => onCellClick && onCellClick(ac.id)}
                  className="py-2 px-3 font-bold text-[#3B1D5E] hover:text-[#7C3AED] cursor-pointer select-none"
                  title={`Inspect ${ac.tail}`}
                >
                  {ac.tail}
                </td>
                {systems.map((sys) => {
                  const cell = matrix.get(`${ac.id}_${sys}`);
                  const hi = cell ? Math.round(cell.healthIndex) : undefined;
                  return (
                    <td key={sys} className="py-1 px-1 text-center">
                      <button
                        onClick={() => onCellClick && onCellClick(ac.id, cell?.systemId)}
                        title={
                          cell
                            ? `${ac.tail} • ${sys}: Health Index ${hi} (${cell.status})${
                                cell.driverComponent ? `\nDriver: ${cell.driverComponent}` : ''
                              }`
                            : `${ac.tail} • ${sys}: No data`
                        }
                        className={`w-full py-1.5 rounded-[8px] border text-[11px] font-bold transition-all duration-150 ${getCellColor(
                          hi
                        )}`}
                      >
                        {hi !== undefined ? hi : '—'}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
