import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FindingMixCategory,
  DecisionOutcomes,
  CycleTrendPoint,
  CaseCategory,
  ReviewFunnelStep,
  ReviewStage,
} from '../../lib/reviewApi';
import { CheckCircle2, HelpCircle, AlertCircle, Eye, Filter, ArrowDown, Sparkles } from 'lucide-react';

interface VisualSummariesProps {
  findingMix: FindingMixCategory[];
  outcomes: DecisionOutcomes;
  trend: CycleTrendPoint[];
  totalCases: number;
  activeCategoryFilter: CaseCategory | 'all';
  onSelectCategory: (category: CaseCategory | 'all') => void;
  activeOutcomeFilter?: string;
  onSelectOutcome?: (outcome: string) => void;
  funnel?: ReviewFunnelStep[];
  activeStageFilter?: ReviewStage | 'all';
  onSelectStage?: (stage: ReviewStage | 'all') => void;
}

export const VisualSummaries: React.FC<VisualSummariesProps> = ({
  findingMix,
  outcomes,
  trend,
  totalCases,
  activeCategoryFilter,
  onSelectCategory,
  activeOutcomeFilter = 'all',
  onSelectOutcome,
  funnel,
  activeStageFilter,
  onSelectStage,
}) => {
  const [hoveredSegment, setHoveredSegment] = useState<FindingMixCategory | null>(null);
  const [hoveredTrendPoint, setHoveredTrendPoint] = useState<CycleTrendPoint | null>(null);
  const [card3Tab, setCard3Tab] = useState<'funnel' | 'trend'>('funnel');

  // SVG Donut calculation
  const size = 144;
  const strokeWidth = 22;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  let accumulatedPercent = 0;

  // Semantic light chart color mapping
  const categoryColors: Record<CaseCategory, string> = {
    safety: '#f43f5e',      // soft coral
    data_quality: '#0ea5e9',// soft cyan/blue
    compliance: '#6366f1',  // soft indigo
    site_pattern: '#f59e0b',// soft amber
  };

  // Decision outcomes bar calculation
  const outcomeTotal = outcomes.total || 1;
  const outcomeBars = [
    {
      key: 'approved',
      label: 'APPROVED',
      count: outcomes.approved,
      pct: (outcomes.approved / outcomeTotal) * 100,
      barColor: 'bg-[#10b981]',
      textColor: 'text-[#047857]',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />,
    },
    {
      key: 'clarify',
      label: 'CLARIFY',
      count: outcomes.clarify,
      pct: (outcomes.clarify / outcomeTotal) * 100,
      barColor: 'bg-[#f59e0b]',
      textColor: 'text-[#b45309]',
      icon: <HelpCircle className="w-3.5 h-3.5 text-[#f59e0b]" />,
    },
    {
      key: 'rejected',
      label: 'REJECTED',
      count: outcomes.rejected,
      pct: (outcomes.rejected / outcomeTotal) * 100,
      barColor: 'bg-[#f43f5e]',
      textColor: 'text-[#be123c]',
      icon: <AlertCircle className="w-3.5 h-3.5 text-[#f43f5e]" />,
    },
    {
      key: 'monitoring',
      label: 'MONITORING',
      count: outcomes.monitoring,
      pct: (outcomes.monitoring / outcomeTotal) * 100,
      barColor: 'bg-[#94a3b8]',
      textColor: 'text-[#475569]',
      icon: <Eye className="w-3.5 h-3.5 text-[#64748b]" />,
    },
  ];

  // SVG Trend dimensions
  const trendWidth = 320;
  const trendHeight = 120;
  const padding = { top: 14, right: 16, bottom: 24, left: 24 };
  const graphWidth = trendWidth - padding.left - padding.right;
  const graphHeight = trendHeight - padding.top - padding.bottom;

  const maxVal = Math.max(...trend.map((t) => Math.max(t.newCases, t.resolvedCases, t.openCases || 0)), 40);

  const getX = (index: number) => padding.left + (index / (trend.length - 1)) * graphWidth;
  const getY = (val: number) => padding.top + graphHeight - (val / maxVal) * graphHeight;

  // Path generators
  const newCasesPath = trend.reduce(
    (acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(pt.newCases)}`,
    ''
  );
  const resolvedCasesPath = trend.reduce(
    (acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(pt.resolvedCases)}`,
    ''
  );
  const openCasesPath = trend.reduce(
    (acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(pt.openCases)}`,
    ''
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* ========================================================= */}
      {/* A. FINDING MIX — DONUT CHART */}
      {/* ========================================================= */}
      <div className="rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl flex flex-col justify-between">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="mono text-[11px] font-bold uppercase tracking-[.18em] text-[#0f172a]">
              Finding Mix
            </h3>
            <p className="text-xs text-[#64748b]">
              Distribution of reviewed issues
            </p>
          </div>
          {activeCategoryFilter !== 'all' && (
            <button
              onClick={() => onSelectCategory('all')}
              className="text-xs mono font-semibold text-[#0d9488] hover:underline"
            >
              Reset filter
            </button>
          )}
        </div>

        <div className="flex items-center justify-between gap-4 my-2">
          {/* Donut SVG */}
          <div className="relative flex items-center justify-center shrink-0">
            <svg width={size} height={size} className="rotate-[-90deg]">
              {findingMix.map((seg) => {
                const strokeDasharray = `${(seg.percentage / 100) * circumference} ${circumference}`;
                const strokeDashoffset = -((accumulatedPercent / 100) * circumference);
                accumulatedPercent += seg.percentage;

                const isSelected = activeCategoryFilter === seg.category;
                const segmentColor = categoryColors[seg.category] || seg.color;

                return (
                  <circle
                    key={seg.category}
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="transparent"
                    stroke={segmentColor}
                    strokeWidth={isSelected ? strokeWidth + 3 : strokeWidth}
                    strokeDasharray={strokeDasharray}
                    strokeDashoffset={strokeDashoffset}
                    className="cursor-pointer transition-all duration-300 hover:opacity-85"
                    onMouseEnter={() => setHoveredSegment(seg)}
                    onMouseLeave={() => setHoveredSegment(null)}
                    onClick={() =>
                      onSelectCategory(activeCategoryFilter === seg.category ? 'all' : seg.category)
                    }
                  />
                );
              })}
            </svg>

            {/* Donut Center */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
              <span className="text-2xl font-bold text-[#0f172a] tracking-tight leading-none">
                {hoveredSegment ? hoveredSegment.count : totalCases}
              </span>
              <span className="mono text-[9px] font-semibold uppercase tracking-wider text-[#64748b] mt-1 leading-tight">
                {hoveredSegment ? hoveredSegment.label : 'cases reviewed'}
              </span>
            </div>
          </div>

          {/* Clean Legend */}
          <div className="flex-1 space-y-1.5">
            {findingMix.map((cat) => {
              const isSelected = activeCategoryFilter === cat.category;
              const color = categoryColors[cat.category] || cat.color;

              return (
                <button
                  key={cat.category}
                  onClick={() =>
                    onSelectCategory(activeCategoryFilter === cat.category ? 'all' : cat.category)
                  }
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-left text-xs transition ${
                    isSelected
                      ? 'border-[#0d9488] bg-[#f0fdfa] text-[#0f172a]'
                      : 'border-[#f1f5f9] bg-white hover:border-[#cbd5e1] hover:bg-[#f8fafc] text-[#334155]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="font-semibold text-xs text-[#0f172a]">{cat.label}</span>
                  </div>
                  <div className="mono text-xs text-[#64748b]">
                    <strong className="text-[#0f172a]">{cat.count}</strong> ({cat.percentage}%)
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="mono text-[10px] text-[#64748b] pt-2 border-t border-[#f1f5f9]">
          Click any segment to filter Review Center
        </div>
      </div>

      {/* ========================================================= */}
      {/* B. DECISION OUTCOMES — HORIZONTAL STACKED BAR */}
      {/* ========================================================= */}
      <div className="rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-1">
            <h3 className="mono text-[11px] font-bold uppercase tracking-[.18em] text-[#0f172a]">
              Decision Outcomes
            </h3>
            <span className="mono text-xs font-semibold text-[#64748b]">
              {outcomes.total} total
            </span>
          </div>
          <p className="text-xs text-[#64748b] mb-3">
            Human monitor resolution breakdown
          </p>

          {/* Horizontal Stacked Bars */}
          <div className="space-y-2.5">
            {outcomeBars.map((bar) => {
              const isSelected = activeOutcomeFilter === bar.key;

              return (
                <div
                  key={bar.key}
                  onClick={() => onSelectOutcome?.(activeOutcomeFilter === bar.key ? 'all' : bar.key)}
                  className={`group p-2 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-[#0d9488] bg-[#f0fdfa]'
                      : 'border-[#f1f5f9] bg-white hover:border-[#cbd5e1] hover:bg-[#f8fafc]'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <div className="flex items-center gap-1.5">
                      {bar.icon}
                      <span className="mono text-xs font-bold text-[#0f172a]">
                        {bar.label}
                      </span>
                    </div>
                    <span className="mono text-xs font-bold text-[#0f172a]">
                      {bar.count}{' '}
                      <span className="text-[#64748b] font-normal">
                        ({Math.round(bar.pct)}%)
                      </span>
                    </span>
                  </div>

                  {/* Horizontal Bar Track */}
                  <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200/50">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${bar.pct}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                      className={`h-full rounded-full ${bar.barColor}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mono text-[10px] text-[#64748b] pt-2 border-t border-[#f1f5f9]">
          Zero cases discarded · All tracked in study memory
        </div>
      </div>

      {/* ========================================================= */}
      {/* C. REVIEW FUNNEL (SELECTIVE ESCALATION) / CYCLE TREND */}
      {/* ========================================================= */}
      <div className="rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              {card3Tab === 'funnel' ? (
                <Filter className="w-4 h-4 text-[#0d9488]" />
              ) : (
                <Sparkles className="w-4 h-4 text-[#0284c7]" />
              )}
              <h3 className="mono text-[11px] font-bold uppercase tracking-[.18em] text-[#0f172a]">
                {card3Tab === 'funnel' ? 'Review Funnel' : 'Cycle Trend'}
              </h3>
            </div>

            {/* View Switcher Toggle */}
            <div className="flex items-center gap-1 bg-[#f1f5f9] p-0.5 rounded-lg border border-[#e2e8f0]">
              <button
                onClick={() => setCard3Tab('funnel')}
                className={`mono text-[10px] font-bold px-2 py-0.5 rounded transition ${
                  card3Tab === 'funnel'
                    ? 'bg-white text-[#0f766e] shadow-2xs'
                    : 'text-[#64748b] hover:text-[#0f172a]'
                }`}
              >
                Funnel
              </button>
              <button
                onClick={() => setCard3Tab('trend')}
                className={`mono text-[10px] font-bold px-2 py-0.5 rounded transition ${
                  card3Tab === 'trend'
                    ? 'bg-white text-[#0f766e] shadow-2xs'
                    : 'text-[#64748b] hover:text-[#0f172a]'
                }`}
              >
                Trend
              </button>
            </div>
          </div>

          <p className="text-xs text-[#64748b] mb-2.5">
            {card3Tab === 'funnel'
              ? 'How findings are narrowed into human decisions.'
              : 'Workload progression across cuts'}
          </p>

          {card3Tab === 'funnel' ? (
            /* Review Funnel Visualization */
            <div className="space-y-1.5 py-1">
              {(funnel && funnel.length > 0
                ? funnel
                : [
                    { stage: 'detected', label: 'Detected', count: 202, sub: 'Surveillance', pct: 100 },
                    { stage: 'medical_review', label: 'Medically relevant', count: 64, sub: 'Criteria verified', pct: 31.7 },
                    { stage: 'action_monitoring', label: 'Action / Monitoring', count: 18, sub: 'Queries & auto-monitored', pct: 8.9 },
                    { stage: 'human_gate', label: 'Human escalation', count: 3, sub: 'Medical Monitor gate', pct: 1.5 },
                  ]
              ).map((step, idx, arr) => {
                const mappedStage: ReviewStage =
                  step.stage === 'medically_relevant'
                    ? 'medical_review'
                    : step.stage === 'human_escalation'
                    ? 'human_gate'
                    : (step.stage as ReviewStage);

                const isSelected = activeStageFilter === mappedStage;
                const widthPct = Math.max(48, 100 - idx * 16);

                const colors = [
                  { bg: 'bg-[#f0f9ff]', border: 'border-[#bae6fd]', text: 'text-[#0369a1]', bar: '#0ea5e9' },
                  { bg: 'bg-[#faf5ff]', border: 'border-[#ddd6fe]', text: 'text-[#6d28d9]', bar: '#8b5cf6' },
                  { bg: 'bg-[#f8fafc]', border: 'border-[#cbd5e1]', text: 'text-[#334155]', bar: '#64748b' },
                  { bg: 'bg-[#fffbeb]', border: 'border-[#fde68a]', text: 'text-[#b45309]', bar: '#f59e0b' },
                ][idx] || { bg: 'bg-white', border: 'border-slate-200', text: 'text-slate-700', bar: '#0d9488' };

                return (
                  <div
                    key={step.stage}
                    onClick={() => onSelectStage?.(activeStageFilter === mappedStage ? 'all' : mappedStage)}
                    className="group flex flex-col items-center cursor-pointer"
                  >
                    <div
                      style={{ width: `${widthPct}%` }}
                      className={`flex items-center justify-between px-3 py-1.5 rounded-xl border transition-all ${
                        isSelected
                          ? 'border-[#0d9488] bg-[#f0fdfa] ring-2 ring-[#0d9488]/20 shadow-2xs'
                          : `${colors.border} ${colors.bg} hover:border-[#0d9488]/50 hover:shadow-2xs`
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: colors.bar }} />
                        <span className="text-xs font-bold text-[#0f172a]">{step.label}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mono text-xs">
                        <strong className="text-[#0f172a]">{step.count}</strong>
                        <span className="text-[#64748b] text-[10px]">({step.pct}%)</span>
                      </div>
                    </div>
                    {idx < arr.length - 1 && (
                      <ArrowDown className="w-2.5 h-2.5 text-[#cbd5e1] my-0.5" />
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            /* SVG Trend Chart */
            <div className="relative w-full overflow-hidden flex justify-center">
              <svg
                viewBox={`0 0 ${trendWidth} ${trendHeight}`}
                className="w-full h-[120px] overflow-visible"
              >
                {/* Gridlines */}
                <line
                  x1={padding.left}
                  y1={padding.top}
                  x2={trendWidth - padding.right}
                  y2={padding.top}
                  stroke="#e2e8f0"
                  strokeDasharray="3 3"
                />
                <line
                  x1={padding.left}
                  y1={padding.top + graphHeight / 2}
                  x2={trendWidth - padding.right}
                  y2={padding.top + graphHeight / 2}
                  stroke="#e2e8f0"
                  strokeDasharray="3 3"
                />
                <line
                  x1={padding.left}
                  y1={padding.top + graphHeight}
                  x2={trendWidth - padding.right}
                  y2={padding.top + graphHeight}
                  stroke="#cbd5e1"
                />

                {/* Open Cases Subtle Line */}
                <path
                  d={openCasesPath}
                  fill="none"
                  stroke="#818cf8"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                  opacity="0.6"
                />

                {/* Resolved Cases Line (Mint) */}
                <path
                  d={resolvedCasesPath}
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* New Cases Line (Cyan) */}
                <path
                  d={newCasesPath}
                  fill="none"
                  stroke="#0ea5e9"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Interactive Points on Trend */}
                {trend.map((pt, i) => (
                  <g key={pt.cut}>
                    <circle
                      cx={getX(i)}
                      cy={getY(pt.resolvedCases)}
                      r={hoveredTrendPoint?.cut === pt.cut ? 4.5 : 2.5}
                      fill="#10b981"
                      className="cursor-pointer transition-all"
                      onMouseEnter={() => setHoveredTrendPoint(pt)}
                      onMouseLeave={() => setHoveredTrendPoint(null)}
                    />
                    <circle
                      cx={getX(i)}
                      cy={getY(pt.newCases)}
                      r={hoveredTrendPoint?.cut === pt.cut ? 4.5 : 2.5}
                      fill="#0ea5e9"
                      className="cursor-pointer transition-all"
                      onMouseEnter={() => setHoveredTrendPoint(pt)}
                      onMouseLeave={() => setHoveredTrendPoint(null)}
                    />
                  </g>
                ))}

                {/* X Axis Labels */}
                <text
                  x={getX(0)}
                  y={trendHeight - 3}
                  fill="#64748b"
                  fontSize="9"
                  fontFamily="DM Mono, monospace"
                  textAnchor="middle"
                >
                  Cut 1
                </text>
                <text
                  x={getX(5)}
                  y={trendHeight - 3}
                  fill="#64748b"
                  fontSize="9"
                  fontFamily="DM Mono, monospace"
                  textAnchor="middle"
                >
                  Cut 6
                </text>
                <text
                  x={getX(11)}
                  y={trendHeight - 3}
                  fill="#64748b"
                  fontSize="9"
                  fontFamily="DM Mono, monospace"
                  textAnchor="middle"
                >
                  Cut 12
                </text>
              </svg>
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="pt-2 border-t border-[#f1f5f9]">
          {card3Tab === 'funnel' ? (
            <div className="flex items-center justify-between text-[10px] mono text-[#64748b]">
              <span>Click tier to filter</span>
              <span className="font-bold text-[#0d9488]">Selective: 1.5% human gate</span>
            </div>
          ) : hoveredTrendPoint ? (
            <div className="text-xs bg-[#f8fafc] border border-[#e2e8f0] p-1.5 rounded-lg flex items-center justify-between">
              <span className="mono font-bold text-[#0f172a]">{hoveredTrendPoint.cutLabel}:</span>
              <span className="text-[#0284c7] font-semibold">{hoveredTrendPoint.newCases} new</span>
              <span className="text-[#059669] font-semibold">{hoveredTrendPoint.resolvedCases} res</span>
              <span className="text-[#6366f1] font-semibold">{hoveredTrendPoint.openCases} open</span>
            </div>
          ) : (
            <div className="flex items-center justify-between text-xs mono text-[#64748b]">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#0ea5e9]" />
                <span>New</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#10b981]" />
                <span>Resolved</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#818cf8]" />
                <span>Monitored</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
