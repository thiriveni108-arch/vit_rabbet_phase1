/**
 * Stage 3 StudyWatch & Data Intake API Client.
 * Strongly typed interface directly wired to backend /api/watch/* endpoints.
 */

import { fetchApi } from './api';

export interface WatchStatus {
  current_cut: number;
  protocol_version: number;
  budget_tier: 'FULL' | 'REDUCED' | 'SAFETY_ONLY';
  budget_used: number;
  total_decisions: number;
  active_alerts_count: number;
  subjects_count: number;
  sites_count: number;
  is_live: boolean;
}

export interface WatchCutInfo {
  cut: number;
  protocol_version: number;
  new_records: number;
  corrections: number;
  processed: boolean;
  signals_detected: number;
}

export interface PipelineStageInfo {
  stage: string;
  count: number;
  status: string;
}

export interface DataIntakeRecord {
  domain: string;
  usubjid: string;
  seq: number;
  visit?: string;
  test?: string;
  raw_value: string;
  numeric_value?: number | null;
  unit?: string;
  trust_state: string;
  version: number;
  cut_available: number;
}

export interface CorrectionItem {
  domain: string;
  usubjid: string;
  seq: number;
  field: string;
  old_value: string;
  new_value: string;
  effective_cut: number;
  reason: string;
  superseded_version: number;
  current_version: number;
  state: string;
}

export interface DataIntakeLatest {
  cut: number;
  protocol_version: number;
  metrics: {
    cut: number;
    new_records: number;
    updated_records: number;
    corrected_records: number;
    new_subjects: number;
    new_sites: number;
    new_domains: number;
    missing_values: number;
    suspect_units: number;
    quarantined_records: number;
    affected_subjects: number;
    affected_findings: number;
    full_build_calls: number;
    records_examined: number;
    records_inserted: number;
    subjects_recomputed: number;
    findings_recomputed: number;
    incremental_elapsed_ms: number;
  };
  recent_records: DataIntakeRecord[];
  corrections: CorrectionItem[];
  pipeline_stages: PipelineStageInfo[];
}

export interface UnitAnomaly {
  alert_id: string;
  cut: number;
  site: string;
  test: string;
  historical_median: number;
  incoming_median: number;
  ratio: number;
  expected_conversion: string;
  proportion_affected: number;
  trust_state: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  lab_query: string;
  alternatives_considered: string[];
}

export interface SiteIntegrityItem {
  site: string;
  status: 'NORMAL' | 'WATCH' | 'SUSPECT' | 'QUARANTINED';
  trust_state: string;
  flags_count: number;
  reasons: string[];
  recommendation: string;
  sysbp_stdev: number;
  pulse_stdev: number;
  peer_sysbp_median_stdev: number;
  peer_pulse_median_stdev: number;
}

export interface DocumentTamperEvent {
  document_name: string;
  cut: number;
  sha256_hash: string;
  previous_hash?: string;
  changed: boolean;
  tamper_suspected: boolean;
  instruction_like_text: string[];
  action_taken: string;
}

export interface WatchIntegrityData {
  cut: number;
  unit_anomalies: UnitAnomaly[];
  site_integrity: Record<string, SiteIntegrityItem>;
  document_tamper_events: DocumentTamperEvent[];
  retracted_findings: any[];
}

export interface HistoricalEvidenceItem {
  domain: string;
  usubjid: string;
  seq: number;
  field?: string;
  raw_value: string;
  normalized_numeric?: number | null;
  unit?: string;
  version: number;
  cut_observed: number;
  trust_state: string;
}

export interface DecisionTraceItem {
  decision_id: string;
  cut: number;
  sequence: number;
  timestamp: string;
  component: string;
  what: string;
  why: string;
  evidence_refs: Array<{ domain?: string; usubjid?: string; seq?: number; [key: string]: any }>;
  evidence_lines: string[];
  historical_evidence?: HistoricalEvidenceItem[];
  alternatives: string[];
  action: string;
  result: string;
  trust_state: string;
  protocol_version: number;
  budget_tier: string;
}

export interface ExplainResult {
  decision_id: string;
  cut: number;
  timestamp: string;
  component: string;
  what: string;
  why: string;
  evidence: any[];
  evidence_lines: string[];
  evidence_validation: Array<{
    domain?: string;
    usubjid?: string;
    seq?: number;
    historical_value?: string;
    historical_numeric?: number | null;
    verified_in_historical_store: boolean;
    [key: string]: any;
  }>;
  historical_evidence: HistoricalEvidenceItem[];
  alternatives: string[];
  action: string;
  result: string;
  trust_state: string;
  protocol_version: number;
  budget_tier: string;
  consistent_with_trace: boolean;
}

export interface SiteRiskItem {
  site: string;
  site_id: string;
  rank: number;
  status: 'STABLE' | 'WATCH' | 'ATTENTION';
  risk_tier: string;
  reasons: string[];
  is_quarantined: boolean;
  open_queries: number;
  unanswered_queries: number;
  recurring_subjects: number;
  integrity_events: number;
  safety_findings: number;
  data_quality_findings: number;
  regularity_anomalies: number;
  last_incident_cut?: number;
  quarantined_tests: string[];
  quarantined_domains: string[];
  affected_cuts: number[];
  evidence_refs: any[];
}

export interface SurveillanceReportData {
  cut: number;
  protocol_version: number;
  signals_detected: number;
  critical_alerts: number;
  data_integrity_events: number;
  corrections_applied: number;
  retracted_findings: number;
  open_escalations: number;
  standing_limits_count: number;
  budget_used: number;
  budget_tier: string;
  elapsed_ms: number;
  decision_ids: string[];
  site_risk_ranking?: SiteRiskItem[];
  false_alarm_metrics?: {
    candidate_alerts: number;
    clinical_alerts_emitted: number;
    data_integrity_alerts_emitted: number;
    clinical_alerts_suppressed_integrity: number;
    suppression_rate: number;
    false_alarm_rate?: number | null;
  };
  signal_detection_latency?: {
    signals_tracked: number;
    cut_signals_count: number;
    same_cut_escalated_count: number;
    records: Array<{
      signal_id: string;
      signal_type: string;
      subject_or_site: string;
      first_seen_cut: number;
      detected_cut: number;
      escalated_cut?: number;
      detection_latency_cuts: number;
      escalation_latency_cuts: number;
    }>;
  };
  budget_usage?: {
    limit: number;
    used: number;
    remaining: number;
    percentage: number;
    tier: string;
    optional_narrative_suppressed: boolean;
  };
  open_items?: Array<{
    case_id: string;
    finding_type: string;
    subject: string;
    site: string;
    status: string;
    cuts_waiting: number;
    standing_limits: boolean;
  }>;
  decision_log_path?: string;
  alerts: Array<{
    alert_id: string;
    cut: number;
    subject: string;
    site: string;
    type: 'CLINICAL_SAFETY' | 'DATA_INTEGRITY' | 'PROTOCOL_COMPLIANCE';
    category: string;
    severity: string;
    rule: string;
    observed_value: string;
    unit: string;
    title: string;
    description: string;
    trust_state: string;
    status: string;
    action?: string;
    evidence?: any[];
    corroborated?: boolean;
  }>;
}

export const watchApi = {
  getStatus: () => fetchApi<WatchStatus>('/api/watch/status'),
  getCuts: () => fetchApi<WatchCutInfo[]>('/api/watch/cuts'),
  runCut: (cut: number) => fetchApi<SurveillanceReportData>(`/api/watch/run-cut/${cut}`, { method: 'POST' }),
  getIntakeLatest: () => fetchApi<DataIntakeLatest>('/api/watch/intake/latest'),
  ingestRecords: (records: any[], domain: string, cut?: number) =>
    fetchApi<{ success: boolean; metrics: any }>('/api/watch/ingest', {
      method: 'POST',
      body: JSON.stringify({ records, domain, cut }),
    }),
  getIntegrity: () => fetchApi<WatchIntegrityData>('/api/watch/integrity'),
  getSites: () => fetchApi<SiteRiskItem[]>('/api/watch/sites'),
  getAlerts: () => fetchApi<any[]>('/api/watch/alerts'),
  getDecisions: () => fetchApi<DecisionTraceItem[]>('/api/watch/decisions'),
  getDecision: (id: string) => fetchApi<DecisionTraceItem>(`/api/watch/decisions/${id}`),
  explainDecision: (id: string) => fetchApi<ExplainResult>(`/api/watch/decisions/${id}/explain`),
  getReport: () => fetchApi<SurveillanceReportData>('/api/watch/report'),
  exportDecisions: () =>
    fetchApi<{ success: boolean; decision_log_path: string; total_persisted_decisions: number }>(
      '/api/watch/export-decisions'
    ),
};

