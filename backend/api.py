"""FastAPI HTTP Backend Service for Study Sentinel.

Thin adapter delegating all queries directly to the authoritative StudyService.
Maintains a single module-level StudyService instance with no clinical logic in routes.
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.study_service import StudyService

# Single authoritative service instance initialized at Cut 12
service = StudyService()
service.load(cut=12)

app = FastAPI(
    title="Study Sentinel Clinical Intelligence API",
    version="1.0.0",
    description="Live backend API powered by StudyGraph single source of truth.",
)

# CORS middleware for local development (FastAPI 8000 <-> Vite 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: Optional[str] = None
    text: Optional[str] = None


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "cut": service.graph.current_cut,
        "protocol_version": service.graph.current_protocol_version,
        "subjects": len(service.graph.subjects),
        "findings": len(service.graph.findings),
    }


@app.get("/api/context")
def get_context() -> Dict[str, Any]:
    """Returns study context, protocol version, and current cut info."""
    return service.get_context()


@app.get("/api/dashboard")
def get_dashboard() -> Dict[str, Any]:
    """Returns Page 1 Dashboard aggregate metrics for the active cut."""
    return service.get_dashboard()


@app.post("/api/cut/{cut}")
def set_cut(cut: int = Path(..., ge=1, le=12)) -> Dict[str, Any]:
    """Switches the active cut across the entire backend synchronously."""
    stats = service.load(cut=cut)
    return {
        "success": True,
        "cut": cut,
        "stats": stats,
        "dashboard": service.get_dashboard(),
    }


@app.get("/api/subjects")
def get_subjects() -> List[Dict[str, Any]]:
    """Returns compact list of all enrolled subjects in current snapshot."""
    return service.get_subjects()


@app.get("/api/subjects/{usubjid}/graph")
def get_subject_graph(usubjid: str) -> Dict[str, Any]:
    """Returns Page 2 Study Graph network nodes and edges for a subject."""
    return service.get_subject_graph(usubjid)


@app.get("/api/subjects/{usubjid}/timeline")
def get_subject_timeline(usubjid: str) -> List[Dict[str, Any]]:
    """Returns Page 2 Subject chronological event timeline."""
    return service.get_subject_timeline(usubjid)


@app.get("/api/findings")
def get_findings(usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns Page 4 clinical and protocol findings list."""
    return service.get_findings(usubjid=usubjid)


@app.get("/api/findings/{finding_id}")
def get_finding(finding_id: str) -> Dict[str, Any]:
    """Returns metadata for a specific finding."""
    f = service.get_finding(finding_id)
    if not f:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found.")
    return f


@app.get("/api/findings/{finding_id}/evidence")
def get_finding_evidence(finding_id: str) -> List[Dict[str, Any]]:
    """Returns rich evidence records supporting a finding."""
    return service.get_evidence(finding_id)


@app.post("/api/ask")
def ask_atlas(req: AskRequest) -> Dict[str, Any]:
    """Page 3 Atlas Agent natural-language query endpoint."""
    q_str = req.question or req.text or ""
    if not q_str.strip():
        raise HTTPException(status_code=400, detail="Question string cannot be empty.")
    return service.ask(q_str)


# -------------------------------------------------------------------------
# STAGE 2: REVIEW CENTER & SAFEGUARDS ENDPOINTS
# -------------------------------------------------------------------------
from backend.review_crew import ReviewCrew

review_crew = ReviewCrew(study_graph=service.graph)


@app.get("/api/review")
def get_review_data(cut: Optional[int] = None) -> Dict[str, Any]:
    """Returns complete Stage 2 Review Center data for the requested cut."""
    return review_crew.run_cycle(cut=cut)


@app.post("/api/review/rerun")
def rerun_review_cut(cut: Optional[int] = None) -> Dict[str, Any]:
    """Demonstrates Stage 2 ReviewMemory persistence by re-running current cut with 0 repeated work."""
    return review_crew.rerun_cut_check(cut=cut)


# -------------------------------------------------------------------------
# STAGE 3: STUDYWATCH SURVEILLANCE & DATA INTAKE ENDPOINTS
# -------------------------------------------------------------------------

class IngestRequest(BaseModel):
    records: List[Dict[str, Any]]
    domain: str
    cut: Optional[int] = None


@app.get("/api/watch/status")
def get_watch_status() -> Dict[str, Any]:
    """Returns current surveillance and ingestion state."""
    return service.get_watch_status()


@app.get("/api/watch/cuts")
def get_watch_cuts() -> List[Dict[str, Any]]:
    """Returns available cuts and surveillance status."""
    return service.get_watch_cuts()


@app.post("/api/watch/run-cut/{cut}")
def run_watch_cut(cut: int = Path(..., ge=1, le=12)) -> Dict[str, Any]:
    """Runs incremental surveillance for a specific cut."""
    return service.run_watch_cut(cut)


@app.get("/api/watch/intake/latest")
def get_watch_intake_latest() -> Dict[str, Any]:
    """Returns data intake pipeline results, counts, and recent records."""
    return service.get_watch_intake_latest()


@app.post("/api/watch/ingest")
def ingest_records_api(req: IngestRequest) -> Dict[str, Any]:
    """Manual/website uploader intake endpoint calling IncrementalIngestionEngine."""
    if not req.records:
        raise HTTPException(status_code=400, detail="No records provided.")
    return service.ingest_records(req.records, domain=req.domain, cut=req.cut)


@app.get("/api/watch/integrity")
def get_watch_integrity() -> Dict[str, Any]:
    """Returns unit shift anomalies, suspicious sites, and document tamper events."""
    return service.get_watch_integrity()


@app.get("/api/watch/decisions")
def get_watch_decisions() -> List[Dict[str, Any]]:
    """Returns all trace-first decisions recorded during surveillance."""
    return service.get_watch_decisions()


@app.get("/api/watch/decisions/{decision_id}")
def get_watch_decision(decision_id: str) -> Dict[str, Any]:
    """Returns a specific decision trace by ID."""
    traces = {t["decision_id"]: t for t in service.get_watch_decisions()}
    if decision_id not in traces:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found.")
    return traces[decision_id]


@app.get("/api/watch/decisions/{decision_id}/explain")
def explain_watch_decision(decision_id: str) -> Dict[str, Any]:
    """Explains a decision by reading from immutable historical decision record."""
    exp = service.explain_decision(decision_id)
    if not exp.get("found", True):
        raise HTTPException(status_code=404, detail=exp.get("error", "Decision not found"))
    return exp


@app.get("/api/watch/report")
def get_watch_report() -> Dict[str, Any]:
    """Returns the comprehensive surveillance report."""
    return service.get_watch_report()


@app.get("/api/watch/sites")
def get_watch_sites() -> List[Dict[str, Any]]:
    """Returns live site attention ranking with real contributing evidence."""
    return service.get_watch_sites()


@app.get("/api/watch/alerts")
def get_watch_alerts() -> List[Dict[str, Any]]:
    """Returns active clinical safety and data integrity alerts."""
    return service.get_watch_alerts()


@app.get("/api/watch/export-decisions")
def export_watch_decisions() -> Dict[str, Any]:
    """Exports and returns details of the persistent append-only decision log."""
    path = service.export_decision_log()
    return {
        "success": True,
        "decision_log_path": path,
        "total_persisted_decisions": len(service.watch.decision_traces),
    }




