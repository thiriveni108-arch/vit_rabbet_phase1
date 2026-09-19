import React from 'react';
import { ArrowRight, AlertTriangle, MessageSquare, ShieldAlert, HeartPulse, Sparkles } from 'lucide-react';
import { ReviewCase, EvidenceReadinessType } from '../../lib/reviewApi';

interface NeedsAttentionPanelProps {
  cases: ReviewCase[];
  onSelectCase: (caseItem: ReviewCase) => void;
  selectedCaseId?: string;
}

export const NeedsAttentionPanel: React.FC<NeedsAttentionPanelProps> = ({
  cases,
  onSelectCase,
  selectedCaseId,
}) => {
  const actionableCases = cases.slice(0, 4);

  const getBadgeStyle = (category: string) => {
    switch (category) {
      case 'safety':
        return {
          label: 'SERIOUS EVENT',
          badgeClass: 'bg-[#fff1f2] text-[#9f1239] border-[#fecdd3]',
          icon: <HeartPulse className="w-3.5 h-3.5 text-[#e11d48]" />,
          buttonText: 'Review →',
        };
      case 'data_quality':
        return {
          label: 'SITE QUERY',
          badgeClass: 'bg-[#f0fdfa] text-[#0f766e] border-[#99f6e4]',
          icon: <MessageSquare className="w-3.5 h-3.5 text-[#0d9488]" />,
          buttonText: 'Open case →',
        };
      case 'compliance':
        return {
          label: 'COMPLIANCE',
          badgeClass: 'bg-[#eef2ff] text-[#4338ca] border-[#c7d2fe]',
          icon: <ShieldAlert className="w-3.5 h-3.5 text-[#6366f1]" />,
          buttonText: 'Assess →',
        };
      default:
        return {
          label: 'ATTENTION',
          badgeClass: 'bg-[#fffbeb] text-[#92400e] border-[#fde68a]',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-[#d97706]" />,
          buttonText: 'Review →',
        };
    }
  };

  const renderReadiness = (readiness?: EvidenceReadinessType) => {
    switch (readiness) {
      case 'READY_FOR_REVIEW':
        return <span className="mono text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0]">READY</span>;
      case 'NEEDS_CLARIFICATION':
        return <span className="mono text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#fffbeb] text-[#92400e] border border-[#fde68a]">CLARIFY</span>;
      case 'WAITING_FOR_SITE':
        return <span className="mono text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#f0fdfa] text-[#0f766e] border border-[#99f6e4]">WAITING SITE</span>;
      case 'EVIDENCE_INCOMPLETE':
        return <span className="mono text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#fff1f2] text-[#9f1239] border border-[#fecdd3]">INCOMPLETE</span>;
      case 'MONITORING':
        return <span className="mono text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#faf5ff] text-[#6d28d9] border border-[#ddd6fe]">MONITORING</span>;
      case 'RESOLVED':
        return <span className="mono text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#f0fdf4] text-[#15803d] border border-[#86efac]">RESOLVED</span>;
      default:
        return <span className="mono text-[9px] font-bold px-1.5 py-0.2 rounded bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0]">READY</span>;
    }
  };

  return (
    <div className="flex flex-col h-full rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl">
      <div className="flex items-center justify-between mb-3 px-0.5 border-b border-[#e2e8f0] pb-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#f59e0b] animate-pulse" />
          <h3 className="mono text-[11px] font-bold uppercase tracking-[.18em] text-[#0f172a]">
            Needs Attention
          </h3>
        </div>
        <span className="mono text-[10px] text-[#92400e] font-semibold bg-[#fffbeb] px-2 py-0.5 rounded border border-[#fde68a]">
          {cases.length} Actionable
        </span>
      </div>

      <div className="flex-1 flex flex-col justify-between space-y-2.5">
        {actionableCases.map((c) => {
          const style = getBadgeStyle(c.category);
          const isSelected = selectedCaseId === c.id;

          return (
            <div
              key={c.id}
              onClick={() => onSelectCase(c)}
              className={`group relative flex flex-col justify-between p-3.5 rounded-xl border transition-all cursor-pointer ${
                isSelected
                  ? 'border-[#0d9488] bg-[#f0fdfa] ring-2 ring-[#0d9488]/20 shadow-xs'
                  : 'border-[#e2e8f0] bg-white hover:border-[#0d9488]/40 hover:bg-[#f8fafc] hover:shadow-xs'
              }`}
            >
              {/* Row 1: Badge + Readiness + Subject / Site */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] mono font-bold border ${style.badgeClass}`}
                  >
                    {style.icon}
                    {style.label}
                  </span>
                  {renderReadiness(c.evidenceReadiness)}
                </div>
                <span className="mono text-[11px] text-[#64748b]">
                  <strong className="text-[#0f172a] font-semibold">{c.usubjid}</strong> · Site {c.siteId}
                </span>
              </div>

              {/* Row 2: Plain language description */}
              <div className="mt-2 text-xs font-semibold text-[#0f172a] group-hover:text-[#0d9488] transition leading-snug">
                {c.whatHappened.summary}
              </div>

              {/* Row 3: Status & Action CTA */}
              <div className="mt-2.5 flex items-center justify-between text-[11px]">
                <span className="text-[#64748b] font-medium">
                  {c.stage === 'human_gate'
                    ? 'Human decision required'
                    : c.category === 'data_quality'
                    ? 'Waiting for site response'
                    : 'Awaiting clinical review'}
                </span>

                <button
                  type="button"
                  className="inline-flex items-center gap-1 font-semibold text-[#0d9488] group-hover:text-[#0f766e] transition"
                >
                  <span>{style.buttonText}</span>
                </button>
              </div>
            </div>
          );
        })}

        {cases.length === 0 && (
          <div className="flex flex-col items-center justify-center p-8 text-center text-[#64748b]">
            <Sparkles className="w-8 h-8 text-[#10b981]/50 mb-2" />
            <p className="text-xs text-[#64748b]">All high-priority items resolved.</p>
          </div>
        )}
      </div>
    </div>
  );
};
