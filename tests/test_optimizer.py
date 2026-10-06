"""Tests for the diet optimizer (PLAN C)."""
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not (ROOT / "data/processed/foods_master.csv").exists(), reason="master not built")


@pytest.fixture(scope="module")
def setup():
    from src import optimizer as O
    from src.targets import load_profile
    s, _ = O.spec_from_profile(load_profile(ROOT / "config/profiles/owner.yaml"))
    return O, O.food_table(), s


def test_solution_meets_every_target(setup):
    O, t, s = setup
    sol = O.solve(t, s)
    assert sol.status == "optimal"
    tot = sol.totals.set_index("nutrient").diet
    assert s.energy * (1 - s.energy_tol) - 1e-6 <= tot.kcal <= s.energy * (1 + s.energy_tol) + 1e-6
    assert tot.protein >= s.protein - 1e-6
    assert s.carb_lo - 1e-6 <= tot.carb <= s.carb_hi + 1e-6
    assert s.fat_lo - 1e-6 <= tot.fat <= s.fat_hi + 1e-6
    assert tot.free_sugars <= s.free_sugars_max + 1e-6
    # decision D9; tolerance covers the 2-decimal rounding of the reported grams
    assert (O.aa_adequacy(t, sol.foods, s.protein) >= 1 - 1e-3).all()
    assert (sol.foods.energy_share <= s.max_share + 1e-6).all()
    caps = t.cap.reindex(sol.foods.index)
    assert (sol.foods.g_eaten <= caps + 1e-6).all()


def test_more_constraints_never_cheaper(setup):
    O, t, s = setup
    costs = [O.solve(t, replace(s, safeguards=g)).cost_eur for g in ("none", "macros", "full")]
    assert costs[0] <= costs[1] + 1e-9 <= costs[2] + 2e-9
    assert O.solve(t, replace(s, protein_mode="crude")).cost_eur <= O.solve(t, s).cost_eur + 1e-9


def test_milp_respects_min_foods_and_portions(setup):
    O, t, s = setup
    sol = O.solve(t, replace(s, milp=True, min_foods=10, min_portion=40))
    assert sol.status == "optimal" and len(sol.foods) >= 10
    assert (sol.foods.g_eaten >= 40 - 1e-6).all()


def test_infeasible_reports_conflicts(setup):
    O, t, s = setup
    bad = replace(s, protein=400, protein_max=None)       # 400 g protein in 3,300 kcal with the carb band: impossible
    sol = O.solve(t, bad)
    assert sol.status == "infeasible" and len(sol.conflicts) > 0
    assert set(sol.conflicts.columns) >= {"constraint", "violation"}


def test_mass_objective_lighter_than_cost_objective(setup):
    O, t, s = setup
    assert O.solve(t, replace(s, objective="mass")).mass_g < O.solve(t, s).mass_g
