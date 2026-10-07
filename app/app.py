"""Food value app (multipage). Run from the project root:

    host-spawn .venv/bin/streamlit run app/app.py --server.address localhost   (inside the VS Code Flatpak terminal)
    .venv/bin/streamlit run app/app.py --server.address localhost   (normal terminal)

Only the open page runs on each interaction (st.navigation), and expensive results are cached, which keeps the app fast
(owner comments 2026-10-07). The profile lives in st.session_state and is shared by all pages.
"""
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import export as X  # noqa: E402
from src import formula as F  # noqa: E402
from src import meals as ML  # noqa: E402
from src import metrics as M  # noqa: E402
from src import optimizer as O  # noqa: E402
from src import personal as PS  # noqa: E402
from src import plots as P  # noqa: E402
from src import targets as TG  # noqa: E402
from src.prices import countries as CT  # noqa: E402

st.set_page_config(page_title="Food Value", page_icon="🥣", layout="wide", initial_sidebar_state="collapsed")
ss = st.session_state
PROFILES = {f.stem: f for f in sorted((ROOT / "config/profiles").glob("*.yaml"))}
GOALS = TG.RULES["presets"]
VERDICT = [(90, "excellent"), (75, "good"), (50, "fair"), (0, "poor")]   # display bands (judgment call)
CSS = """
<style>
.fv-band {background: #FCD592; color: #403621; border-left: 6px solid #9A6619; padding: .55rem .9rem;
          border-radius: .4rem; margin: .2rem 0 .8rem 0; font-size: .95rem}
.fv-band b {color: #403621}
.fv-formula {background: #E7E8EB; border: 1px solid #CED2DE; border-radius: .4rem; padding: .45rem .8rem;
             font-family: 'Roboto Mono', monospace; font-size: .85rem; color: #403621; margin: .3rem 0 .6rem 0}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def formula_box(text):
    st.markdown(f'<div class="fv-formula">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- cached computations
@st.cache_data
def base_data():
    return M.load()


@st.cache_data(max_entries=32)
def priced(quality, price_scn, country):
    df = M.with_price(M.with_quality(base_data(), quality), price_scn, country)
    return df[~df.food_id.isin(CT.LV_ONLY)] if country != CT.BASE else df


@st.cache_data(max_entries=64)
def ftable(quality, price_scn, roles, country, exclude=()):
    return O.food_table(quality, price_scn, roles=list(roles), exclude=tuple(exclude), country=country)


@st.cache_data(max_entries=64, show_spinner="Optimizing…")
def solve(_prof, prof_key, quality, price_scn, country, roles, exclude, kw):
    t = ftable(quality, price_scn, roles, country, exclude)
    spec, _ = O.spec_from_profile(_prof, **dict(kw))
    if spec.objective == "mix":
        spec.fixed_cost_norm = max(O.solve(t, replace(spec, objective="cost", milp=False)).cost_eur, 1e-6)
        spec.fixed_mass_norm = max(O.solve(t, replace(spec, objective="mass", milp=False)).mass_g, 1e-6)
    return O.solve(t, spec), spec


@st.cache_data(max_entries=32, show_spinner="Building the AI export…")
def bundle(_prof, prof_key, quality, price_scn, country):
    return X.build_bundle(_prof, None, ("core", "ingredient"), quality, price_scn, country=country)


@st.cache_data(max_entries=64, show_spinner="Optimizing the meal…")
def improve_meal(_prof, prof_key, country, quality, price_scn, items, mode, tiebreak, max_cost, exclude):
    t = ftable(quality, price_scn, ("core", "ingredient", "snack", "supplement"), country)
    return ML.improve(t, pd.Series(dict(items), dtype=float), TG.compute(_prof), mode, max_cost, exclude, tiebreak)


@st.cache_data(max_entries=32)
def personal_rank(_prof, prof_key, quality, price_scn, country, groups):
    t = ftable(quality, price_scn, ("core",), country, tuple(_prof.dislikes or ()))
    t = t[t.group.isin(groups)]
    sol, _ = solve(_prof, prof_key, quality, price_scn, country, ("core", "ingredient"), tuple(_prof.dislikes or ()), ())
    return PS.rank(t, TG.compute(_prof), _prof, sol)


# ---------------------------------------------------------------- shared state: profile, settings, country
if "profile" not in ss:
    key = os.environ.get("NUTRITION_DEFAULT_PROFILE", "owner")   # set on Streamlit Cloud (DEPLOY.md)
    ss.profile_key = key if key in PROFILES else next(iter(PROFILES))
    ss.profile = TG.load_profile(PROFILES[ss.profile_key])
prof = ss.profile
pkey = repr(prof)
res = TG.compute(prof)

with st.sidebar:
    st.header("Data settings")
    st.caption("For the data pages (Explorer, Rankings, Food details) and all prices.")
    quality = st.selectbox("Protein quality definition", list(M.QUALITY), format_func=lambda q: M.QUALITY[q], key="quality")
    price_scn = st.selectbox("Price scenario", list(M.PRICE_SCENARIOS), key="price_scn",
                             help="Central = CSP 12-month mean or Cenu Depo median. Band edges = CSP monthly "
                                  "min/max or Cenu Depo P25/P75.")
    roles = st.multiselect("Foods to include", ["core", "ingredient", "snack", "supplement"], default=["core"],
                           key="roles", help="Ingredients (oil, sugar, flour…), snacks and supplements are shown "
                                             "for comparison; rankings use everyday (core) foods.")
    groups = st.multiselect("Food groups", M.GROUPS, default=[g for g in M.GROUPS if g != "Supplements"], key="groups")
    min_grade = st.select_slider("Worst acceptable data grade", ["A", "B", "C"], value="C", key="min_grade",
                                 help="Composition, digestibility and price grades (A best). C = proxy/estimate.")

CTRY = CT.countries()
h1, h2 = st.columns([5, 1.3])
with h1:
    st.markdown(f'<div class="fv-band">👤 <b>{prof.name}</b> · {prof.sex}, {prof.age:g} y, {prof.mass_kg:g} kg · '
                f'{GOALS[prof.goal]["label"]} · <b>{res.targets["energy"].value:,.0f} kcal</b>, '
                f'{res.targets["protein"].value:.0f} g protein per day</div>', unsafe_allow_html=True)
country = h2.selectbox("Prices for", list(CTRY), format_func=lambda c: f"{CTRY[c]} ({c})", key="country",
                       label_visibility="collapsed",
                       help=f"Latvia = observed shop prices. Other countries = Latvian prices × Eurostat food price level "
                            f"index of the food's category ({CT.year()}), relative to Latvia: approximate.")

df = priced(quality, price_scn, country)
order = {"A": 0, "B": 1, "C": 2, "": 0}
worst = df[["comp_grade", "digest_grade", "price_grade"]].fillna("").apply(
    lambda r: max(order.get(str(x), 0) for x in r), axis=1)
view = df[df.role.isin(roles) & df.group.isin(groups) & (worst <= order[min_grade])
          & df.eur_per_kg_used.notna() & df.kcal_100g_purchased.notna()].copy()
food_names = df.set_index("food_id").name_en


def persistent_editor(name, initial, options, help_text=None):
    """Data editor (food, grams eaten) whose content survives page switches and template changes."""
    ver, data = f"_{name}_ver", f"_{name}_data"
    if ss.get(f"_{name}_init") != initial:          # new template: start from it
        ss[data] = pd.DataFrame({"food": list(initial), "grams eaten": list(initial.values())},
                                columns=["food", "grams eaten"]).astype({"food": str, "grams eaten": float})
        ss[f"_{name}_init"] = initial
        ss[ver] = ss.get(ver, 0) + 1
    elif ss.get("_entered") and f"_{name}_last" in ss:  # back on the page: continue from the last edited table
        ss[data] = ss[f"_{name}_last"]
        ss[ver] = ss.get(ver, 0) + 1
    ed = st.data_editor(ss[data], num_rows="dynamic", width="stretch", key=f"{name}_{ss[ver]}",
                        column_config={"food": st.column_config.SelectboxColumn(options=sorted(options), required=True),
                                       "grams eaten": st.column_config.NumberColumn(min_value=0, step=10)})
    ss[f"_{name}_last"] = ed
    if help_text:
        st.caption(help_text)
    return ed


def editor_series(ed, n2id):
    return pd.Series({n2id[r.food]: float(r["grams eaten"]) for _, r in ed.iterrows()
                      if isinstance(r.food, str) and r.food in n2id and pd.notna(r["grams eaten"]) and r["grams eaten"] > 0},
                     dtype=float)


def keep(name):
    """Make a widget value survive page switches (Streamlit forgets widgets that are not rendered)."""
    if f"_{name}" in ss and name not in ss:
        ss[name] = ss[f"_{name}"]


def remember(*names):
    for n in names:
        if n in ss:
            ss[f"_{n}"] = ss[n]


UNIT_HINT = ("Grams **as eaten** (cooked, drained, without shell or bone). Rough guide: 1 egg (size M) ≈ 51 g · "
             "1 can of beans/chickpeas ≈ 240 g drained · 1 slice of bread ≈ 35 g · 1 tbsp oil ≈ 10 g · "
             "1 glass of milk ≈ 250 g · 1 cup of cooked rice ≈ 160 g.")


# ================================================================ pages: start
def page_profile():
    st.title("My profile & targets")
    st.markdown("Start here. Everything else (meal scores, day plans, rankings, the AI export) is calculated for "
                "**this** person. Values are kept while you use the app.")

    def load_base():
        ss.profile_key = ss.base_profile
        ss.profile = TG.load_profile(PROFILES[ss.base_profile])
    st.selectbox("Start from an example profile", list(PROFILES), index=list(PROFILES).index(ss.profile_key),
                 key="base_profile", on_change=load_base)
    p = ss.profile
    with st.form("profile_form"):
        with st.container(border=True):
            st.markdown("**Body**")
            c1, c2, c3, c4 = st.columns(4)
            sex = c1.selectbox("Sex", ["male", "female"], index=0 if p.sex == "male" else 1)
            age = c2.number_input("Age", 18, 90, int(max(18, p.age)))
            mass = c3.number_input("Body mass (kg)", 35.0, 200.0, float(p.mass_kg), 0.5)
            height = c4.number_input("Height (cm)", 130.0, 220.0, float(p.height_cm), 1.0)
            c1, c2, c3, c4 = st.columns(4)
            bf = c1.number_input("Body fat % (0 = unknown)", 0.0, 60.0, float(p.body_fat_pct or 0), 0.5)
            tmass = c2.number_input("Target body mass (kg, 0 = none)", 0.0, 200.0, float(p.target_mass_kg or 0), 0.5)
            tdee = c3.number_input("Known energy expenditure (kcal/day, 0 = estimate)", 0, 8000, int(p.tdee_kcal or 0), 50)
            appetite = c4.number_input("Appetite ceiling (g food/day, 0 = none)", 0, 8000, int(p.appetite_max_g or 0), 100,
                                       help="The most food (grams as eaten) you can comfortably eat in a day.")
        with st.container(border=True):
            st.markdown("**Training & goal**")
            c1, c2, c3, c4 = st.columns(4)
            mods = ["none", "strength", "endurance", "hybrid"]
            modality = c1.selectbox("Training", mods, index=mods.index(p.modality))
            hours = c2.number_input("Training hours / week", 0.0, 40.0, float(p.training.get("hours_per_week", 0)), 0.5)
            goal = c3.selectbox("Goal", list(GOALS), index=list(GOALS).index(p.goal), format_func=lambda g: GOALS[g]["label"])
            exp = c4.selectbox("Training experience", ["novice_intermediate", "advanced"],
                               index=0 if p.experience != "advanced" else 1)
        with st.container(border=True):
            st.markdown("**Preferences & personal targets**")
            c1, c2, c3, c4 = st.columns(4)
            cost_w = c1.selectbox("Does price matter?", ["yes", "no"], index=0 if (p.priorities or {}).get("cost", 1) else 1)
            o = p.overrides or {}
            fib_max = c2.number_input("Fibre maximum (g/day)", 20, 100, int(o.get("fibre_g_max", 45)), 5,
                                      help="No official upper limit exists; 45 g is our default (raise intake "
                                           "gradually if you are not used to high fibre).")
            vit_c = c3.checkbox("Higher vitamin C target (200 mg/day)", value=float(o.get("vitamin_c_mg_min", 0)) >= 200,
                                help="EFSA's 110/95 mg keeps plasma near saturation; 200 mg is the first intake past the "
                                     "steep part of the plasma curve (Levine 1996; Carr & Frei 1999).")
            o_e = c4.number_input("Override energy (kcal, 0 = calculate)", 0, 8000, int(o.get("energy_kcal", 0)), 50)
            c1, c2 = st.columns([1, 3])
            o_p = c1.number_input("Override protein (g/day, 0 = calculate)", 0, 400, int(o.get("protein_g", 0)), 5)
            dislikes = c2.multiselect("Foods I don't eat (allergies, dislikes)", sorted(food_names.index),
                                      default=[f for f in (p.dislikes or []) if f in food_names.index],
                                      format_func=lambda f: food_names[f])
        if st.form_submit_button("Save & calculate targets", type="primary"):
            ov = {"energy_kcal": o_e, "protein_g": o_p, "vitamin_c_mg_min": 200 if vit_c else 0,
                  "fibre_g_max": fib_max if fib_max != 45 else 0}
            ss.profile = replace(p, sex=sex, age=age, mass_kg=mass, height_cm=height, goal=goal, experience=exp,
                                 training={"modality": modality, "hours_per_week": hours}, body_fat_pct=bf or None,
                                 target_mass_kg=tmass or None, tdee_kcal=tdee or None,
                                 overrides={k: v for k, v in ov.items() if v}, priorities={"cost": 1.0 if cost_w == "yes" else 0.0},
                                 appetite_max_g=appetite or None, dislikes=list(dislikes))
            st.rerun()
    r = TG.compute(ss.profile)
    for c in r.conflicts:
        st.error(c)
    for wmsg in r.warnings:
        st.warning(wmsg)
    st.subheader("Daily targets")
    st.markdown(r.to_markdown().split("\n\n", 1)[1].split("**Conflicts**")[0].split("**Warnings**")[0].split("**Notes**")[0])
    for n in r.notes:
        st.caption(n)
    with st.expander("How energy is calculated"):
        formula_box("REE (ten Haaf 2014) = 11.936 × kg + 587.728 × height m − 8.129 × age + 191.027 × male + 29.279<br>"
                    "Expenditure = REE × 1.5 + (MET − 1) × kg × training h/day (MET 5 strength, 8 endurance, 7 hybrid)<br>"
                    "Target = expenditure × (1 + surplus) or − deficit, by goal; protein = g/kg × body mass")
    with st.expander("Vitamins, minerals, fibre, omega-3, sodium, fats (EFSA / WHO adult values)"):
        st.markdown(r.micro_markdown())
    st.markdown("**Next:** ")
    c1, c2, c3 = st.columns(3)
    c1.page_link(PAGES["meal"], label="Rate & improve a meal", icon=":material/restaurant:")
    c2.page_link(PAGES["plan"], label="Plan my day", icon=":material/calendar_today:")
    c3.page_link(PAGES["export"], label="AI export", icon=":material/smart_toy:")


# ================================================================ pages: improve what you eat
def page_meal():
    st.title("Rate & improve a meal")
    st.markdown("Enter one meal. It is scored against **your** daily needs scaled to the meal's calories, and an "
                "improved meal with the **same calories** is built.")
    tmeal = ftable(quality, price_scn, ("core", "ingredient", "snack", "supplement"), country)
    mt = ML.TEMPLATES
    keep("meal_start")
    ss.setdefault("meal_start", next(iter(mt), "(empty)"))
    pick = st.selectbox("Start from an example meal", ["(empty)"] + list(mt), key="meal_start",
                        format_func=lambda k: mt[k]["label"] if k in mt else k)
    init = {tmeal.name[f]: g for f, g in (mt[pick]["foods"] if pick in mt else {}).items() if f in tmeal.index}
    n2id = {v: k for k, v in tmeal.name.items()}
    ed = persistent_editor("meal", init, list(n2id), UNIT_HINT)
    meal = editor_series(ed, n2id)
    for k, v in (("meal_mode", "tweak"), ("meal_tb", "similar"), ("meal_cheap", False)):
        keep(k)
        ss.setdefault(k, v)
    keep("meal_excl")
    c1, c2, c3 = st.columns(3)
    mmode = c1.radio("Improvement", ["tweak", "best"], key="meal_mode",
                     format_func={"tweak": "Small tweak: keep my foods (50–150 % of each), add ≤ 2",
                                  "best": "Best possible: any foods, ≤ 6"}.get)
    mtb = c2.radio("Among equally good meals prefer", ["similar", "cost"], key="meal_tb",
                   format_func={"similar": "the one most like my meal", "cost": "the cheapest"}.get)
    mcheap = c3.checkbox("Not more expensive than my meal", key="meal_cheap")
    if "meal_excl" not in ss:
        ss.meal_excl = [f for f in prof.dislikes if f in tmeal.index]
    mexcl = c3.multiselect("Never suggest", sorted(tmeal.index), format_func=lambda f: tmeal.name[f], key="meal_excl")
    remember("meal_start", "meal_mode", "meal_tb", "meal_cheap", "meal_excl")
    if not len(meal):
        st.info("Add at least one food with grams.")
        return
    sc0, b0, tot0 = ML.score(tmeal, meal, res)
    r = improve_meal(prof, pkey, country, quality, price_scn, tuple(sorted(meal.items())), mmode, mtb,
                     tot0["cost_eur"] if mcheap else None, tuple(f for f in mexcl if f not in meal.index))
    with st.container(border=True):
        a, b, c, d = st.columns(4)
        a.metric("Your meal", f"{sc0:.0f} / 100", next(v for lim, v in VERDICT if sc0 >= lim), delta_color="off",
                 delta_arrow="off")
        if r.status == "optimal":
            b.metric("Improved meal", f"{r.score:.0f} / 100", f"{r.score - sc0:+.0f}")
            c.metric("Energy", f"{r.totals['kcal']:,.0f} kcal", f"{r.totals['kcal'] - tot0['kcal']:+.0f} vs yours",
                     delta_color="off")
            d.metric("Cost", f"€{r.totals['cost_eur']:.2f}", f"{r.totals['cost_eur'] - tot0['cost_eur']:+.2f} vs yours",
                     delta_color="inverse")
    if r.status != "optimal":
        st.error("No improved meal satisfies these options (try 'Best possible' or untick 'not more expensive').")
    else:
        lcol, rcol = st.columns(2)

        def _tbl(g):
            tt = tmeal.loc[g.index]
            return pd.DataFrame({"food": tt.name, "grams eaten": g, "kcal": tt.kcal * g, "protein g": tt.protein * g,
                                 "€": tt.eur * g}).round(1).reset_index(drop=True)
        lcol.markdown(f"**Your meal**: {tot0['kcal']:,.0f} kcal, {tot0['protein']:.0f} g protein, "
                      f"{tot0['share_of_day']:.0%} of your day")
        lcol.dataframe(_tbl(meal), hide_index=True)
        rcol.markdown(f"**Improved meal**: {r.totals['kcal']:,.0f} kcal, {r.totals['protein']:.0f} g protein")
        rcol.dataframe(_tbl(r.grams), hide_index=True)
    tips = ML.hints(tmeal, meal, b0, exclude=mexcl)
    if tips:
        st.markdown("**What holds your meal back**\n" + "\n".join(f"- {x}" for x in tips))
    else:
        st.success("Your meal already meets its share of every target without exceeding a limit.")
    fig = P.meal_score_fig(b0, r.breakdown) if r.status == "optimal" else None
    if fig is not None:
        st.plotly_chart(fig, width="stretch", theme=None)
        st.caption("Items that both meals fully cover, and limits neither meal exceeds, are not shown.")
    st.markdown("**How the score is calculated**")
    formula_box("share = meal kcal ÷ daily kcal<br>"
                "item score = min(1, amount ÷ (daily minimum × share)) for 20 items: protein, protein quality (most "
                "limiting amino acid), fibre, 17 vitamins & minerals<br>"
                "penalty = min(1, amount ÷ (daily limit × share) − 1) for free sugars, saturated fat, sodium<br>"
                "<b>Meal score = 100 × (mean item score − mean penalty)</b>")
    with st.expander("Item-by-item table and notes"):
        st.markdown("In the spirit of the Nutrient Rich Foods index (Drewnowski 2010), but against *your* targets. The "
                    "improved meal maximizes exactly this score at the same energy (±3 %) with realistic portions, then "
                    "picks the meal most like yours or the cheapest among those within 0.5 points. Verdict bands are a "
                    "judgment call. Omega-3 is not judged per meal (fish is a once-or-twice-a-week food).")
        st.dataframe(b0.drop(columns="key").round(3), hide_index=True)


def page_plan():
    st.title("Plan my day")
    st.markdown("The cheapest (or lightest) day of food that meets **all** your targets: energy, protein and every "
                "essential amino acid, carbohydrate, fat, fibre, vitamins, minerals, omega-3, and the limits. A "
                "nutritional skeleton, not a menu: taste is not modelled.")
    for k in ("pl_real", "pl_obj", "pl_excl", "pl_mass", "pl_snacks", "pl_sg", "pl_pmode", "pl_milp", "pl_nmin", "pl_micros"):
        keep(k)
    for k, v in (("pl_excl", list(prof.dislikes)), ("pl_mass", int(prof.appetite_max_g or 0)), ("pl_real", True),
                 ("pl_obj", "mass" if (prof.priorities or {}).get("cost", 1) == 0 else "cost"), ("pl_snacks", False),
                 ("pl_sg", "full"), ("pl_pmode", "aa"), ("pl_micros", True), ("pl_milp", False), ("pl_nmin", 8)):
        ss.setdefault(k, v)
    c1, c2, c3 = st.columns([1, 1, 2])
    realistic = c1.toggle("Realistic limits", key="pl_real",
                          help="≤ 400 g of any food, legumes + soy ≤ 500 g, no food > 20 % of energy, every nutrient "
                               "from ≥ 2 foods. Off = mathematical minimum (monotonous).")
    objective = c2.selectbox("Optimize for", ["cost", "mass", "mix"], key="pl_obj",
                             format_func={"cost": "lowest cost", "mass": "least food mass", "mix": "balance both"}.get)
    tall = ftable(quality, price_scn, ("core", "ingredient", "snack"), country)
    excl = c3.multiselect("Foods I don't eat", sorted(tall.index), format_func=lambda f: tall.name[f], key="pl_excl")
    with st.expander("Advanced settings"):
        a1, a2, a3, a4 = st.columns(4)
        maxmass = a1.number_input("Max food mass (g/day, 0 = none)", 0, 6000, step=100, key="pl_mass")
        snacks = a1.checkbox("Allow snacks", key="pl_snacks")
        sg = a2.selectbox("Safeguards", ["full", "macros", "none"], key="pl_sg",
                          format_func={"full": "full (recommended)", "macros": "macro bands only",
                                       "none": "none (shows why they exist)"}.get)
        pmode = a3.selectbox("Protein quality constraint", ["aa", "pq", "crude"], key="pl_pmode",
                             format_func={"aa": "per amino acid (diet level)", "pq": "Σ protein × DIAAS (food level)",
                                          "crude": "crude protein only"}.get)
        micros = a4.checkbox("Vitamins & minerals", key="pl_micros")
        milp_ = a4.checkbox("Require variety (MILP)", key="pl_milp")
        nmin = a4.number_input("Minimum number of foods", 3, 20, key="pl_nmin", disabled=not milp_)
    remember("pl_real", "pl_obj", "pl_excl", "pl_mass", "pl_snacks", "pl_sg", "pl_pmode", "pl_milp", "pl_nmin", "pl_micros")
    roles_ = ("core", "ingredient") + (("snack",) if snacks else ())
    kw = (("realistic", realistic), ("objective", objective), ("max_mass", maxmass or None), ("safeguards", sg),
          ("protein_mode", pmode), ("milp", milp_), ("min_foods", int(nmin)), ("use_micros", micros))
    sol, spec = solve(prof, pkey, quality, price_scn, country, roles_, tuple(excl), kw)
    t = ftable(quality, price_scn, roles_, country, tuple(excl))
    if sol.status != "optimal":
        st.error("No diet can meet all targets with these settings. Smallest changes that would make it possible:")
        st.dataframe(sol.conflicts.round(2), hide_index=True)
        return
    with st.container(border=True):
        a, b, c, d = st.columns(4)
        a.metric("Cost per day", f"€{sol.cost_eur:.2f}")
        b.metric("Food eaten per day", f"{sol.mass_g:,.0f} g")
        c.metric("Different foods", len(sol.foods))
        aa = O.aa_adequacy(t, sol.foods, spec.protein)
        d.metric("Lowest amino-acid adequacy", f"{aa.min():.2f} ({aa.idxmin()})")
    tab1, tab2, tab3, tab4 = st.tabs(["Foods", "Meals", "Nutrients", "Why these foods?"])
    with tab1:
        show = sol.foods.rename(columns={"name": "food", "g_eaten": "g eaten", "g_bought": "g bought (gross)",
                                         "cost_eur": "€", "kcal_total": "kcal", "protein_total": "protein g",
                                         "carb_total": "carb g", "fat_total": "fat g", "free_sugars_total": "free sugars g",
                                         "fibre_total": "fibre g", "energy_share": "energy share"})
        st.dataframe(show.reset_index(drop=True), width="stretch", hide_index=True)
        tot = sol.totals.copy()
        tot["target"] = tot.target.astype(str)
        st.dataframe(tot.round(1), hide_index=True)
        st.download_button("Download this day (CSV)", sol.foods.to_csv(), "my_day.csv", "text/csv")
    with tab2:
        sp = ML.split_day(t, sol.foods.g_eaten, prof.mass_kg)
        if sp is None:
            st.info("This day cannot be split under the per-meal limits (config/meals.yaml).")
        else:
            st.dataframe(sp.reset_index(drop=True), hide_index=True)
            st.dataframe(ML.split_summary(t, sp).T, width="stretch")
            st.caption("≥ 4 meals, each ≥ 0.4 g protein per kg body mass and 20–35 % of energy, with as few food pieces "
                       "as possible. Arithmetic grouping, not cuisine: regroup foods into dishes you like.")
    with tab3:
        st.dataframe(O.nutrient_status(t, sol.foods.g_eaten, res, exclude=excl).round(2), hide_index=True)
    with tab4:
        formula_box("minimize Σ cost_i × x_i (x_i = grams eaten of food i)<br>subject to: energy within ±2 %; "
                    "protein ≥ target; Σ digestible amino acid_a × x ≥ FAO pattern_a × protein target (each of 9); "
                    "carbohydrate, fat bands; free sugars, saturated & trans fat, sodium ≤ limits; "
                    "vitamins & minerals ≥ minimum (and ≤ upper limit); per-food caps"
                    + ("; realistic: ≤ 400 g/food, legumes ≤ 500 g, ≤ 20 % energy/food, no food > 60 % of any nutrient"
                       if realistic else ""))
        if len(sol.binding):
            st.markdown("**What drives the cost**: the targets that bind, and how much the objective would change if "
                        "each were one unit stricter (shadow prices):")
            st.dataframe(sol.binding[~sol.binding.constraint.str.startswith(O.INTERNAL_ROWS)].round(4), hide_index=True)
        if len(sol.reduced_costs):
            near = sol.reduced_costs[~sol.reduced_costs.used].head(8)
            st.markdown("**Foods that almost made it**: how much cheaper per kg eaten they would have to be:")
            st.dataframe(near.assign(eur_per_kg_cheaper=near.reduced_cost_per_g * 1000)[["name", "eur_per_kg_cheaper"]]
                         .round(2), hide_index=True)
        if st.checkbox("Show cost vs food-mass trade-off (a few seconds)"):
            fr = O.cost_mass_front(t, replace(spec, milp=False), 8)
            if len(fr):
                st.plotly_chart(P.front_fig(fr), width="stretch", theme=None)


def page_fix():
    st.title("Fix my usual day")
    st.markdown("Enter what you usually eat in a day. The tool finds the **smallest change** that makes it meet all your "
                "targets: changing a large item a little counts less than adding a new food (Maillot 2010).")
    tfix = ftable(quality, price_scn, ("core", "ingredient", "snack"), country)
    tmpl = yaml.safe_load(open(ROOT / "config/diet_templates.yaml"))
    keep("fix_start")
    ss.setdefault("fix_start", "(empty)")
    start = st.selectbox("Start from", ["(empty)"] + list(tmpl), key="fix_start",
                         format_func=lambda k: tmpl[k]["label"] if k in tmpl else k)
    remember("fix_start")
    init = {tfix.name[f]: g for f, g in (tmpl[start]["foods"] if start in tmpl else {}).items() if f in tfix.index}
    n2id = {v: k for k, v in tfix.name.items()}
    ed = persistent_editor("usual", init, list(n2id), UNIT_HINT)
    usual = editor_series(ed, n2id)
    keep_cost = st.checkbox("Not more expensive than my usual day", value=False)
    if not len(usual):
        st.info("Add at least one food with grams.")
        return
    short = O.shortfall_text(O.nutrient_status(tfix, usual, res, exclude=prof.dislikes))
    if short:
        st.markdown("**Your usual day misses:**\n" + "\n".join(f"- {x}" for x in short))
    fspec, _ = O.spec_from_profile(prof)
    tf = tfix.drop(index=[f for f in prof.dislikes if f in tfix.index and f not in usual.index])
    now_cost = float((tf.eur.reindex(usual.index) * usual).sum())
    fsol = O.closest_diet(tf, fspec, usual, max_cost=now_cost if keep_cost else None)
    a, b = st.columns(2)
    a.metric("Usual day cost", f"€{now_cost:.2f}/day")
    if fsol.status != "optimal":
        st.error("No adjustment meets every target. Conflicting targets:")
        st.dataframe(fsol.conflicts.round(2), hide_index=True)
        return
    b.metric("Adjusted day cost", f"€{fsol.cost_eur:.2f}/day", f"{fsol.cost_eur - now_cost:+.2f}")
    ch = fsol.changes.rename(columns={"name": "food", "usual_g": "usual g", "new_g": "new g", "change_g": "change g"})
    st.markdown("**Changes needed**" if len(ch) else "**Your usual day already meets every target.**")
    if len(ch):
        st.dataframe(ch.round(0).reset_index(drop=True), hide_index=True)
    formula_box("minimize Σ w_i × |new_i − usual_i| with w_i = 1 ÷ max(usual_i, 50 g), subject to every daily target")
    st.download_button("Download adjusted day (CSV)", fsol.foods.to_csv(), "adjusted_day.csv", "text/csv")


# ================================================================ pages: explore the data
SCATTER_PRESETS = {
    "Density: useful protein vs calories (per 100 g eaten)": ("useful_protein_100g_eaten", "kcal_100g_eaten", False, False),
    "Economy: useful protein/€ vs calories/€": ("useful_protein_per_eur", "kcal_per_eur", True, True),
    "Endurance: useful protein/€ vs carbs/€": ("useful_protein_per_eur", "carb_per_eur", True, True),
    "Volume: grams eaten vs € for 1000 kcal": ("g_eaten_per_1000kcal", "eur_per_1000kcal", True, True),
    "Cutting view: useful protein per 1000 kcal vs calories/€": ("useful_protein_per_1000kcal", "kcal_per_eur", False, True),
}
EX_KEYS = ["ex_chart", "ex_defs", "ex_x", "ex_y", "ex_xl", "ex_yl", "ex_logx", "ex_logy", "ex_hx", "ex_hy", "ex_c", "ex_s",
           "ex_f", "ex_front", "ex_n", "ex_asc"]
EX_DEFAULT = {"ex_chart": "Scatter", "ex_defs": "", "ex_x": "cost", "ex_y": "protein / kcal * 100",
              "ex_xl": "Cost of 100 g eaten (€)", "ex_yl": "Protein per 100 kcal (g)", "ex_logx": True, "ex_logy": False,
              "ex_hx": "lower", "ex_hy": "higher", "ex_c": "", "ex_s": "", "ex_f": "", "ex_front": True, "ex_n": 25,
              "ex_asc": False}
EX_EXAMPLES = {
    "Protein per 100 kcal vs cost per 100 g": {},
    "Digestible leucine per 100 kcal vs cost": {
        "ex_y": "dleu / kcal * 100", "ex_yl": "Digestible leucine per 100 kcal (g)", "ex_f": "protein > 2"},
    "Lysine vs methionine + cysteine (per g protein)": {
        "ex_x": "lys / protein * 1000", "ex_y": "(met + cys) / protein * 1000", "ex_xl": "Lysine (mg/g protein)",
        "ex_yl": "Methionine + cysteine (mg/g protein)", "ex_logx": False, "ex_hx": "higher", "ex_f": "protein > 3",
        "ex_front": False},
    "Fibre per 100 kcal vs cost (colour: soluble share)": {
        "ex_x": "cost", "ex_y": "fibre / kcal * 100", "ex_xl": "Cost of 100 g eaten (€)", "ex_yl": "Fibre per 100 kcal (g)",
        "ex_c": "fibre_sol_g / fibre * 100", "ex_f": "fibre > 0"},
    "Fat quality: unsaturated ÷ saturated vs fat share of energy": {
        "ex_x": "fat * 9 / kcal * 100", "ex_y": "(mufa_g + pufa_g) / sat_fat", "ex_xl": "Energy from fat (%)",
        "ex_yl": "Unsaturated ÷ saturated fat", "ex_logx": False, "ex_logy": True, "ex_hx": "lower", "ex_hy": "higher",
        "ex_f": "fat > 1"},
    "Omega-6 ÷ omega-3 ratio (ranking, lowest first)": {
        "ex_chart": "Ranking bar", "ex_y": "n6_g / n3_g", "ex_yl": "Omega-6 ÷ omega-3", "ex_asc": True,
        "ex_f": "fat > 2 and n3_g > 0"},
    "Vitamin C per € (ranking)": {
        "ex_chart": "Ranking bar", "ex_y": "vitamin_c_mg / cost / 10", "ex_yl": "Vitamin C per € of eaten food (mg/€)",
        "ex_f": "vitamin_c_mg > 0"},
    "My own score: useful protein and fibre per € (defined variables)": {
        "ex_defs": "up_per_eur = useful_protein / cost        # g per € eaten\nfibre_per_eur = fibre / cost\n"
                   "my_score = pct(up_per_eur) + pct(fibre_per_eur)",
        "ex_chart": "Ranking bar", "ex_y": "my_score", "ex_yl": "My score (sum of percentile ranks)"},
}


def _ex_apply(spec):
    for k in EX_KEYS:
        ss[k] = spec.get(k, EX_DEFAULT[k])


def _ex_example():
    _ex_apply({**EX_DEFAULT, **EX_EXAMPLES[ss.ex_example]})


def page_explorer():
    st.title("Explorer")
    keep("ex_mode")
    ss.setdefault("ex_mode", "Custom chart (formulas)")
    mode = st.segmented_control("Mode", ["Custom chart (formulas)", "Preset views"], key="ex_mode")
    remember("ex_mode")
    if mode == "Preset views":
        c1, c2 = st.columns([2, 1])
        choice = c1.selectbox("View", ["(pick two metrics)"] + list(SCATTER_PRESETS), index=1)
        metric_keys = [m for m in M.METRICS if m in view.columns]
        if choice == "(pick two metrics)":
            a, b, c, d = st.columns(4)
            x = a.selectbox("x axis", metric_keys, index=metric_keys.index("useful_protein_per_eur"))
            y = b.selectbox("y axis", metric_keys, index=metric_keys.index("kcal_per_eur"))
            logx, logy = c.checkbox("log x"), d.checkbox("log y")
        else:
            x, y, logx, logy = SCATTER_PRESETS[choice]
        show_front = c2.checkbox("Show Pareto front", value=True)
        plot_df = view[(view[x] > 0) | (not logx)] if logx else view
        plot_df = plot_df[(plot_df[y] > 0)] if logy else plot_df
        st.plotly_chart(P.scatter_fig(plot_df, x, y, logx, logy, front=show_front), width="stretch", theme=None)
        formula_box(f"x = {M.METRICS[x][0]} = {M.FORMULAS.get(x, x)}<br>y = {M.METRICS[y][0]} = {M.FORMULAS.get(y, y)}")
        hidden = len(view) - len(plot_df)
        if hidden:
            st.caption(f"{hidden} foods with a zero value are not shown on log axes.")
        return
    for k in EX_KEYS:
        keep(k)
        ss.setdefault(k, EX_DEFAULT[k])
    st.markdown("Plot **anything you can calculate** from the data: nutrients, amino acids, fatty acids, fibre types, "
                "prices. Formulas use the variables listed below, `+ − * / **`, comparisons, `and/or/not` and a few "
                "functions; e.g. `dleu / kcal * 100` = digestible leucine per 100 kcal. Foods and prices follow the "
                "sidebar and the country.")
    c1, c2 = st.columns([2, 1])
    c1.selectbox("Start from an example", list(EX_EXAMPLES), key="ex_example", on_change=_ex_example, index=None,
                 placeholder="choose an example…")
    c2.radio("Chart", ["Scatter", "Ranking bar"], horizontal=True, key="ex_chart")
    st.text_area("My variables (optional, one per line: `name = formula`; later lines may use earlier ones)",
                 key="ex_defs", height=90, placeholder="protein_per_100kcal = protein / kcal * 100")
    scatter = ss.ex_chart == "Scatter"
    a, b = st.columns(2)
    if scatter:
        a.text_input("x axis formula", key="ex_x")
        a.text_input("x axis title (optional)", key="ex_xl")
        a.checkbox("log x", key="ex_logx")
        a.radio("x is better when", ["higher", "lower"], horizontal=True, key="ex_hx")
    b.text_input("y axis formula" if scatter else "Formula to rank by", key="ex_y")
    b.text_input("y axis title (optional)" if scatter else "Title (optional)", key="ex_yl")
    if scatter:
        b.checkbox("log y", key="ex_logy")
        b.radio("y is better when", ["higher", "lower"], horizontal=True, key="ex_hy")
    else:
        b.slider("Foods shown", 5, 60, key="ex_n")
        b.checkbox("Lowest first", key="ex_asc")
    with st.expander("Filter, colour, size" if scatter else "Filter"):
        st.text_input("Filter: only foods where this is true (empty = all)", key="ex_f",
                      placeholder='protein > 5 and group != "Supplements"')
        if scatter:
            st.text_input("Colour by formula (empty = food group)", key="ex_c", placeholder="pct(kcal_per_eur)")
            st.text_input("Marker size by formula (empty = equal size)", key="ex_s", placeholder="fibre")
            st.checkbox("Pareto front (foods no other food beats on both axes)", key="ex_front")
    remember(*EX_KEYS)
    user_vars = {}
    try:
        env, user_vars = F.environment(view, ss.ex_defs)
        keep_ = pd.Series(True, index=view.index)
        if ss.ex_f.strip():
            keep_ = F._bool(F.evaluate(ss.ex_f, env))
            if not isinstance(keep_, pd.Series):
                keep_ = pd.Series(bool(keep_), index=view.index)
        sub = view[keep_]
        ev = lambda f: F.evaluate(f, env)[keep_] if f.strip() else None  # noqa: E731
        yv = ev(ss.ex_y)
        ylab = ss.ex_yl.strip() or ss.ex_y
        if scatter:
            xv, cv, sv = ev(ss.ex_x), ev(ss.ex_c), ev(ss.ex_s)
            xlab = ss.ex_xl.strip() or ss.ex_x
            fig, hidden = P.custom_scatter_fig(sub, xv, yv, xlab, ylab, ss.ex_logx, ss.ex_logy, color=cv,
                                               color_label=ss.ex_c, size=sv, size_label=ss.ex_s,
                                               front=(ss.ex_hx == "higher", ss.ex_hy == "higher") if ss.ex_front else None)
            st.plotly_chart(fig, width="stretch", theme=None)
            formula_box(f"x = {ss.ex_x}<br>y = {ss.ex_y}" + (f"<br>colour = {ss.ex_c}" if ss.ex_c else "")
                        + (f"<br>size = {ss.ex_s}" if ss.ex_s else "") + (f"<br>filter: {ss.ex_f}" if ss.ex_f else ""))
            if hidden:
                st.caption(f"{hidden} foods not shown: missing value"
                           + (" or ≤ 0 on a log axis." if ss.ex_logx or ss.ex_logy else "."))
            table = pd.DataFrame({"food": sub.name_en, "group": sub.group, xlab: xv, ylab: yv})
        else:
            st.plotly_chart(P.custom_bar_fig(sub, yv, ylab, ss.ex_n, ss.ex_asc), width="stretch", theme=None)
            formula_box(f"value = {ss.ex_y}" + (f"<br>filter: {ss.ex_f}" if ss.ex_f else ""))
            table = pd.DataFrame({"food": sub.name_en, "group": sub.group, ylab: yv}).sort_values(ylab, ascending=ss.ex_asc)
        with st.expander(f"Data ({len(table)} foods)"):
            st.dataframe(table.round(4), hide_index=True)
            st.download_button("Download data (CSV)", table.to_csv(index=False), "custom_chart.csv", "text/csv")
    except F.FormulaError as e:
        st.error(f"Formula problem: {e}")
    d1, d2 = st.columns(2)
    d1.download_button("Save this chart (JSON)", json.dumps({k: ss[k] for k in EX_KEYS}, indent=2), "chart.json",
                       "application/json", help="Load it again below, or send it to a friend")
    up = d2.file_uploader("Load a saved chart", type="json", key="ex_upload")
    if up is not None and ss.get("ex_loaded") != up.file_id:
        ss.ex_loaded = up.file_id
        try:
            _ex_apply({**EX_DEFAULT, **{k: v for k, v in json.load(up).items() if k in EX_KEYS}})
            remember(*EX_KEYS)
            st.rerun()
        except (ValueError, AttributeError):
            st.error("Not a chart file saved by this app.")
    with st.expander("Variables you can use"):
        st.caption("Short names (protein, kcal, fibre, leu, dleu, cost, price, …) are per 100 g as eaten. Every column of "
                   "the food table is available too; search with the table's 🔍.")
        st.dataframe(F.reference(view), hide_index=True, height=360)
        if user_vars:
            st.markdown("**Your variables:** " + ", ".join(f"`{k} = {v}`" for k, v in user_vars.items()))
    with st.expander("Functions"):
        st.markdown("\n".join(f"- `{k}`: {v[1]}" for k, v in F.FUNCS.items()))


def page_rankings():
    st.title("Rankings")
    keep("rk_mode")
    ss.setdefault("rk_mode", "Personal (from my profile)")
    mode = st.segmented_control("Ranking", ["Personal (from my profile)", "Custom weighting"], key="rk_mode")
    remember("rk_mode")
    if mode != "Custom weighting":
        r, w, v_up = personal_rank(prof, pkey, quality, price_scn, country, tuple(groups))
        st.markdown(f"Everyday foods ranked for **{prof.name}** ({GOALS[prof.goal]['label']}"
                    f"{'' if (prof.priorities or {}).get('cost', 1) else ', price ignored'}). Change the goal or "
                    "'Does price matter?' in **My profile** and the ranking changes.")
        formula_box(PS.formula_text(w, v_up).replace(" × pct", "<br>&nbsp;&nbsp;× pct"))
        with st.expander("What the components mean"):
            st.markdown("\n".join(f"- **{lab}** ({unit}): {f}" for k, (lab, unit, _, f) in PS.COMPONENTS.items()) +
                        "\n- **pct** = percentile rank among the shown foods (1 = best on that component).\n"
                        "- Weights by goal are in `config/target_rules.yaml` (judgment calls); price weight is 0 when "
                        "price does not matter.\n- **Optimizer value %** = what the food's nutrients are worth in *your* "
                        "optimal day (at its shadow prices) ÷ its price. 100 % = worth exactly its price (it is in the "
                        "optimal day); < 100 % = you pay for more than the nutrients you need; > 100 % = held back only "
                        "by a portion cap.")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(P.custom_bar_fig(r.rename(columns={"name": "name_en"}), r.score,
                                             "Personal score (0–100, higher = better fit for you)", n=30), width="stretch", theme=None)
        with c2:
            cols = ["rank", "name", "group", "score", "N", "P", "K", "C", "V"] + \
                [c for c in ("optimizer value %", "in optimal diet (g)") if c in r]
            st.dataframe(r[cols].round(2), hide_index=True, height=650,
                         column_config={k: st.column_config.NumberColumn(help=f"{PS.COMPONENTS[k][0]} ({PS.COMPONENTS[k][1]})")
                                        for k in "NPKCV"})
        st.download_button("Download ranking (CSV)", r.to_csv(), "personal_ranking.csv", "text/csv")
        return
    st.markdown("Build your own score from food metrics: a weighted geometric mean of normalized metrics.")
    c1, c2 = st.columns([1, 2])
    preset = c1.selectbox("Start from preset", ["(custom)"] + list(M.PRESETS), index=1)
    norm = c1.radio("Normalization", list(M.NORMALIZATIONS), index=1, help=" · ".join(
        f"{k}: {v}" for k, v in M.NORMALIZATIONS.items()))
    defaults = M.PRESETS.get(preset, {})
    weightable = [m for m, (_, _, hib) in M.METRICS.items() if hib is not None and m != "diaas"]
    weights = {}
    with c2.container(border=True):
        for m in weightable:
            weights[m] = st.slider(f"{M.METRICS[m][0]} ({'↑' if M.METRICS[m][2] else '↓'} better)", 0.0, 5.0,
                                   float(defaults.get(m, 0)), 0.5, key=f"w_{m}_{preset}")
    w = {k: v for k, v in weights.items() if v > 0}
    if not w:
        st.info("Set at least one weight.")
        return
    v = view.assign(score=M.composite(view, w, norm))
    tot = sum(w.values())
    formula_box("score = " + " × ".join(f"norm({M.METRICS[k][0]})^{x / tot:.2f}" for k, x in w.items())
                + f"<br>norm = {norm}: {M.NORMALIZATIONS[norm]}<br>"
                + "<br>".join(f"{M.METRICS[k][0]} = {M.FORMULAS.get(k, k)}" for k in w))
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(P.ranking_bar_fig(v, "score", n=min(30, len(v))), width="stretch", theme=None)
    with c2:
        tbl = v.sort_values("score", ascending=False)[["name_en", "group", "score"] + list(w)].round(2).reset_index(drop=True)
        tbl.index += 1
        st.dataframe(tbl, height=650)
    st.download_button("Download ranking (CSV)", v.sort_values("score", ascending=False).to_csv(index=False),
                       "ranking.csv", "text/csv")


def page_food():
    st.title("Food details")
    names = df.sort_values("name_en").set_index("food_id").name_en
    fid = st.selectbox("Food", names.index, format_func=lambda i: f"{names[i]} ({i})")
    r = df.set_index("food_id").loc[fid]
    a, b, c, d = st.columns(4)
    a.metric("kcal / 100 g eaten", f"{r.kcal_100g_eaten:.0f}" if pd.notna(r.kcal_100g_eaten) else "–")
    b.metric("Useful protein / 100 g eaten", f"{r.useful_protein_100g_eaten:.1f} g" if pd.notna(r.useful_protein_100g_eaten) else "–")
    c.metric("DIAAS", f"{r.diaas:.0f}" if pd.notna(r.diaas) else "–")
    d.metric("Price", f"€{r.eur_per_kg_used:.2f}/kg" if pd.notna(r.eur_per_kg_used) else "no price")
    st.markdown(f"""
**{r.name_en}** ({r.name_lv}) · group {r.group} · role {r.role}

- Composition: `{r.comp_source}`: {r.comp_description} (grade **{r.comp_grade}**); amino acids from `{r.aa_source}`
- Cooking: eaten mass = {r.yield_eaten_per_purchased:.2f} × bought mass; edible portion {r.edible_portion:.2f}
- Protein quality: DIAAS **{r.diaas:.0f}** (adult), {r.diaas_child:.0f} (young-child pattern), limiting amino acid
  **{r.limiting_aa}**, digestibility grade **{r.digest_grade}**
- Price ({CTRY[country]}): €{r.eur_per_kg_used:.2f}/kg edible as bought; source {r.price_source}, grade **{r.price_grade}**
- Flags: {r.flags if isinstance(r.flags, str) and r.flags else "none"}
""")
    formula_box("per 100 g eaten = per 100 g bought ÷ (eaten mass ÷ bought mass) × cooking retention (vitamins/minerals)"
                "<br>useful protein = protein × min(DIAAS, 100) / 100")
    rows = [("Energy", "kcal", "kcal"), ("Protein", "protein", "g"), ("Carbohydrate", "carb", "g"), ("  of which starch", "starch_g", "g"),
            ("  of which sugars", "sugars", "g"), ("  free sugars", "free_sugars", "g"), ("Fibre", "fibre", "g"),
            ("  soluble", "fibre_sol_g", "g"), ("  insoluble", "fibre_insol_g", "g"), ("Fat", "fat", "g"),
            ("  saturated", "sat_fat", "g"), ("  monounsaturated", "mufa_g", "g"), ("  polyunsaturated", "pufa_g", "g"),
            ("  trans", "trans_g", "g"), ("  omega-6", "n6_g", "g"), ("  omega-3", "n3_g", "g"), ("Sodium", "sodium_mg", "mg")]
    comp = pd.DataFrame([{"": n, "per 100 g bought": r.get(f"{k}_100g_purchased"), "per 100 g eaten": r.get(f"{k}_100g_eaten"),
                          "unit": u} for n, k, u in rows]).round(2)
    aa = pd.DataFrame({"amino acid": F.AA_NAMES.values(),
                       "mg per g protein": [r[f"{a}_mg_per_g_protein"] for a in F.AA_NAMES],
                       "g per 100 g eaten": [r.protein_100g_eaten * r[f"{a}_mg_per_g_protein"] / 1000 for a in F.AA_NAMES],
                       "digestibility": [r.get(f"dig_{a}") for a in F.AA_NAMES]}).round(3)
    c1, c2 = st.columns(2)
    c1.dataframe(comp, hide_index=True, height=640)
    c2.dataframe(aa, hide_index=True)
    st.caption("Blank = not analysed in the source database. Fibre types are measured for few foods (Frida).")


def page_export():
    st.title("AI export")
    st.markdown("Files for an AI recipe / meal-plan assistant, for **your profile** and the selected country: foods "
                "ranked with the personal score and full nutrition (`foods_ranked.csv`), the minimum-cost day "
                "(`optimal_diet.csv`), a realistic day split into ≥ 4 meals (`realistic_diet.csv`) and a brief with "
                "every rule and a ready-to-paste prompt (`brief.md`).")
    b = bundle(prof, pkey, quality, price_scn, country)
    ranked, brief, diet, real = b["foods"], b["brief"], b["diet"], b["realistic"]
    csv_text = ranked.to_csv(index=False)
    diet_csv = diet.to_csv(index=False) if diet is not None else None
    real_csv = real.to_csv(index=False) if real is not None else None
    stem = f"{ss.profile_key}_{country}"
    with st.container(border=True):
        e1, e2, e3, e4, e5 = st.columns(5)
        e1.download_button("foods_ranked.csv", csv_text, f"{stem}_foods_ranked.csv", "text/csv")
        if diet_csv:
            e2.download_button("optimal_diet.csv", diet_csv, f"{stem}_optimal_diet.csv", "text/csv")
        if real_csv:
            e3.download_button("realistic_diet.csv", real_csv, f"{stem}_realistic_diet.csv", "text/csv")
        e4.download_button("brief.md", brief, f"{stem}_brief.md", "text/markdown")
        e5.download_button("All (ZIP)", X.zip_bytes(csv_text, brief, diet_csv, real_csv), f"{stem}_ai_export.zip",
                           "application/zip", type="primary")
    with st.expander("Preview brief.md"):
        st.markdown(brief)


def page_methods():
    st.title("How it works")
    st.markdown("Every number in this app comes from a formula and a source. The main ones:")
    sections = {
        "Food data": "Composition: Frida 5.5 (DTU, Denmark), USDA SR Legacy where Frida lacks a food. Values **as "
                     "eaten** = as bought ÷ (cooked mass ÷ raw mass); vitamins and minerals also × cooking retention "
                     "(USDA raw↔cooked pairs). Cooking does not destroy fibre: across 20 raw↔cooked pairs the median "
                     "retention is 1.06; per 100 g it looks lower only because cooked food holds water.",
        "Protein quality": "DIAAS = min over essential amino acids (digestible amino acid per g protein ÷ FAO 2013 "
                           "reference) × 100; useful protein = protein × min(DIAAS, 100)/100. Diets are checked per "
                           "amino acid over the whole day, so complementary foods (grains + legumes) count.",
        "Targets": "Energy (ten Haaf 2014 resting energy × activity), protein by goal (Morton 2018, Helms 2014, "
                   "Thomas 2016), carbohydrate by training load (Thomas 2016), fat 20–35 % of energy, free sugars < "
                   "10 %, vitamins and minerals EFSA 2017 with upper limits (EFSA 2025), fibre ≥ 25 g (EFSA; WHO 2023), "
                   "saturated < 10 % and trans fat < 1 % of energy (WHO 2023), omega-3 (EFSA 2010).",
        "Meal score": "100 × (mean of 20 adequacy items scaled to the meal's share of your day − mean of 3 limit "
                      "penalties).",
        "Personal ranking": "Weighted geometric mean of percentile ranks of: nutrient score of 100 kcal, useful protein "
                            "per 100 kcal, carbohydrate share, cost of 100 kcal, food mass per 100 kcal (direction by goal).",
        "Day plan": "Linear programming (HiGHS): minimize cost (or mass) subject to every target; shadow prices tell "
                    "which targets drive the cost.",
        "Prices": "Latvia: official CSP monthly means and Cenu Depo shop prices (personal use only). Other countries: "
                  "Latvian price × Eurostat food price level index of the food's category ÷ Latvia's (2024).",
        "What we cannot know": "Only nutrients with reference values and data are modelled. Compounds without agreed "
                               "requirements (e.g. ergothioneine in mushrooms, polyphenols) are not; eating a variety of "
                               "foods is the hedge, which is why the realistic plan takes every nutrient from ≥ 2 foods.",
    }
    for k, v in sections.items():
        with st.container(border=True):
            st.markdown(f"**{k}**  \n{v}")
    st.caption("Details, sources and decisions: reports/technical_report.md and literature/SOURCES.md in the project. "
               "Not medical advice.")


START = os.environ.get("NUTRITION_START_PAGE", "profile")   # test hook (tests/test_app.py)
PAGE_DEFS = {  # key: (function, title, icon)
    "profile": (page_profile, "My profile", ":material/person:"),
    "meal": (page_meal, "Rate & improve a meal", ":material/restaurant:"),
    "plan": (page_plan, "Plan my day", ":material/calendar_today:"),
    "fix": (page_fix, "Fix my usual day", ":material/build:"),
    "explorer": (page_explorer, "Explorer", ":material/scatter_plot:"),
    "rankings": (page_rankings, "Rankings", ":material/leaderboard:"),
    "food": (page_food, "Food details", ":material/nutrition:"),
    "export": (page_export, "AI export", ":material/smart_toy:"),
    "methods": (page_methods, "How it works", ":material/functions:"),
}
PAGES = {k: st.Page(f, title=t, icon=i, url_path=k, default=k == START) for k, (f, t, i) in PAGE_DEFS.items()}
nav = st.navigation({
    "Start": [PAGES["profile"]],
    "Improve what you eat": [PAGES["meal"], PAGES["plan"], PAGES["fix"]],
    "Explore the data": [PAGES["explorer"], PAGES["rankings"], PAGES["food"], PAGES["export"], PAGES["methods"]],
}, position="top")
ss._entered = ss.get("_page") != nav.url_path
ss._page = nav.url_path
nav.run()
