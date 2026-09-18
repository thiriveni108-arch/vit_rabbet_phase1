/**
 * Live API Client for Study Sentinel Backend (FastAPI / StudyService).
 * Connects directly to authoritative backend endpoints without second truth.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API error ${res.status}: ${errText || res.statusText}`);
  }
  return res.json();
}

export interface DashboardData {
  cut: number;
  protocol_version: number;
  subjects: number;
  sites: number;
  total_records: number;
  total_findings: number;
  potential_hys_law_count: number;
  serious_ae_count: number;
  creatinine_exclusion_count: number;
  prohibited_medication_count: number;
  visit_deviation_count: number;
  domain_record_counts: Record<string, number>;
  findings_by_type: Record<string, number>;
  build_time_ms?: number;
}

export interface SubjectItem {
  usubjid: string;
  site_id: string;
  arm?: string;
  age?: string | number;
  sex?: string;
  findings_count: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface GraphViewData {
  usubjid: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FindingItem {
  finding_id: string;
  finding_type: string;
  usubjid: string;
  cut: number;
  protocol_version: number;
  status: string;
  details: Record<string, any>;
  evidence: Array<{ domain: string; usubjid: string; seq: number }>;
}

export interface EvidenceRecord {
  reference: { domain: string; usubjid: string; seq: number };
  details: Record<string, any>;
}

export interface AskResponse {
  question_id?: string;
  text: string;
  answer: any;
  evidence: Array<{ domain: string; usubjid: string; seq: number }>;
  confidence?: number;
  status?: string;
}

export interface StudyContext {
  study_id: string;
  study_name: string;
  current_cut: number;
  protocol_version: number;
  available_cuts: number[];
  total_subjects: number;
  total_records: number;
  total_findings: number;
}

export interface TimelineItem {
  date: string | null;
  domain: string;
  visit?: string;
  label: string;
  seq?: number;
  details: Record<string, any>;
  evidence?: { domain: string; usubjid: string; seq: number };
}

export const api = {
  getContext: () => fetchApi<StudyContext>('/api/context'),
  getDashboard: () => fetchApi<DashboardData>('/api/dashboard'),
  setCut: (cut: number) => fetchApi<{ success: boolean; cut: number; dashboard: DashboardData }>(`/api/cut/${cut}`, { method: 'POST' }),
  getSubjects: () => fetchApi<SubjectItem[]>('/api/subjects'),
  getSubjectGraph: (usubjid: string) => fetchApi<GraphViewData>(`/api/subjects/${encodeURIComponent(usubjid)}/graph`),
  getTimeline: (usubjid: string) => fetchApi<TimelineItem[]>(`/api/subjects/${encodeURIComponent(usubjid)}/timeline`),
  getFindings: (usubjid?: string) => fetchApi<FindingItem[]>(usubjid ? `/api/findings?usubjid=${encodeURIComponent(usubjid)}` : '/api/findings'),
  getFinding: (id: string) => fetchApi<FindingItem>(`/api/findings/${encodeURIComponent(id)}`),
  getEvidence: (id: string) => fetchApi<EvidenceRecord[]>(`/api/findings/${encodeURIComponent(id)}/evidence`),
  askAtlas: (question: string) => fetchApi<AskResponse>('/api/ask', { method: 'POST', body: JSON.stringify({ question }) }),
};
