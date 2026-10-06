"""Tests for src/metrics.py."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import metrics as M  # noqa: E402


def test_pareto_mask_simple_maximize():
    v = np.array([[1, 5], [2, 4], [3, 3], [1, 1], [2, 2]])
    assert M.pareto_mask(v, [True, True]).tolist() == [True, True, True, False, False]


def test_pareto_mask_mixed_directions_and_ties():
    # maximize x, minimize y; duplicates of a front point are both kept (neither strictly dominates)
    v = np.array([[3, 1], [3, 1], [2, 0.5], [1, 2], [3, 2]])
    assert M.pareto_mask(v, [True, False]).tolist() == [True, True, True, False, False]


def test_pareto_mask_nan_never_on_front():
    v = np.array([[np.nan, 10], [1, 1]])
    assert M.pareto_mask(v, [True, True]).tolist() == [False, True]


def test_pareto_ranks_peel_layers():
    v = np.array([[3, 3], [2, 2], [1, 1], [3, 1]])
    assert M.pareto_ranks(v, [True, True]).tolist() == [1, 2, 3, 2]


def test_normalize_direction_and_range():
    s = pd.Series([1.0, 2.0, 3.0])
    up, down = M.normalize(s, True, "minmax"), M.normalize(s, False, "minmax")
    assert up.iloc[2] == 1 and down.iloc[0] == 1
    assert (up > 0).all() and (up <= 1).all()


def test_composite_geometric_penalizes_weak_metric():
    df = pd.DataFrame({"kcal_per_eur": [100, 50, 10], "useful_protein_per_eur": [1, 50, 100]})
    s = M.composite(df, {"kcal_per_eur": 1, "useful_protein_per_eur": 1}, "minmax")
    assert s.idxmax() == 1  # the balanced food beats both specialists


def test_composite_respects_lower_is_better():
    df = pd.DataFrame({"g_eaten_per_1000kcal": [150, 1500]})
    s = M.composite(df, {"g_eaten_per_1000kcal": 1})
    assert s.iloc[0] > s.iloc[1]


def test_composite_rejects_directionless_metric():
    with pytest.raises(ValueError):
        M.composite(pd.DataFrame({"fat_energy_pct": [10, 20]}), {"fat_energy_pct": 1})


def test_compare_rankings_identical_and_reversed():
    a = pd.Series([1, 2, 3, 4], index=list("abcd"))
    assert M.compare_rankings(a, a, k=2)["spearman"] == pytest.approx(1)
    r = M.compare_rankings(a, -a, k=2)
    assert r["spearman"] == pytest.approx(-1) and r["top2_overlap"] == 0


def test_quality_definitions_on_master():
    if not M.MASTER.exists():
        pytest.skip("foods_master.csv not built")
    df = M.load()
    crude, adult, child = (M.with_quality(df, q) for q in ("crude", "diaas", "diaas_child"))
    p = df.protein_100g_purchased.fillna(0) > 0
    # stricter definitions can only lower useful protein
    assert (adult.useful_protein_100g_eaten[p] <= crude.useful_protein_100g_eaten[p] + 1e-9).all()
    assert (child.useful_protein_100g_eaten[p] <= adult.useful_protein_100g_eaten[p] + 1e-9).all()
    assert set(df.group) <= set(M.GROUPS)
