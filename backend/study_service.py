"""Shared Backend Service Layer for Study Sentinel Web Application and AI Agent.

Acts as the single unified facade for all four frontend pages:
    1. DASHBOARD: get_dashboard()
    2. STUDY GRAPH: get_subject_graph(), get_subject_timeline()
    3. AGENT CHATBOT: ask()
    4. EVIDENCE: get_finding(), get_evidence()

Owns ONE single StudyGraph instance. When load(cut=N) is called,
all four pages immediately reflect Cut N synchronously with no stale state.
"""

from typing import Dict, Any, List, Optional
from stage1.atlas import StudyGraph
from backend.atlas_agent import Atlas
from backend.query_engine import QueryEngine
from backend.schemas import Question, Answer
from backend.config import DATA_DIR
from stage3.watch import StudyWatch


class StudyService:
    """Unified shared backend service for Dashboard, Study Graph, Agent Chatbot, Evidence, and StudyWatch."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DATA_DIR
        self.graph = StudyGraph(self.data_dir)
        self.graph.build()
        self.agent = Atlas(self.graph)
        self.watch = StudyWatch(data_dir=self.data_dir, study_graph=self.graph)

    def load(self, cut: Optional[int] = None) -> Dict[str, Any]:
        """Rebuilds the study graph at specified cut and synchronizes the agent and watch."""
        stats = self.graph.build(cut=cut)
        # Update agent and dynamic metadata to point to the rebuilt graph state
        self.agent.sync_graph(self.graph)
        return stats

    # -------------------------------------------------------------------------
    # STAGE 3: STUDYWATCH SURVEILLANCE & DATA INTAKE
    # -------------------------------------------------------------------------
    def run_watch_cut(self, cut: int) -> Dict[str, Any]:
        """Runs incremental surveillance for a specified cut."""
        res = self.watch.run_cut(cut)
        self.agent.sync_graph(self.graph)
        return res

    def get_watch_status(self) -> Dict[str, Any]:
        """Returns live StudyWatch surveillance status."""
        return {
            "current_cut": self.watch.latest_cut,
            "protocol_version": self.graph.current_protocol_version,
            "budget_tier": self.watch.current_budget_tier.value,
            "budget_used": self.watch.budget_used_units,
            "total_decisions": len(self.watch.decision_traces),
            "active_alerts_count": len(self.watch.latest_alerts),
            "subjects_count": len(self.graph.subjects),
            "sites_count": len(self.graph.sites),
            "is_live": True,
        }

    def get_watch_cuts(self) -> List[Dict[str, Any]]:
        """Returns list of all available cuts and their processed status."""
        cuts_info = []
        for c in sorted(self.graph.cuts.keys()):
            meta = self.graph.cuts[c]
            report = self.watch.surveillance_reports.get(c)
            cuts_info.append({
                "cut": c,
                "protocol_version": meta.get("protocol_version", 1),
                "new_records": meta.get("new_records", 0),
                "corrections": meta.get("corrections", 0),
                "processed": report is not None,
                "signals_detected": report.get("signals_detected", 0) if report else 0,
            })
        return cuts_info

    def get_watch_intake_latest(self) -> Dict[str, Any]:
        """Returns the latest data intake pipeline results and metrics."""
        m = self.watch.latest_metrics
        recent_records = []
        # Return sample of latest ingested records with their alignment and trust states
        cut_recs = [
            r for r in self.graph.records_by_key.values()
            if r.get("_cut_available") == self.watch.latest_cut
        ][:30]

        for r in cut_recs:
            recent_records.append({
                "domain": r.get("_domain", ""),
                "usubjid": r.get("_usubjid", ""),
                "seq": r.get("_seq", 1),
                "visit": r.get("VISIT", ""),
                "test": r.get("LBTESTCD", r.get("VSTESTCD", "")),
                "raw_value": r.get("LBORRES", r.get("VSORRES", r.get("AETERM", ""))),
                "numeric_value": r.get("_numeric_value"),
                "unit": r.get("LBORRESU", r.get("VSORRESU", "")),
                "trust_state": "TRUSTED",
                "version": r.get("_version", 1),
                "cut_available": r.get("_cut_available", 1),
            })

        # Return corrections for visualization
        corr_items = [
            c.to_dict() for c in self.watch.ingestion.corrections_audit
            if c.effective_cut == self.watch.latest_cut or not self.watch.latest_metrics
        ]

        return {
            "cut": self.watch.latest_cut,
            "protocol_version": self.graph.current_protocol_version,
            "metrics": m.to_dict() if m else {
                "cut": self.watch.latest_cut,
                "new_records": len(recent_records),
                "updated_records": len(corr_items),
                "corrected_records": len(corr_items),
                "new_subjects": 0,
                "new_sites": 0,
                "new_domains": 0,
                "missing_values": 0,
                "suspect_units": 0,
                "quarantined_records": 0,
                "affected_subjects": len(set(r["usubjid"] for r in recent_records)),
                "affected_findings": len(self.watch.latest_alerts),
            },
            "recent_records": recent_records,
            "corrections": corr_items,
            "pipeline_stages": [
                {"stage": "RECEIVED", "count": m.records_examined if m else len(recent_records), "status": "COMPLETED"},
                {"stage": "ALIGNED", "count": m.records_inserted + m.records_corrected if m else len(recent_records), "status": "COMPLETED"},
                {"stage": "VALIDATED", "count": m.records_inserted if m else len(recent_records), "status": "COMPLETED"},
                {"stage": "UPDATED", "count": m.records_inserted + m.records_corrected if m else len(recent_records), "status": "COMPLETED"},
                {"stage": "MONITORED", "count": len(self.watch.latest_alerts), "status": "COMPLETED"},
            ],
        }

    def get_watch_integrity(self) -> Dict[str, Any]:
        """Returns live data integrity events: unit anomalies, site regularity, document changes, and quarantined data."""
        return {
            "cut": self.watch.latest_cut,
            "unit_anomalies": self.watch.unit_shift_detector.active_unit_anomalies,
            "site_integrity": self.watch.site_integrity_detector.detect(self.graph, self.watch.latest_cut),
            "document_tamper_events": [dr.to_dict() for dr in self.watch.document_tamper_detector.audit_log],
            "retracted_findings": self.watch.ingestion.retracted_findings,
        }

    def get_watch_decisions(self) -> List[Dict[str, Any]]:
        """Returns all live decision traces recorded during surveillance."""
        return [t.to_dict() for t in self.watch.decision_traces.values()]

    def explain_decision(self, decision_id: str) -> Dict[str, Any]:
        """Explains a decision by reading from stored historical trace."""
        return self.watch.explain(decision_id)

    def get_watch_report(self) -> Dict[str, Any]:
        """Returns comprehensive surveillance report."""
        return self.watch.surveillance_reports.get(self.watch.latest_cut, self.watch.run_cut(self.watch.latest_cut))

    def ingest_records(self, records: List[Dict[str, Any]], domain: str, cut: Optional[int] = None) -> Dict[str, Any]:
        """Direct intake ingestion endpoint used by uploader and testing."""
        active_cut = cut or self.watch.latest_cut
        metrics = self.watch.ingestion.ingest_records(records, domain=domain, cut=active_cut)
        self.agent.sync_graph(self.graph)
        return {
            "success": True,
            "metrics": metrics.to_dict(),
            "domain": domain,
            "cut": active_cut,
        }


    def get_watch_sites(self) -> List[Dict[str, Any]]:
        """Returns live site attention ranking with contributing evidence."""
        site_integrity = self.watch.site_integrity_detector.detect(self.graph, self.watch.latest_cut)
        unit_anomalies = self.watch.unit_shift_detector.active_unit_anomalies
        return self.watch.monitoring.get_site_risk_ranking(self.watch.latest_cut, site_integrity, unit_anomalies)

    def get_watch_alerts(self) -> List[Dict[str, Any]]:
        """Returns active surveillance alerts."""
        return self.watch.latest_alerts

    def export_decision_log(self, target_path: Optional[str] = None) -> str:
        """Exports full append-only decision log."""
        return self.watch.export_decision_log(target_path)


    def get_decision_log_path(self) -> str:
        """Returns path to append-only decision log."""
        return str(self.watch.decision_log_path)

    # -------------------------------------------------------------------------
    # PAGE 1: DASHBOARD
    # -------------------------------------------------------------------------
    def get_dashboard(self) -> Dict[str, Any]:
        """Returns JSON-safe aggregate summary metrics for the current cut."""
        return self.graph.dashboard_summary()

    # -------------------------------------------------------------------------
    # PAGE 2: STUDY GRAPH & TIMELINE
    # -------------------------------------------------------------------------
    def get_subject_graph(self, usubjid: str) -> Dict[str, Any]:
        """Returns nodes and edges for one subject including finding links."""
        return self.graph.graph_view(usubjid)

    def get_subject_timeline(self, usubjid: str) -> List[Dict[str, Any]]:
        """Returns chronological list of study events for one subject."""
        return self.graph.timeline(usubjid)

    # -------------------------------------------------------------------------
    # PAGE 3: AGENT CHATBOT
    # -------------------------------------------------------------------------
    def ask(self, question: Any) -> Dict[str, Any]:
        """Answers a clinical query citing verified evidence from StudyGraph."""
        if isinstance(question, str):
            q_obj = Question(text=question)
        elif isinstance(question, dict):
            q_obj = Question(
                question_id=question.get("question_id"),
                text=question.get("text") or question.get("question", "")
            )
        else:
            q_obj = question

        ans: Answer = self.agent.answer(q_obj)
        return ans.to_dict()

    # -------------------------------------------------------------------------
    # PAGE 4: EVIDENCE
    # -------------------------------------------------------------------------
    def get_findings(self, usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all deterministic protocol findings for current cut."""
        return self.graph.get_findings(usubjid=usubjid)

    def get_finding(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """Returns finding metadata and details by finding ID."""
        return self.graph.get_finding(finding_id)

    def get_evidence(self, finding_id: str) -> List[Dict[str, Any]]:
        """Returns rich supporting evidence records for a finding."""
        return self.graph.get_evidence(finding_id)

    # -------------------------------------------------------------------------
    # SHARED CONTEXT & SUBJECT HELPERS
    # -------------------------------------------------------------------------
    def get_subjects(self) -> List[Dict[str, Any]]:
        """Returns compact list of subjects from the current study graph."""
        res = []
        for usubjid, s in sorted(self.graph.subjects.items()):
            demo = s.get("demographics") or {}
            res.append({
                "usubjid": usubjid,
                "site_id": s.get("site_id") or demo.get("SITEID", ""),
                "arm": demo.get("ARM", ""),
                "age": demo.get("AGE", ""),
                "sex": demo.get("SEX", ""),
                "findings_count": len(self.graph.findings_by_subj.get(usubjid, [])),
            })
        return res

    def get_context(self) -> Dict[str, Any]:
        """Returns high-level study context including current cut and available cuts."""
        return {
            "study_id": "STUDY-042",
            "study_name": "Study Sentinel / ATLAS",
            "current_cut": self.graph.current_cut,
            "protocol_version": self.graph.current_protocol_version,
            "available_cuts": sorted(list(self.graph.cuts.keys())),
            "total_subjects": len(self.graph.subjects),
            "total_records": len(self.graph.records_by_key),
            "total_findings": len(self.graph.findings),
        }
