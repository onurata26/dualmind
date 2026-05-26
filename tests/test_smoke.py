import os
import sys
import pytest

# Add parent dir to path so we can import project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_layer import env_bool
from agent_factory import normalize_segments


def test_env_bool():
    os.environ["TEST_TRUE"] = "1"
    os.environ["TEST_FALSE"] = "0"
    
    assert env_bool("TEST_TRUE", False) is True
    assert env_bool("TEST_FALSE", True) is False
    
    # Clean up
    del os.environ["TEST_TRUE"]
    del os.environ["TEST_FALSE"]

def test_normalize_segments():
    raw_segments = [
        {"id": "s1", "name": "A", "weight_pct": 50, "age_range": [20, 30], "avg_income": 10000, "core_value": "V1", "price_sensitivity": 5, "sustainability_focus": 5, "brand_loyalty": 5, "ad_receptivity": 5, "tech_savviness": 5},
        {"id": "s2", "name": "B", "weight_pct": 200, "age_range": [30, 40], "avg_income": 20000, "core_value": "V2", "price_sensitivity": 5, "sustainability_focus": 5, "brand_loyalty": 5, "ad_receptivity": 5, "tech_savviness": 5}
    ]
    
    normalized = normalize_segments(raw_segments)
    
    assert len(normalized) == 2
    # 50 + 200 = 250 total. s1 = 50/250 = 20%, s2 = 200/250 = 80%
    assert normalized[0]["weight_pct"] == 20.0
    assert normalized[1]["weight_pct"] == 80.0


