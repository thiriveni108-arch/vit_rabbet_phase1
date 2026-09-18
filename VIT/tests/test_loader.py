import pytest
from backend.data_loader import DataLoader
from backend.config import DATA_DIR

def test_data_loader_basic():
    loader = DataLoader(DATA_DIR)
    tables = loader.load()
    
    assert "DM" in tables
    assert "LB" in tables
    assert "AE" in tables
    assert len(tables["DM"]) == 241
    assert len(tables["LB"]) == 14400

def test_parse_lab_values():
    is_num, val, raw = DataLoader.parse_lab_value("40.4")
    assert is_num is True
    assert val == 40.4

    is_num, val, raw = DataLoader.parse_lab_value("<5")
    assert is_num is False
    assert val is None
    assert raw == "<5"

    is_num, val, raw = DataLoader.parse_lab_value("ND")
    assert is_num is False
    assert val is None

def test_parse_dates():
    assert DataLoader.parse_date("2026-03-30") == "2026-03-30"
    assert DataLoader.parse_date("03-FEB-2026") == "2026-02-03"
    assert DataLoader.parse_date("13-FEB-2026") == "2026-02-13"
