"""
Standard competition stage1/atlas.py entry point.
Exposes StudyGraph and Atlas classes.
"""
from backend.study_graph import StudyGraph
from backend.atlas_agent import Atlas
from backend.schemas import Question, Answer

__all__ = ["StudyGraph", "Atlas", "Question", "Answer"]
