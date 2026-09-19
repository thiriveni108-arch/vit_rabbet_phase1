import React from 'react';
import { Filter, ArrowDown, Sparkles } from 'lucide-react';
import { ReviewFunnelStep, ReviewStage } from '../../lib/reviewApi';

interface ReviewFunnelProps {
  funnel?: ReviewFunnelStep[];
  activeFilter?: string;
  onSelectStage?: (stage: ReviewStage | 'all') => void;
}

export const ReviewFunnel: React.FC<ReviewFunnelProps> = ({
  funnel,
  activeFilter,
  onSelectStage,
}) => {
  const defaultFunnel: ReviewFunnelStep[] = [
    { stage: 'detected', label: 'Detected Findings', count: 202, sub: 'Surveillance intake', pct: 100 },
    { stage: 'medical_review', label: 'Medically Relevant', count: 64, sub: 'Safety & criteria verified', pct: 31.7 },
    { stage: 'action_monitoring', label: 'Action / Monitoring', count: 18, sub: 'Queries & auto-monitored', pct: 8.9 },
    { stage: 'human_gate', label: 'Human Gate Escalations', count: 3, sub: 'Medical Monitor review', pct: 1.5 },
  ];

  const steps = funnel && funnel.length > 0 ? funnel : defaultFunnel;

  const stageColors: Record<string, { bg: string; border: string; text: string; fill: string }> = {
    detected: { bg: 'bg-[#f0f9ff]', border: 'border-[#bae6fd]', text: 'text-[#0369a1]', fill: '#0ea5e9' },
    medical_review: { bg: 'bg-[#faf5ff]', border: 'border-[#ddd6fe]', text: 'text-[#6d28d9]', fill: '#8b5cf6' },
    medically_relevant: { bg: 'bg-[#faf5ff]', border: 'border-[#ddd6fe]', text: 'text-[#6d28d9]', fill: '#8b5cf6' },
    action_monitoring: { bg: 'bg-[#f8fafc]', border: 'border-[#cbd5e1]', text: 'text-[#334155]', fill: '#64748b' },
    human_gate: { bg: 'bg-[#fffbeb]', border: 'border-[#fde68a]', text: 'text-[#b45309]', fill: '#f59e0b' },
    human_escalation: { bg: 'bg-[#fffbeb]', border: 'border-[#fde68a]', text: 'text-[#b45309]', fill: '#f59e0b' },
  };

  return (
    <div className="rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#0d9488]" />
            <h3 className="mono text-[11px] font-bold uppercase tracking-[.18em] text-[#0f172a]">
              Review Funnel
            </h3>
          </div>
          <span className="mono text-[10px] text-[#0f766e] font-bold bg-[#f0fdfa] px-2 py-0.5 rounded border border-[#99f6e4]">
            Selective Escalation
          </span>
        </div>
        <p className="text-xs text-[#64748b] mb-4">
          How findings are narrowed into human decisions — only 1.5% reach Medical Monitor
        </p>

        {/* Funnel Steps */}
        <div className="space-y-2">
          {steps.map((step, idx) => {
            const mappedStage = step.stage === 'medically_relevant' ? 'medical_review' : step.stage === 'human_escalation' ? 'human_gate' : step.stage;
            const style = stageColors[step.stage] || stageColors['detected'];
            const isSelected = activeFilter === mappedStage;

            // Width scaling: 100% down to 38%
            const widthPct = Math.max(38, 100 - idx * 20);

            return (
              <div
                key={step.stage}
                onClick={() => onSelectStage?.(mappedStage as ReviewStage)}
                className="group flex flex-col items-center cursor-pointer"
              >
                <div
                  style={{ width: `${widthPct}%` }}
                  className={`flex items-center justify-between px-3.5 py-2 rounded-xl border transition-all ${
                    isSelected
                      ? 'border-[#0d9488] bg-[#f0fdfa] ring-2 ring-[#0d9488]/20 shadow-xs'
                      : `${style.border} ${style.bg} hover:border-[#0d9488]/50 hover:shadow-xs`
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full`} style={{ backgroundColor: style.fill }} />
                    <span className="text-xs font-bold text-[#0f172a]">{step.label}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="mono text-xs font-bold text-[#0f172a]">{step.count}</span>
                    <span className="mono text-[10px] text-[#64748b] font-medium">
                      ({step.pct}%)
                    </span>
                  </div>
                </div>

                {idx < steps.length - 1 && (
                  <ArrowDown className="w-3 h-3 text-[#cbd5e1] my-0.5" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mono text-[10px] text-[#64748b] pt-3 border-t border-[#f1f5f9] mt-3 flex items-center justify-between">
        <span>Click any tier to filter case queue</span>
        <span className="text-[#0d9488] font-bold">Zero alert fatigue</span>
      </div>
    </div>
  );
};
