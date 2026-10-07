"""Smoke tests for the multipage Streamlit app (streamlit.testing.AppTest runs the script headless).
NUTRITION_START_PAGE selects the page AppTest opens (pages are functions registered with st.navigation)."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def open_page(monkeypatch, page):
    from streamlit.testing.v1 import AppTest
    if not (ROOT / "data/processed/foods_master.csv").exists():
        pytest.skip("foods_master.csv not built")
    monkeypatch.setenv("NUTRITION_START_PAGE", page)
    at = AppTest.from_file(str(ROOT / "app/app.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("page", ["profile", "meal", "plan", "fix", "explorer", "rankings", "food", "export", "methods"])
def test_every_page_runs(monkeypatch, page):
    at = open_page(monkeypatch, page)
    assert not at.error, [e.value for e in at.error]
    assert not at.warning or page == "profile", [w.value for w in at.warning]


def test_profile_targets_and_settings(monkeypatch):
    at = open_page(monkeypatch, "profile")
    assert any("energy" in m.value for m in at.markdown), "targets table not rendered"
    at.sidebar.selectbox(key="quality").set_value("crude").run()
    at.sidebar.selectbox(key="price_scn").set_value("high (band upper edge)").run()
    assert not at.exception, at.exception


def test_export_downloads(monkeypatch):
    at = open_page(monkeypatch, "export")
    labels = {b.label for b in at.get("download_button")}
    assert {"foods_ranked.csv", "optimal_diet.csv", "realistic_diet.csv", "brief.md", "All (ZIP)"} <= labels, labels


def test_plan_and_country(monkeypatch):
    at = open_page(monkeypatch, "plan")
    cost = lambda: next(m.value for m in at.metric if m.label == "Cost per day")  # noqa: E731
    lv = cost()
    at.selectbox(key="country").set_value("DK").run()
    assert not at.exception, at.exception
    assert cost() != lv
    at.toggle(key="pl_real").set_value(False).run()
    assert not at.exception, at.exception


def test_fix_my_day(monkeypatch):
    at = open_page(monkeypatch, "fix")
    at.selectbox(key="fix_start").set_value("latvian_typical").run()
    assert not at.exception, at.exception
    assert any(m.label == "Adjusted day cost" for m in at.metric), [m.label for m in at.metric]


def test_meal_scores_and_improves(monkeypatch):
    at = open_page(monkeypatch, "meal")
    labels = [m.label for m in at.metric]
    assert "Your meal" in labels and "Improved meal" in labels, labels
    mine = next(m for m in at.metric if m.label == "Your meal")
    better = next(m for m in at.metric if m.label == "Improved meal")
    assert float(better.value.split("/")[0]) >= float(mine.value.split("/")[0])
    at.radio(key="meal_mode").set_value("best").run()
    assert not at.exception, at.exception


def test_rankings_personal_and_custom(monkeypatch):
    at = open_page(monkeypatch, "rankings")
    assert any("pct(" in m.value for m in at.markdown), "formula not shown"
    at.segmented_control(key="rk_mode").set_value("Custom weighting").run()
    assert not at.exception, at.exception


def test_custom_chart(monkeypatch):
    at = open_page(monkeypatch, "explorer")
    assert not at.error, [e.value for e in at.error]
    at.text_input(key="ex_y").set_value("dleu / kcal * 100").run()
    at.text_input(key="ex_c").set_value("pct(kcal_per_eur)").run()
    assert not at.exception and not at.error
    at.text_input(key="ex_y").set_value("__import__('os')").run()
    assert any("Formula problem" in e.value for e in at.error)
    for ex in ["Omega-6 ÷ omega-3 ratio (ranking, lowest first)", "My own score: useful protein and fibre per € (defined variables)",
               "Lysine vs methionine + cysteine (per g protein)"]:
        at.selectbox(key="ex_example").set_value(ex).run()
        assert not at.exception and not at.error, (ex, [e.value for e in at.error])
    at.segmented_control(key="ex_mode").set_value("Preset views").run()
    assert not at.exception, at.exception
