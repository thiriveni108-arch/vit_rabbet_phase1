"""Evidence extraction and validation engine connected to StudyGraph."""

from typing import List, Dict, Any, Optional
from backend.schemas import RecordRef


class EvidenceEngine:
    """Handles evidence extraction, validation, and citation matching for ATLAS answers."""

    @staticmethod
    def extract_record_ref(record: dict) -> RecordRef:
        """Creates a RecordRef from a clinical domain record."""
        domain = record.get("domain") or record.get("_domain", "")
        usubjid = record.get("USUBJID") or record.get("_usubjid", "")
        seq = record.get("seq") or record.get("_seq")
        if seq is None and f"{domain}SEQ" in record:
            try:
                seq = int(record[f"{domain}SEQ"])
            except (ValueError, TypeError):
                seq = 0
        return RecordRef(domain=domain, usubjid=usubjid, seq=seq)

    @staticmethod
    def extract_doc_ref(document: str, section: str) -> RecordRef:
        """Creates a RecordRef for a study document reference."""
        return RecordRef(domain="DOC", document=document, section=section)

    @staticmethod
    def verify_evidence(graph: Any, evidence_refs: List[RecordRef]) -> bool:
        """Verifies that every RecordRef in evidence list exists in the active graph snapshot."""
        if not evidence_refs:
            return True

        for ref in evidence_refs:
            if ref.domain == "DOC":
                continue

            subj = ref.usubjid
            seq = ref.seq
            domain = ref.domain

            if hasattr(graph, "records_by_key"):
                if (domain, subj, seq) not in graph.records_by_key:
                    return False
            else:
                p360 = graph.patient360(subj)
                if not p360:
                    return False

        return True
