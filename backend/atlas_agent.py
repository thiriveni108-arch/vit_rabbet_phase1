"""Atlas Clinical QA Agent engine connected to StudyGraph, DocumentKnowledge, and LLMService."""

import time
import logging
from typing import Any, Optional
from backend.question_parser import QuestionParser
from backend.query_planner import QueryPlanner
from backend.query_engine import QueryEngine
from backend.study_metadata import StudyMetadata
from backend.document_knowledge import DocumentKnowledge
from backend.conversation_state import ConversationState
from backend.router import QueryRouter, QueryCategory
from backend.llm_service import LLMService
from backend.schemas import Question, Answer, QueryPlan, RecordRef

logger = logging.getLogger("ATLAS_AGENT")


class Atlas:
    """Main ATLAS AI Agent engine for clinical trial question answering.
    Operates deterministically against StudyGraph dataset and local study documents.
    """

    def __init__(self, graph: Any):
        self.graph = graph
        self.metadata = StudyMetadata(graph)
        self.doc_knowledge = DocumentKnowledge()
        self.conversation_state = ConversationState()
        self.llm_service = LLMService()
        self.query_engine = QueryEngine(graph, metadata=self.metadata, doc_knowledge=self.doc_knowledge)

    def sync_graph(self, graph: Any) -> None:
        """Synchronizes agent with a newly built or cut-updated StudyGraph."""
        self.graph = graph
        self.metadata = StudyMetadata(graph)
        self.query_engine = QueryEngine(graph, metadata=self.metadata, doc_knowledge=self.doc_knowledge)

    def reset_conversation(self) -> None:
        """Resets the short-term conversational context."""
        self.conversation_state.reset()

    def answer(self, question: Any) -> Answer:
        """Processes input question, generates structured QueryPlan, executes deterministically,
        validates evidence, and returns structured Answer.
        """
        start_time = time.perf_counter()

        if isinstance(question, str):
            q_obj = Question(text=question)
        elif isinstance(question, dict):
            q_obj = Question(
                question_id=question.get("question_id"),
                text=question.get("text") or question.get("question", "")
            )
        else:
            q_obj = question

        logger.info(f"[AGENT] Processing question: '{q_obj.text}'")

        # 0. Route Question
        category, route_meta = QueryRouter.route(q_obj.text)

        # 1. GENERAL Questions (Pure clinical concept or external knowledge query)
        if category == QueryCategory.GENERAL:
            explanation = self.llm_service.answer_general_question(q_obj.text)
            return Answer(
                question_id=q_obj.question_id,
                answer=[],
                text=explanation,
                evidence=[],
                confidence=1.0,
                intent="GENERAL",
                structured_data={
                    "type": "general_knowledge",
                    "suggested_followups": [
                        "Which subjects show a potential liver injury pattern?",
                        "What is Hy's Law and does anyone in our study meet it?",
                        "Show serious adverse events.",
                        "Summarize subject 042-S07-001."
                    ]
                }
            )

        # 2. MIXED Questions (General medical explanation + real StudyGraph query)
        if category == QueryCategory.MIXED and route_meta:
            gen_part = route_meta.get("general_query", "")
            study_part = route_meta.get("study_query", "")
            gen_explanation = self.llm_service.answer_general_question(gen_part)

            # Map study query using context from general query
            study_q_text = study_part
            if "hy" in gen_part.lower() and "hy" not in study_part.lower():
                study_q_text = "Which subjects meet potential Hy's Law criteria?"

            study_parsed = QuestionParser.parse(Question(text=study_q_text), metadata=self.metadata)
            study_ans = self.query_engine.execute(study_parsed)

            # Combine explanations: General explanation from knowledge layer, StudyGraph result for study
            cut_val = getattr(self.graph, "current_cut", 12)
            combined_text = (
                f"{gen_explanation}\n\n"
                f"{study_ans.text}"
            )

            # Update conversation state with study findings
            if isinstance(study_ans.answer, list):
                self.conversation_state.update(study_parsed, result_subjects=study_ans.answer)
            else:
                self.conversation_state.update(study_parsed)

            # Validate evidence
            valid_evidence = []
            for ref in study_ans.evidence:
                if ref.domain == "DOC":
                    valid_evidence.append(ref)
                elif hasattr(self.graph, "has_record") and self.graph.has_record(ref.domain, ref.usubjid, ref.seq):
                    valid_evidence.append(ref)
                elif (ref.domain, ref.usubjid, ref.seq) in getattr(self.graph, "records_by_key", {}):
                    valid_evidence.append(ref)

            return Answer(
                question_id=q_obj.question_id,
                answer=study_ans.answer,
                text=combined_text,
                evidence=valid_evidence,
                confidence=1.0,
                intent="MIXED",
                structured_data=study_ans.structured_data
            )

        # 3. STUDY_DATA & STUDY_KNOWLEDGE
        # 3.1. Parse question with dynamic metadata and concept resolver
        parsed_q = QuestionParser.parse(q_obj, metadata=self.metadata)

        # 3.2. Apply short-term conversational context for follow-ups
        parsed_q = self.conversation_state.apply_context(parsed_q, q_obj.text)

        # 3.3. Generate transparent QueryPlan model (no clinical calculations)
        plan = QueryPlanner.create_plan(parsed_q)

        # 3.4. Execute structured query against StudyGraph / DocumentKnowledge
        raw_answer = self.query_engine.execute(parsed_q)
        raw_answer.intent = parsed_q.intent
        raw_answer.query_plan = plan

        # 3.5. Update conversational references
        result_subjs = raw_answer.answer if isinstance(raw_answer.answer, list) else None
        self.conversation_state.update(parsed_q, result_subjects=result_subjs)

        # 4. Strict Evidence Validation
        # Verify that every clinical evidence record physically exists in current graph snapshot.
        # Factual supported claims must not be emitted with invalid evidence.
        valid_evidence = []
        has_invalid = False
        for ref in raw_answer.evidence:
            if ref.domain == "DOC":
                valid_evidence.append(ref)
            elif hasattr(self.graph, "has_record") and self.graph.has_record(ref.domain, ref.usubjid, ref.seq):
                valid_evidence.append(ref)
            elif (ref.domain, ref.usubjid, ref.seq) in getattr(self.graph, "records_by_key", {}):
                valid_evidence.append(ref)
            else:
                has_invalid = True
                logger.warning(f"[EVIDENCE] Dropping invalid evidence reference: ({ref.domain}, {ref.usubjid}, {ref.seq})")

        raw_answer.evidence = valid_evidence

        # If evidence was claimed but all of it was invalid, clear unsubstantiated claims
        if has_invalid and not valid_evidence and raw_answer.answer and raw_answer.intent not in ("STUDY_METADATA", "DOCUMENT_LOOKUP"):
            logger.warning("[EVIDENCE] All claimed evidence was invalid; suppressing unsubstantiated answer.")
            raw_answer.confidence = 0.0
            raw_answer.answer = []
            raw_answer.text = "Unable to substantiate claim with verified study records."

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(f"[AGENT] Query executed in {elapsed_ms:.2f} ms")

        return raw_answer
