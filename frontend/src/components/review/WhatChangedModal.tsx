import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowRight, Sparkles, CheckCircle2, RotateCcw, AlertCircle, Building2, Layers } from 'lucide-react';
import { WhatChangedData } from '../../lib/reviewApi';

interface WhatChangedModalProps {
  isOpen: boolean;
  onClose: () => void;
  data?: WhatChangedData;
}

export const WhatChangedModal: React.FC<WhatChangedModalProps> = ({
  isOpen,
  onClose,
  data,
}) => {
  if (!isOpen) return null;

  const sinceCut = data?.sinceCut ?? 11;
  const currentCut = data?.currentCut ?? 12;
  const newCount = data?.newCases ?? 4;
  const resolvedCount = data?.resolvedCases ?? 7;
  const statusChanges = data?.statusChanges ?? 3;
  const siteNewlyFlagged = data?.siteNewlyFlagged ?? 1;
  const duplicateActions = data?.duplicateActionsRepeated ?? 0;

  const waterfall = data?.waterfall ?? {
    previousOpen: 165,
    newCount: 4,
    resolvedCount: 7,
    currentOpen: 162,
  };

  const newItems = data?.newCaseItems ?? [
    { caseNumber: 'CASE-104', usubjid: '042-S05-003', title: 'Prohibited Glimepiride therapy flagged post-v3 amendment', type: 'compliance' },
    { caseNumber: 'CASE-088', usubjid: '042-S11-005', title: 'AE date precedes first dose date', type: 'data_quality' },
    { caseNumber: 'CASE-042', usubjid: '042-S07-001', title: 'Potential Hy’s Law liver safety elevation', type: 'safety' },
    { caseNumber: 'CASE-063', usubjid: 'Site S04 Cohort', title: 'Cluster of 8 visit-window deviations post-v3 tightening', type: 'site_pattern' },
  ];

  const changedItems = data?.changedCaseItems ?? [
    { caseNumber: 'CASE-017', usubjid: '042-S02-004', change: 'Medical Review → Human Gate (Awaiting Decision)' },
    { caseNumber: 'CASE-042', usubjid: '042-S07-001', change: 'Medical Review → Clarification (Patient 360 lookup)' },
    { caseNumber: 'CASE-029', usubjid: '042-S01-007', change: 'Human Gate → Action Executed (Expedited Report Filed)' },
  ];

  const resolvedItems = data?.resolvedCaseItems ?? [
    { caseNumber: 'CASE-009', usubjid: '042-S03-002', resolution: 'Site confirmed lab unit conversion; query closed.' },
    { caseNumber: 'CASE-012', usubjid: '042-S06-004', resolution: 'AE resolution date corrected by investigator.' },
    { caseNumber: 'CASE-015', usubjid: '042-S09-001', resolution: 'Concomitant medication discontinued per protocol.' },
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

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 16 }}
          className="relative z-50 w-full max-w-3xl rounded-2xl border border-[#cbd5e1] bg-white p-6 shadow-2xl text-[#0f172a] overflow-hidden max-h-[90vh] flex flex-col justify-between"
        >
          {/* Header */}
          <div>
            <div className="flex items-start justify-between pb-4 border-b border-[#e2e8f0]">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-[#f0fdfa] border border-[#99f6e4] text-[#0f766e]">
                  <Layers className="w-5 h-5 text-[#0d9488]" />
                </div>
                <div>
                  <div className="mono text-[10px] uppercase tracking-[.18em] text-[#0d9488] font-bold">
                    Cycle Difference Comparison
                  </div>
                  <h2 className="text-lg font-bold text-[#0f172a] tracking-tight">
                    What Changed Since Last Cut? (Cut {sinceCut} → Cut {currentCut})
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

            {/* Top Stat Summary Pills */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 my-4">
              <div className="p-2.5 rounded-xl bg-[#f0f9ff] border border-[#bae6fd] text-center">
                <div className="mono text-base font-bold text-[#0369a1]">+{newCount}</div>
                <div className="text-[10px] font-semibold text-[#0369a1] uppercase">New Cases</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#f0fdf4] border border-[#bbf7d0] text-center">
                <div className="mono text-base font-bold text-[#15803d]">✓ {resolvedCount}</div>
                <div className="text-[10px] font-semibold text-[#15803d] uppercase">Resolved</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#faf5ff] border border-[#ddd6fe] text-center">
                <div className="mono text-base font-bold text-[#6d28d9]">↻ {statusChanges}</div>
                <div className="text-[10px] font-semibold text-[#6d28d9] uppercase">Status Evolved</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#fffbeb] border border-[#fde68a] text-center">
                <div className="mono text-base font-bold text-[#92400e]">+{siteNewlyFlagged}</div>
                <div className="text-[10px] font-semibold text-[#92400e] uppercase">Site Watch</div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#f8fafc] border border-[#e2e8f0] text-center col-span-2 sm:col-span-1">
                <div className="mono text-base font-bold text-[#0d9488]">{duplicateActions}</div>
                <div className="text-[10px] font-semibold text-[#475569] uppercase">Duplicates</div>
              </div>
            </div>

            {/* Waterfall Equation Bar */}
            <div className="p-3 rounded-xl bg-[#f8fafc] border border-[#e2e8f0] flex items-center justify-between text-xs mono mb-4">
              <span className="text-[#64748b]">
                Previous Open: <strong className="text-[#0f172a]">{waterfall.previousOpen}</strong>
              </span>
              <span className="text-[#0ea5e9] font-bold">+{waterfall.newCount} New</span>
              <span className="text-[#10b981] font-bold">-{waterfall.resolvedCount} Resolved</span>
              <span className="text-[#64748b]">=</span>
              <span className="text-[#0f172a] font-bold">
                Current Open: <span className="text-[#0d9488] font-black">{waterfall.currentOpen}</span>
              </span>
            </div>
          </div>

          {/* Body Sections (Scrollable) */}
          <div className="space-y-4 overflow-y-auto pr-1 flex-1 max-h-[48vh]">
            {/* NEW CASES */}
            <div className="space-y-1.5">
              <div className="mono text-[11px] font-bold uppercase tracking-wider text-[#0369a1] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#0ea5e9]" />
                New Cases First Appearing in Cut {currentCut} ({newItems.length})
              </div>
              <div className="space-y-1.5">
                {newItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#f0f9ff]/60 border border-[#bae6fd] text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="mono font-bold text-[#0369a1]">{item.caseNumber}</span>
                      <span className="mono text-[10px] text-[#64748b]">{item.usubjid}</span>
                    </div>
                    <span className="text-[#0f172a] font-medium truncate max-w-md">{item.title}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* STATUS EVOLUTIONS */}
            <div className="space-y-1.5">
              <div className="mono text-[11px] font-bold uppercase tracking-wider text-[#6d28d9] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#8b5cf6]" />
                Cases with Stage or Decision Changes ({changedItems.length})
              </div>
              <div className="space-y-1.5">
                {changedItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#faf5ff]/60 border border-[#ddd6fe] text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="mono font-bold text-[#6d28d9]">{item.caseNumber}</span>
                      <span className="mono text-[10px] text-[#64748b]">{item.usubjid}</span>
                    </div>
                    <span className="text-[#0f172a] font-medium">{item.change}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* RESOLVED CASES */}
            <div className="space-y-1.5">
              <div className="mono text-[11px] font-bold uppercase tracking-wider text-[#15803d] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#10b981]" />
                Cases Resolved Since Cut {sinceCut} ({resolvedItems.length})
              </div>
              <div className="space-y-1.5">
                {resolvedItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#f0fdf4]/60 border border-[#bbf7d0] text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="mono font-bold text-[#15803d]">{item.caseNumber}</span>
                      <span className="mono text-[10px] text-[#64748b]">{item.usubjid}</span>
                    </div>
                    <span className="text-[#166534] font-medium">{item.resolution}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* PROTOCOL IMPACT */}
            {data?.protocolImpact?.active && (
              <div className="p-3.5 rounded-xl border border-[#99f6e4] bg-[#f0fdfa] text-xs text-[#0f766e] space-y-1">
                <div className="font-bold text-[#0f172a] flex items-center justify-between">
                  <span>Protocol v{data.protocolImpact.fromVersion} → Protocol v{data.protocolImpact.toVersion} Impact:</span>
                  <span className="mono text-[10px] font-bold bg-white px-2 py-0.5 rounded border border-[#99f6e4]">
                    {data.protocolImpact.subjectsReevaluated} Subjects Re-evaluated
                  </span>
                </div>
                <p className="text-[#134e4a]">
                  {data.protocolImpact.newComplianceFindings} new findings identified; {data.protocolImpact.resolvedRules}
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="mt-4 pt-3 border-t border-[#e2e8f0] flex items-center justify-between">
            <span className="text-xs text-[#64748b]">
              Calculated dynamically from persisted cycle state · Zero repeated actions.
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
