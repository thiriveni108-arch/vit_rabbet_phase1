import React, { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldAlert,
  Sparkles,
  RefreshCw,
  HeartPulse,
  Database,
  ClipboardCheck,
  Building2,
  FileCheck,
  UserCheck,
  Layers,
  ArrowRight,
  Filter,
  ArrowUpDown,
  Download,
  CheckCircle2,
  FileText
} from 'lucide-react';
import { api } from '../lib/api';
import {
  getReviewCenterData,
  ReviewCenterData,
  ReviewCase,
  ReviewStage,
  CaseCategory,
  HumanDecisionType,
} from '../lib/reviewApi';
import { DecisionStream } from '../components/review/DecisionStream';
import { NeedsAttentionPanel } from '../components/review/NeedsAttentionPanel';
import { VisualSummaries } from '../components/review/VisualSummaries';
import { SitePulseMatrix } from '../components/review/SitePulseMatrix';
import { SystemMemoryPanel } from '../components/review/SystemMemoryPanel';
import { CaseStoryDrawer } from '../components/review/CaseStoryDrawer';
import { ProtocolUpdateModal } from '../components/review/ProtocolUpdateModal';
import { ReviewIntegrityStrip } from '../components/review/ReviewIntegrityStrip';
import { WhatChangedModal } from '../components/review/WhatChangedModal';
import { CaseFocusMode } from '../components/review/CaseFocusMode';

type ActiveTab = 'overview' | 'cases' | 'human_gate' | 'cycle_report';

export default function ReviewCenter() {
  const qc = useQueryClient();
  const { data: context } = useQuery({ queryKey: ['context'], queryFn: api.getContext });

  // Review Center dataset query
  const currentCut = context?.current_cut ?? 12;
  const { data: reviewData, isLoading, refetch } = useQuery<ReviewCenterData>({
    queryKey: ['reviewCenter', currentCut],
    queryFn: () => getReviewCenterData(currentCut),
  });

  // State management
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [selectedCase, setSelectedCase] = useState<ReviewCase | null>(null);
  const [activeStageFilter, setActiveStageFilter] = useState<ReviewStage | 'all'>('all');
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<CaseCategory | 'all'>('all');
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [caseFilterCategory, setCaseFilterCategory] = useState<string>('all');
  const [caseSortOrder, setCaseSortOrder] = useState<'attention' | 'newest' | 'oldest'>('attention');
  const [showProtocolModal, setShowProtocolModal] = useState<boolean>(false);
  const [focusedCase, setFocusedCase] = useState<ReviewCase | null>(null);
  const [showWhatChangedModal, setShowWhatChangedModal] = useState<boolean>(false);
  const [casesState, setCasesState] = useState<ReviewCase[]>([]);

  // Initialize cases from data
  useEffect(() => {
    if (reviewData?.cases) {
      setCasesState(reviewData.cases);
    }
  }, [reviewData]);

  // Cut mutation handler
  const cutMutation = useMutation({
    mutationFn: (cut: number) => api.setCut(cut),
    onSuccess: () => {
      qc.invalidateQueries();
      refetch();
    },
  });

  // Handle in-memory decisions
  const handleDecisionSubmit = (caseId: string, decision: HumanDecisionType, note?: string) => {
    setCasesState((prev) =>
      prev.map((c) => {
        if (c.id === caseId) {
          return {
            ...c,
            decisionStatus: decision,
            stage: 'action_monitoring',
            humanGate: {
              ...c.humanGate,
              decisionReason: note,
              requiredDecision: 'Adjudicated',
            },
          };
        }
        return c;
      })
    );
  };

  // Filtered cases for the main views
  const filteredCases = useMemo(() => {
    return casesState.filter((c) => {
      if (activeStageFilter !== 'all' && c.stage !== activeStageFilter) return false;
      if (activeCategoryFilter !== 'all' && c.category !== activeCategoryFilter) return false;
      if (selectedSiteId && c.siteId !== selectedSiteId) return false;
      return true;
    });
  }, [casesState, activeStageFilter, activeCategoryFilter, selectedSiteId]);

  // Human gate queue cases
  const humanGateCases = useMemo(() => {
    return casesState.filter((c) => c.stage === 'human_gate' || c.decisionStatus === 'AWAITING');
  }, [casesState]);

  // Selected Human Gate case (defaults to first in queue if none selected)
  const [humanGateSelectedId, setHumanGateSelectedId] = useState<string>('case-017');
  const activeHumanGateCase = useMemo(() => {
    return (
      humanGateCases.find((c) => c.id === humanGateSelectedId) ||
      humanGateCases[0] ||
      casesState[0]
    );
  }, [humanGateCases, humanGateSelectedId, casesState]);

  // Category Icon helper
  const getCategoryIcon = (category: CaseCategory) => {
    switch (category) {
      case 'safety':
        return <HeartPulse className="w-4 h-4 text-[#e11d48]" />;
      case 'data_quality':
        return <Database className="w-4 h-4 text-[#0284c7]" />;
      case 'compliance':
        return <ClipboardCheck className="w-4 h-4 text-[#6366f1]" />;
      case 'site_pattern':
        return <Building2 className="w-4 h-4 text-[#d97706]" />;
    }
  };

  if (isLoading || !reviewData) {
    return (
      <div className="flex min-h-[600px] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-7 w-7 animate-spin text-[#0d9488]" />
          <span className="mono text-xs text-[#64748b]">Loading Review Center Stream...</span>
        </div>
      </div>
    );
  }

  // Feature 2: Case Focus Mode (distraction-free workspace without navigating away)
  if (focusedCase) {
    return (
      <div className="relative min-h-screen pb-16 px-4 sm:px-6 lg:px-9 max-w-[1720px] mx-auto pt-4">
        <CaseFocusMode
          caseItem={focusedCase}
          onExitFocus={() => setFocusedCase(null)}
          onDecisionSubmit={handleDecisionSubmit}
        />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen pb-16 px-4 sm:px-6 lg:px-9 max-w-[1720px] mx-auto space-y-6">
      {/* ==================================================== */}
      {/* 1. HEADER / HERO (MATCHING COMMAND CENTER & STUDY GRAPH) */}
      {/* ==================================================== */}
      <header className="pt-4 pb-2 flex flex-col md:flex-row md:items-end md:justify-between gap-4 border-b border-[#e2e8f0]">
        <div>
          {/* Eyebrow */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className="mono text-[9px] font-bold uppercase tracking-[.22em] text-[#0f766e] bg-[#f0fdfa] px-2.5 py-0.5 rounded-full border border-[#99f6e4]">
              STAGE 2 · MONITOR
            </span>
            <span className="mono text-[11px] text-[#64748b]">Live Decision Stream</span>
          </div>

          {/* Title & Subtitle */}
          <h1 className="display text-2xl sm:text-[32px] font-bold tracking-[-0.04em] text-[#0f172a]">
            REVIEW CENTER
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-[#64748b] leading-relaxed">
            "From detection to decision — every case, every reason, every action."
          </p>
        </div>

        {/* Right Header Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Feature 1: What Changed Action Button */}
          <button
            onClick={() => setShowWhatChangedModal(true)}
            className="flex items-center gap-2 rounded-xl border border-[#0d9488]/40 bg-[#f0fdfa] px-3.5 py-1.5 shadow-2xs hover:bg-[#ccfbf1] hover:border-[#0d9488] transition text-xs font-bold text-[#0f766e] cursor-pointer"
            title="Inspect changes between current and previous cut"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#0d9488]" />
            <span>What changed?</span>
          </button>

          {/* Subtle Status Pill: "3 awaiting human review" */}
          <div className="flex items-center gap-2 rounded-xl border border-[#fde68a] bg-[#fffbeb] px-3 py-1.5 shadow-2xs">
            <span className="h-2 w-2 rounded-full bg-[#f59e0b] animate-pulse" />
            <span className="mono text-xs font-bold text-[#92400e]">
              {reviewData.awaitingHumanCount} awaiting human review
            </span>
          </div>

          {/* Cut Selector (Clean Light Glass Pill) */}
          <div className="flex items-center gap-2 rounded-xl border border-[#cbd5e1] bg-white px-3 py-1.5 shadow-xs">
            <span className="mono text-xs font-bold text-[#0d9488]">Cut</span>
            <select
              value={currentCut}
              onChange={(e) => cutMutation.mutate(Number(e.target.value))}
              disabled={cutMutation.isPending}
              className="cursor-pointer rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-2 py-0.5 mono text-xs font-bold text-[#0f172a] outline-none hover:border-[#0d9488] transition"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((c) => (
                <option key={c} value={c} className="bg-white text-[#0f172a]">
                  Cut {c} {c === 12 ? '(Latest)' : ''}
                </option>
              ))}
            </select>

            {/* Protocol Version */}
            <span className="mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#f1f5f9] text-[#475569] border border-[#e2e8f0]">
              Protocol v{reviewData.protocolVersion}
            </span>
          </div>
        </div>
      </header>

      {/* ==================================================== */}
      {/* 2. PROTOCOL UPDATE INFORMATIVE RIBBON (LIGHT GLASS) */}
      {/* ==================================================== */}
      {reviewData.protocolUpdate && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-2.5 rounded-xl border border-[#99f6e4] bg-gradient-to-r from-[#f0fdfa]/95 via-white to-[#f0f9ff]/95 shadow-xs"
        >
          <div className="flex items-center gap-2.5 text-xs text-[#134e4a] flex-wrap">
            <span className="mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4] uppercase tracking-wider">
              PROTOCOL UPDATE
            </span>
            <span className="font-bold text-[#0f172a]">
              Protocol v{reviewData.protocolUpdate.activeVersion} is now active.
            </span>
            <span className="text-[#cbd5e1]">·</span>
            <span className="text-[#334155]">
              <strong className="text-[#0d9488]">{reviewData.protocolUpdate.subjectsReevaluated}</strong> subjects were automatically re-evaluated.
            </span>
            <span className="text-[#cbd5e1]">·</span>
            <span className="text-[#b45309]">
              <strong className="text-[#b45309]">{reviewData.protocolUpdate.newFindingsIdentified}</strong> new compliance findings identified.
            </span>
          </div>

          <button
            onClick={() => setShowProtocolModal(true)}
            className="shrink-0 text-xs mono font-bold text-[#0d9488] hover:text-[#0f766e] flex items-center gap-1.5 transition underline underline-offset-4 decoration-[#5eead4] hover:decoration-[#0d9488]"
          >
            <span>See what changed</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </motion.div>
      )}

      {/* ==================================================== */}
      {/* 3. TABS (MATCHING STUDY GRAPH RHYTHM) */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-2">
        <div className="flex items-center gap-1.5 sm:gap-2">
          {[
            { id: 'overview', label: 'Overview', icon: Layers },
            { id: 'cases', label: 'Cases', count: filteredCases.length, icon: FileText },
            { id: 'human_gate', label: 'Human Gate', count: humanGateCases.length, icon: UserCheck },
            { id: 'cycle_report', label: 'Cycle Report', icon: FileCheck },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as ActiveTab)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? 'bg-white text-[#0f766e] border border-[#5eead4] shadow-xs font-bold'
                    : 'text-[#64748b] hover:text-[#0f172a] hover:bg-white/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#0d9488]' : 'text-[#64748b]'}`} />
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span
                    className={`mono text-[10px] px-1.5 py-0.2 rounded font-bold ${
                      isActive ? 'bg-[#f0fdfa] text-[#0f766e]' : 'bg-slate-100 text-[#64748b]'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Quick Filter Reset */}
        {(activeStageFilter !== 'all' || activeCategoryFilter !== 'all' || selectedSiteId) && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-[#64748b]">Active filters:</span>
            {activeStageFilter !== 'all' && (
              <span className="mono text-[10px] bg-[#f0fdfa] text-[#0f766e] px-2 py-0.5 rounded border border-[#99f6e4] font-semibold">
                Stage: {activeStageFilter}
              </span>
            )}
            {selectedSiteId && (
              <span className="mono text-[10px] bg-[#f0fdfa] text-[#0f766e] px-2 py-0.5 rounded border border-[#99f6e4] font-semibold">
                Site: {selectedSiteId}
              </span>
            )}
            <button
              onClick={() => {
                setActiveStageFilter('all');
                setActiveCategoryFilter('all');
                setSelectedSiteId(null);
              }}
              className="text-xs font-semibold text-[#0d9488] hover:underline"
            >
              Reset all ✕
            </button>
          </div>
        )}
      </div>

      {/* ==================================================== */}
      {/* TAB 1: OVERVIEW (LIGHT CLINICAL WORKSPACE) */}
      {/* ==================================================== */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* ROW 1: DECISION STREAM (8 cols) | NEEDS ATTENTION (4 cols) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* The Restyled Light Hero Decision Stream */}
            <div className="lg:col-span-8">
              <DecisionStream
                stages={reviewData.stages}
                activeFilter={activeStageFilter}
                onSelectStage={(stage) => setActiveStageFilter(stage)}
              />
            </div>

            {/* Restyled Light Needs Attention Panel */}
            <div className="lg:col-span-4">
              <NeedsAttentionPanel
                cases={reviewData.needsAttention}
                onSelectCase={(c) => setSelectedCase(c)}
                selectedCaseId={selectedCase?.id}
              />
            </div>
          </div>

          {/* ROW 2: THREE VISUAL SUMMARIES (WITH INTEGRATED REVIEW FUNNEL) */}
          <VisualSummaries
            findingMix={reviewData.findingMix}
            outcomes={reviewData.outcomes}
            trend={reviewData.trend}
            totalCases={202}
            activeCategoryFilter={activeCategoryFilter}
            onSelectCategory={(cat) => setActiveCategoryFilter(cat)}
            funnel={reviewData.funnel}
            activeStageFilter={activeStageFilter}
            onSelectStage={(stage) => setActiveStageFilter(stage)}
          />

          {/* ROW 3: SITE PULSE (7 cols) | SYSTEM MEMORY (5 cols) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            <div className="lg:col-span-7">
              <SitePulseMatrix
                sites={reviewData.sites}
                selectedSiteId={selectedSiteId}
                onSelectSite={(siteId) => setSelectedSiteId(siteId)}
              />
            </div>

            <div className="lg:col-span-5">
              <SystemMemoryPanel memory={reviewData.memory} currentCut={currentCut} />
            </div>
          </div>

          {/* ROW 4: REVIEW INTEGRITY (FOUR CONNECTED SAFEGUARD PILLARS) */}
          <ReviewIntegrityStrip integrity={reviewData.integrity} />
        </div>
      )}

      {/* ==================================================== */}
      {/* TAB 2: CASES (LIGHT POLISHED INBOX) */}
      {/* ==================================================== */}
      {activeTab === 'cases' && (
        <div className="rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#e2e8f0]">
            {/* Category Filter Chips */}
            <div className="flex flex-wrap items-center gap-2">
              {[
                { id: 'all', label: 'All Cases' },
                { id: 'safety', label: 'Safety' },
                { id: 'data_quality', label: 'Data Quality' },
                { id: 'compliance', label: 'Compliance' },
                { id: 'site_pattern', label: 'Site Patterns' },
              ].map((chip) => (
                <button
                  key={chip.id}
                  onClick={() => setCaseFilterCategory(chip.id)}
                  className={`px-3 py-1 rounded-xl text-xs font-semibold transition ${
                    caseFilterCategory === chip.id
                      ? 'bg-[#f0fdfa] text-[#0f766e] border border-[#5eead4] font-bold shadow-2xs'
                      : 'bg-white text-[#64748b] hover:text-[#0f172a] border border-[#e2e8f0]'
                  }`}
                >
                  {chip.label}
                </button>
              ))}
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center gap-2 text-xs">
              <ArrowUpDown className="w-3.5 h-3.5 text-[#64748b]" />
              <span className="text-[#64748b]">Sort:</span>
              <select
                value={caseSortOrder}
                onChange={(e) => setCaseSortOrder(e.target.value as any)}
                className="rounded-lg bg-white border border-[#cbd5e1] px-2.5 py-1 text-xs text-[#0f172a] outline-none shadow-2xs"
              >
                <option value="attention">Needs Attention</option>
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
              </select>
            </div>
          </div>

          {/* Cases Rows */}
          <div className="space-y-2">
            {filteredCases
              .filter((c) => caseFilterCategory === 'all' || c.category === caseFilterCategory)
              .map((c) => (
                <div
                  key={c.id}
                  onClick={() => setSelectedCase(c)}
                  className="group flex flex-col md:flex-row md:items-center justify-between p-3.5 rounded-xl border border-[#e2e8f0] bg-white hover:border-[#0d9488]/40 hover:bg-[#f8fafc] cursor-pointer transition shadow-2xs"
                >
                  <div className="flex items-start md:items-center gap-3">
                    <div className="p-2 rounded-lg bg-[#f8fafc] border border-[#e2e8f0]">
                      {getCategoryIcon(c.category)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="mono text-xs font-bold text-[#0f172a] group-hover:text-[#0d9488] transition">
                          {c.caseNumber}
                        </span>
                        <span className="mono text-[11px] text-[#64748b]">
                          {c.usubjid} · Site {c.siteId}
                        </span>
                      </div>
                      <p className="text-xs text-[#334155] font-semibold mt-0.5">
                        {c.title}
                      </p>
                    </div>
                  </div>

                  <div className="mt-2 md:mt-0 flex items-center gap-3 text-xs">
                    {/* Evidence Readiness Workflow State */}
                    <span
                      className={`mono text-[9px] font-bold px-2 py-0.5 rounded border ${
                        c.evidenceReadiness === 'READY_FOR_REVIEW'
                          ? 'bg-[#f0fdf4] text-[#15803d] border-[#bbf7d0]'
                          : c.evidenceReadiness === 'NEEDS_CLARIFICATION'
                          ? 'bg-[#fffbeb] text-[#92400e] border-[#fde68a]'
                          : c.evidenceReadiness === 'WAITING_FOR_SITE'
                          ? 'bg-[#f0fdfa] text-[#0f766e] border-[#99f6e4]'
                          : c.evidenceReadiness === 'EVIDENCE_INCOMPLETE'
                          ? 'bg-[#fff1f2] text-[#9f1239] border-[#fecdd3]'
                          : c.evidenceReadiness === 'MONITORING'
                          ? 'bg-[#faf5ff] text-[#6d28d9] border-[#ddd6fe]'
                          : 'bg-[#f0fdf4] text-[#15803d] border-[#86efac]'
                      }`}
                    >
                      {c.evidenceReadiness ? c.evidenceReadiness.replace(/_/g, ' ') : 'READY FOR REVIEW'}
                    </span>

                    {/* Stage Badge */}
                    <span className="mono text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[#f8fafc] text-[#475569] border border-[#e2e8f0]">
                      {c.stage.replace('_', ' ')}
                    </span>

                    {/* Evidence count */}
                    <span className="mono text-[11px] text-[#64748b] flex items-center gap-1">
                      <FileCheck className="w-3 h-3 text-[#0d9488]" />
                      {c.evidenceCount} evidence
                    </span>

                    {/* Focus Quick Action */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setFocusedCase(c);
                      }}
                      className="px-2 py-0.5 rounded-lg border border-[#e2e8f0] bg-[#f8fafc] hover:bg-[#f0fdfa] hover:border-[#0d9488] text-[10px] mono font-bold text-[#64748b] hover:text-[#0d9488] transition cursor-pointer"
                      title="Open in distraction-free Focus Mode"
                    >
                      Focus
                    </button>

                    <button className="text-[#0d9488] group-hover:translate-x-0.5 transition">
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* TAB 3: HUMAN GATE (CLINICAL DECISION DESK) */}
      {/* ==================================================== */}
      {activeTab === 'human_gate' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-xl border border-[#fde68a] bg-[#fffbeb] shadow-xs">
            <div className="flex items-center gap-3">
              <span className="h-3 w-3 rounded-full bg-[#f59e0b] animate-pulse" />
              <div>
                <h3 className="text-sm font-bold text-[#92400e]">
                  {humanGateCases.length} decisions waiting
                </h3>
                <p className="text-xs text-[#b45309]">
                  Medical monitor adjudication desk · Authorize safety reporting and site queries
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Large Workspace */}
            <div className="lg:col-span-8 space-y-4">
              {activeHumanGateCase ? (
                <div className="rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-6 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl space-y-5">
                  <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-4">
                    <div>
                      <span className="mono text-xs font-bold text-[#0e7490] bg-[#ecfeff] px-2 py-0.5 rounded border border-[#a5f3fc]">
                        {activeHumanGateCase.caseNumber}
                      </span>
                      <h2 className="text-lg font-bold text-[#0f172a] mt-1">
                        {activeHumanGateCase.title}
                      </h2>
                      <div className="mono text-xs text-[#64748b] mt-0.5">
                        Subject: <strong className="text-[#0f172a]">{activeHumanGateCase.usubjid}</strong> · Site {activeHumanGateCase.siteId}
                      </div>
                    </div>

                    <button
                      onClick={() => setSelectedCase(activeHumanGateCase)}
                      className="px-3.5 py-2 rounded-xl bg-[#f0fdfa] border border-[#99f6e4] text-[#0f766e] hover:bg-[#ccfbf1] text-xs font-bold transition flex items-center gap-1.5 shadow-2xs"
                    >
                      <span>Open Case Story</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Summary of What Happened */}
                  <div className="space-y-1.5">
                    <div className="mono text-[10px] font-bold text-[#0e7490] uppercase tracking-wider">
                      Clinical Summary
                    </div>
                    <p className="text-sm text-[#0f172a] font-semibold leading-relaxed">
                      "{activeHumanGateCase.whatHappened.summary}"
                    </p>
                  </div>

                  {/* Facts */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {activeHumanGateCase.whatHappened.facts.map((f, i) => (
                      <div key={i} className="p-3 rounded-xl bg-[#f8fafc] border border-[#e2e8f0]">
                        <div className="mono text-[10px] text-[#64748b] uppercase">{f.label}</div>
                        <div className="text-xs font-bold text-[#0f172a] mt-1">{f.value}</div>
                      </div>
                    ))}
                  </div>

                  {/* Monitor question */}
                  <div className="rounded-xl border border-[#fde68a] bg-[#fffbeb] p-4 text-xs text-[#92400e]">
                    <div className="font-bold text-[#92400e] mb-1">
                      Monitor Decision Context:
                    </div>
                    {activeHumanGateCase.humanGate?.monitorQuestion ||
                      'Confirm whether finding criteria require expedited regulatory reporting or safety protocol hold.'}
                  </div>

                  {/* Quick Action buttons */}
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => {
                        handleDecisionSubmit(activeHumanGateCase.id, 'APPROVED', 'Approved via Clinical Desk');
                      }}
                      className="px-5 py-2.5 rounded-xl bg-[#0d9488] text-white font-bold text-xs hover:bg-[#0f766e] transition flex items-center gap-1.5 shadow-md shadow-[#0d9488]/20"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Approve Case</span>
                    </button>

                    <button
                      onClick={() => setSelectedCase(activeHumanGateCase)}
                      className="px-5 py-2.5 rounded-xl bg-[#fffbeb] border border-[#fde68a] text-[#92400e] font-bold text-xs hover:bg-[#fef3c7] transition flex items-center gap-1.5 shadow-2xs"
                    >
                      <span>Ask For Clarification (Patient 360)</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-[#64748b]">
                  No cases awaiting human gate adjudication.
                </div>
              )}
            </div>

            {/* Right Small Queue */}
            <div className="lg:col-span-4 rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-4.5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl space-y-3">
              <div className="mono text-xs font-bold text-[#0f172a] uppercase tracking-wider pb-2 border-b border-[#e2e8f0]">
                Decision Queue
              </div>
              <div className="space-y-2">
                {humanGateCases.map((c) => {
                  const isSelected = c.id === humanGateSelectedId;
                  return (
                    <div
                      key={c.id}
                      onClick={() => setHumanGateSelectedId(c.id)}
                      className={`p-3 rounded-xl border transition cursor-pointer ${
                        isSelected
                          ? 'border-[#0d9488] bg-[#f0fdfa] ring-2 ring-[#0d9488]/20 shadow-xs'
                          : 'border-[#e2e8f0] bg-white hover:bg-[#f8fafc]'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="mono font-bold text-[#0f172a]">{c.caseNumber}</span>
                        <span className="mono text-[10px] text-[#64748b]">Site {c.siteId}</span>
                      </div>
                      <div className="text-xs font-semibold text-[#334155] truncate">
                        {c.title}
                      </div>
                      <div className="mt-2 flex items-center justify-between text-[11px] mono text-[#b45309] font-bold">
                        <span>Awaiting monitor</span>
                        <ArrowRight className="w-3 h-3" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* TAB 4: CYCLE REPORT (REVIEW REPORT VISUAL STORY) */}
      {/* ==================================================== */}
      {activeTab === 'cycle_report' && (
        <div className="rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-6 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl space-y-6">
          {/* Top Banner: CUT REVIEW COMPLETE */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-xl border border-[#99f6e4] bg-[#f0fdfa]">
            <div>
              <div className="mono text-[10px] font-bold text-[#0f766e] uppercase tracking-wider">
                Formal Stage 2 Summary
              </div>
              <h2 className="text-xl font-bold text-[#0f172a] mt-0.5">
                CUT {currentCut} REVIEW COMPLETE
              </h2>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-[#334155]">
                <span><strong className="text-[#0f172a]">202</strong> findings reviewed</span>
                <span>·</span>
                <span className="text-[#be123c]"><strong>3</strong> escalations</span>
                <span>·</span>
                <span className="text-[#0e7490]"><strong>17</strong> site queries</span>
                <span>·</span>
                <span className="text-[#4338ca]"><strong>178</strong> compliance checks</span>
              </div>
            </div>

            <button
              onClick={() => alert(`Review Report for Cut ${currentCut} exported successfully.`)}
              className="px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-xs font-bold text-[#0f172a] transition flex items-center gap-2 self-start md:self-auto border border-[#cbd5e1] shadow-2xs"
            >
              <Download className="w-4 h-4 text-[#0d9488]" />
              <span>Export report</span>
            </button>
          </div>

          {/* Activity Timeline */}
          <div className="space-y-3">
            <div className="mono text-xs font-bold text-[#0f172a] uppercase tracking-wider">
              Cycle Execution Activity Log
            </div>
            <div className="space-y-2 font-mono text-xs">
              {[
                { time: '09:41', text: 'Detection complete — 202 cases surfaced across 12 study sites', color: 'text-[#0284c7]' },
                { time: '09:42', text: 'Medical review complete — Safety criteria verified against ICH E2A', color: 'text-[#7c3aed]' },
                { time: '09:43', text: '17 queries generated and dispatched to investigative sites', color: 'text-[#b45309]' },
                { time: '09:44', text: '3 cases submitted to human medical monitor gate for adjudication', color: 'text-[#be123c]' },
                { time: '09:47', text: 'Cycle complete — State persisted to system memory; zero duplicate findings', color: 'text-[#15803d]' },
              ].map((log, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-2.5 rounded-lg bg-[#f8fafc] border border-[#e2e8f0]"
                >
                  <span className="text-[#64748b]">{log.time}</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#cbd5e1]" />
                  <span className={`font-semibold ${log.color}`}>{log.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* CASE STORY DRAWER (RESTYLED LIGHT CLINICAL DRAWER) */}
      {/* ==================================================== */}
      <CaseStoryDrawer
        caseItem={selectedCase}
        onClose={() => setSelectedCase(null)}
        onDecisionSubmit={handleDecisionSubmit}
        onFocusCase={(c) => {
          setSelectedCase(null);
          setFocusedCase(c);
        }}
      />

      {/* ==================================================== */}
      {/* PROTOCOL UPDATE COMPARISON MODAL */}
      {/* ==================================================== */}
      <ProtocolUpdateModal
        isOpen={showProtocolModal}
        onClose={() => setShowProtocolModal(false)}
        updateData={reviewData.protocolUpdate}
      />

      {/* ==================================================== */}
      {/* WHAT CHANGED CUT COMPARISON MODAL (FEATURE 1) */}
      {/* ==================================================== */}
      <WhatChangedModal
        isOpen={showWhatChangedModal}
        onClose={() => setShowWhatChangedModal(false)}
        data={reviewData.whatChanged}
      />
    </div>
  );
}
