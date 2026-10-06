"""Tests for the target calculator (PLAN B.7)."""
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.targets import compute, estimate_tdee, load_profile, ree  # noqa: E402

PROFILES = sorted((ROOT / "config/profiles").glob("*.yaml"))


def macro_kcal(r):
    t = r.targets
    return 4 * t["protein"].value + 4 * t["carbohydrate"].value + 9 * t["fat"].value


@pytest.mark.parametrize("path", PROFILES, ids=[p.stem for p in PROFILES])
def test_archetypes_consistent_and_conflict_free(path):
    r = compute(load_profile(path))
    assert not r.conflicts, r.conflicts
    assert macro_kcal(r) == pytest.approx(r.targets["energy"].value, rel=1e-6)
    f = r.targets["fat"]
    assert f.low - 1e-6 <= f.value <= f.high + 1e-6
    c = r.targets["carbohydrate"]
    if c.low is not None:
        assert c.value >= c.low - 1e-6
    if c.high is not None:
        assert c.value <= c.high + 1e-6


def test_owner_numbers():
    r = compute(load_profile(ROOT / "config/profiles/owner.yaml"))
    t = r.targets
    assert t["energy"].value == pytest.approx(3300)              # 3000 kcal user value + 10 % surplus
    assert t["protein"].value == pytest.approx(1.8 * 76)         # D1 default
    assert (t["carbohydrate"].low, t["carbohydrate"].high) == pytest.approx((5 * 76, 7 * 76))  # moderate band
    assert any("differs" in w for w in r.warnings)               # 3000 kcal vs ≈3550 estimate


def test_ten_haaf_equation_matches_review_example():
    p = load_profile(ROOT / "config/profiles/owner.yaml")
    assert ree(p)[0] == pytest.approx(2041.8, abs=1)             # REVIEW.md §3


def test_conflict_detected_when_energy_too_low_for_carb_band():
    p = load_profile(ROOT / "config/profiles/ironman.yaml")
    p = replace(p, overrides={"energy_kcal": 2600})
    r = compute(p)
    assert r.conflicts and "too low" in r.conflicts[0]


def test_deficit_and_surplus_directions():
    fl = compute(load_profile(ROOT / "config/profiles/fat_loss.yaml"))
    bb = compute(load_profile(ROOT / "config/profiles/bodybuilder_bulk.yaml"))
    assert fl.targets["energy"].value < fl.targets["energy expenditure"].value
    assert bb.targets["energy"].value > bb.targets["energy expenditure"].value


def test_exercise_raises_tdee():
    p = load_profile(ROOT / "config/profiles/owner.yaml")
    rest = replace(p, training={"modality": "none", "hours_per_week": 0})
    assert estimate_tdee(p)[0] > estimate_tdee(rest)[0]


def test_unknown_goal_rejected():
    p = replace(load_profile(ROOT / "config/profiles/owner.yaml"), goal="keto_magic")
    with pytest.raises(ValueError):
        compute(p)
