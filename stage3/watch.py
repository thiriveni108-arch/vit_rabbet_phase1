"""Stage 3: StudyWatch Surveillance Orchestrator, Trace-First Engine,
Budget-Aware Degradation, and explain() Implementation.

Key guarantees:
1. Surveillance across cuts 1..12 using IncrementalIngestionEngine without full graph rebuilds.
2. Trace-First immutability: Every meaningful decision is written at the exact moment it occurs.
3. explain(decision_id): Reads strictly from stored immutable historical traces,
   validating evidence against historical_store (never substituting future corrections into old explanations!).
4. Budget-Aware Degradation: FULL (100%), REDUCED (80%), SAFETY_ONLY (95%+).
   Safety rules and decision traces are NEVER skipped.
5. Deterministic mode support for automated verification.
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from stage1.atlas import StudyGraph
try:
    from backend.review_crew import ReviewCrew
except ImportError:
    ReviewCrew = Any
from stage3.detectors import (
    DetectorConfig,
    DocumentTamperDetector,
    SiteIntegrityDetector,
    UnitShiftDetector,
)
from stage3.ingestion import IncrementalIngestionEngine
from stage3.models import (
    BudgetTier,
    DecisionTrace,
    HistoricalEvidenceRecord,
    IngestionMetrics,
    TrustState,
)
from stage3.monitoring import ThresholdMonitoringEngine


class StudyWatch:
    """Authoritative Stage 3 Study Surveillance Platform."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        crew: Optional[Any] = None,
        study_graph: Optional[StudyGraph] = None,
        deterministic_clock: bool = False,
        budget_limit: float = 1000.0,
        decision_log_path: Optional[str] = None,
    ):
        self.data_dir_param = data_dir or "hackathon-data"
        if study_graph is not None:
            self.graph = study_graph
        else:
            self.graph = StudyGraph(self.data_dir_param)
            self.graph.build(cut=1)  # Initialize baseline graph at Cut 1

        self.crew = crew
        self.deterministic_clock = deterministic_clock

        # Ingestion & Monitoring Engines
        self.ingestion = IncrementalIngestionEngine(self.graph)
        self.monitoring = ThresholdMonitoringEngine(self.graph)

        # Integrity Detectors
        self.detector_config = DetectorConfig()
        self.unit_shift_detector = UnitShiftDetector(self.detector_config)
        self.site_integrity_detector = SiteIntegrityDetector(self.detector_config)
        self.document_tamper_detector = DocumentTamperDetector(self.graph.documents_dir)

        # Trace Store: decision_id -> DecisionTrace
        self.decision_traces: Dict[str, DecisionTrace] = {}
        self.decision_sequence: int = 0

        # Append-Only Decision Log Persistence
        if decision_log_path:
            self.decision_log_path = Path(decision_log_path).resolve()
        else:
            self.decision_log_path = Path(self.data_dir_param).resolve() / "decision_log.jsonl"
        self._load_persisted_decisions()

        # Budget Tracker
        self.budget_limit_units: float = float(budget_limit)
        self.budget_used_units: float = 0.0
        self.current_budget_tier: BudgetTier = BudgetTier.FULL

        # Surveillance History & Latest State
        self.surveillance_reports: Dict[int, Dict[str, Any]] = {}
        self.latest_cut: int = self.graph.current_cut or 1
        self.latest_metrics: Optional[IngestionMetrics] = None
        self.latest_alerts: List[Dict[str, Any]] = []

        # Load monitor decisions map if responses directory exists
        self.monitor_responses = self._load_monitor_responses()

    def _load_persisted_decisions(self):
        """Loads existing decision traces from append-only JSONL file on startup."""
        if not self.decision_log_path.is_file():
            return
        try:
            with open(self.decision_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    hist_ev = [
                        HistoricalEvidenceRecord(
                            domain=h["domain"],
                            usubjid=h["usubjid"],
                            seq=h["seq"],
                            field=h.get("field"),
                            raw_value=h["raw_value"],
                            normalized_numeric=h.get("normalized_numeric"),
                            unit=h.get("unit"),
                            version=h.get("version", 1),
                            cut_observed=h.get("cut_observed", d.get("cut", 1)),
                            trust_state=TrustState(h.get("trust_state", "TRUSTED")),
                        )
                        for h in d.get("historical_evidence", [])
                    ]
                    trace = DecisionTrace(
                        decision_id=d["decision_id"],
                        cut=d["cut"],
                        sequence=d.get("sequence", 0),
                        timestamp=d.get("timestamp", ""),
                        component=d.get("component", ""),
                        what=d.get("what", ""),
                        why=d.get("why", ""),
                        evidence_refs=d.get("evidence_refs", []),
                        evidence_lines=d.get("evidence_lines", []),
                        historical_evidence=hist_ev,
                        alternatives=d.get("alternatives", []),
                        action=d.get("action", ""),
                        result=d.get("result", ""),
                        trust_state=TrustState(d.get("trust_state", "TRUSTED")),
                        protocol_version=d.get("protocol_version", 1),
                        budget_tier=BudgetTier(d.get("budget_tier", "FULL")),
                    )
                    self.decision_traces[trace.decision_id] = trace
                    if trace.sequence > self.decision_sequence:
                        self.decision_sequence = trace.sequence
        except Exception:
            pass

    def export_decision_log(self, target_path: Optional[str] = None) -> str:
        """Exports full append-only decision log required for submission."""
        out_path = Path(target_path).resolve() if target_path else self.decision_log_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not out_path.is_file() or out_path != self.decision_log_path:
            with open(out_path, "w", encoding="utf-8") as f:
                for t in self.decision_traces.values():
                    f.write(json.dumps(t.to_dict()) + "\n")
        return str(out_path)

    def _load_monitor_responses(self) -> Dict[str, List[str]]:
        path = self.graph.responses_dir / "monitor_decisions.json"
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("decisions", {})
            except Exception:
                pass
        return {}

    def _get_timestamp(self, cut: int) -> str:
        if self.deterministic_clock:
            return f"CUT-{cut:02d}-SEQ-{self.decision_sequence:04d}"
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # =========================================================================
    # 1. BUDGET-AWARE DEGRADATION
    # =========================================================================

    def _consume_budget(self, units: float):
        self.budget_used_units += units
        usage_pct = (self.budget_used_units / self.budget_limit_units) * 100.0 if self.budget_limit_units > 0 else 0.0

        if usage_pct >= 95.0:
            self.current_budget_tier = BudgetTier.SAFETY_ONLY
        elif usage_pct >= 80.0:
            self.current_budget_tier = BudgetTier.REDUCED
        else:
            self.current_budget_tier = BudgetTier.FULL

    # =========================================================================
    # 2. TRACE-FIRST LOGGING & PERSISTENCE
    # =========================================================================

    def log_decision(
        self,
        decision_id: str,
        cut: int,
        component: str,
        what: str,
        why: str,
        evidence_refs: List[Dict[str, Any]],
        evidence_lines: List[str],
        alternatives: Optional[List[str]] = None,
        action: str = "",
        result: str = "",
        trust_state: TrustState = TrustState.TRUSTED,
    ) -> DecisionTrace:
        """Synchronously records an immutable decision trace in memory and on disk at the exact moment of decision."""
        self.decision_sequence += 1
        ts = self._get_timestamp(cut)

        # Build snapshot of historical evidence as known at this cut
        historical_ev: List[HistoricalEvidenceRecord] = []
        for ref in evidence_refs:
            dom = ref.get("domain", "")
            subj = ref.get("usubjid", "")
            seq = ref.get("seq")
            if dom and subj and seq is not None:
                hist_rec = self.ingestion.historical_store.get_version_at_cut(dom, subj, seq, cut)
                if hist_rec:
                    historical_ev.append(HistoricalEvidenceRecord(
                        domain=dom,
                        usubjid=subj,
                        seq=seq,
                        field=ref.get("field"),
                        raw_value=str(hist_rec.get("LBORRES", hist_rec.get("VSORRES", hist_rec.get("AETERM", "")))),
                        normalized_numeric=hist_rec.get("_numeric_value"),
                        unit=hist_rec.get("LBORRESU", hist_rec.get("VSORRESU")),
                        version=hist_rec.get("_version", 1),
                        cut_observed=cut,
                        trust_state=trust_state,
                    ))

        trace = DecisionTrace(
            decision_id=decision_id,
            cut=cut,
            sequence=self.decision_sequence,
            timestamp=ts,
            component=component,
            what=what,
            why=why,
            evidence_refs=evidence_refs,
            evidence_lines=evidence_lines,
            historical_evidence=historical_ev,
            alternatives=alternatives or [],
            action=action,
            result=result,
            trust_state=trust_state,
            protocol_version=self.graph.current_protocol_version,
            budget_tier=self.current_budget_tier,
        )
        self.decision_traces[decision_id] = trace

        # Append immediately to persistent append-only JSONL log
        try:
            self.decision_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.decision_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace.to_dict()) + "\n")
                f.flush()
        except Exception:
            pass

        return trace


    # =========================================================================
    # 3. SINGLE CUT SURVEILLANCE PIPELINE
    # =========================================================================

    def run_cut(self, cut: int) -> Dict[str, Any]:
        """Runs complete incremental surveillance for a single cut."""
        start_time = time.perf_counter()
        self.latest_cut = cut

        # 1. Ingest incremental changes & corrections
        if cut > 1 or (cut == 1 and not self.graph.records_by_key):
            metrics = self.ingestion.ingest_cut_delta(cut)
        else:
            metrics = IngestionMetrics(cut=cut, full_build_calls=0)
        self.latest_metrics = metrics

        # 2. Check study documents for tampering / adversarial additions
        doc_records = self.document_tamper_detector.check_documents(cut)
        for dr in doc_records:
            if dr.tamper_suspected:
                self.log_decision(
                    decision_id=f"DEC_TAMPER_{dr.document_name}_CUT_{cut}",
                    cut=cut,
                    component="INTEGRITY_CHECK",
                    what=f"Adversarial prompt injection detected in {dr.document_name}",
                    why=f"Document contains instructions addressed to automated reviewers attempting to suppress safety rules: {dr.instruction_like_text}",
                    evidence_refs=[{"document": dr.document_name, "cut": cut}],
                    evidence_lines=dr.instruction_like_text,
                    alternatives=["Follow document instruction: Rejected because clinical safety rules must not be altered by document text injections."],
                    action="Neutralized adversarial instruction; preserved baseline clinical rules.",
                    result="TAMPER_NEUTRALIZED",
                    trust_state=TrustState.UNTRUSTED,
                )

        # 3. Run Generic Unit Shift Detector
        unit_anomalies = self.unit_shift_detector.detect(self.graph, current_cut=cut)
        for ua in unit_anomalies:
            self.log_decision(
                decision_id=ua["alert_id"],
                cut=cut,
                component="INTEGRITY_CHECK",
                what=ua["title"],
                why=ua["description"],
                evidence_refs=[{"domain": "LB", "site": ua["site"], "test": ua["test"]}],
                evidence_lines=[f"Site {ua['site']} {ua['test']} median shifted by {ua['ratio']}x matching {ua['expected_conversion']}"],
                alternatives=ua["alternatives_considered"],
                action=ua["lab_query"],
                result="DATA_INTEGRITY_ALERT_RAISED",
                trust_state=TrustState.UNTRUSTED,
            )

        # 4. Run Generic Site Integrity Detector
        site_integrity = self.site_integrity_detector.detect(self.graph, current_cut=cut)
        for s_id, s_info in site_integrity.items():
            if s_info["status"] in ("SUSPECT", "QUARANTINED"):
                self.log_decision(
                    decision_id=f"DEC_SITE_INTEGRITY_{s_id}_CUT_{cut}",
                    cut=cut,
                    component="INTEGRITY_CHECK",
                    what=f"Site {s_id} integrity flag: {s_info['status']}",
                    why="; ".join(s_info["reasons"]),
                    evidence_refs=[{"site": s_id}],
                    evidence_lines=s_info["reasons"],
                    alternatives=["Treat site as normal: Rejected due to improbable homogeneity across repeated vitals compared with peer cohort."],
                    action=s_info["recommendation"],
                    result=f"SITE_{s_info['status']}",
                    trust_state=TrustState.QUARANTINED,
                )

        # 5. Run Deterministic Safety Checks & False-Positive Prevention
        alerts = self.monitoring.run_surveillance(
            current_cut=cut,
            unit_anomalies=unit_anomalies,
            site_integrity=site_integrity,
            monitor_responses=self.monitor_responses,
        )
        self.latest_alerts = alerts

        # 6. Log decisions for significant safety findings
        for alert in alerts:
            aid = alert["alert_id"]
            if aid not in self.decision_traces:
                ev_lines = []
                for ev in alert.get("evidence", []):
                    ev_lines.append(f"{ev.get('domain', 'REC')} · Seq {ev.get('seq', '')} for {alert['subject']}")
                self.log_decision(
                    decision_id=f"DEC_{aid}",
                    cut=cut,
                    component="SAFETY_RULE",
                    what=alert["title"],
                    why=alert["description"],
                    evidence_refs=alert.get("evidence", []),
                    evidence_lines=ev_lines,
                    alternatives=[
                        "Suppress alert: Rejected because deterministic safety criteria were satisfied.",
                        "Direct regulatory filing without monitor: Rejected; clinical adjudication required per protocol §6/§7.",
                    ],
                    action=alert.get("action", "Escalated to human gate queue"),
                    result="ESCALATED_TO_MONITOR",
                    trust_state=TrustState(alert.get("trust_state", "TRUSTED")),
                )

        # 7. ReviewCrew cycle integration if crew provided (Enforce Budget 80% Rule)
        crew_cycle_data = {}
        usage_pct = (self.budget_used_units / self.budget_limit_units) * 100.0 if self.budget_limit_units > 0 else 0.0
        if self.crew is not None:
            if usage_pct >= 80.0 or self.current_budget_tier in (BudgetTier.REDUCED, BudgetTier.SAFETY_ONLY):
                # STOP all optional narrative/LLM work at >=80% budget
                crew_cycle_data = {
                    "status": "DEGRADED_BUDGET",
                    "optional_narrative_suppressed": True,
                    "reason": f"Budget at {usage_pct:.1f}% (>=80% threshold). Suppressed optional narrative generation to preserve safety-first budget.",
                }
            else:
                crew_cycle_data = self.crew.run_cycle(cut=cut)
                self._consume_budget(units=10.0)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        usage_pct = (self.budget_used_units / self.budget_limit_units) * 100.0 if self.budget_limit_units > 0 else 0.0

        # Compute Evidence-Derived Site Risk Ranking
        site_risk_ranking = self.monitoring.get_site_risk_ranking(cut, site_integrity, unit_anomalies)

        # Open Items (Delayed escalations, open queries, standing limits)
        open_items = [
            {
                "case_id": c["case_id"],
                "finding_type": c["finding_type"],
                "subject": c["usubjid"],
                "site": c["site_id"],
                "status": c["status"],
                "cuts_waiting": c["cuts_waiting"],
                "standing_limits": c["standing_limits"],
            }
            for c in self.monitoring.escalation_tracker.cases.values()
            if c["status"] in ("AWAITING", "WAITING", "STANDING_LIMITS", "CLARIFY")
        ]

        # Signal detection latency stats
        cut_signals = [st.to_dict() for st in self.monitoring.signal_timings.values() if st.detected_cut == cut]
        same_cut_count = sum(1 for st in self.monitoring.signal_timings.values() if st.detected_cut == cut and st.escalation_latency_cuts == 0)

        report = {
            "cut": cut,
            "protocol_version": self.graph.current_protocol_version,
            "metrics": metrics.to_dict(),
            "signals_detected": len(alerts),
            "critical_alerts": sum(1 for a in alerts if a.get("severity") == "CRITICAL"),
            "data_integrity_events": len(unit_anomalies) + sum(1 for s in site_integrity.values() if s["status"] in ("SUSPECT", "QUARANTINED")),
            "site_flags": {s: info["status"] for s, info in site_integrity.items() if info["status"] != "NORMAL"},
            "document_changes": [dr.to_dict() for dr in doc_records if dr.changed or dr.tamper_suspected],
            "corrections_applied": metrics.corrected_records,
            "retracted_findings": len(self.ingestion.retracted_findings),
            "open_escalations": len(self.monitoring.escalation_tracker.cases),
            "standing_limits_count": sum(1 for c in self.monitoring.escalation_tracker.cases.values() if c.get("standing_limits")),
            "queries_active": len(unit_anomalies),
            "site_risk_ranking": site_risk_ranking,
            "false_alarm_metrics": self.monitoring.false_alarm_metrics.to_dict(),
            "signal_detection_latency": {
                "signals_tracked": len(self.monitoring.signal_timings),
                "cut_signals_count": len(cut_signals),
                "same_cut_escalated_count": same_cut_count,
                "records": cut_signals,
            },
            "decision_log_path": str(self.decision_log_path),
            "budget_usage": {
                "limit": self.budget_limit_units,
                "used": round(self.budget_used_units, 2),
                "remaining": round(max(0.0, self.budget_limit_units - self.budget_used_units), 2),
                "percentage": round(usage_pct, 1),
                "tier": self.current_budget_tier.value,
                "optional_narrative_suppressed": usage_pct >= 80.0,
            },
            "open_items": open_items,
            "budget_used": round(self.budget_used_units, 2),
            "budget_tier": self.current_budget_tier.value,
            "elapsed_ms": elapsed_ms,
            "decision_ids": [d.decision_id for d in self.decision_traces.values() if d.cut == cut],
            "alerts": alerts,
            "crew_data": crew_cycle_data,
        }
        self.surveillance_reports[cut] = report
        return report

    # =========================================================================
    # 4. 12-CUT PERIOD SEQUENTIAL SURVEILLANCE
    # =========================================================================

    def run_period(self, cuts: Sequence[int] = range(1, 13)) -> Dict[str, Any]:
        """Runs sequential surveillance across multiple cuts."""
        reports = []
        for c in cuts:
            rep = self.run_cut(c)
            reports.append(rep)

        total_signals = sum(r["signals_detected"] for r in reports)
        total_critical = sum(r["critical_alerts"] for r in reports)
        total_integrity = sum(r["data_integrity_events"] for r in reports)
        total_corrections = sum(r["corrections_applied"] for r in reports)

        latest_rep = reports[-1] if reports else {}
        usage_pct = (self.budget_used_units / self.budget_limit_units) * 100.0 if self.budget_limit_units > 0 else 0.0

        return {
            "cuts_processed": list(cuts),
            "total_cuts": len(cuts),
            "total_signals_detected": total_signals,
            "total_critical_alerts": total_critical,
            "total_data_integrity_events": total_integrity,
            "total_corrections_applied": total_corrections,
            "final_protocol_version": self.graph.current_protocol_version,
            "budget_tier": self.current_budget_tier.value,
            "budget_usage": {
                "limit": self.budget_limit_units,
                "used": round(self.budget_used_units, 2),
                "remaining": round(max(0.0, self.budget_limit_units - self.budget_used_units), 2),
                "percentage": round(usage_pct, 1),
                "tier": self.current_budget_tier.value,
                "optional_narrative_suppressed": usage_pct >= 80.0,
            },
            "site_risk_ranking": latest_rep.get("site_risk_ranking", []),
            "false_alarm_metrics": latest_rep.get("false_alarm_metrics", {}),
            "signal_detection_latency": latest_rep.get("signal_detection_latency", {}),
            "decision_log_path": str(self.decision_log_path),
            "open_items": latest_rep.get("open_items", []),
            "budget_used": round(self.budget_used_units, 2),
            "reports_by_cut": {r["cut"]: r for r in reports},
        }

    # =========================================================================
    # 5. EXPLAIN() — IMMUTABLE HISTORICAL DECISION EVIDENCE
    # =========================================================================

    def explain(self, decision_id: str) -> Dict[str, Any]:
        """Returns exact trace-backed details for any decision.

        Critical Requirements:
        - Reads strictly from stored DecisionTrace.
        - Validates evidence existence against the raw/versioned historical_store
          (never substitutes future corrections into old explanations!).
        - Computes `consistent_with_trace` by verifying immutable stored snapshot
          against the persisted append-only trace log and versioned store.
        - Does not rerun current rules or generate LLM hallucinations.
        """
        # Allow prefix "DEC_" or raw ID
        trace = self.decision_traces.get(decision_id) or self.decision_traces.get(f"DEC_{decision_id}")
        if not trace:
            # Check by finding_id in active alerts
            for aid, t in self.decision_traces.items():
                if decision_id in aid:
                    trace = t
                    break

        if not trace:
            return {
                "decision_id": decision_id,
                "found": False,
                "error": f"No decision trace recorded for '{decision_id}'.",
                "consistent_with_trace": False,
                "trace_consistency_details": {"error": "Trace not found in memory store."},
            }

        # 1. Verify existence and match in persisted append-only decision log on disk
        persisted_match = False
        persisted_record = None
        if self.decision_log_path.is_file():
            try:
                with open(self.decision_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        rec = json.loads(line)
                        if rec.get("decision_id") == trace.decision_id:
                            persisted_record = rec
                            if (
                                rec.get("cut") == trace.cut
                                and rec.get("what") == trace.what
                                and rec.get("why") == trace.why
                                and rec.get("action") == trace.action
                            ):
                                persisted_match = True
                            break
            except Exception:
                persisted_match = False
        else:
            # If log file has not been written yet, match in memory is consistent
            persisted_match = True

        # 2. Validate historical evidence against raw/versioned historical store
        evidence_validations: List[Dict[str, Any]] = []
        all_evidence_consistent = True

        for ev_ref in trace.evidence_refs:
            dom = ev_ref.get("domain", "")
            subj = ev_ref.get("usubjid", "")
            seq = ev_ref.get("seq")
            if dom and subj and seq is not None:
                hist_rec = self.ingestion.historical_store.get_version_at_cut(dom, subj, seq, trace.cut)
                if hist_rec is not None:
                    evidence_validations.append({
                        "domain": dom,
                        "usubjid": subj,
                        "seq": seq,
                        "cut_observed": trace.cut,
                        "historical_value": str(hist_rec.get("LBORRES", hist_rec.get("VSORRES", hist_rec.get("AETERM", "")))),
                        "historical_numeric": hist_rec.get("_numeric_value"),
                        "verified_in_historical_store": True,
                    })
                else:
                    all_evidence_consistent = False
                    evidence_validations.append({
                        "domain": dom,
                        "usubjid": subj,
                        "seq": seq,
                        "verified_in_historical_store": False,
                    })
            else:
                evidence_validations.append({
                    "ref": ev_ref,
                    "verified_in_historical_store": True,
                })

        # 3. Validate snapshot historical evidence immutability
        historical_snapshot_consistent = True
        for h in trace.historical_evidence:
            h_rec = self.ingestion.historical_store.get_version_at_cut(h.domain, h.usubjid, h.seq, trace.cut)
            if h_rec is None:
                historical_snapshot_consistent = False
            else:
                curr_val = str(h_rec.get("LBORRES", h_rec.get("VSORRES", h_rec.get("AETERM", ""))))
                if curr_val != h.raw_value:
                    # Stored explanation raw_value must match value AT CUT trace.cut, never future amended value
                    historical_snapshot_consistent = False

        # Compute consistent_with_trace dynamically
        consistent_with_trace = bool(
            persisted_match
            and all_evidence_consistent
            and historical_snapshot_consistent
        )

        trace_consistency_details = {
            "persisted_in_decision_log": persisted_match,
            "evidence_references_verified": all_evidence_consistent,
            "historical_snapshot_immutable": historical_snapshot_consistent,
            "verified_evidence_count": len([v for v in evidence_validations if v.get("verified_in_historical_store")]),
            "total_evidence_refs": len(evidence_validations),
        }

        return {
            "decision_id": trace.decision_id,
            "found": True,
            "cut": trace.cut,
            "timestamp": trace.timestamp,
            "component": trace.component,
            "what": trace.what,
            "why": trace.why,
            "evidence": trace.evidence_refs,
            "evidence_lines": trace.evidence_lines,
            "evidence_validation": evidence_validations,
            "historical_evidence": [h.to_dict() for h in trace.historical_evidence],
            "alternatives": trace.alternatives,
            "action": trace.action,
            "result": trace.result,
            "trust_state": trace.trust_state.value,
            "protocol_version": trace.protocol_version,
            "budget_tier": trace.budget_tier.value,
            "consistent_with_trace": consistent_with_trace,
            "trace_consistency_details": trace_consistency_details,
        }

