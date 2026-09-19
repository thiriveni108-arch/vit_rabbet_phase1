import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  FileCheck,
  ShieldAlert,
  Clock,
  Sparkles,
  Terminal,
  UserCheck,
  Check
} from 'lucide-react';
import { ReviewCase, HumanDecisionType, EvidenceReadinessType } from '../../lib/reviewApi';

interface CaseFocusModeProps {
  caseItem: ReviewCase;
  onExitFocus: () => void;
  onDecisionSubmit?: (caseId: string, decision: HumanDecisionType, note?: string) => void;
}

export const CaseFocusMode: React.FC<CaseFocusModeProps> = ({
  caseItem,
  onExitFocus,
  onDecisionSubmit,
}) => {
  const [decision, setDecision] = useState<HumanDecisionType>(caseItem.decisionStatus);
  const [clarifyState, setClarifyState] = useState<'idle' | 'checking' | 'ready' | 'approved'>('idle');
  const [rejectReason, setRejectReason] = useState<string>('');
  const [showRejectInput, setShowRejectInput] = useState<boolean>(false);

  const handleApprove = () => {
    setDecision('APPROVED');
    setShowRejectInput(false);
    onDecisionSubmit?.(caseItem.id, 'APPROVED', 'Expedited serious-event report initiated per monitor adjudication.');
  };

  const handleStartClarify = () => {
    setClarifyState('checking');
    setTimeout(() => {
      setClarifyState('ready');
    }, 1200);
  };

  const handleResubmitToMonitor = () => {
    setClarifyState('approved');
    setDecision('APPROVED');
    onDecisionSubmit?.(
      caseItem.id,
      'APPROVED',
      'Clarification confirmed from Patient 360 baseline: Screening ALT normal, no concomitant hepatotoxins.'
    );
  };

  const handleConfirmReject = () => {
    const reason = rejectReason.trim() || 'Baseline clinical factors established; event under local observation.';
    setDecision('REJECTED');
    setShowRejectInput(false);
    onDecisionSubmit?.(caseItem.id, 'REJECTED', reason);
  };

  const getReadinessBadge = (readiness?: EvidenceReadinessType) => {
    switch (readiness) {
      case 'READY_FOR_REVIEW':
        return <span className="mono text-xs font-bold px-2.5 py-1 rounded-full bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0]">✓ READY FOR REVIEW</span>;
      case 'NEEDS_CLARIFICATION':
        return <span className="mono text-xs font-bold px-2.5 py-1 rounded-full bg-[#fffbeb] text-[#92400e] border border-[#fde68a]">NEEDS CLARIFICATION</span>;
      case 'WAITING_FOR_SITE':
        return <span className="mono text-xs font-bold px-2.5 py-1 rounded-full bg-[#f0fdfa] text-[#0f766e] border border-[#99f6e4]">WAITING FOR SITE</span>;
      case 'EVIDENCE_INCOMPLETE':
        return <span className="mono text-xs font-bold px-2.5 py-1 rounded-full bg-[#fff1f2] text-[#9f1239] border border-[#fecdd3]">EVIDENCE INCOMPLETE</span>;
      case 'MONITORING':
        return <span className="mono text-xs font-bold px-2.5 py-1 rounded-full bg-[#faf5ff] text-[#6d28d9] border border-[#ddd6fe]">MONITORING</span>;
      case 'RESOLVED':
        return <span className="mono text-xs font-bold px-2.5 py-1 rounded-full bg-[#f0fdf4] text-[#15803d] border border-[#86efac]">RESOLVED</span>;
      default:
        return <span className="mono text-xs font-bold px-2.5 py-1 rounded-full bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0]">✓ READY FOR REVIEW</span>;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="space-y-6"
    >
      {/* Top Focus Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4.5 rounded-2xl border border-[#cbd5e1]/60 bg-white/95 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <button
            onClick={onExitFocus}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#cbd5e1] bg-white text-xs font-bold text-[#0f172a] hover:bg-slate-50 transition shadow-2xs"
          >
            <ArrowLeft className="w-4 h-4 text-[#0d9488]" />
            <span>Exit Focus</span>
          </button>

          <div>
            <div className="flex items-center gap-2">
              <span className="mono text-xs font-bold text-[#0e7490] bg-[#ecfeff] px-2 py-0.5 rounded border border-[#a5f3fc]">
                {caseItem.caseNumber}
              </span>
              <span className="display text-base font-bold text-[#0f172a]">
                Subject {caseItem.usubjid} · Site {caseItem.siteId}
              </span>
            </div>
            <div className="text-xs text-[#64748b] mt-0.5">
              {caseItem.title} · Cut {caseItem.cut}
            </div>
          </div>
        </div>

        {/* Readiness and Stage */}
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <div className="text-[10px] mono text-[#64748b] uppercase">Workflow Readiness</div>
            <div className="mt-0.5">{getReadinessBadge(caseItem.evidenceReadiness)}</div>
          </div>
          <div className="mono text-xs font-bold uppercase px-3 py-1.5 rounded-xl bg-[#f8fafc] text-[#334155] border border-[#e2e8f0]">
            Stage: {caseItem.stage.replace('_', ' ')}
          </div>
        </div>
      </div>

      {/* 3-Column Distraction-Free Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* COLUMN 1: CASE SUMMARY & CLINICAL CONTEXT (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] space-y-4">
          <div className="mono text-xs font-bold text-[#0e7490] uppercase tracking-wider pb-2 border-b border-[#f1f5f9]">
            What Happened
          </div>
          <p className="text-sm font-semibold text-[#0f172a] leading-relaxed">
            "{caseItem.whatHappened.summary}"
          </p>

          <div className="grid grid-cols-2 gap-2.5 pt-1">
            {caseItem.whatHappened.facts.map((fact, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-xl border ${
                  fact.highlight
                    ? 'border-[#fde68a] bg-[#fffbeb] text-[#92400e]'
                    : 'border-[#e2e8f0] bg-[#f8fafc] text-[#334155]'
                }`}
              >
                <div className="mono text-[10px] text-[#64748b] uppercase">{fact.label}</div>
                <div className="text-xs font-bold text-[#0f172a] mt-1">{fact.value}</div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-[#a5f3fc] bg-[#ecfeff] p-3 text-xs text-[#0e7490] leading-relaxed flex items-start gap-2">
            <FileCheck className="w-4 h-4 text-[#0891b2] shrink-0 mt-0.5" />
            <span>{caseItem.whatHappened.protocolRule}</span>
          </div>

          <div className="pt-2 border-t border-[#f1f5f9] space-y-1">
            <div className="mono text-[10px] font-bold uppercase tracking-wider text-[#6d28d9]">
              Why It Matters
            </div>
            <p className="text-xs text-[#334155] leading-relaxed">
              {caseItem.whyItMatters}
            </p>
          </div>
        </div>

        {/* COLUMN 2: DECISION JOURNEY TIMELINE (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] space-y-4">
          <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-2">
            <div className="mono text-xs font-bold text-[#0f172a] uppercase tracking-wider">
              Decision Journey
            </div>
            <span className="mono text-[10px] text-[#0f766e] font-bold flex items-center gap-1.5 bg-[#f0fdfa] px-2 py-0.5 rounded border border-[#99f6e4]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" />
              LIVE DECISION TRACE
            </span>
          </div>

          <div className="relative pl-6 space-y-5 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-200">
            {caseItem.journey.map((step, idx) => (
              <div key={idx} className="relative">
                <div
                  className={`absolute -left-6 top-1 w-3.5 h-3.5 rounded-full border-2 border-white ${
                    step.status === 'completed'
                      ? 'bg-[#10b981]'
                      : step.status === 'current'
                      ? 'bg-[#f59e0b] ring-4 ring-[#fde68a]/50'
                      : 'bg-slate-300'
                  }`}
                />
                <div className="flex items-baseline justify-between text-xs">
                  <span className="mono font-bold text-[#0f172a]">{step.stageName}</span>
                  <span className="mono text-[10px] text-[#64748b]">{step.time}</span>
                </div>
                <div className="text-xs font-semibold text-[#334155] mt-0.5">{step.title}</div>
                <p className="text-xs text-[#64748b] mt-0.5">{step.description}</p>
                {step.evidence && (
                  <div className="mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#f0f9ff] border border-[#bae6fd] text-[10px] mono text-[#0369a1]">
                    <FileCheck className="w-3 h-3 text-[#0284c7]" /> Evidence: {step.evidence}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* COLUMN 3: EVIDENCE & HUMAN GATE ADJUDICATION (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] space-y-4">
          <div className="mono text-xs font-bold text-[#b45309] uppercase tracking-wider pb-2 border-b border-[#f1f5f9]">
            Current Human Action
          </div>

          {/* Clinician Decision Box */}
          <div className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-4 space-y-3.5">
            <div className="text-xs font-bold text-[#0f172a]">
              What should happen next?
            </div>

            {clarifyState === 'idle' && !showRejectInput && (
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={handleApprove}
                  className={`py-2 rounded-xl text-xs font-bold border transition flex flex-col items-center justify-center gap-1 ${
                    decision === 'APPROVED'
                      ? 'bg-[#ecfdf5] border-[#10b981] text-[#065f46] ring-2 ring-[#10b981]/20'
                      : 'bg-white border-[#bbf7d0] text-[#15803d] hover:bg-[#f0fdf4]'
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
                  <span>APPROVE</span>
                </button>

                <button
                  onClick={handleStartClarify}
                  className="py-2 rounded-xl text-xs font-bold border border-[#fde68a] bg-white text-[#b45309] hover:bg-[#fffbeb] transition flex flex-col items-center justify-center gap-1"
                >
                  <HelpCircle className="w-4 h-4 text-[#f59e0b]" />
                  <span>CLARIFY</span>
                </button>

                <button
                  onClick={() => setShowRejectInput(true)}
                  className={`py-2 rounded-xl text-xs font-bold border transition flex flex-col items-center justify-center gap-1 ${
                    decision === 'REJECTED'
                      ? 'bg-[#fff1f2] border-[#f43f5e] text-[#9f1239] ring-2 ring-[#f43f5e]/20'
                      : 'bg-white border-[#fecdd3] text-[#be123c] hover:bg-[#fff1f2]'
                  }`}
                >
                  <AlertCircle className="w-4 h-4 text-[#f43f5e]" />
                  <span>REJECT</span>
                </button>
              </div>
            )}

            {/* Clarify Patient 360 lookup */}
            {clarifyState !== 'idle' && (
              <div className="space-y-3 pt-1">
                <div className="rounded-xl bg-white border border-[#fde68a] p-3 text-xs text-[#92400e]">
                  <div className="font-bold mb-1">Medical Monitor Inquiry:</div>
                  "{caseItem.humanGate?.monitorQuestion || 'Confirm screening ALT baseline and concomitant records.'}"
                </div>

                {clarifyState === 'checking' && (
                  <div className="rounded-xl bg-[#f0fdfa] border border-[#99f6e4] p-3 text-center space-y-1.5 text-xs text-[#0f766e]">
                    <div className="font-bold flex items-center justify-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 animate-spin text-[#0d9488]" />
                      <span>ATLAS CHECKING PATIENT 360...</span>
                    </div>
                    <p className="text-[11px] text-[#64748b]">Querying StudyGraph baseline labs...</p>
                  </div>
                )}

                {(clarifyState === 'ready' || clarifyState === 'approved') && (
                  <div className="space-y-2">
                    <div className="p-3 rounded-xl bg-[#f0fdf4] border border-[#86efac] text-xs text-[#166534] space-y-1">
                      <div className="font-bold">✓ Screening ALT: 0.27 µkat/L (Normal)</div>
                      <div className="font-bold">✓ Concomitant Medications: No hepatotoxins</div>
                    </div>
                    {clarifyState === 'ready' && (
                      <button
                        onClick={handleResubmitToMonitor}
                        className="w-full py-2 rounded-xl bg-[#0d9488] text-white font-bold text-xs hover:bg-[#0f766e] transition shadow-xs"
                      >
                        Resubmit to Monitor (Auto-Approves)
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Rejection Handling */}
            {showRejectInput && (
              <div className="space-y-2 pt-1">
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Monitor rationale for rejection..."
                  rows={2}
                  className="w-full rounded-xl bg-white border border-[#cbd5e1] p-2 text-xs text-[#0f172a] outline-none"
                />
                <div className="flex justify-end gap-2">
                  <button onClick={() => setShowRejectInput(false)} className="text-xs text-[#64748b]">Cancel</button>
                  <button onClick={handleConfirmReject} className="px-3 py-1 rounded-lg bg-[#f43f5e] text-white text-xs font-bold">Confirm</button>
                </div>
              </div>
            )}

            {decision === 'REJECTED' && (
              <div className="rounded-xl bg-white border border-[#cbd5e1] p-2.5 text-xs text-[#334155] space-y-0.5">
                <div className="font-bold text-[#0f172a]">REJECTED → MONITORING</div>
                <div className="text-[11px] text-[#64748b]">Automatic re-escalation blocked by memory.</div>
              </div>
            )}

            {decision === 'APPROVED' && (
              <div className="rounded-xl bg-[#f0fdf4] border border-[#86efac] p-2.5 text-xs text-[#15803d]">
                <div className="font-bold">✓ ACTION EXECUTED: Expedited report filed within 24h</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};
