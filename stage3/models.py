"""Stage 3: Data Models, Value State, Trust State, and Decision Trace Schemas.

Defines typed representations for:
- Clinical Value States (preserving provenance, blanks, ND, <5)
- Trust States (trusted, suspect, untrusted, quarantined)
- Escalation States (pending, approved, rejected, clarify, waiting, standing_limits)
- Execution Tiers (FULL, REDUCED, SAFETY_ONLY)
- Historical Decision Records (immutable snapshot for explain())
- Generic Anomaly & Ingestion Metrics
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ValueState(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"               # blank / None / empty string
    NOT_DONE = "NOT_DONE"             # "ND"
    BELOW_DETECTION = "BELOW_DETECTION"  # "<5" (qualifier="LT", threshold=5.0)
    ABOVE_DETECTION = "ABOVE_DETECTION"  # ">100" (qualifier="GT", threshold=100.0)
    INVALID_FORMAT = "INVALID_FORMAT"   # corrupted characters
    SUSPECT_UNIT = "SUSPECT_UNIT"       # systematic unit shift detected
    QUARANTINED = "QUARANTINED"         # excluded from safety aggregation
    CORRECTED = "CORRECTED"             # amended by lab re-issue
    SUPERSEDED = "SUPERSEDED"           # historic version replaced by correction


class TrustState(str, Enum):
    TRUSTED = "TRUSTED"
    SUSPECT = "SUSPECT"
    UNTRUSTED = "UNTRUSTED"
    QUARANTINED = "QUARANTINED"


class EscalationState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLARIFY = "CLARIFY"
    WAITING = "WAITING"
    STANDING_LIMITS = "STANDING_LIMITS"


class BudgetTier(str, Enum):
    FULL = "FULL"
    REDUCED = "REDUCED"
    SAFETY_ONLY = "SAFETY_ONLY"


class AlignmentStatus(str, Enum):
    ALIGNED = "ALIGNED"
    NEW_SUBJECT = "NEW_SUBJECT"
    NEW_SITE = "NEW_SITE"
    NEW_DOMAIN = "NEW_DOMAIN"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED = "REJECTED"


@dataclass
class NormalizedValue:
    """Represents a clinical value preserving raw input and clinical intent."""
    raw_value: str
    normalized_numeric: Optional[float] = None
    qualifier: Optional[str] = None       # "LT", "GT", "EQ", None
    threshold: Optional[float] = None     # e.g., 5.0 for "<5"
    unit: Optional[str] = None
    state: ValueState = ValueState.VALID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "normalized_numeric": self.normalized_numeric,
            "qualifier": self.qualifier,
            "threshold": self.threshold,
            "unit": self.unit,
            "state": self.state.value,
        }


@dataclass
class AlignmentResult:
    """Direct answer to jury question: 'How do you align an inserted value?'"""
    record_ref: Tuple[str, str, int]       # (domain, usubjid, seq)
    matched_subject: Optional[str]
    matched_site: Optional[str]
    matched_domain: str
    matched_visit: Optional[str]
    matched_date: Optional[str]
    test_code: Optional[str]
    unit: Optional[str]
    normalized_fields: Dict[str, Any]
    alignment_status: AlignmentStatus
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_ref": list(self.record_ref),
            "matched_subject": self.matched_subject,
            "matched_site": self.matched_site,
            "matched_domain": self.matched_domain,
            "matched_visit": self.matched_visit,
            "matched_date": self.matched_date,
            "test_code": self.test_code,
            "unit": self.unit,
            "normalized_fields": self.normalized_fields,
            "alignment_status": self.alignment_status.value,
            "warnings": self.warnings,
        }


@dataclass
class CorrectionVersion:
    """Historical versioning for corrected records."""
    domain: str
    usubjid: str
    seq: int
    field_name: str
    old_value: str
    new_value: str
    effective_cut: int
    reason: str
    superseded_version: int = 1
    current_version: int = 2
    state: ValueState = ValueState.CORRECTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "usubjid": self.usubjid,
            "seq": self.seq,
            "field": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "effective_cut": self.effective_cut,
            "reason": self.reason,
            "superseded_version": self.superseded_version,
            "current_version": self.current_version,
            "state": self.state.value,
        }


@dataclass
class HistoricalEvidenceRecord:
    """Immutable snapshot of evidence as known at decision time."""
    domain: str
    usubjid: str
    seq: int
    field: Optional[str]
    raw_value: str
    normalized_numeric: Optional[float]
    unit: Optional[str]
    version: int
    cut_observed: int
    trust_state: TrustState

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "usubjid": self.usubjid,
            "seq": self.seq,
            "field": self.field,
            "raw_value": self.raw_value,
            "normalized_numeric": self.normalized_numeric,
            "unit": self.unit,
            "version": self.version,
            "cut_observed": self.cut_observed,
            "trust_state": self.trust_state.value,
        }


@dataclass
class DecisionTrace:
    """Trace-first immutable decision artifact written at the moment of decision."""
    decision_id: str
    cut: int
    sequence: int
    timestamp: str                       # e.g., ISO or format string
    component: str                       # "SURVEILLANCE", "SAFETY_RULE", "INTEGRITY_CHECK", "REVIEW_GATE"
    what: str                            # Concise statement of what was decided
    why: str                             # Plain clinical / integrity justification
    evidence_refs: List[Dict[str, Any]]  # List of {"domain": "...", "usubjid": "...", "seq": N}
    evidence_lines: List[str]            # Human-readable evidence excerpts
    historical_evidence: List[HistoricalEvidenceRecord] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list) # Alternatives considered & why rejected
    action: str = ""                     # Executed or recommended action
    result: str = ""                     # Finding created, query sent, escalation queued, etc.
    trust_state: TrustState = TrustState.TRUSTED
    protocol_version: int = 1
    budget_tier: BudgetTier = BudgetTier.FULL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "cut": self.cut,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "component": self.component,
            "what": self.what,
            "why": self.why,
            "evidence_refs": self.evidence_refs,
            "evidence_lines": self.evidence_lines,
            "historical_evidence": [h.to_dict() for h in self.historical_evidence],
            "alternatives": self.alternatives,
            "action": self.action,
            "result": self.result,
            "trust_state": self.trust_state.value,
            "protocol_version": self.protocol_version,
            "budget_tier": self.budget_tier.value,
        }


@dataclass
class IngestionMetrics:
    """Metrics tracking incremental intake."""
    cut: int
    new_records: int = 0
    updated_records: int = 0
    corrected_records: int = 0
    records_corrected: int = 0
    new_subjects: int = 0
    new_sites: int = 0
    new_domains: int = 0
    missing_values: int = 0
    suspect_units: int = 0
    rejected_records: int = 0
    quarantined_records: int = 0
    affected_subjects: int = 0
    affected_findings: int = 0
    full_build_calls: int = 0
    records_examined: int = 0
    records_inserted: int = 0
    subjects_recomputed: int = 0
    findings_recomputed: int = 0
    incremental_elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        corr = self.corrected_records or self.records_corrected
        return {
            "cut": self.cut,
            "new_records": self.new_records,
            "updated_records": self.updated_records,
            "corrected_records": corr,
            "records_corrected": corr,
            "new_subjects": self.new_subjects,
            "new_sites": self.new_sites,
            "new_domains": self.new_domains,
            "missing_values": self.missing_values,
            "suspect_units": self.suspect_units,
            "rejected_records": self.rejected_records,
            "quarantined_records": self.quarantined_records,
            "affected_subjects": self.affected_subjects,
            "affected_findings": self.affected_findings,
            "full_build_calls": self.full_build_calls,
            "records_examined": self.records_examined,
            "records_inserted": self.records_inserted,
            "subjects_recomputed": self.subjects_recomputed,
            "findings_recomputed": self.findings_recomputed,
            "incremental_elapsed_ms": self.incremental_elapsed_ms,
        }


@dataclass
class DocumentHashRecord:
    """Cryptographic tracking of study documents."""
    document_name: str
    cut: int
    sha256_hash: str
    previous_hash: Optional[str]
    changed: bool = False
    tamper_suspected: bool = False
    instruction_like_text: List[str] = field(default_factory=list)
    action_taken: str = "Preserved authoritative protocol rules"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_name": self.document_name,
            "cut": self.cut,
            "sha256_hash": self.sha256_hash,
            "previous_hash": self.previous_hash,
            "changed": self.changed,
            "tamper_suspected": self.tamper_suspected,
            "instruction_like_text": self.instruction_like_text,
            "action_taken": self.action_taken,
        }


@dataclass
class FalseAlarmMetrics:
    """Metrics tracking alert suppression and data integrity classification."""
    candidate_alerts: int = 0
    clinical_alerts_emitted: int = 0
    data_integrity_alerts_emitted: int = 0
    clinical_alerts_suppressed_integrity: int = 0
    suppression_rate: float = 0.0
    false_alarm_rate: Optional[float] = None  # Exposed ONLY when genuine ground-truth labels are available

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_alerts": self.candidate_alerts,
            "clinical_alerts_emitted": self.clinical_alerts_emitted,
            "data_integrity_alerts_emitted": self.data_integrity_alerts_emitted,
            "clinical_alerts_suppressed_integrity": self.clinical_alerts_suppressed_integrity,
            "suppression_rate": round(self.suppression_rate, 4),
            "false_alarm_rate": round(self.false_alarm_rate, 4) if self.false_alarm_rate is not None else None,
        }


@dataclass
class SignalTimingRecord:
    """Tracks latency from signal appearance to detection and escalation."""
    signal_id: str
    signal_type: str  # "SERIOUS_ADVERSE_EVENT", "DATA_INTEGRITY_UNIT", "DATA_INTEGRITY_SITE", "HYS_LAW", etc.
    subject_or_site: str
    first_seen_cut: int
    detected_cut: int
    escalated_cut: Optional[int] = None
    resolved_cut: Optional[int] = None
    detection_latency_cuts: int = 0
    escalation_latency_cuts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "subject_or_site": self.subject_or_site,
            "first_seen_cut": self.first_seen_cut,
            "detected_cut": self.detected_cut,
            "escalated_cut": self.escalated_cut,
            "resolved_cut": self.resolved_cut,
            "detection_latency_cuts": self.detection_latency_cuts,
            "escalation_latency_cuts": self.escalation_latency_cuts,
        }


@dataclass
class SiteRiskRank:
    """Evidence-derived site attention ranking without invented clinical scores."""
    site_id: str
    rank: int
    status: str = "STABLE"  # "STABLE" | "WATCH" | "ATTENTION"
    risk_tier: str = "LOW"  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    reasons: List[str] = field(default_factory=list)
    is_quarantined: bool = False
    integrity_events_count: int = 0
    unanswered_queries_count: int = 0
    recurring_subjects_count: int = 0
    safety_findings_count: int = 0
    data_quality_findings_count: int = 0
    regularity_anomalies_count: int = 0
    last_incident_cut: Optional[int] = None
    quarantined_tests: List[str] = field(default_factory=list)
    quarantined_domains: List[str] = field(default_factory=list)
    affected_cuts: List[int] = field(default_factory=list)
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site": self.site_id,
            "site_id": self.site_id,
            "rank": self.rank,
            "status": self.status,
            "risk_tier": self.risk_tier,
            "reasons": self.reasons,
            "is_quarantined": self.is_quarantined,
            "open_queries": self.unanswered_queries_count,
            "unanswered_queries": self.unanswered_queries_count,
            "recurring_subjects": self.recurring_subjects_count,
            "integrity_events": self.integrity_events_count,
            "integrity_events_count": self.integrity_events_count,
            "unanswered_queries_count": self.unanswered_queries_count,
            "safety_findings": self.safety_findings_count,
            "data_quality_findings": self.data_quality_findings_count,
            "regularity_anomalies": self.regularity_anomalies_count,
            "last_incident_cut": self.last_incident_cut,
            "quarantined_tests": self.quarantined_tests,
            "quarantined_domains": self.quarantined_domains,
            "affected_cuts": self.affected_cuts,
            "evidence_refs": self.evidence_refs,
        }


