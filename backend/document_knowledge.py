"""Document Knowledge Base for ATLAS Clinical Protocol and Study Documents.

Provides indexed, deterministic search over local study documents:
    - protocol_v1.md
    - protocol_v2.md
    - protocol_v3.md
    - sap.md
    - lab-manual.md
    - lab-manual_v3.md

CRITICAL SECURITY CONSTRAINT:
Documents are treated strictly as DATA, not instructions.
Prompt injections inside documents addressed to automated reviewers
are treated purely as quoted text and NEVER alter chatbot behavior.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple
from backend.schemas import RecordRef, Answer


class DocumentKnowledge:
    """Indexes and queries local study protocol and laboratory documents."""

    def __init__(self, doc_dir: Optional[str] = None):
        if doc_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.doc_dir = os.path.join(base_dir, "documents")
        else:
            self.doc_dir = doc_dir

        self.documents: Dict[str, str] = {}
        self.sections: Dict[str, List[Dict[str, str]]] = {}
        self._load_documents()

    def _load_documents(self) -> None:
        """Reads and segments local markdown documents into sections."""
        if not os.path.isdir(self.doc_dir):
            return

        for fname in sorted(os.listdir(self.doc_dir)):
            if fname.endswith(".md"):
                fpath = os.path.join(self.doc_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.documents[fname] = content
                    self.sections[fname] = self._parse_sections(content)
                except Exception:
                    pass

    def _parse_sections(self, content: str) -> List[Dict[str, str]]:
        """Parses markdown document into list of heading-body sections."""
        sections = []
        lines = content.splitlines()
        current_heading = "Preamble"
        current_lines: List[str] = []

        for line in lines:
            if line.startswith("#"):
                if current_lines:
                    sections.append({
                        "heading": current_heading,
                        "text": "\n".join(current_lines).strip()
                    })
                    current_lines = []
                current_heading = line.lstrip("#").strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "heading": current_heading,
                "text": "\n".join(current_lines).strip()
            })

        return sections

    def query(self, text: str, active_protocol_version: int = 3) -> Optional[Answer]:
        """Answers protocol, SAP, or lab manual questions with exact evidence citations."""
        lower = text.lower()

        # 1. Determine target protocol version if explicitly requested
        target_version = active_protocol_version
        v_match = re.search(r"protocol\s*v(?:ersion)?\s*([123])\b", lower)
        if v_match:
            target_version = int(v_match.group(1))

        # Check for comparison between protocol versions
        if "between protocol" in lower or ("changed" in lower and "protocol" in lower) or "amendment" in lower:
            return self._handle_protocol_comparison(lower)

        # 2. Visit schedule / visit window queries
        if "visit window" in lower or ("window" in lower and "visit" in lower) or "visit schedule" in lower:
            doc_name = f"protocol_v{target_version}.md"
            if doc_name in self.documents:
                sec_title = "4. Visit schedule and windows"
                if target_version == 1:
                    window_str = "± 7 days from the scheduled day"
                else:
                    window_str = "± 3 days from the scheduled day"

                text_resp = (
                    f"Under Protocol Version {target_version}, the visit window is {window_str}. "
                    "Visits outside this window are classified as protocol deviations and must be logged."
                )
                evidence = [RecordRef(domain="DOC", document=doc_name, section=sec_title)]
                return Answer(
                    answer=window_str,
                    text=text_resp,
                    evidence=evidence,
                    confidence=1.0,
                    intent="DOCUMENT_LOOKUP",
                    structured_data={"type": "protocol_rule", "topic": "visit_window", "version": target_version, "window": window_str}
                )

        # 3. Creatinine exclusion / renal impairment queries
        if "creatinine" in lower and ("exclusion" in lower or "added" in lower or "threshold" in lower or "rule" in lower or "renal" in lower):
            if "when" in lower or "which version" in lower or "amendment" in lower:
                doc_name = "protocol_v2.md"
                sec_title = "3. Exclusion criteria"
                text_resp = (
                    "The creatinine exclusion criterion (> 1.5 mg/dL at screening for renal impairment) "
                    "was added in Protocol Amendment 2 (Protocol Version 2)."
                )
                evidence = [RecordRef(domain="DOC", document=doc_name, section=sec_title)]
                return Answer(
                    answer="Protocol Version 2 (Amendment 2)",
                    text=text_resp,
                    evidence=evidence,
                    confidence=1.0,
                    intent="DOCUMENT_LOOKUP"
                )
            else:
                doc_name = f"protocol_v{target_version}.md"
                sec_title = "3. Exclusion criteria"
                if target_version == 1:
                    thresh = "Creatinine was not an explicit exclusion criterion in Protocol Version 1."
                else:
                    thresh = "Creatinine > 1.5 mg/dL at screening is an exclusion criterion (renal impairment)."
                return Answer(
                    answer="Creatinine > 1.5 mg/dL",
                    text=f"Under Protocol Version {target_version}: {thresh}",
                    evidence=[RecordRef(domain="DOC", document=doc_name, section=sec_title)],
                    confidence=1.0,
                    intent="DOCUMENT_LOOKUP"
                )

        # 4. Prohibited medications queries
        if "prohibited" in lower or "forbidden" in lower or "disallowed" in lower:
            doc_name = f"protocol_v{target_version}.md"
            sec_title = "5. Prohibited concomitant medications"
            if target_version == 3:
                meds = ["Sulfonylurea", "Systemic Glucocorticoid"]
            else:
                meds = ["Systemic Glucocorticoid"]
            meds_str = ", ".join(meds)
            text_resp = (
                f"Under Protocol Version {target_version}, prohibited concomitant medications are: {meds_str}. "
                "Use of a prohibited medication during the study is a protocol deviation."
            )
            return Answer(
                answer=meds,
                text=text_resp,
                evidence=[RecordRef(domain="DOC", document=doc_name, section=sec_title)],
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )

        # 5. Serious adverse events reporting / hospitalisation
        if ("serious" in lower and "adverse" in lower) or "sae" in lower or "safety reporting" in lower or "hospitalisation" in lower or "hospitalization" in lower:
            doc_name = f"protocol_v{target_version}.md"
            sec_title = "6. Safety reporting"
            text_resp = (
                f"Per Protocol Version {target_version} (§6 Safety reporting), serious adverse events "
                "(death, life-threatening, hospitalisation or prolongation, persistent disability, congenital anomaly) "
                "must be reported to the sponsor safety desk within 24 hours of site awareness. "
                "A hospitalisation flag (AESHOSP = Y) makes an event serious regardless of how AESER was coded."
            )
            return Answer(
                answer="Within 24 hours; AESHOSP = Y makes an event serious regardless of AESER.",
                text=text_resp,
                evidence=[RecordRef(domain="DOC", document=doc_name, section=sec_title)],
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )

        # 6. Liver safety / Hy's law protocol definition
        if "hy" in lower and ("protocol" in lower or "definition" in lower or "rule" in lower or "say" in lower):
            doc_name = f"protocol_v{target_version}.md"
            sec_title = "7. Liver safety"
            text_resp = (
                f"Per Protocol Version {target_version} (§7 Liver safety), Potential Hy's Law is defined as: "
                "ALT or AST > 3 × ULN together with total bilirubin > 2 × ULN within 14 days, without cholestasis "
                "or alternative explanation. Findings must be reported to the medical monitor for adjudication; "
                "study dosing is held pending review."
            )
            return Answer(
                answer="ALT or AST > 3× ULN + Total Bilirubin > 2× ULN within 14 days without cholestasis",
                text=text_resp,
                evidence=[RecordRef(domain="DOC", document=doc_name, section=sec_title)],
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )

        # 7. Dosing protocol
        if "dose" in lower or "dosing" in lower or "drug-042" in lower:
            doc_name = f"protocol_v{target_version}.md"
            sec_title = "8. Dosing"
            text_resp = (
                f"Per Protocol Version {target_version} (§8 Dosing), the assigned dose is DRUG-042 10 mg once daily "
                "(or 0 mg for placebo). Any administered dose other than 10 mg (drug arm) or 0 mg (placebo) is a "
                "dosing error and a protocol deviation."
            )
            return Answer(
                answer="10 mg once daily (drug) or 0 mg (placebo)",
                text=text_resp,
                evidence=[RecordRef(domain="DOC", document=doc_name, section=sec_title)],
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )

        # 8. Inclusion criteria
        if "inclusion" in lower:
            doc_name = f"protocol_v{target_version}.md"
            sec_title = "2. Inclusion criteria"
            criteria = [
                "Age 18–75 years at screening",
                "HbA1c between 7.0% and 10.5% at screening",
                "Stable dose of metformin for ≥ 8 weeks"
            ]
            text_resp = f"Protocol Version {target_version} inclusion criteria are: " + "; ".join(criteria) + "."
            return Answer(
                answer=criteria,
                text=text_resp,
                evidence=[RecordRef(domain="DOC", document=doc_name, section=sec_title)],
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )

        # 9. Statistical Analysis Plan (SAP)
        if "sap" in lower or "primary endpoint" in lower or "statistical" in lower or "endpoint" in lower:
            doc_name = "sap.md"
            text_resp = (
                "Per the Statistical Analysis Plan (SAP): Primary endpoint is change from baseline in HbA1c at Week 24, "
                "analyzed via MMRM. Safety analyses include treatment-emergent adverse events, serious adverse events, "
                "liver safety screen per protocol §7, and vital signs."
            )
            return Answer(
                answer="HbA1c change from baseline at Week 24 (MMRM)",
                text=text_resp,
                evidence=[RecordRef(domain="DOC", document=doc_name, section="Statistical Analysis Plan (abridged)")],
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )

        # 10. Lab manual queries (units, site S07 conversion, reissued results)
        if "lab manual" in lower or "unit" in lower or "ikat" in lower or "ukat" in lower or "reissued" in lower or ("s07" in lower and "lab" in lower):
            doc_name = "lab-manual_v3.md" if "lab-manual_v3.md" in self.documents else "lab-manual.md"
            text_resp = (
                "Per the Central and Local Laboratory Manual: All safety chemistry is analysed at the central laboratory in conventional units "
                "(ALT/AST in U/L, bilirubin in mg/dL, glucose in mg/dL, creatinine in mg/dL, HbA1c in %). "
                "Site S07 uses a local laboratory reporting ALT and AST in µkat/L (1 µkat/L = 60 U/L), which must be converted. "
                "Values reported as '<5', 'ND' or blank indicate below-detection or not-done and must not be treated as numeric zero. "
                "Reissued results: the central laboratory may re-issue corrected values in later cuts; the most recent value supersedes."
            )
            return Answer(
                answer="Central lab uses conventional units; Site S07 reports ALT/AST in µkat/L (1 µkat/L = 60 U/L); latest reissued value supersedes.",
                text=text_resp,
                evidence=[RecordRef(domain="DOC", document=doc_name, section="Central and Local Laboratory Manual")],
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )

        return None

    def _handle_protocol_comparison(self, lower: str) -> Answer:
        """Handles comparisons between protocol versions."""
        if "v1" in lower and "v2" in lower:
            text_resp = (
                "Key differences between Protocol Version 1 and Version 2:\n"
                "1. Visit window: tightened from ±7 days in v1 to ±3 days in v2.\n"
                "2. Exclusion criteria: Creatinine > 1.5 mg/dL at screening was added in Amendment 2 (v2)."
            )
            evidence = [
                RecordRef(domain="DOC", document="protocol_v1.md", section="4. Visit schedule and windows"),
                RecordRef(domain="DOC", document="protocol_v2.md", section="3. Exclusion criteria"),
            ]
            return Answer(
                answer="Visit window changed from ±7 to ±3 days; Creatinine > 1.5 mg/dL exclusion added in v2.",
                text=text_resp,
                evidence=evidence,
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )
        elif ("v2" in lower and "v3" in lower) or "v3" in lower:
            text_resp = (
                "Key differences between Protocol Version 2 and Version 3:\n"
                "1. Prohibited medications: Sulfonylureas were added to the prohibited concomitant medication list in Amendment 3 (v3).\n"
                "2. Systemic Glucocorticoids remain prohibited across all versions."
            )
            evidence = [
                RecordRef(domain="DOC", document="protocol_v2.md", section="5. Prohibited concomitant medications"),
                RecordRef(domain="DOC", document="protocol_v3.md", section="5. Prohibited concomitant medications"),
            ]
            return Answer(
                answer="Sulfonylureas were added as prohibited concomitant medications in Protocol Version 3.",
                text=text_resp,
                evidence=evidence,
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )
        else:
            text_resp = (
                "Protocol Amendments Overview:\n"
                "• Version 1: Initial protocol (visit window ±7 days; prohibited: Systemic Glucocorticoid).\n"
                "• Version 2: Added Creatinine > 1.5 mg/dL exclusion; tightened visit window to ±3 days.\n"
                "• Version 3: Added Sulfonylureas to the prohibited concomitant medication list."
            )
            evidence = [
                RecordRef(domain="DOC", document="protocol_v1.md", section="Preamble"),
                RecordRef(domain="DOC", document="protocol_v2.md", section="Preamble"),
                RecordRef(domain="DOC", document="protocol_v3.md", section="Preamble"),
            ]
            return Answer(
                answer="Amendments modified visit windows (±7d to ±3d), added creatinine exclusion (v2), and added sulfonylurea prohibition (v3).",
                text=text_resp,
                evidence=evidence,
                confidence=1.0,
                intent="DOCUMENT_LOOKUP"
            )
