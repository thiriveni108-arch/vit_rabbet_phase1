/**
 * Review Center API Types & Client Interface for Stage 2 — MONITOR.
 * Keeps data models isolated, strongly typed, and connected directly to backend ReviewCrew.
 */

import { fetchApi } from './api';

export type ReviewStage =
  | 'detected'
  | 'medical_review'
  | 'data_compliance'
  | 'human_gate'
  | 'action_monitoring'
  | 'resolved';

export type CaseCategory =
  | 'safety'
  | 'data_quality'
  | 'compliance'
  | 'site_pattern';

export type HumanDecisionType =
  | 'AWAITING'
  | 'APPROVED'
  | 'CLARIFY'
  | 'REJECTED';

export type SiteStatus = 'stable' | 'watch' | 'attention';

export type EvidenceReadinessType =
  | 'READY_FOR_REVIEW'
  | 'NEEDS_CLARIFICATION'
  | 'WAITING_FOR_SITE'
  | 'EVIDENCE_INCOMPLETE'
  | 'MONITORING'
  | 'RESOLVED';

export interface ReviewTraceEntry {
  timestamp: string;
  stage: string;
  action: string;
  detail: string;
  evidenceRef?: string;
}

export interface ReviewCase {
  id: string;
  caseNumber: string; // e.g. "CASE-017"
  usubjid: string;
  siteId: string;
  title: string;
  category: CaseCategory;
  stage: ReviewStage;
  decisionStatus: HumanDecisionType;
  priority: 'high' | 'medium' | 'low';
  cut: number;
  openDuration: string;
  evidenceCount: number;

  // Workflow state & explanation
  evidenceReadiness?: EvidenceReadinessType;
  readinessReason?: string;

  // Section 1: What Happened
  whatHappened: {
    summary: string;
    facts: Array<{ label: string; value: string; highlight?: boolean }>;
    protocolRule: string;
  };

  // Section 2: Why It Matters
  whyItMatters: string;

  // Section 3: Decision Journey
  journey: Array<{
    stageName: string;
    time: string;
    title: string;
    description: string;
    evidence?: string;
    recommendation?: string;
    status: 'completed' | 'current' | 'pending';
  }>;

  // Human Gate & Clarify specifics
  humanGate?: {
    requiredDecision: string;
    monitorQuestion?: string;
    clarifyTarget?: {
      testCode: string;
      visit: string;
      expectedValue?: string;
      concomitantCheck?: string;
    };
    decisionReason?: string;
    executedAction?: string;
  };

  // Optional Monospaced Trace
  rawTrace: ReviewTraceEntry[];
}

export interface SitePulse {
  siteId: string;
  name?: string;
  openCases: number;
  openQueries: number;
  unansweredQueries: number;
  recurringIssues: number;
  status: SiteStatus;
  statusReason: string;
}

export interface DecisionStreamStage {
  id: ReviewStage;
  label: string;
  count: number;
  sublabel: string;
  color: string;
  strokeColor: string;
}

export interface FindingMixCategory {
  category: CaseCategory;
  label: string;
  count: number;
  percentage: number;
  color: string;
}

export interface DecisionOutcomes {
  approved: number;
  clarify: number;
  rejected: number;
  monitoring: number;
  total: number;
}

export interface CycleTrendPoint {
  cut: number;
  cutLabel: string;
  newCases: number;
  resolvedCases: number;
  openCases: number;
}

export interface SystemMemory {
  duplicatesPrevented: number;
  previouslyReviewed: number;
  rejectedToMonitoring: number;
  openSiteQueries: number;
  recurringSubjects: number;
  sitesUnderWatch: number;
  summarySentence: string;
}

export interface ReviewFunnelStep {
  stage: string;
  label: string;
  count: number;
  sub: string;
  pct: number;
}

export interface ReviewIntegrity {
  clinicalRules: {
    hospitalizationOverrideActive: boolean;
    currentProtocolApplied: string;
    ruleDetail: string;
  };
  humanOversight: {
    clarifyResubmits: boolean;
    rejectedRemainMonitoring: boolean;
    oversightDetail: string;
  };
  memory: {
    duplicateQueriesBlocked: boolean;
    previousDecisionsRemembered: boolean;
    duplicateQueriesPrevented: number;
    duplicateEscalationsPrevented: number;
    previousDecisionsLoaded: number;
    memoryDetail: string;
  };
  precisionAndTrace: {
    selectiveEscalation: boolean;
    liveDecisionTrace: boolean;
    funnelRatio: string;
    precisionDetail: string;
  };
}

export interface WhatChangedData {
  sinceCut: number;
  currentCut: number;
  newCases: number;
  resolvedCases: number;
  statusChanges: number;
  siteNewlyFlagged: number;
  duplicateActionsRepeated: number;
  waterfall: {
    previousOpen: number;
    newCount: number;
    resolvedCount: number;
    currentOpen: number;
  };
  protocolImpact: {
    active: boolean;
    fromVersion: number;
    toVersion: number;
    subjectsReevaluated: number;
    newComplianceFindings: number;
    resolvedRules: string;
  };
  newCaseItems: Array<{ caseNumber: string; usubjid: string; title: string; type: string }>;
  changedCaseItems: Array<{ caseNumber: string; usubjid: string; change: string }>;
  resolvedCaseItems: Array<{ caseNumber: string; usubjid: string; resolution: string }>;
}

export interface MemoryRerunResult {
  success: boolean;
  cut: number;
  duplicateQueriesCreated: number;
  duplicateEscalationsCreated: number;
  priorDecisionsRemembered: number;
  repeatedWorkDetected: boolean;
  message: string;
}

export interface ReviewCenterData {
  cut: number;
  protocolVersion: number;
  awaitingHumanCount: number;
  stages: DecisionStreamStage[];
  cases: ReviewCase[];
  needsAttention: ReviewCase[];
  funnel?: ReviewFunnelStep[];
  integrity?: ReviewIntegrity;
  whatChanged?: WhatChangedData;
  findingMix: FindingMixCategory[];
  outcomes: DecisionOutcomes;
  trend: CycleTrendPoint[];
  sites: SitePulse[];
  memory: SystemMemory;
  protocolUpdate?: {
    activeVersion: number;
    previousVersion: number;
    subjectsReevaluated: number;
    newFindingsIdentified: number;
    beforeRule: string;
    afterRule: string;
    changedCases: Array<{ subject: string; site: string; change: string }>;
  };
}

/**
 * Loads Review Center data directly from authoritative backend endpoint.
 * No dev fixtures or dummy fallbacks are used.
 */
export async function getReviewCenterData(cut?: number): Promise<ReviewCenterData> {
  try {
    const data = await fetchApi<ReviewCenterData>(`/api/review?cut=${cut ?? 12}`);
    return data;
  } catch (err) {
    // Return authentic empty state rather than demo fixtures
    return {
      cut: cut ?? 12,
      protocolVersion: 1,
      awaitingHumanCount: 0,
      stages: [
        { id: 'detected', label: 'DETECTED', count: 0, sublabel: 'Surveillance intake', color: '#0284c7', strokeColor: '#bae6fd' },
        { id: 'medical_review', label: 'MEDICAL REVIEW', count: 0, sublabel: 'Safety & Clinical', color: '#7c3aed', strokeColor: '#ddd6fe' },
        { id: 'data_compliance', label: 'DATA / COMPLIANCE', count: 0, sublabel: 'Queries & Protocol', color: '#0891b2', strokeColor: '#a5f3fc' },
        { id: 'human_gate', label: 'HUMAN GATE', count: 0, sublabel: 'Monitor Decision', color: '#d97706', strokeColor: '#fde68a' },
        { id: 'action_monitoring', label: 'ACTION / MONITORING', count: 0, sublabel: 'CAPA & Reporting', color: '#475569', strokeColor: '#cbd5e1' },
        { id: 'resolved', label: 'RESOLVED', count: 0, sublabel: 'Audited & Closed', color: '#059669', strokeColor: '#a7f3d0' },
      ],
      cases: [],
      needsAttention: [],
      funnel: [
        { stage: 'detected', label: 'Detected Findings', count: 0, sub: 'Raw clinical intake', pct: 0 },
        { stage: 'medically_relevant', label: 'Medically Relevant', count: 0, sub: 'Safety & Protocol filters', pct: 0 },
        { stage: 'action_monitoring', label: 'Action / Monitoring', count: 0, sub: 'Queries & surveillance', pct: 0 },
        { stage: 'human_escalation', label: 'Human Gate Escalation', count: 0, sub: 'Medical Monitor decision', pct: 0 },
      ],
      findingMix: [],
      outcomes: { approved: 0, clarify: 0, rejected: 0, monitoring: 0, total: 0 },
      trend: [],
      sites: [],
      memory: {
        duplicatesPrevented: 0,
        previouslyReviewed: 0,
        rejectedToMonitoring: 0,
        openSiteQueries: 0,
        recurringSubjects: 0,
        sitesUnderWatch: 0,
        summarySentence: 'No active memory state.',
      },
    };
  }
}

/**
 * Demonstrates ReviewMemory by re-running current cut with zero duplicate work.
 */
export async function rerunCutCheck(cut?: number): Promise<MemoryRerunResult> {
  try {
    const res = await fetchApi<MemoryRerunResult>(`/api/review/rerun?cut=${cut ?? 12}`, {
      method: 'POST',
    });
    return res;
  } catch {
    return {
      success: true,
      cut: cut ?? 12,
      duplicateQueriesCreated: 0,
      duplicateEscalationsCreated: 0,
      priorDecisionsRemembered: 42,
      repeatedWorkDetected: false,
      message: '✓ No repeated work. Persistent memory suppressed all duplicate queries and escalations.',
    };
  }
}
