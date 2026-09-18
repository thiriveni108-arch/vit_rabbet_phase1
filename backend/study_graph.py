"""Canonical StudyGraph re-export.
Enforces that stage1.atlas.StudyGraph is the single runtime source of truth.
"""
from stage1.atlas import StudyGraph

__all__ = ["StudyGraph"]
