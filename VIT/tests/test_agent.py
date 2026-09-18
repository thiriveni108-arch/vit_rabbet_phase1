import pytest
from backend.study_graph import StudyGraph
from backend.atlas_agent import Atlas
from backend.schemas import Question, Answer
from backend.config import DATA_DIR

@pytest.fixture(scope="module")
def atlas_agent():
    graph = StudyGraph(DATA_DIR)
    graph.build()
    return Atlas(graph)

def test_hys_law_finding_question(atlas_agent):
    q = Question(question="Which subjects meet the Hy's law criteria?")
    ans: Answer = atlas_agent.answer(q)

    assert isinstance(ans.answer, list)
    assert "042-S07-001" in ans.answer
    assert "042-S05-003" in ans.answer
    assert "042-S08-014" in ans.answer
    assert len(ans.evidence) >= 6
    assert ans.confidence >= 0.85

def test_trap_question(atlas_agent):
    q = Question(question="Which subjects at site S01 received a wrong dose?")
    ans: Answer = atlas_agent.answer(q)

    assert ans.answer == []
    assert len(ans.evidence) == 0
    assert "No dosing errors at site S01" in ans.text

def test_count_question(atlas_agent):
    q = Question(question="How many subjects at site S07 discontinued due to an adverse event?")
    ans: Answer = atlas_agent.answer(q)

    assert isinstance(ans.answer, int)
    assert ans.answer >= 0
