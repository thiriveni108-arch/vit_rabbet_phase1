"""
LOCAL COMPATIBILITY SHIM — organizer starter schemas were not included
in the supplied package. Replace with official schemas if provided.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict


@dataclass
class RecordRef:
    """Reference identifying evidence in a clinical study dataset or document.

    Clinical data reference:
        domain: e.g. "LB", "AE", "DM", "VS", "EX", "CM", "DS", "MH", "EG"
        usubjid: Subject ID, e.g. "042-S07-001"
        seq: Sequence number in the domain (e.g. LBSEQ)

    Document reference:
        domain: "DOC"
        document: Document name (e.g. "lab-manual", "protocol_v1")
        section: Section name / identifier (e.g. "units", "7")
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


@dataclass
class Question:
    """Clinical review question submitted to Atlas."""
    question_id: str
    text: str
    kind: Optional[str] = None  # "count", "lookup", "finding", "trap"


@dataclass
class Answer:
    """Schema-compliant answer returned by Atlas."""
    question_id: str
    answer: Any
    text: str
    evidence: List[RecordRef] = field(default_factory=list)
    confidence: float = 1.0
    steps_used: int = 0
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "answer": self.answer,
            "text": self.text,
            "evidence": [e.to_dict() if isinstance(e, RecordRef) else e for e in self.evidence],
            "confidence": self.confidence,
            "steps_used": self.steps_used,
            "tokens_used": self.tokens_used,
        }
