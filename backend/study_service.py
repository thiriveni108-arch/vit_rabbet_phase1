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


class StudyService:
    """Unified shared backend service for Dashboard, Study Graph, Agent Chatbot, and Evidence."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DATA_DIR
        self.graph = StudyGraph(self.data_dir)
        self.graph.build()
        self.agent = Atlas(self.graph)

    def load(self, cut: Optional[int] = None) -> Dict[str, Any]:
        """Rebuilds the study graph at specified cut and synchronizes the agent."""
        stats = self.graph.build(cut=cut)
        # Update agent and dynamic metadata to point to the rebuilt graph state
        self.agent.sync_graph(self.graph)
        return stats

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
