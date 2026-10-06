"""Food value explorer (v0.1). Run from the project root:

    host-spawn .venv/bin/streamlit run app/app.py      (inside the VS Code Flatpak terminal)
    .venv/bin/streamlit run app/app.py                   (normal terminal)
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import metrics as M  # noqa: E402
from src import plots as P  # noqa: E402
from src import export as X  # noqa: E402
from src import targets as TG  # noqa: E402
from dataclasses import replace  # noqa: E402

st.set_page_config(page_title="Food Value Explorer", page_icon="🥣", layout="wide")


@st.cache_data
def base_data():
    return M.load()


WEIGHTABLE = [m for m, (_, _, hib) in M.METRICS.items() if hib is not None and m != "diaas"]
SCATTER_PRESETS = {
    "Density: useful protein vs calories (per 100 g eaten)": ("useful_protein_100g_eaten", "kcal_100g_eaten", False, False),
    "Economy: useful protein/€ vs calories/€": ("useful_protein_per_eur", "kcal_per_eur", True, True),
    "Endurance: useful protein/€ vs carbs/€": ("useful_protein_per_eur", "carb_per_eur", True, True),
    "Volume: grams eaten vs € for 1000 kcal": ("g_eaten_per_1000kcal", "eur_per_1000kcal", True, True),
    "Cutting view: useful protein per 1000 kcal vs calories/€": ("useful_protein_per_1000kcal", "kcal_per_eur", False, True),
}

# ---------------------------------------------------------------- sidebar: settings
with st.sidebar:
    st.header("Settings")
    quality = st.selectbox("Protein quality definition", list(M.QUALITY), format_func=lambda q: M.QUALITY[q])
    price_scn = st.selectbox("Price scenario", list(M.PRICE_SCENARIOS),
                             help="Central = CSP 12-month mean or Cenu Depo median. Band edges = CSP monthly "
                                  "min/max or Cenu Depo P25/P75.")
    st.subheader("Foods")
    roles = st.multiselect("Include", ["core", "ingredient", "snack", "supplement"], default=["core"],
                           help="Ingredients (oil, sugar, flour…) and snacks are shown for comparison; "
                                "the project ranks core foods only (PROJECT.md §9.1).")
    groups = st.multiselect("Food groups", M.GROUPS, default=[g for g in M.GROUPS if g != "Supplements"])
    min_grade = st.select_slider("Worst acceptable data grade", ["A", "B", "C"], value="C",
                                 help="Composition, digestibility and price grades (A best). C = proxy/estimate.")
    st.subheader("Weights for the composite score")
    preset = st.selectbox("Start from preset", ["(custom)"] + list(M.PRESETS), index=1)
    defaults = M.PRESETS.get(preset, {})
    weights = {}
    with st.expander("Adjust weights (0 = ignore)", expanded=False):
        for m in WEIGHTABLE:
            weights[m] = st.slider(f"{M.METRICS[m][0]} ({'↑' if M.METRICS[m][2] else '↓'} better)", 0.0, 5.0,
                                   float(defaults.get(m, 0)), 0.5, key=f"w_{m}_{preset}")
    norm = st.radio("Normalization", list(M.NORMALIZATIONS), index=1, horizontal=True,
                    help=" · ".join(f"{k}: {v}" for k, v in M.NORMALIZATIONS.items()))

# ---------------------------------------------------------------- data under current settings
df = M.with_price(M.with_quality(base_data(), quality), price_scn)
order = {"A": 0, "B": 1, "C": 2, "": 0}
worst = df[["comp_grade", "digest_grade", "price_grade"]].fillna("").apply(
    lambda r: max(order.get(str(x), 0) for x in r), axis=1)
view = df[df.role.isin(roles) & df.group.isin(groups) & (worst <= order[min_grade])
          & df.eur_per_kg_used.notna() & df.kcal_100g_purchased.notna()].copy()
w = {k: v for k, v in weights.items() if v > 0}
if w:
    view["score"] = M.composite(view, w, norm)

st.title("Food value explorer")
st.caption(f"{len(view)} foods shown · quality: {quality} · prices: {price_scn} · "
           "prices dated 2026-10-06 (personal-use phase; Cenu Depo data is not for publication). "
           "**Scores are hypotheses under your weights, not recommendations.**")

tab_me, tab_rank, tab_scatter, tab_day, tab_food = st.tabs(
    ["My targets & AI export", "Rankings", "Explorer", "One-food day", "Food details"])


# ---------------------------------------------------------------- tab 0: profile → targets → AI export (v0.2)
with tab_me:
    profiles = {f.stem: f for f in sorted((ROOT / "config/profiles").glob("*.yaml"))}
    base_key = st.selectbox("Start from profile", list(profiles), index=list(profiles).index("owner")
                            if "owner" in profiles else 0)
    base = TG.load_profile(profiles[base_key])
    goals = TG.RULES["presets"]
    with st.form("profile"):
        c1, c2, c3, c4 = st.columns(4)
        sex = c1.selectbox("Sex", ["male", "female"], index=0 if base.sex == "male" else 1)
        age = c2.number_input("Age", 14, 90, int(base.age))
        mass = c3.number_input("Body mass (kg)", 35.0, 200.0, float(base.mass_kg), 0.5)
        height = c4.number_input("Height (cm)", 130.0, 220.0, float(base.height_cm), 1.0)
        c1, c2, c3, c4 = st.columns(4)
        modality = c1.selectbox("Training", ["none", "strength", "endurance", "hybrid"],
                                index=["none", "strength", "endurance", "hybrid"].index(base.modality))
        hours = c2.number_input("Training hours / week", 0.0, 40.0, float(base.training.get("hours_per_week", 0)), 0.5)
        goal = c3.selectbox("Goal", list(goals), index=list(goals).index(base.goal),
                            format_func=lambda g: goals[g]["label"])
        exp = c4.selectbox("Training experience", ["novice_intermediate", "advanced"],
                           index=0 if base.experience != "advanced" else 1)
        c1, c2, c3, c4 = st.columns(4)
        bf = c1.number_input("Body fat % (0 = unknown)", 0.0, 60.0, float(base.body_fat_pct or 0), 0.5)
        tmass = c2.number_input("Target body mass (kg, 0 = none)", 0.0, 200.0, float(base.target_mass_kg or 0), 0.5)
        tdee = c3.number_input("Known energy expenditure (kcal/day, 0 = estimate)", 0, 8000, int(base.tdee_kcal or 0), 50)
        cost_w = c4.selectbox("Does price matter?", ["yes", "no"], index=0 if (base.priorities or {}).get("cost", 1) else 1)
        c1, c2 = st.columns(2)
        o_e = c1.number_input("Override energy target (kcal, 0 = calculate)", 0, 8000,
                              int(base.overrides.get("energy_kcal", 0)), 50)
        o_p = c2.number_input("Override protein (g/day, 0 = calculate)", 0, 400, int(base.overrides.get("protein_g", 0)), 5)
        st.form_submit_button("Calculate targets")
    prof = replace(base, sex=sex, age=age, mass_kg=mass, height_cm=height, goal=goal, experience=exp,
                   training={"modality": modality, "hours_per_week": hours},
                   body_fat_pct=bf or None, target_mass_kg=tmass or None, tdee_kcal=tdee or None,
                   overrides={k: v for k, v in {"energy_kcal": o_e, "protein_g": o_p}.items() if v},
                   priorities={"cost": 1.0 if cost_w == "yes" else 0.0})
    res = TG.compute(prof)
    st.session_state["energy_target"] = int(round(res.targets["energy"].value / 50) * 50)
    for c in res.conflicts:
        st.error(c)
    for wmsg in res.warnings:
        st.warning(wmsg)
    st.markdown(res.to_markdown().split("**Conflicts**")[0].split("**Warnings**")[0].split("**Notes**")[0])
    for n in res.notes:
        st.caption(n)
    st.subheader("Export for an AI recipe / meal-plan assistant")
    st.markdown("Ranks the foods for this person with the **sidebar settings** (weights, protein quality, price "
                "scenario, food groups). Cooking ingredients are always included (unranked). Upload both files to "
                "the AI and paste the prompt at the end of `brief.md`.")
    exp_roles = tuple(sorted(set(roles) | {"core", "ingredient"}))
    ranked, brief, _ = X.build(prof, preset if preset in M.PRESETS else "Bulking: balanced", exp_roles, quality,
                               price_scn, weights=(w or None) if preset == "(custom)" or w != M.PRESETS.get(preset)
                               else None, groups=groups)
    csv_text = ranked.to_csv(index=False)
    e1, e2, e3 = st.columns(3)
    stem = f"{base_key}_targets"
    e1.download_button("foods_ranked.csv", csv_text, f"{stem}_foods_ranked.csv", "text/csv")
    e2.download_button("brief.md", brief, f"{stem}_brief.md", "text/markdown")
    e3.download_button("Both (ZIP)", X.zip_bytes(csv_text, brief), f"{stem}_ai_export.zip", "application/zip")
    with st.expander("Preview brief.md"):
        st.markdown(brief)

# ---------------------------------------------------------------- tab 1: rankings
with tab_rank:
    if not w:
        st.info("Set at least one weight in the sidebar to compute a composite score.")
    else:
        st.markdown("Composite score = weighted geometric mean of normalized metrics "
                    f"({', '.join(f'{M.METRICS[k][0]} ×{v:g}' for k, v in w.items())}).")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(P.ranking_bar_fig(view, "score", n=min(30, len(view))), width="stretch")
        with c2:
            cols = ["name_en", "group", "score"] + list(w)
            tbl = view.sort_values("score", ascending=False)[cols].round(2).reset_index(drop=True)
            tbl.index += 1
            st.dataframe(tbl, height=650)
        export = view.sort_values("score", ascending=False)
        config = {"quality": quality, "price_scenario": price_scn, "roles": roles, "groups": groups,
                  "min_grade": min_grade, "weights": w, "normalization": norm}
        d1, d2 = st.columns(2)
        d1.download_button("Download ranking (CSV)", export.to_csv(index=False), "ranking.csv", "text/csv")
        d2.download_button("Download settings (JSON)", json.dumps(config, indent=2), "settings.json",
                           "application/json")

# ---------------------------------------------------------------- tab 2: scatter explorer
with tab_scatter:
    c1, c2 = st.columns([2, 1])
    choice = c1.selectbox("View", ["(custom)"] + list(SCATTER_PRESETS), index=1)
    metric_keys = [m for m in M.METRICS if m in view.columns]
    if choice == "(custom)":
        a, b, c, d = st.columns(4)
        x = a.selectbox("x axis", metric_keys, index=metric_keys.index("useful_protein_per_eur"))
        y = b.selectbox("y axis", metric_keys, index=metric_keys.index("kcal_per_eur"))
        logx, logy = c.checkbox("log x"), d.checkbox("log y")
    else:
        x, y, logx, logy = SCATTER_PRESETS[choice]
    show_front = c2.checkbox("Show Pareto front", value=True)
    top_n = c2.slider("Highlight top N by composite score", 0, 30, 0) if w else 0
    hl = set(view.nlargest(top_n, "score").food_id) if top_n else None
    plot_df = view[(view[x] > 0) | (not logx)] if logx else view
    plot_df = plot_df[(plot_df[y] > 0)] if logy else plot_df
    st.plotly_chart(P.scatter_fig(plot_df, x, y, logx, logy, front=show_front, highlight=hl), width="stretch")
    hidden = len(view) - len(plot_df)
    if hidden:
        st.caption(f"{hidden} foods with a zero value are not shown on log axes (e.g. oils/sugar have no protein).")

# ---------------------------------------------------------------- tab 3: one-food day
with tab_day:
    kcal = st.number_input("Daily energy target (kcal)", 1000, 8000, st.session_state.get("energy_target", 3400), 50,
                           help="Default: the energy target from 'My targets'. Illustration only: "
                                "a real diet mixes foods (v1.0 optimizer).")
    day = view.assign(kg_eaten=kcal / view.kcal_100g_eaten / 10, cost_eur=view.eur_per_1000kcal * kcal / 1000,
                      useful_protein_g=view.useful_protein_per_1000kcal * kcal / 1000,
                      carbs_g=view.carb_100g_purchased / view.kcal_100g_purchased * kcal)
    sort = st.radio("Sort by", ["kg_eaten", "cost_eur", "useful_protein_g"], horizontal=True)
    t = day.sort_values(sort, ascending=sort != "useful_protein_g")[
        ["name_en", "group", "kg_eaten", "cost_eur", "useful_protein_g", "carbs_g"]].round(2).reset_index(drop=True)
    t.index += 1
    st.dataframe(t, height=600)

# ---------------------------------------------------------------- tab 4: food details
with tab_food:
    names = df.sort_values("name_en").set_index("food_id").name_en
    fid = st.selectbox("Food", names.index, format_func=lambda i: f"{names[i]} ({i})")
    r = df.set_index("food_id").loc[fid]
    a, b, c = st.columns(3)
    a.metric("kcal / 100 g eaten", f"{r.kcal_100g_eaten:.0f}" if pd.notna(r.kcal_100g_eaten) else "–")
    b.metric("Useful protein / 100 g eaten", f"{r.useful_protein_100g_eaten:.1f} g"
             if pd.notna(r.useful_protein_100g_eaten) else "–")
    c.metric("Price", f"€{r.eur_per_kg_used:.2f}/kg edible" if pd.notna(r.eur_per_kg_used) else "no price")
    st.markdown(f"""
**{r.name_en}** ({r.name_lv}) · group {r.group} · role {r.role}

- Composition: `{r.comp_source}`: {r.comp_description} (grade **{r.comp_grade}**); amino acids from `{r.aa_source}`
- Cooking: eaten mass = {r.yield_eaten_per_purchased:.2f} × purchased; edible portion {r.edible_portion:.2f}
- Protein quality: DIAAS **{r.diaas:.0f}** (adult), {r.diaas_child:.0f} (young-child pattern), limiting amino acid
  **{r.limiting_aa}**, digestibility grade **{r.digest_grade}** ({r.get('digest_note', '')})
- Price: €{r.eur_per_kg_edible:.2f}/kg edible (band {r.price_band_lo:.2f}–{r.price_band_hi:.2f}), source
  {r.price_source}, grade **{r.price_grade}**
- Flags: {r.flags if isinstance(r.flags, str) and r.flags else "none"}
""")
    per100 = pd.DataFrame({
        "purchased (per 100 g edible)": [r[f"{k}_100g_purchased"] for k in
                                         ["kcal", "protein", "carb", "fat", "free_sugars", "fibre"]],
        "eaten (per 100 g)": [r[f"{k}_100g_eaten"] for k in ["kcal", "protein", "carb", "fat", "free_sugars", "fibre"]],
    }, index=["kcal", "protein g", "carbohydrate g", "fat g", "free sugars g", "fibre g"]).round(1)
    aa = pd.Series({a: r[f"{a}_mg_per_g_protein"] for a in
                    ["HIS", "ILE", "LEU", "LYS", "MET", "CYS", "PHE", "TYR", "THR", "TRP", "VAL"]}).round(1)
    c1, c2 = st.columns(2)
    c1.dataframe(per100)
    c2.dataframe(aa.rename("mg per g protein"))
