"""Safe formula language for custom charts (src/formula.py)."""
import numpy as np
import pandas as pd
import pytest

from src import formula as F
from src import metrics as M


@pytest.fixture(scope="module")
def env():
    return F.environment(M.with_price(M.load()))[0]


def test_aliases_and_arithmetic(env):
    v = F.evaluate("protein / kcal * 100", env)
    assert isinstance(v, pd.Series) and np.isfinite(v.dropna()).all()
    assert (v.dropna() >= 0).all()


def test_functions_filters_and_text(env):
    assert F.evaluate("pct(kcal_per_eur)", env).dropna().between(0, 100).all()
    m = F.evaluate('protein > 10 and group != "Supplements"', env)
    assert m.dtype == bool and 0 < m.sum() < len(m)
    assert (F.evaluate("min(protein, 20)", env).dropna() <= 20).all()
    assert F.evaluate("where(fat > 50, 1, 0)", env).isin([0, 1]).all()


def test_division_by_zero_gives_nan(env):
    v = F.evaluate("protein / fibre", env)
    assert not np.isinf(v).any()


@pytest.mark.parametrize("bad", [
    "__import__('os').system('ls')", "protein.__class__", "open('x')", "[1, 2]", "lambda: 1", "protein if 1 else 2",
    "x" * 500, "", "1 +", "kcall / 2", "name + 1"])
def test_rejects_unsafe_or_invalid(env, bad):
    with pytest.raises(F.FormulaError):
        F.evaluate(bad, env)


def test_unknown_name_suggests(env):
    with pytest.raises(F.FormulaError, match="did you mean"):
        F.evaluate("protien / kcal", env)


def test_user_definitions_chain():
    env, meta = F.environment(M.with_price(M.load()), "p100 = protein / kcal * 100\nscore = p100 * diaas / 100  # quality")
    assert "score" in env and meta["p100"].startswith("protein")
    with pytest.raises(F.FormulaError):
        F.environment(M.load(), "bad line without equals")


def test_reference_table():
    t = F.reference(M.with_price(M.load()))
    assert {"protein", "cost", "price", "fibre_sol_g", "group"} <= set(t.name)
