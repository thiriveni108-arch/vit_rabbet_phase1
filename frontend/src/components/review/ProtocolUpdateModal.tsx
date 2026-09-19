import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, AlertTriangle } from 'lucide-react';

interface ProtocolUpdateModalProps {
  isOpen: boolean;
  onClose: () => void;
  updateData?: {
    activeVersion: number;
    previousVersion: number;
    subjectsReevaluated: number;
    newFindingsIdentified: number;
    beforeRule: string;
    afterRule: string;
    changedCases: Array<{ subject: string; site: string; change: string }>;
  };
}

export const ProtocolUpdateModal: React.FC<ProtocolUpdateModalProps> = ({
  isOpen,
  onClose,
  updateData,
}) => {
  if (!isOpen) return null;

  const activeV = updateData?.activeVersion ?? 3;
  const prevV = updateData?.previousVersion ?? 2;
  const subjectsCount = updateData?.subjectsReevaluated ?? 23;
  const findingsCount = updateData?.newFindingsIdentified ?? 4;

  const defaultCases = updateData?.changedCases ?? [
    { subject: '042-S05-003', site: 'S05', change: 'Glimepiride (Sulfonylurea) flagged as prohibited concomitant therapy' },
    { subject: '042-S04-002', site: 'S04', change: 'Visit 5 recorded at +5 days flagged under narrowed ±3-day window' },
    { subject: '042-S04-006', site: 'S04', change: 'Visit 4 recorded at -4 days flagged under narrowed ±3-day window' },
    { subject: '042-S08-001', site: 'S08', change: 'Lab re-test window tightened from 72h to 48h; unconfirmed elevation queued' },
  ];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Soft Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        />

        {/* Modal Container (White Clinical Card) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 16 }}
          className="relative z-50 w-full max-w-2xl rounded-2xl border border-[#cbd5e1] bg-white p-6 shadow-2xl text-[#0f172a] overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-start justify-between pb-4 border-b border-[#e2e8f0]">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-[#ecfeff] border border-[#a5f3fc] text-[#0e7490]">
                <Sparkles className="w-5 h-5 text-[#0d9488]" />
              </div>
              <div>
                <div className="mono text-[10px] uppercase tracking-[.18em] text-[#0d9488] font-bold">
                  Protocol Amendment Re-Evaluation
                </div>
                <h2 className="text-base font-bold text-[#0f172a] tracking-tight">
                  Protocol v{prevV} → Protocol v{activeV} Transition
                </h2>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#64748b] hover:text-[#0f172a] hover:bg-[#f1f5f9] transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Stats Bar */}
          <div className="my-5 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-3">
              <div className="mono text-[10px] text-[#64748b] uppercase tracking-wider">
                Subjects Automatically Re-Evaluated
              </div>
              <div className="text-xl font-bold text-[#0f172a] mt-0.5">
                {subjectsCount} <span className="text-xs text-[#64748b] font-normal">participants</span>
              </div>
            </div>

            <div className="rounded-xl border border-[#fde68a] bg-[#fffbeb] p-3">
              <div className="mono text-[10px] text-[#b45309] uppercase tracking-wider">
                New Compliance Findings Identified
              </div>
              <div className="text-xl font-bold text-[#92400e] mt-0.5">
                {findingsCount} <span className="text-xs text-[#b45309]/80 font-normal">new deviations</span>
              </div>
            </div>
          </div>

          {/* Side-by-Side Comparison */}
          <div className="space-y-3">
            <div className="text-xs font-bold mono uppercase tracking-wider text-[#0f172a]">
              Rule Evolution Comparison
            </div>

            <div className="grid grid-cols-2 gap-3.5">
              {/* BEFORE */}
              <div className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="mono text-xs font-bold text-[#64748b]">BEFORE</span>
                  <span className="mono text-[10px] px-2 py-0.5 rounded bg-white text-[#475569] border border-[#cbd5e1] font-semibold">
                    Protocol v{prevV}
                  </span>
                </div>
                <div className="text-xs text-[#334155] font-semibold">
                  Status: Compliant baseline
                </div>
                <p className="text-xs text-[#64748b] leading-relaxed">
                  {updateData?.beforeRule ??
                    'Visit windows allowed ±7 calendar days. Sulfonylureas (glimepiride/glipizide) permitted with monitor notification.'}
                </p>
              </div>

              {/* AFTER */}
              <div className="rounded-xl border border-[#99f6e4] bg-[#f0fdfa] p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="mono text-xs font-bold text-[#0f766e]">AFTER</span>
                  <span className="mono text-[10px] px-2 py-0.5 rounded bg-white text-[#0f766e] border border-[#99f6e4] font-bold">
                    Protocol v{activeV} (Current)
                  </span>
                </div>
                <div className="text-xs text-[#0f766e] font-bold flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-[#d97706]" />
                  Newly Flagged Requirements
                </div>
                <p className="text-xs text-[#134e4a] leading-relaxed">
                  {updateData?.afterRule ??
                    'Visit window strictly narrowed to ±3 calendar days. All sulfonylureas strictly prohibited; causes immediate compliance deviation.'}
                </p>
              </div>
            </div>
          </div>

          {/* List of Affected Cases */}
          <div className="mt-5 space-y-2">
            <div className="text-xs font-bold mono uppercase tracking-wider text-[#0f172a]">
              Newly Flagged Compliance Findings
            </div>
            <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
              {defaultCases.map((c, idx) => (
                <div
                  key={idx}
                  className="flex items-start justify-between p-2.5 rounded-lg bg-[#f8fafc] border border-[#e2e8f0] text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="mono font-bold text-[#0e7490]">{c.subject}</span>
                    <span className="mono text-[10px] text-[#64748b]">Site {c.site}</span>
                  </div>
                  <span className="text-[#334155] text-right max-w-sm">{c.change}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-4 border-t border-[#e2e8f0] flex items-center justify-between">
            <span className="text-xs text-[#64748b]">
              All findings have been automatically routed to Stage 2 review queues.
            </span>
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-bold text-[#0f172a] transition"
            >
              Close Comparison
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
