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
