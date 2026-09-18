"""Atlas Clinical QA Agent engine connected to StudyGraph and DocumentKnowledge."""

import time
import logging
from typing import Any, Optional
from backend.question_parser import QuestionParser
from backend.query_planner import QueryPlanner
from backend.query_engine import QueryEngine
from backend.study_metadata import StudyMetadata
from backend.document_knowledge import DocumentKnowledge
from backend.conversation_state import ConversationState
from backend.schemas import Question, Answer, QueryPlan

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

        # 1. Parse question with dynamic metadata
        parsed_q = QuestionParser.parse(q_obj, metadata=self.metadata)

        # 2. Apply short-term conversational context for follow-ups
        parsed_q = self.conversation_state.apply_context(parsed_q, q_obj.text)

        # 3. Update conversational references
        self.conversation_state.update(parsed_q)

        # 4. Generate transparent QueryPlan model (no clinical calculations)
        plan = QueryPlanner.create_plan(parsed_q)

        # 5. Execute structured query against StudyGraph / DocumentKnowledge
        raw_answer = self.query_engine.execute(parsed_q)
        raw_answer.intent = parsed_q.intent
        raw_answer.query_plan = plan

        # 6. Strict Evidence Validation
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
