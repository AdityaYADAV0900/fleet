import React from 'react';

export interface SystemStatusInfo {
  name: string;
  healthIndex: number;
  status: string;
  driverComponent?: string;
}

interface SvgSchematicProps {
  systems: SystemStatusInfo[];
  selectedSystem?: string | null;
  onSelectSystem?: (systemName: string) => void;
}

export const SvgSchematic: React.FC<SvgSchematicProps> = ({
  systems,
  selectedSystem,
  onSelectSystem,
}) => {
  const getSystemColor = (name: string) => {
    const s = systems.find((sys) => sys.name.toLowerCase().includes(name.toLowerCase()));
    if (!s) return { fill: '#F4F2FB', stroke: '#E6E2F0', hi: 100 };
    if (s.healthIndex >= 75) return { fill: '#ECFDF5', stroke: '#059669', hi: s.healthIndex };
    if (s.healthIndex >= 50) return { fill: '#FFFBEB', stroke: '#D97706', hi: s.healthIndex };
    return { fill: '#FEF2F2', stroke: '#DC2626', hi: s.healthIndex };
  };

  const systemsMap = [
    { key: 'Avionics', label: 'Avionics', x: 260, y: 55, r: 24 },
    { key: 'Propulsion', label: 'Propulsion', x: 190, y: 220, r: 28 },
    { key: 'Hydraulics', label: 'Hydraulics', x: 330, y: 220, r: 28 },
    { key: 'Fuel', label: 'Fuel System', x: 120, y: 250, r: 24 },
    { key: 'Environmental', label: 'ECS (Cooling)', x: 260, y: 160, r: 24 },
    { key: 'Electrical', label: 'Electrical', x: 260, y: 280, r: 24 },
    { key: 'Landing gear', label: 'Landing Gear', x: 260, y: 350, r: 24 },
  ];

  return (
    <div className="w-full flex flex-col items-center bg-white border border-[#E6E2F0] rounded-[20px] p-5 shadow-ap-card relative overflow-hidden">
      <div className="w-full flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-3 border-b border-[#EDE9F5]">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3B1D5E]">
            Subsystem Health Telemetry Schematic
          </h4>
          <p className="text-xs text-[#6B5B84]">
            Interactive multi-system topological airframe overlay
          </p>
        </div>
        <div className="flex items-center space-x-3 text-[10px] font-mono text-[#6B5B84]">
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-[#059669] mr-1" /> Nominal
          </span>
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-[#D97706] mr-1" /> Degraded
          </span>
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-[#DC2626] mr-1" /> Critical
          </span>
        </div>
      </div>

      <div className="relative w-full max-w-[520px] aspect-[520/420]">
        <svg viewBox="0 0 520 420" className="w-full h-full select-none">
          {/* Subtle Grid Background */}
          <defs>
            <pattern id="grid-schematic" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#F4F2FB" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="520" height="420" fill="url(#grid-schematic)" />

          {/* Aircraft Silhouette Outline */}
          <path
            d="M 260 25
               C 264 45, 270 90, 272 130
               L 395 240
               L 405 255
               L 330 260
               L 282 250
               L 285 360
               L 325 385
               L 320 395
               L 260 388
               L 200 395
               L 195 385
               L 235 360
               L 238 250
               L 190 260
               L 115 255
               L 125 240
               L 248 130
               C 250 90, 256 45, 260 25 Z"
            fill="#F4F2FB"
            stroke="#D8D2E5"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />

          {/* Internal Structure Lines */}
          <line x1="260" y1="35" x2="260" y2="385" stroke="#E6E2F0" strokeDasharray="3 3" />
          <line x1="190" y1="220" x2="330" y2="220" stroke="#E6E2F0" strokeDasharray="2 2" />

          {/* Subsystem Interactive Nodes */}
          {systemsMap.map((node) => {
            const style = getSystemColor(node.key);
            const isSelected = selectedSystem && selectedSystem.toLowerCase().includes(node.key.toLowerCase());

            return (
              <g
                key={node.key}
                onClick={() => onSelectSystem && onSelectSystem(node.label)}
                className="cursor-pointer group"
              >
                {/* Node Target Circle */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isSelected ? node.r + 4 : node.r}
                  fill={style.fill}
                  stroke={isSelected ? '#7C3AED' : style.stroke}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                  className="transition-all duration-200 group-hover:stroke-[#7C3AED]"
                />

                {/* Pulsing indicator if degraded/critical */}
                {style.hi < 75 && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.r + 6}
                    fill="none"
                    stroke={style.stroke}
                    strokeWidth="1"
                    opacity="0.6"
                    className="animate-ping"
                  />
                )}

                {/* Score in circle */}
                <text
                  x={node.x}
                  y={node.y + 4}
                  textAnchor="middle"
                  fill="#3B1D5E"
                  fontSize="11"
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  {Math.round(style.hi)}
                </text>

                {/* System label */}
                <text
                  x={node.x}
                  y={node.y + node.r + 14}
                  textAnchor="middle"
                  fill={isSelected ? '#7C3AED' : '#6B5B84'}
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight={isSelected ? 'bold' : 'normal'}
                  className="group-hover:fill-[#3B1D5E]"
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
