import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analytics import (
    calculate_bmi,
    calculate_one_rep_max,
    detect_progressive_overload,
    calculate_recovery_score,
)


def test_calculate_bmi_normal():
    # 180cm, 75kg -> BMI ~ 23.1
    res = calculate_bmi(180, 75)
    assert res["bmi"] == 23.1
    assert res["category"] == "Normal weight"
    assert res["healthy_weight_range_kg"][0] < 75 < res["healthy_weight_range_kg"][1]


def test_calculate_bmi_invalid():
    with pytest.raises(ValueError):
        calculate_bmi(0, 70)


def test_one_rep_max_epley():
    # 100kg for 1 rep = 100kg
    assert calculate_one_rep_max(100, 1) == 100.0
    # 100kg for 10 reps = 100 * (1 + 10/30) = 133.3kg
    assert calculate_one_rep_max(100, 10) == 133.3


def test_detect_progressive_overload_baseline():
    res = detect_progressive_overload("Bench Press", 80, 8, history=[])
    assert res["is_overload"] is True
    assert "Baseline" in res["badge"]


def test_detect_progressive_overload_weight_pr():
    history = [
        {"exercise_name": "Bench Press", "weight_kg": 80, "reps": 8}
    ]
    # Current set is 82.5kg for 8 reps -> heavier than 80kg
    res = detect_progressive_overload("Bench Press", 82.5, 8, history)
    assert res["is_overload"] is True
    assert "+2.5kg Weight PR" in res["badge"]


def test_calculate_recovery_score():
    # 8 hrs sleep (40 pts) + 160g protein (40 pts) + 3.5L water (20 pts) = 100
    res = calculate_recovery_score(sleep_hours=8.0, water_liters=3.5, protein_grams=160.0, target_protein=160.0)
    assert res["score"] == 100
    assert res["readiness"] == "Prime Readiness"

    # Poor sleep and low protein
    low_res = calculate_recovery_score(sleep_hours=4.0, water_liters=1.0, protein_grams=50.0, target_protein=160.0)
    assert low_res["score"] < 50
    assert low_res["readiness"] == "Low Recovery"
