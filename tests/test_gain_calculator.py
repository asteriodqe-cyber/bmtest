from __future__ import annotations

import pytest
from evaluators.gain_calculator import (
    calculate_metrics,
    calculate_skill_gain,
    calculate_cohens_kappa,
    _get_absolute_tier,
    _calculate_efficacy,
    _generate_diagnosis
)


# ── calculate_metrics ─────────────────────────────────────

def test_metrics_empty():
    result = calculate_metrics([])
    assert result["pass_rate"] == 0.0
    assert result["consistency"] == 0.0
    assert result["final_score"] == 0.0

def test_metrics_all_pass():
    result = calculate_metrics([1.0, 1.0, 1.0, 1.0, 1.0])
    assert result["pass_rate"] == 1.0
    assert result["consistency"] == 1.0
    assert result["final_score"] == 1.0

def test_metrics_all_fail():
    result = calculate_metrics([0.0, 0.0, 0.0, 0.0, 0.0])
    assert result["pass_rate"] == 0.0
    assert result["consistency"] == 1.0  # 稳定失败，consistency=1
    assert result["final_score"] == 0.0  # 但 final_score 仍为 0

def test_metrics_mixed():
    result = calculate_metrics([1.0, 0.0, 1.0, 0.0, 1.0])
    assert result["pass_rate"] == 0.6
    assert result["consistency"] < 1.0  # 不稳定

def test_metrics_single_value():
    result = calculate_metrics([0.8])
    assert result["pass_rate"] == 0.8
    assert result["consistency"] == 1.0  # 单值视为完全一致


# ── calculate_skill_gain ──────────────────────────────────

def test_skill_gain_positive():
    skill = [1.0, 1.0, 1.0, 1.0, 1.0]
    baseline = [0.0, 0.0, 0.0, 0.0, 0.0]
    result = calculate_skill_gain(skill, baseline, "b1")
    assert result["gain"] == 1.0
    assert result["efficacy"] == "high"

def test_skill_gain_zero():
    scores = [0.5, 0.5, 0.5]
    result = calculate_skill_gain(scores, scores, "b1")
    assert result["gain"] == 0.0

def test_skill_gain_baseline_perfect():
    """baseline 已满分时 gain 应为 0"""
    skill = [1.0, 1.0, 1.0]
    baseline = [1.0, 1.0, 1.0]
    result = calculate_skill_gain(skill, baseline, "b1")
    assert result["gain"] == 0.0

def test_skill_gain_includes_tier():
    skill = [0.9, 0.9, 0.9]
    baseline = [0.3, 0.3, 0.3]
    result = calculate_skill_gain(skill, baseline, "b1")
    assert result["absolute_tier"] == "A"
    assert result["meets_quality_floor"] is True


# ── calculate_cohens_kappa ────────────────────────────────

def test_kappa_perfect_agreement_all_pass():
    assert calculate_cohens_kappa([1.0, 1.0, 1.0, 1.0, 1.0]) == 1.0

def test_kappa_perfect_agreement_all_fail():
    assert calculate_cohens_kappa([0.0, 0.0, 0.0, 0.0, 0.0]) == 1.0

def test_kappa_single_value():
    assert calculate_cohens_kappa([0.8]) == 1.0

def test_kappa_mixed():
    result = calculate_cohens_kappa([1.0, 0.0, 1.0, 0.0, 1.0])
    assert 0.0 <= result <= 1.0


# ── _get_absolute_tier ────────────────────────────────────

def test_tier_a():
    assert _get_absolute_tier(0.8) == "A"
    assert _get_absolute_tier(1.0) == "A"

def test_tier_b():
    assert _get_absolute_tier(0.6) == "B"
    assert _get_absolute_tier(0.79) == "B"

def test_tier_c():
    assert _get_absolute_tier(0.4) == "C"
    assert _get_absolute_tier(0.59) == "C"

def test_tier_d():
    assert _get_absolute_tier(0.0) == "D"
    assert _get_absolute_tier(0.39) == "D"


# ── _calculate_efficacy ───────────────────────────────────

def test_efficacy_high():
    assert _calculate_efficacy(0.6, 0.8) == "high"

def test_efficacy_medium():
    assert _calculate_efficacy(0.3, 0.6) == "medium"

def test_efficacy_low_bad_skill():
    assert _calculate_efficacy(0.8, 0.3) == "low"  # skill_score < 0.5

def test_efficacy_low_low_gain():
    assert _calculate_efficacy(0.1, 0.7) == "low"
