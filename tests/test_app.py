"""Smoke tests for the Streamlit app (streamlit.testing.AppTest runs the script headless)."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app():
    from streamlit.testing.v1 import AppTest
    if not (ROOT / "data/processed/foods_master.csv").exists():
        pytest.skip("foods_master.csv not built")
    at = AppTest.from_file(str(ROOT / "app/app.py"), default_timeout=60)
    at.run()
    return at


def test_app_runs_without_exceptions(app):
    assert not app.exception, app.exception


def test_app_switching_settings(app):
    app.sidebar.selectbox[0].set_value("crude").run()          # quality definition
    app.sidebar.selectbox[1].set_value("high (band upper edge)").run()  # price scenario
    app.sidebar.multiselect[0].set_value(["core", "ingredient", "snack", "supplement"]).run()
    assert not app.exception, app.exception
    app.sidebar.selectbox[2].set_value("Protein on a budget").run()
    assert not app.exception, app.exception


def test_targets_tab_and_export(app):
    assert any("Daily targets" in m.value for m in app.markdown), "targets table not rendered"
    labels = [b.label for b in app.get("download_button")]
    assert {"foods_ranked.csv", "optimal_diet.csv", "brief.md", "All (ZIP)"} <= set(labels), labels


def test_optimizer_tab(app):
    assert any("Cost per day" in m.label for m in app.metric), [m.label for m in app.metric]


def test_fix_my_diet_tab(app):
    sel = [s for s in app.selectbox if s.label == "Start from"][0]
    sel.set_value("latvian_typical").run()
    assert not app.exception, app.exception
    assert any(m.label == "Adjusted diet cost" for m in app.metric), [m.label for m in app.metric]


def test_meal_tab_scores_and_improves(app):
    labels = [m.label for m in app.metric]
    assert "Your meal" in labels and "Improved meal" in labels, labels
    mine = next(m for m in app.metric if m.label == "Your meal")
    better = next(m for m in app.metric if m.label == "Improved meal")
    assert float(better.value.split("/")[0]) >= float(mine.value.split("/")[0])
    app.radio(key="meal_mode").set_value("best").run()
    assert not app.exception, app.exception


def test_country_selector(app):
    cost = lambda: next(m.value for m in app.metric if m.label == "Cost per day")  # noqa: E731
    lv = cost()
    app.selectbox(key="country").set_value("DK").run()
    assert not app.exception, app.exception
    assert cost() != lv
    assert "realistic_diet.csv" in [b.label for b in app.get("download_button")]
