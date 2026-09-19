import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { DecisionStreamStage, ReviewStage } from '../../lib/reviewApi';
import { cn } from '../../lib/utils';
import { ArrowRight, Sparkles, Filter, CheckCircle2 } from 'lucide-react';

interface DecisionStreamProps {
  stages: DecisionStreamStage[];
  activeFilter: ReviewStage | 'all' | string;
  onSelectStage: (stage: ReviewStage | 'all') => void;
  className?: string;
}

export function DecisionStream({
  stages,
  activeFilter,
  onSelectStage,
  className = '',
}: DecisionStreamProps) {
  const [hoveredStage, setHoveredStage] = useState<string | null>(null);

  // Define light clinical node coordinates across a 1020 x 270 SVG canvas
  const stageNodes = useMemo(() => {
    return [
      {
        id: 'detected',
        x: 80,
        y: 135,
        label: 'DETECTED',
        count: 202,
        sub: 'Surveillance intake',
        color: '#0284c7',
        bg: '#f0f9ff',
        border: '#bae6fd',
        textColor: '#0369a1',
      },
      {
        id: 'medical_review',
        x: 310,
        y: 75,
        label: 'MEDICAL REVIEW',
        count: 64,
        sub: 'Safety & Clinical',
        color: '#7c3aed',
        bg: '#faf5ff',
        border: '#ddd6fe',
        textColor: '#6d28d9',
      },
      {
        id: 'data_compliance',
        x: 310,
        y: 195,
        label: 'DATA / COMPLIANCE',
        count: 86,
        sub: 'Queries & Protocol',
        color: '#0891b2',
        bg: '#ecfeff',
        border: '#a5f3fc',
        textColor: '#0e7490',
      },
      {
        id: 'human_gate',
        x: 580,
        y: 75,
        label: 'HUMAN GATE',
        count: 3,
        sub: 'Monitor Decision',
        color: '#d97706',
        bg: '#fffbeb',
        border: '#fde68a',
        textColor: '#b45309',
        pulse: true,
      },
      {
        id: 'action_monitoring',
        x: 790,
        y: 135,
        label: 'ACTION / MONITORING',
        count: 18,
        sub: 'CAPA & Reporting',
        color: '#475569',
        bg: '#f8fafc',
        border: '#cbd5e1',
        textColor: '#334155',
      },
      {
        id: 'resolved',
        x: 935,
        y: 215,
        label: 'RESOLVED',
        count: 31,
        sub: 'Audited & Closed',
        color: '#059669',
        bg: '#f0fdf4',
        border: '#a7f3d0',
        textColor: '#047857',
      },
    ];
  }, []);

  // Ribbons connecting stages with clean pastel colors
  const ribbons = [
    {
      id: 'detected-to-med',
      from: stageNodes[0],
      to: stageNodes[1],
      width: 12,
      color: '#a78bfa',
      label: 'Safety Escalation (64)',
      category: 'safety',
      d: 'M 140 125 C 210 125, 230 75, 250 75',
    },
    {
      id: 'detected-to-data',
      from: stageNodes[0],
      to: stageNodes[2],
      width: 14,
      color: '#38bdf8',
      label: 'Compliance & Data (86)',
      category: 'data',
      d: 'M 140 145 C 210 145, 230 195, 250 195',
    },
    {
      id: 'med-to-human',
      from: stageNodes[1],
      to: stageNodes[3],
      width: 7,
      color: '#f59e0b',
      label: 'Clinician Gate (3)',
      category: 'human',
      d: 'M 370 75 C 460 75, 480 75, 520 75',
    },
    {
      id: 'med-to-monitoring',
      from: stageNodes[1],
      to: stageNodes[4],
      width: 10,
      color: '#c4b5fd',
      label: 'Auto-Monitored (61)',
      category: 'monitoring',
      d: 'M 370 85 C 500 95, 680 125, 730 130',
    },
    {
      id: 'data-to-monitoring',
      from: stageNodes[2],
      to: stageNodes[4],
      width: 12,
      color: '#67e8f9',
      label: 'Site Queries In-Flight (68)',
      category: 'data',
      d: 'M 370 195 C 540 195, 670 145, 730 140',
    },
    {
      id: 'human-to-action',
      from: stageNodes[3],
      to: stageNodes[4],
      width: 6,
      color: '#f59e0b',
      label: 'Approved Actions',
      category: 'action',
      d: 'M 640 75 C 700 75, 720 120, 730 130',
    },
    {
      id: 'action-to-resolved',
      from: stageNodes[4],
      to: stageNodes[5],
      width: 9,
      color: '#34d399',
      label: 'Reconciliation Closed (31)',
      category: 'resolved',
      d: 'M 850 135 C 890 135, 890 215, 875 215',
    },
  ];

  return (
    <div className={cn('relative rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl', className)}>
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e2e8f0] pb-3.5">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#0d9488] animate-pulse" />
            <h3 className="display text-base font-bold text-[#0f172a]">The Decision Stream</h3>
            <span className="rounded-md border border-[#99f6e4] bg-[#f0fdfa] px-2 py-0.5 mono text-[10px] font-bold text-[#0f766e]">
              Live Case Flow
            </span>
          </div>
          <p className="mt-0.5 text-xs text-[#64748b]">
            From intake to resolution — click any stage to filter workspace cases
          </p>
        </div>

        {/* Filter Reset Button */}
        {activeFilter !== 'all' && (
          <button
            type="button"
            onClick={() => onSelectStage('all')}
            className="flex items-center gap-1.5 rounded-lg border border-[#99f6e4] bg-[#f0fdfa] px-2.5 py-1 text-[11px] font-semibold text-[#0f766e] transition hover:bg-[#ccfbf1]"
          >
            <Filter size={12} />
            Showing: <span className="uppercase font-bold">{activeFilter.replace('_', ' ')}</span> · Clear filter ✕
          </button>
        )}
      </div>

      {/* Interactive Flow Canvas */}
      <div className="relative mt-3 w-full overflow-x-auto">
        <svg
          viewBox="0 0 1020 270"
          className="w-full min-w-[860px] select-none"
          style={{ height: '240px' }}
        >
          {/* Flow Ribbons */}
          {ribbons.map((ribbon) => {
            const isHovered =
              hoveredStage === ribbon.id ||
              hoveredStage === ribbon.from.id ||
              hoveredStage === ribbon.to.id;
            const isDimmed = hoveredStage && !isHovered;

            return (
              <g key={ribbon.id} className="transition-opacity duration-300">
                {/* Background flow curve */}
                <path
                  d={ribbon.d}
                  fill="none"
                  stroke={ribbon.color}
                  strokeWidth={ribbon.width}
                  strokeLinecap="round"
                  opacity={isDimmed ? 0.12 : isHovered ? 0.75 : 0.42}
                  className="transition-all duration-300 cursor-pointer"
                  onMouseEnter={() => setHoveredStage(ribbon.id)}
                  onMouseLeave={() => setHoveredStage(null)}
                />
                {/* Subtle flow dashes */}
                <path
                  d={ribbon.d}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth={2}
                  strokeDasharray="4 12"
                  strokeDashoffset={10}
                  opacity={isHovered ? 0.9 : 0.5}
                  className="pointer-events-none"
                  style={{
                    animation: 'dashFlow 3s linear infinite',
                  }}
                />
              </g>
            );
          })}

          {/* Interactive Stage Nodes (Light clinical cards) */}
          {stageNodes.map((node) => {
            const isSelected = activeFilter === node.id;
            const isHovered = hoveredStage === node.id;

            return (
              <g
                key={node.id}
                className="cursor-pointer transition-transform duration-200"
                onClick={() => onSelectStage(node.id as ReviewStage)}
                onMouseEnter={() => setHoveredStage(node.id)}
                onMouseLeave={() => setHoveredStage(null)}
              >
                {/* Outer halo if selected or hovered */}
                {(isSelected || isHovered) && (
                  <rect
                    x={node.x - 64}
                    y={node.y - 37}
                    width={128}
                    height={74}
                    rx={14}
                    fill={node.color}
                    opacity={isSelected ? 0.18 : 0.08}
                  />
                )}

                {/* Node Box (Light card surface with soft border) */}
                <rect
                  x={node.x - 60}
                  y={node.y - 33}
                  width={120}
                  height={66}
                  rx={12}
                  fill={node.bg}
                  stroke={isSelected ? node.color : isHovered ? node.color : node.border}
                  strokeWidth={isSelected ? 2.2 : 1.2}
                  className="transition-all duration-200"
                />

                {/* Pulse dot for Human Gate */}
                {node.pulse && (
                  <g>
                    <circle
                      cx={node.x + 48}
                      cy={node.y - 21}
                      r={4}
                      fill="#f59e0b"
                      className="animate-ping opacity-75"
                    />
                    <circle
                      cx={node.x + 48}
                      cy={node.y - 21}
                      r={3.5}
                      fill="#d97706"
                    />
                  </g>
                )}

                {/* Count */}
                <text
                  x={node.x}
                  y={node.y - 8}
                  textAnchor="middle"
                  className="font-bold select-none"
                  fontSize="17"
                  fontFamily="Space Grotesk, sans-serif"
                  fill={node.textColor}
                >
                  {node.count}
                </text>

                {/* Label */}
                <text
                  x={node.x}
                  y={node.y + 11}
                  textAnchor="middle"
                  className="font-bold select-none tracking-wider"
                  fontSize="9.5"
                  fontFamily="DM Mono, monospace"
                  fill={node.textColor}
                >
                  {node.label}
                </text>

                {/* Subtitle */}
                <text
                  x={node.x}
                  y={node.y + 24}
                  textAnchor="middle"
                  className="select-none font-medium"
                  fontSize="8.5"
                  fontFamily="Manrope, sans-serif"
                  fill="#64748b"
                >
                  {node.sub}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Clean Light Legend & Filter Bar */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-[#f1f5f9] pt-3 text-[11px] text-[#64748b]">
        <div className="flex flex-wrap items-center gap-2">
          <span className="mono text-[10px] font-bold text-[#475569] uppercase tracking-wider">
            Flow streams:
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#f5f3ff] text-[#6d28d9] border border-[#ddd6fe] font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-[#8b5cf6]" />
            Safety (64)
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#ecfeff] text-[#0e7490] border border-[#a5f3fc] font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-[#06b6d4]" />
            Data & Compliance (86)
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#fffbeb] text-[#b45309] border border-[#fde68a] font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-[#f59e0b]" />
            Human Decision (3)
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#f0fdf4] text-[#047857] border border-[#a7f3d0] font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-[#10b981]" />
            Resolved (31)
          </span>
        </div>

        <div className="mono text-[10px] text-[#64748b]">
          Proportional flow · Click stage node to isolate cases
        </div>
      </div>
    </div>
  );
}
