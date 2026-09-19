import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Shield,
  HeartPulse,
  Database,
  ClipboardCheck,
  Building,
  UserCheck,
  MessageSquare,
  FileCheck,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  Sparkles,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Terminal,
  Check,
  Maximize2,
  Info
} from 'lucide-react';
import { ReviewCase, HumanDecisionType, CaseCategory, EvidenceReadinessType } from '../../lib/reviewApi';

interface CaseStoryDrawerProps {
  caseItem: ReviewCase | null;
  onClose: () => void;
  onDecisionSubmit?: (caseId: string, decision: HumanDecisionType, note?: string) => void;
  onFocusCase?: (caseItem: ReviewCase) => void;
}

export const CaseStoryDrawer: React.FC<CaseStoryDrawerProps> = ({
  caseItem,
  onClose,
  onDecisionSubmit,
  onFocusCase,
}) => {
  const [decision, setDecision] = useState<HumanDecisionType>('AWAITING');
  const [clarifyState, setClarifyState] = useState<'idle' | 'checking' | 'ready' | 'approved'>('idle');
  const [rejectReason, setRejectReason] = useState<string>('');
  const [showRejectInput, setShowRejectInput] = useState<boolean>(false);
  const [showRawTrace, setShowRawTrace] = useState<boolean>(false);

  // Sync state when caseItem changes
  useEffect(() => {
    if (caseItem) {
      setDecision(caseItem.decisionStatus);
      setClarifyState('idle');
      setShowRejectInput(false);
      setShowRawTrace(false);
      setRejectReason(caseItem.humanGate?.decisionReason || '');
    }
  }, [caseItem]);

  if (!caseItem) return null;

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
      'Clarification confirmed from Patient 360 baseline: Screening ALT normal, no concomitant hepatotoxins. Safety review completed.'
    );
  };

  const handleConfirmReject = () => {
    const reason = rejectReason.trim() || 'Baseline clinical factors established; event under local observation without safety escalation.';
    setDecision('REJECTED');
    setShowRejectInput(false);
    onDecisionSubmit?.(caseItem.id, 'REJECTED', reason);
  };

  const getCategoryIcon = (category: CaseCategory) => {
    switch (category) {
      case 'safety':
        return <HeartPulse className="w-4 h-4 text-[#e11d48]" />;
      case 'data_quality':
        return <Database className="w-4 h-4 text-[#0284c7]" />;
      case 'compliance':
        return <ClipboardCheck className="w-4 h-4 text-[#6366f1]" />;
      case 'site_pattern':
        return <Building className="w-4 h-4 text-[#d97706]" />;
      default:
        return <Shield className="w-4 h-4 text-[#0d9488]" />;
    }
  };

  const getReadinessBadge = (readiness?: EvidenceReadinessType) => {
    switch (readiness) {
      case 'READY_FOR_REVIEW':
        return <span className="mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0]">✓ READY FOR REVIEW</span>;
      case 'NEEDS_CLARIFICATION':
        return <span className="mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#fffbeb] text-[#92400e] border border-[#fde68a]">NEEDS CLARIFICATION</span>;
      case 'WAITING_FOR_SITE':
        return <span className="mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#f0fdfa] text-[#0f766e] border border-[#99f6e4]">WAITING FOR SITE</span>;
      case 'EVIDENCE_INCOMPLETE':
        return <span className="mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#fff1f2] text-[#9f1239] border border-[#fecdd3]">EVIDENCE INCOMPLETE</span>;
      case 'MONITORING':
        return <span className="mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#faf5ff] text-[#6d28d9] border border-[#ddd6fe]">MONITORING</span>;
      case 'RESOLVED':
        return <span className="mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#f0fdf4] text-[#15803d] border border-[#86efac]">RESOLVED</span>;
      default:
        return <span className="mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0]">✓ READY FOR REVIEW</span>;
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex justify-end">
        {/* Soft Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-slate-900/35 backdrop-blur-xs transition-opacity"
        />

        {/* Drawer panel (40% desktop width) */}
        <motion.aside
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 28, stiffness: 280 }}
          className="relative z-50 flex flex-col w-full max-w-[620px] h-full bg-white border-l border-[#cbd5e1] shadow-2xl text-[#0f172a] overflow-y-auto"
        >
          {/* Top Sticky Header */}
          <div className="sticky top-0 z-20 flex items-start justify-between p-6 border-b border-[#e2e8f0] bg-white/95 backdrop-blur-md">
            <div>
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className="mono text-[11px] font-bold tracking-wider px-2 py-0.5 rounded bg-[#ecfeff] text-[#0e7490] border border-[#a5f3fc]">
                  {caseItem.caseNumber}
                </span>
                <span className="mono text-[11px] text-[#64748b]">
                  Subject <strong className="text-[#0f172a]">{caseItem.usubjid}</strong>
                </span>
                <span className="text-[#cbd5e1]">·</span>
                <span className="mono text-[11px] text-[#64748b]">
                  Site <strong className="text-[#0f172a]">{caseItem.siteId}</strong>
                </span>
              </div>
              <h2 className="text-lg font-bold text-[#0f172a] tracking-tight flex items-center gap-2">
                {getCategoryIcon(caseItem.category)}
                <span>{caseItem.title}</span>
              </h2>

              {/* Status Pill */}
              <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                <span className="text-xs text-[#64748b]">Status:</span>
                {decision === 'AWAITING' && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#fffbeb] text-[#92400e] border border-[#fde68a]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] animate-pulse" />
                    AWAITING HUMAN DECISION
                  </span>
                )}
                {decision === 'APPROVED' && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#f0fdf4] text-[#15803d] border border-[#bbf7d0]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />
                    APPROVED · ACTION EXECUTED
                  </span>
                )}
                {decision === 'REJECTED' && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#fff1f2] text-[#be123c] border border-[#fecdd3]">
                    <AlertCircle className="w-3.5 h-3.5 text-[#f43f5e]" />
                    REJECTED · MONITORING
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {/* Focus Case Button */}
              {onFocusCase && (
                <button
                  onClick={() => onFocusCase(caseItem)}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-[#cbd5e1] bg-white text-xs font-bold text-[#0f172a] hover:bg-slate-50 transition shadow-2xs"
                  title="Expand into distraction-free Case Focus Mode"
                >
                  <Maximize2 className="w-3.5 h-3.5 text-[#0d9488]" />
                  <span>Focus case</span>
                </button>
              )}

              <button
                onClick={onClose}
                className="p-2 rounded-xl text-[#64748b] hover:text-[#0f172a] hover:bg-[#f1f5f9] transition"
                aria-label="Close Case Story"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Drawer Body Content */}
          <div className="p-6 space-y-6 flex-1">
            {/* ==================================================== */}
            {/* EVIDENCE READINESS & "WHY IS THIS WAITING?" */}
            {/* ==================================================== */}
            <section className="rounded-xl border border-[#e2e8f0] bg-white p-4 space-y-2 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="mono text-[10px] font-bold text-[#64748b] uppercase tracking-wider">
                  Evidence Readiness
                </span>
                {getReadinessBadge(caseItem.evidenceReadiness)}
              </div>
              <div className="flex items-start gap-2 pt-1 text-xs text-[#334155]">
                <Info className="w-4 h-4 text-[#0d9488] shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  "{caseItem.readinessReason || 'All required clinical supporting records are available for human adjudication.'}"
                </p>
              </div>
            </section>

            {/* ==================================================== */}
            {/* SECTION 1: WHAT HAPPENED */}
            {/* ==================================================== */}
            <section className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-4.5 space-y-3.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <h3 className="mono text-[10px] font-bold uppercase tracking-[.18em] text-[#0e7490]">
                  What Happened
                </h3>
                <span className="mono text-[10px] text-[#64748b]">Cut {caseItem.cut}</span>
              </div>

              <p className="text-[13.5px] leading-relaxed text-[#0f172a] font-semibold">
                "{caseItem.whatHappened.summary}"
              </p>

              {/* Structured Facts Matrix (No JSON) */}
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                {caseItem.whatHappened.facts.map((fact, idx) => (
                  <div
                    key={idx}
                    className={`rounded-lg p-2.5 border transition ${
                      fact.highlight
                        ? 'border-[#fde68a] bg-[#fffbeb] text-[#92400e]'
                        : 'border-[#e2e8f0] bg-white text-[#334155]'
                    }`}
                  >
                    <div className="text-[10px] mono text-[#64748b] uppercase tracking-wider">
                      {fact.label}
                    </div>
                    <div className="text-xs font-bold mt-0.5 text-[#0f172a]">
                      {fact.value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Protocol Rule callout */}
              <div className="rounded-lg border border-[#a5f3fc] bg-[#ecfeff] p-3 text-xs text-[#0e7490] leading-relaxed flex items-start gap-2.5">
                <FileCheck className="w-4 h-4 text-[#0891b2] shrink-0 mt-0.5" />
                <span>{caseItem.whatHappened.protocolRule}</span>
              </div>
            </section>

            {/* ==================================================== */}
            {/* SECTION 2: WHY IT MATTERS */}
            {/* ==================================================== */}
            <section className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-4.5 space-y-2 shadow-2xs">
              <h3 className="mono text-[10px] font-bold uppercase tracking-[.18em] text-[#6d28d9]">
                Why It Matters
              </h3>
              <p className="text-xs leading-relaxed text-[#334155]">
                {caseItem.whyItMatters}
              </p>
            </section>

            {/* ==================================================== */}
            {/* SECTION 3: DECISION JOURNEY TIMELINE (LIVE TRACE) */}
            {/* ==================================================== */}
            <section className="rounded-xl border border-[#e2e8f0] bg-white p-4.5 space-y-4 shadow-2xs">
              <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-2.5">
                <h3 className="mono text-[10px] font-bold uppercase tracking-[.18em] text-[#0f172a]">
                  Decision Journey
                </h3>
                <span className="mono text-[10px] text-[#0f766e] font-bold flex items-center gap-1.5 bg-[#f0fdfa] px-2 py-0.5 rounded border border-[#99f6e4]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" />
                  LIVE DECISION TRACE
                </span>
              </div>

              {/* Vertical Timeline */}
              <div className="relative pl-6 space-y-5 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-200">
                {caseItem.journey.map((step, idx) => (
                  <div key={idx} className="relative group">
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
            </section>

            {/* ==================================================== */}
            {/* HUMAN GATE DECISION MODULE */}
            {/* ==================================================== */}
            <section className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-5 space-y-4 shadow-xs">
              <div className="flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-[#d97706]" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#0f172a]">
                  What should happen next?
                </h3>
              </div>

              {/* If in normal review state */}
              {clarifyState === 'idle' && !showRejectInput && (
                <div className="grid grid-cols-3 gap-2.5 pt-1">
                  <button
                    onClick={handleApprove}
                    className={`px-3 py-2.5 rounded-xl text-xs font-bold border transition flex flex-col items-center justify-center gap-1.5 text-center ${
                      decision === 'APPROVED'
                        ? 'bg-[#ecfdf5] border-[#10b981] text-[#065f46] ring-2 ring-[#10b981]/20 shadow-xs'
                        : 'bg-white border-[#bbf7d0] text-[#15803d] hover:bg-[#f0fdf4] hover:border-[#10b981] shadow-2xs'
                    }`}
                  >
                    <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
                    <span>APPROVE</span>
                  </button>

                  <button
                    onClick={handleStartClarify}
                    className="px-3 py-2.5 rounded-xl text-xs font-bold border border-[#fde68a] bg-white text-[#b45309] hover:bg-[#fffbeb] hover:border-[#f59e0b] transition flex flex-col items-center justify-center gap-1.5 text-center shadow-2xs"
                  >
                    <HelpCircle className="w-4 h-4 text-[#f59e0b]" />
                    <span>CLARIFY</span>
                  </button>

                  <button
                    onClick={() => setShowRejectInput(true)}
                    className={`px-3 py-2.5 rounded-xl text-xs font-bold border transition flex flex-col items-center justify-center gap-1.5 text-center ${
                      decision === 'REJECTED'
                        ? 'bg-[#fff1f2] border-[#f43f5e] text-[#9f1239] ring-2 ring-[#f43f5e]/20 shadow-xs'
                        : 'bg-white border-[#fecdd3] text-[#be123c] hover:bg-[#fff1f2] hover:border-[#f43f5e] shadow-2xs'
                    }`}
                  >
                    <AlertCircle className="w-4 h-4 text-[#f43f5e]" />
                    <span>REJECT</span>
                  </button>
                </div>
              )}

              {/* CLARIFY CONVERSATION FLOW */}
              {clarifyState !== 'idle' && (
                <div className="space-y-3.5 pt-1">
                  <div className="rounded-xl bg-white border border-[#fde68a] p-3.5 space-y-1.5 shadow-2xs">
                    <div className="flex items-center gap-2 text-[10px] mono font-bold text-[#b45309] uppercase tracking-wider">
                      <UserCheck className="w-3.5 h-3.5 text-[#d97706]" /> Medical Monitor Inquiry
                    </div>
                    <p className="text-xs text-[#0f172a] italic leading-relaxed">
                      "{caseItem.humanGate?.monitorQuestion || "What was this subject's screening ALT, and are they receiving any other liver-affecting medication?"}"
                    </p>
                  </div>

                  {clarifyState === 'checking' && (
                    <div className="rounded-xl bg-[#f0fdfa] border border-[#99f6e4] p-4 text-center space-y-2">
                      <div className="flex items-center justify-center gap-2 text-xs font-bold text-[#0f766e]">
                        <Sparkles className="w-4 h-4 text-[#0d9488] animate-spin" />
                        <span>ATLAS CHECKING PATIENT 360...</span>
                      </div>
                      <div className="w-full h-1.5 bg-[#ccfbf1] rounded-full overflow-hidden">
                        <div className="h-full bg-[#0d9488] rounded-full animate-[pulse_1s_infinite] w-3/4" />
                      </div>
                      <p className="text-[11px] text-[#64748b]">
                        Querying StudyGraph baseline labs & concomitant records...
                      </p>
                    </div>
                  )}

                  {(clarifyState === 'ready' || clarifyState === 'approved') && (
                    <motion.div
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-3"
                    >
                      <div className="space-y-2 rounded-xl bg-[#f0fdf4] border border-[#86efac] p-3.5 text-xs text-[#166534] shadow-2xs">
                        <div className="flex items-start gap-2">
                          <Check className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold text-[#0f172a]">Screening Baseline:</span>{' '}
                            {caseItem.humanGate?.clarifyTarget?.expectedValue || '0.27 µkat/L (0.29x ULN) — Normal reference range'}
                          </div>
                        </div>
                        <div className="flex items-start gap-2">
                          <Check className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold text-[#0f172a]">Concomitant Medications:</span>{' '}
                            {caseItem.humanGate?.clarifyTarget?.concomitantCheck || 'No relevant hepatotoxic medications found in CM dataset'}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        <span className="text-xs text-[#15803d] font-bold">
                          Clarification ready
                        </span>
                        {clarifyState === 'ready' && (
                          <button
                            onClick={handleResubmitToMonitor}
                            className="px-4 py-2 rounded-xl bg-[#0d9488] text-white font-bold text-xs hover:bg-[#0f766e] transition flex items-center gap-1.5 shadow-md shadow-[#0d9488]/20"
                          >
                            <span>Resubmit to monitor</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {clarifyState === 'approved' && (
                          <span className="mono text-xs text-[#15803d] font-bold flex items-center gap-1">
                            <CheckCircle2 className="w-4 h-4 text-[#10b981]" /> APPROVED BY MONITOR
                          </span>
                        )}
                      </div>
                    </motion.div>
                  )}
                </div>
              )}

              {/* REJECT INPUT FLOW */}
              {showRejectInput && (
                <div className="space-y-3 pt-1">
                  <div className="text-xs text-[#334155] font-semibold">
                    Please provide medical monitor rationale for rejection:
                  </div>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="e.g. Baseline transaminases were already elevated; monitor, do not escalate."
                    rows={2}
                    className="w-full rounded-xl bg-white border border-[#cbd5e1] p-2.5 text-xs text-[#0f172a] outline-none focus:border-[#f43f5e]"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setShowRejectInput(false)}
                      className="px-3 py-1.5 rounded-lg text-xs text-[#64748b] hover:text-[#0f172a]"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleConfirmReject}
                      className="px-4 py-1.5 rounded-xl bg-[#f43f5e] text-white font-bold text-xs hover:bg-[#e11d48] transition shadow-xs"
                    >
                      Confirm Rejection
                    </button>
                  </div>
                </div>
              )}

              {/* REJECTED EXPLANATION NOTE WITH MEMORY BLOCK */}
              {decision === 'REJECTED' && (
                <div className="rounded-xl bg-white border border-[#cbd5e1] p-3 space-y-1 text-xs text-[#334155]">
                  <div className="font-bold text-[#0f172a]">
                    REJECTED → MONITORING
                  </div>
                  <div className="text-xs text-[#64748b]">
                    Reason: {rejectReason || caseItem.humanGate?.decisionReason || 'Local observation recommended.'}
                  </div>
                  <p className="text-[11px] text-[#0f766e] font-semibold pt-1">
                    ✓ Automatic re-escalation blocked by ReviewMemory.
                  </p>
                </div>
              )}

              {/* APPROVED ACTION SUMMARY */}
              {decision === 'APPROVED' && (
                <div className="rounded-xl bg-[#f0fdf4] border border-[#86efac] p-3 space-y-1 text-xs text-[#15803d]">
                  <div className="font-bold text-[#166534]">
                    Action Executed:
                  </div>
                  <p className="text-xs text-[#15803d]">
                    "{caseItem.humanGate?.executedAction || 'Expedited serious-event report initiated.'}"
                  </p>
                </div>
              )}
            </section>

            {/* ==================================================== */}
            {/* RAW DECISION TRACE */}
            {/* ==================================================== */}
            <div className="pt-2">
              <button
                onClick={() => setShowRawTrace(!showRawTrace)}
                className="flex items-center gap-1.5 text-xs mono text-[#64748b] hover:text-[#0f172a] transition"
              >
                <Terminal className="w-3.5 h-3.5 text-[#0d9488]" />
                <span>{showRawTrace ? 'Hide decision trace' : 'View decision trace'}</span>
                {showRawTrace ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              <AnimatePresence>
                {showRawTrace && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-3 rounded-xl bg-[#f8fafc] border border-[#e2e8f0] p-3.5 text-[11px] mono text-[#334155] space-y-1.5 overflow-x-auto"
                  >
                    {caseItem.rawTrace && caseItem.rawTrace.length > 0 ? (
                      caseItem.rawTrace.map((entry, idx) => (
                        <div key={idx} className="flex items-start gap-2.5">
                          <span className="text-[#0284c7] font-semibold">{entry.timestamp}</span>
                          <span className="text-[#7c3aed] font-semibold">{entry.stage}</span>
                          <span className="text-[#0f172a] font-medium">{entry.action}:</span>
                          <span className="text-[#64748b]">{entry.detail}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-[#94a3b8]">No trace logs recorded.</div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </motion.aside>
      </div>
    </AnimatePresence>
  );
};
