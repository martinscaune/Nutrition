"""Unit tests for the core calculations (run: .venv/bin/python -m pytest -q)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.build_master import PATTERN, diaas  # noqa: E402
from src.prices.cenudepo import pack_size, spaced  # noqa: E402

AA = ["TRP", "THR", "ILE", "LEU", "LYS", "MET", "CYS", "PHE", "TYR", "VAL", "HIS"]


def reference_profile(scale=1.0):
    """An AA profile exactly matching the FAO adult pattern (SAA split 50/50 Met/Cys, AAA split 50/50 Phe/Tyr)."""
    p = {"TRP": PATTERN["TRP"], "THR": PATTERN["THR"], "ILE": PATTERN["ILE"], "LEU": PATTERN["LEU"],
         "LYS": PATTERN["LYS"], "MET": PATTERN["SAA"] / 2, "CYS": PATTERN["SAA"] / 2, "PHE": PATTERN["AAA"] / 2,
         "TYR": PATTERN["AAA"] / 2, "VAL": PATTERN["VAL"], "HIS": PATTERN["HIS"]}
    return pd.Series({k: v * scale for k, v in p.items()})


def test_diaas_reference_protein_fully_digestible_is_100():
    score, _ = diaas(reference_profile(), pd.Series(1.0, index=AA))
    assert score == pytest.approx(100.0)


def test_diaas_scales_with_digestibility_and_is_untruncated():
    score, _ = diaas(reference_profile(1.5), pd.Series(1.0, index=AA))
    assert score == pytest.approx(150.0)  # single foods are NOT truncated (FAO 2013)
    score, _ = diaas(reference_profile(), pd.Series(0.8, index=AA))
    assert score == pytest.approx(80.0)


def test_diaas_finds_limiting_amino_acid():
    p = reference_profile()
    p["LYS"] = PATTERN["LYS"] * 0.5  # lysine-poor, like cereals
    score, lim = diaas(p, pd.Series(1.0, index=AA))
    assert lim == "LYS" and score == pytest.approx(50.0)


def test_diaas_missing_data_gives_nan():
    p = reference_profile()
    p["TRP"] = np.nan
    score, lim = diaas(p, pd.Series(1.0, index=AA))
    assert np.isnan(score) and lim == ""


@pytest.mark.parametrize("name,expected", [
    ("BULGURS VALDO VIDĒJA MALUMA, 500G (4×125G)", (500.0, "g", None)),
    ("PROSA VALDO 4X125G", (500.0, "g", None)),
    ("RĪSI 0,5KG", (500.0, "g", None)),
    ("PIENS 2% 1L", (1000.0, "ml", None)),
    ("OLAS 10GAB", (None, "pcs", 10)),
    ("TUNCIS SAVĀ SULĀ 185G/130G", (130.0, "g", None)),  # last size = drained mass
    ("SALDIE KARTUPEĻI - BATĀTES KG", (1000.0, "g", None)),  # sold by weight → price per kg
    ("MALTĀ GAĻA FOREVERS SVER.", (1000.0, "g", None)),
])
def test_pack_size_parser(name, expected):
    assert pack_size(name) == expected


def test_spaced_sample_keeps_ends_and_size():
    items = list(range(65))
    s = spaced(items, 20)
    assert s[0] == 0 and s[-1] == 64 and len(s) == 20
    assert spaced([1, 2, 3], 20) == [1, 2, 3]


def test_master_dataset_invariants():
    """Run only after the pipeline: basic physical sanity of foods_master.csv."""
    p = ROOT / "data/processed/foods_master.csv"
    if not p.exists():
        pytest.skip("foods_master.csv not built yet")
    m = pd.read_csv(p)
    has = m.kcal_100g_purchased.notna()
    assert (m.loc[has, "kcal_100g_purchased"] <= 905).all()          # nothing denser than pure fat
    assert (m.loc[has, "protein_100g_purchased"] <= 100).all()
    assert (m.yield_eaten_per_purchased.between(0.4, 8)).all()   # porridges are watery (semolina ≈ 6.4)
    assert (m.edible_portion.between(0.3, 1.0)).all()
    assert (m.quality_factor.between(0, 1)).all()
    assert (m.useful_protein_100g_eaten.fillna(0) <= m.protein_100g_eaten.fillna(0) + 1e-9).all()
