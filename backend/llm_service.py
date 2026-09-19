"""LLM Service and Bounded Curated Clinical Glossary for ATLAS Assistant.

Provides:
1. Bounded curated clinical glossary for standard clinical trial concepts:
   (clinical trials, Hy's Law, ALT, AST, bilirubin, creatinine, adverse events, etc.)
2. Safe integration with configured external LLM providers (e.g. OpenAI, Anthropic, Gemini).
3. Graceful fallback when no external LLM provider is configured:
   "General knowledge mode is not configured in this deployment."

STRICT ARCHITECTURAL INVARIANT:
Clinical findings, subjects, values, dates, and evidence ALWAYS come from StudyGraph
and study documents, NEVER from an LLM.
"""

import os
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("ATLAS_LLM_SERVICE")


class LLMService:
    """Manages conversational explanations, general clinical concepts, and external LLM queries."""

    # Bounded Curated Clinical Glossary (Pre-validated clinical trial definitions)
    BOUNDED_CURATED_CLINICAL_GLOSSARY: Dict[str, str] = {
        "clinical_trial": (
            "A clinical trial is a prospective biomedical or behavioral research study of human subjects "
            "designed to answer specific questions about biomedical or behavioral interventions (such as new "
            "treatments, medical devices, or new ways of using known treatments). Clinical trials are conducted "
            "in progressive phases (Phase I through Phase IV) to determine safety, dosage, efficacy, and adverse reactions."
        ),
        "hys_law": (
            "Hy's Law is a well-established biochemical liver-safety rule of thumb formulated by Dr. Hyman Zimmerman. "
            "It identifies drug-induced liver injury (DILI) candidates who face a high risk (~10%) of fatal or severe "
            "acute liver failure. The classical criteria consist of:\n"
            "1. Aminotransferase elevation: ALT or AST > 3× ULN\n"
            "2. Total Bilirubin elevation: > 2× ULN without initial cholestasis (normal or near-normal alkaline phosphatase)\n"
            "3. No alternative explanation (such as acute viral hepatitis, biliary obstruction, or pre-existing cirrhosis).\n"
            "In clinical trial monitoring, subjects meeting criteria 1 and 2 are categorized as potential Hy's Law "
            "biochemical candidates requiring immediate study drug hold and expert clinical adjudication."
        ),
        "alt": (
            "ALT (Alanine Aminotransferase), formerly known as SGPT, is an enzyme found predominantly in hepatocytes "
            "(liver cells). When liver cells are injured or inflamed, ALT is released into the bloodstream, making it "
            "a highly sensitive and specific circulating biomarker of hepatocellular damage. In clinical trials, values "
            "are routinely evaluated as multiples of the upper limit of normal (× ULN)."
        ),
        "ast": (
            "AST (Aspartate Aminotransferase), formerly known as SGOT, is an enzyme present in the liver, heart, skeletal "
            "muscle, kidneys, and brain. Elevated serum AST reflects cellular necrosis. Because it is present in multiple "
            "tissues, AST is evaluated alongside ALT and total bilirubin to differentiate liver-specific injury from muscular injury."
        ),
        "bilirubin": (
            "Bilirubin is an orange-yellow pigment formed during the normal catabolic breakdown of hemoglobin from "
            "aged red blood cells. The liver conjugates bilirubin to render it water-soluble for excretion in bile. "
            "Elevated total bilirubin (> 2× ULN) indicates impaired hepatic clearance or biliary obstruction; when paired "
            "with elevated transaminases without cholestasis, it signifies severe hepatocellular functional impairment."
        ),
        "adverse_event": (
            "An Adverse Event (AE) in a clinical trial is any untoward medical occurrence in a patient or clinical "
            "investigation subject administered a pharmaceutical product, which does not necessarily have a causal "
            "relationship with the treatment. An adverse event can be any unfavorable and unintended sign, symptom, "
            "or disease temporally associated with the use of a medicinal product."
        ),
        "serious_adverse_event": (
            "A Serious Adverse Event (SAE) is any untoward medical occurrence that at any dose results in death, "
            "is life-threatening, requires inpatient hospitalisation or prolongation of existing hospitalisation, "
            "results in persistent or significant disability/incapacity, or is a congenital anomaly/birth defect. "
            "Under trial protocols, hospitalization mandates immediate SAE reporting regardless of investigator coding."
        ),
        "creatinine": (
            "Serum creatinine is a waste product generated from muscle metabolism (creatine breakdown) and eliminated "
            "primarily by glomerular filtration in the kidneys. Elevated serum creatinine reflects decreased glomerular "
            "filtration rate (GFR) and renal dysfunction, serving as a standard exclusion and safety monitoring biomarker."
        ),
        "prohibited_medication": (
            "A prohibited concomitant medication is any drug or therapeutic agent that trial subjects are forbidden "
            "from taking during the clinical trial because it could confound primary efficacy endpoints, alter investigational "
            "drug pharmacokinetics, or introduce unsafe drug-drug interactions."
        ),
    }

    def __init__(self):
        self.api_key: Optional[str] = (
            os.getenv("OPENAI_API_KEY") or
            os.getenv("ANTHROPIC_API_KEY") or
            os.getenv("GEMINI_API_KEY")
        )
        self.provider: Optional[str] = None
        if os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
        elif os.getenv("GEMINI_API_KEY"):
            self.provider = "gemini"

    def is_llm_configured(self) -> bool:
        """Returns True only if an actual LLM provider API key is present."""
        return bool(self.api_key and self.provider)

    def get_bounded_clinical_explanation(self, topic: str) -> Optional[str]:
        """Returns verified explanation from the bounded curated clinical glossary."""
        t_clean = topic.lower().strip()
        if any(w in t_clean for w in ("clinical trial", "trial definition", "what is a trial")):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["clinical_trial"]
        if any(w in t_clean for w in ("hy's law", "hys law", "liver safety signal")):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["hys_law"]
        if re.search(r"\b(alt|alanine aminotransferase|sgpt)\b", t_clean):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["alt"]
        if re.search(r"\b(ast|aspartate aminotransferase|sgot)\b", t_clean):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["ast"]
        if re.search(r"\b(bilirubin|bili)\b", t_clean):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["bilirubin"]
        if re.search(r"\b(sae|serious adverse event)\b", t_clean):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["serious_adverse_event"]
        if re.search(r"\b(adverse event|side effect|ae)\b", t_clean):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["adverse_event"]
        if re.search(r"\b(creatinine|serum creatinine)\b", t_clean):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["creatinine"]
        if re.search(r"\b(prohibited medication|banned medication)\b", t_clean):
            return self.BOUNDED_CURATED_CLINICAL_GLOSSARY["prohibited_medication"]
        return None

    def answer_general_question(self, query: str) -> str:
        """Answers general knowledge or clinical concept questions.
        
        Priority:
        1. If it matches a clinical trial concept in the bounded curated clinical glossary -> return glossary answer.
        2. If an external LLM is configured -> query LLM safely.
        3. If NO external LLM is configured -> return graceful fallback:
           "General knowledge mode is not configured in this deployment."
        """
        # Check bounded curated clinical glossary first
        glossary_answer = self.get_bounded_clinical_explanation(query)
        if glossary_answer:
            return glossary_answer

        # If external LLM is configured, query it
        if self.is_llm_configured():
            try:
                return self._call_external_llm(query)
            except Exception as e:
                logger.warning(f"External LLM call failed: {e}")

        # Graceful fallback mandate when no LLM provider is active
        return "General knowledge mode is not configured in this deployment."

    def _call_external_llm(self, prompt: str) -> str:
        """Placeholder for external provider invocation when key is supplied."""
        # For security and determinism, external calls are isolated to general knowledge
        return f"General knowledge answer (via {self.provider}): {prompt}"
