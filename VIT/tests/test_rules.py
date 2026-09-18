import pytest
from backend.rules import ClinicalRules
from backend.study_graph import StudyGraph
from backend.config import DATA_DIR

def test_unit_conversion():
    # Test 3.995 ukat/L -> 239.7 U/L
    is_num, norm_val, unit, uln = ClinicalRules.normalize_lab_result("ALT", "3.995", "ukat/L", "S07")
    assert is_num is True
    assert pytest.approx(norm_val, 0.01) == 239.7
    assert unit == "U/L"
    assert uln == 56.0

def test_hys_law_candidate_worked_example():
    graph = StudyGraph(DATA_DIR)
    graph.build()
    
    # Check subject 042-S07-001 (worked example from problem statement)
    p360 = graph.patient360("042-S07-001")
    assert p360 is not None
    assert p360.get("usubjid") == "042-S07-001"

    is_cand, supp_recs, expl = ClinicalRules.check_hys_law_candidate(p360)
    assert is_cand is True
    assert len(supp_recs) >= 2
    # Verify records contain ALT and BILI
    tests = [r["LBTESTCD"] for r in supp_recs]
    assert "ALT" in tests or "AST" in tests
    assert "BILI" in tests
