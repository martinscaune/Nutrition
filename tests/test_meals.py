"""Meal score / improvement, meal split, realistic diet variant, race week, country prices (2026-10-07)."""
from dataclasses import replace

import pandas as pd
import pytest

from src import meals as ML
from src import optimizer as O
from src.prices import countries as CT
from src.targets import compute, load_profile

OWNER = load_profile("config/profiles/owner.yaml")
RES = compute(OWNER)
FRIEND = pd.Series(ML.TEMPLATES["friend_eggs_beans"]["foods"], dtype=float)


@pytest.fixture(scope="module")
def t():
    return O.food_table(roles=["core", "ingredient", "snack", "supplement"])


def test_meal_score_range_and_breakdown(t):
    sc, b, tot = ML.score(t, FRIEND, RES)
    assert 0 <= sc <= 100
    assert len(b[b.kind == "encourage"]) == 20 and len(b[b.kind == "limit"]) == 3
    assert abs(tot["kcal"] - 519) < 30          # 4 eggs + 1 can of beans ≈ 520 kcal
    assert b.set_index("item").loc["Sodium", "score"] < 0   # canned beans: sodium over the meal's share


@pytest.mark.parametrize("mode", ["tweak", "best"])
def test_improved_meal_same_energy_and_not_worse(t, mode):
    sc0, _, tot0 = ML.score(t, FRIEND, RES)
    r = ML.improve(t, FRIEND, RES, mode, tiebreak="similar")
    assert r.status == "optimal"
    assert r.score >= sc0 - 1e-6
    assert abs(r.totals["kcal"] / tot0["kcal"] - 1) <= ML.CFG["energy_tolerance_pct"] / 100 + 1e-3
    if mode == "tweak":   # original foods kept within the tweak range; at most 2 new foods
        lo, hi = ML.CFG["tweak_range"]
        for f, g in FRIEND.items():
            assert lo * g - 1 <= r.grams.get(f, 0) <= hi * g + 1
        assert len(set(r.grams.index) - set(FRIEND.index)) <= ML.CFG["max_new_foods_tweak"]
    else:
        assert len(r.grams) <= ML.CFG["max_foods_best"]


def test_improve_respects_cost_cap_and_exclusions(t):
    _, _, tot0 = ML.score(t, FRIEND, RES)
    r = ML.improve(t, FRIEND, RES, "best", max_cost=tot0["cost_eur"], exclude=("peas_split",))
    assert r.status == "optimal"
    assert r.totals["cost_eur"] <= tot0["cost_eur"] + 1e-6
    assert "peas_split" not in r.grams.index


def test_split_day_meets_meal_rules():
    tt = O.food_table()
    sol = O.solve(tt, O.spec_from_profile(OWNER, realistic=True)[0])
    sp = ML.split_day(tt, sol.foods.g_eaten, OWNER.mass_kg)
    assert sp is not None and sp.shape[1] - 1 >= ML.CFG["split"]["n_meals"]
    summ = ML.split_summary(tt, sp)
    day_kcal = summ.kcal.sum()
    assert (summ["protein g"] >= min(0.4 * OWNER.mass_kg, 0.9 * summ["protein g"].sum() / len(summ)) - 0.5).all()
    assert (summ.kcal >= 0.2 * day_kcal - 1).all()
    assert ((sp.drop(columns="food").sum(axis=1) - sol.foods.g_eaten.reindex(sp.index)).abs() <= 2).all()


def test_realistic_variant_limits():
    tt = O.food_table()
    spec, _ = O.spec_from_profile(OWNER, realistic=True)
    sol = O.solve(tt, spec)
    assert sol.status == "optimal"
    assert sol.foods.g_eaten.max() <= O.REAL["max_g_per_food"] + 1e-6
    legumes = sol.foods.index[tt.loc[sol.foods.index, "category"].isin(["legumes", "soy"])]
    assert sol.foods.loc[legumes, "g_eaten"].sum() <= 500 + 1e-6
    x = sol.foods.g_eaten.reindex(tt.index).fillna(0)
    for col in ("vitamin_c_mg", "vitamin_b12_ug", "selenium_ug"):   # ≥ 2 sources: no food > 60 %
        contrib = tt[col] * x
        assert contrib.max() <= 0.6 * contrib.sum() + 1e-6
    plain = O.solve(tt, O.spec_from_profile(OWNER)[0])
    assert sol.cost_eur >= plain.cost_eur - 1e-6


def test_appetite_ceiling_and_dislikes():
    p = replace(OWNER, appetite_max_g=2300, dislikes=["peas_split"])
    tt = O.food_table(exclude=p.dislikes)
    sol = O.solve(tt, O.spec_from_profile(p)[0])
    assert sol.status == "optimal" and sol.mass_g <= 2300 + 1e-6 and "peas_split" not in sol.foods.index


def test_omega3_targets_met():
    tt = O.food_table()
    sol = O.solve(tt, O.spec_from_profile(OWNER)[0])
    assert sol.micro_totals["epa_dha_g"] >= 0.25 - 1e-6
    assert sol.micro_totals["ala_g"] >= RES.micros["ala_g"].min - 1e-6


def test_race_week_carbohydrate_loading():
    r = compute(replace(OWNER, goal="race_week"))
    assert r.targets["carbohydrate"].low == pytest.approx(10 * OWNER.mass_kg)
    assert r.micros["fibre_g"].max == 25 and r.micros["fibre_g"].min is None
    assert not r.micros["vitamin_c_mg"].enforce          # minimums reported only for a 1–2 day phase
    assert not r.conflicts


def test_country_factors():
    df = O.food_table()
    assert set(CT.countries()) >= {"LV", "DK", "NL"}
    dk = O.food_table(country="DK")
    assert not set(CT.LV_ONLY) & set(dk.index)
    common = dk.index.intersection(df.index)
    ratio = dk.eur[common] / df.eur[common]
    assert ratio.between(0.5, 2.5).all()
    assert ratio.loc["chicken_fillet"] == pytest.approx(CT.pli().loc["DK", "Meat"] / CT.pli().loc["LV", "Meat"])
