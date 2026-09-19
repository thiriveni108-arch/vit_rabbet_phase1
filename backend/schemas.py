"""Schema definitions for ATLAS Question, Answer, RecordRef, ParsedQuestion, and QueryPlan."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class RecordRef(BaseModel):
    """Represents an evidence reference.
    For clinical data: domain, usubjid, seq
    For document references: domain="DOC", document, section
    """
    domain: str
    usubjid: Optional[str] = None
    seq: Optional[int] = None
    document: Optional[str] = None
    section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"domain": self.domain}
        if self.usubjid is not None:
            d["usubjid"] = self.usubjid
        if self.seq is not None:
            d["seq"] = self.seq
        if self.document is not None:
            d["document"] = self.document
        if self.section is not None:
            d["section"] = self.section
        return d


class Question(BaseModel):
    """Input question format supporting both 'text' and 'question' field names."""
    question_id: Optional[str] = None
    text: str = Field(default="", alias="question")

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def __init__(self, **data):
        if "text" in data and "question" not in data:
            data["question"] = data["text"]
        super().__init__(**data)
        if not self.text and "question" in data:
            self.text = data["question"]


class QueryPlan(BaseModel):
    """Structured Query Plan model for transparent query execution without clinical arithmetic."""
    operation: str  # COUNT, LIST, LOOKUP, FILTER, AGGREGATE, COMPARE, TREND, FINDING, SUBJECT_SUMMARY, DOCUMENT_LOOKUP, STUDY_METADATA, AMBIGUOUS, UNSUPPORTED
    domain: Optional[str] = None
    subject_ids: List[str] = Field(default_factory=list)
    site_ids: List[str] = Field(default_factory=list)
    visits: List[str] = Field(default_factory=list)
    test_codes: List[str] = Field(default_factory=list)
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    aggregation: Optional[str] = None  # COUNT, AVG, MIN, MAX, SUM
    group_by: Optional[str] = None
    sort_by: Optional[str] = None
    sort_direction: Optional[str] = "ASC"
    limit: Optional[int] = None
    time_window_days: Optional[int] = None
    finding_type: Optional[str] = None
    temporal_modifier: Optional[str] = None  # LATEST, EARLIEST, BEFORE, AFTER, BETWEEN
    protocol_version: Optional[int] = None
    needs_evidence: bool = True
    ambiguities: List[str] = Field(default_factory=list)
    clarification_needed: Optional[str] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Answer(BaseModel):
    """Standard output Answer format conforming to competition specification."""
    question_id: Optional[str] = None
    answer: Any = []
    text: str = ""
    evidence: List[RecordRef] = []
    confidence: float = 1.0
    steps_used: int = 1
    tokens_used: int = 0
    intent: Optional[str] = None
    query_plan: Optional[Any] = None
    structured_data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "question_id": self.question_id,
            "answer": self.answer,
            "text": self.text,
            "evidence": [e.to_dict() if isinstance(e, RecordRef) else e for e in self.evidence],
            "confidence": self.confidence,
            "steps_used": self.steps_used,
            "tokens_used": self.tokens_used,
        }
        if self.intent is not None:
            d["intent"] = self.intent
        if self.query_plan is not None:
            if isinstance(self.query_plan, QueryPlan):
                d["query_plan"] = self.query_plan.to_dict()
            else:
                d["query_plan"] = self.query_plan
        if self.structured_data is not None:
            d["structured_data"] = self.structured_data
        return d


class ParsedQuestion(BaseModel):
    """Structured query representation parsed from natural language question."""
    question_id: Optional[str] = None
    intent: str  # COUNT, LIST, LOOKUP, FILTER, COMPARISON, TREND, AGGREGATE, SUBJECT_360, FINDING, DOCUMENT_LOOKUP, STUDY_METADATA, AMBIGUOUS, UNSUPPORTED, TRAP
    domain: Optional[str] = None
    usubjid: Optional[str] = None
    secondary_usubjid: Optional[str] = None
    site_id: Optional[str] = None
    visit: Optional[str] = None
    secondary_visit: Optional[str] = None
    test_code: Optional[str] = None
    secondary_test_code: Optional[str] = None
    operator: Optional[str] = None  # ">", ">=", "<", "<=", "==", "contains"
    numeric_value: Optional[float] = None
    threshold_type: Optional[str] = None  # "ULN", "RAW", "PROTOCOL"
    threshold_multiplier: Optional[float] = None
    secondary_multiplier: Optional[float] = None
    date_window_days: Optional[int] = None
    temporal_modifier: Optional[str] = None  # "LATEST", "EARLIEST", "TREND"
    aggregation: Optional[str] = None  # "AVG", "MAX", "MIN", "COUNT"
    group_by: Optional[str] = None
    criterion: Optional[str] = None
    window_days: Optional[int] = None
    field_filters: Optional[Dict[str, Any]] = None
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    invalid_site: Optional[str] = None
    invalid_visit: Optional[str] = None
    protocol_version: Optional[int] = None
    raw_text: str = ""
    clarification_needed: Optional[str] = None
    interpretation_note: Optional[str] = None
    category: Optional[str] = None
