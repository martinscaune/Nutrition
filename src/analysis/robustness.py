"""v1.x robustness (PLAN D.1–D.6) → reports/v1x_robustness.md + figures/v1x/*.png

D.1 prices · D.2 protein-quality pattern · D.3 ranking weights · D.4 safeguards/targets ·
D.5 Monte Carlo over composition, digestibility and prices · D.6 composition database (Frida vs USDA).
Main subject: the owner profile (minimum-cost diet); D.1 also for every profile.
"""
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src import metrics as M  # noqa: E402
from src import optimizer as O  # noqa: E402
from src import plots as P  # noqa: E402
from src.analysis.explore import md_table  # noqa: E402
from src.data import composition as C  # noqa: E402
from src.targets import load_profile  # noqa: E402

OUT = ROOT / "reports/v1x_robustness.md"
FIG = ROOT / "figures/v1x"
PROFILES = {p.stem: p for p in sorted((ROOT / "config/profiles").glob("*.yaml"))}
CV_COMP = {"A": 0.05, "B": 0.10, "C": 0.20}   # assumed relative uncertainty of composition by grade [U]
CV_DIG = {"A": 0.03, "B": 0.06, "C": 0.12}    # assumed relative uncertainty of digestibility by grade [U]
N_MC = 300


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


def owner():
    s, _ = O.spec_from_profile(load_profile(PROFILES["owner"]))
    return s


def scale_own_prices(t, factor):
    """Multiply prices of foods priced from Cenu Depo (own observations) by factor."""
    foods = pd.read_csv(ROOT / "data/foods/foods.csv").set_index("food_id").price_source
    t = t.copy()
    own = foods.reindex(t.index) == "own"
    t.loc[own, "eur"] *= factor
    return t


# ---------------------------------------------------------------- D.1 prices
def d1(L):
    rows = []
    for k, path in PROFILES.items():
        s, _ = O.spec_from_profile(load_profile(path))
        base = O.solve(O.food_table(), s)
        for label, t in [("central", O.food_table()), ("low band", O.food_table(price_scenario="low (band lower edge)")),
                         ("high band", O.food_table(price_scenario="high (band upper edge)")),
                         ("Cenu Depo prices +10 %", scale_own_prices(O.food_table(), 1.10))]:
            sol = O.solve(t, s)
            rows.append({"profile": load_profile(path).name.split("(")[0].split(",")[0].strip(), "prices": label,
                         "cost €/day": sol.cost_eur, "mass g": sol.mass_g,
                         "same foods (Jaccard)": jaccard(base.foods.index, sol.foods.index)})
    L += ["## D.1 Price scenarios (each profile, its own objective)\n\n", md_table(pd.DataFrame(rows), 2),
          "\nBand edges = CSP 12-month min/max or Cenu Depo P25/P75. '+10 %' corrects Cenu Depo prices toward the CSP "
          "level (cross-check showed Cenu Depo ≈ 10 % lower). Per-retailer scenarios need per-retailer CSP data (not "
          "public).\n\n"]


# ---------------------------------------------------------------- D.2 protein-quality pattern
def d2(L):
    s = owner()
    base = O.solve(O.food_table(), s)
    rows = []
    for q in ["diaas", "diaas_child"]:
        # pattern change matters for the AA constraints: use the child pattern by scaling requirements
        from src.build_master import PATTERN, PATTERN_CHILD
        if q == "diaas_child":
            old = dict(PATTERN)
            PATTERN.update(PATTERN_CHILD)
            sol = O.solve(O.food_table(quality=q), s)
            PATTERN.update(old)
        else:
            sol = base
        rows.append({"reference pattern": "adult (3+ y), default" if q == "diaas" else "young child 0.5–3 y (stricter)",
                     "cost €/day": sol.cost_eur, "protein g": sol.totals.set_index("nutrient").diet.protein,
                     "same foods (Jaccard)": jaccard(base.foods.index, sol.foods.index),
                     "foods": ", ".join(sol.foods.name.head(6))})
    L += ["## D.2 Amino-acid reference pattern (owner)\n\n", md_table(pd.DataFrame(rows), 2), "\n"]


# ---------------------------------------------------------------- D.3 ranking weights (tornado)
def d3(L):
    df = M.load()
    core = df[(df.role == "core") & df.eur_per_kg_edible.notna()].set_index("food_id")
    preset = "Hybrid: bulk + endurance fuel"
    w0 = M.PRESETS[preset]
    base = M.composite(core, w0)
    rows = []
    for k in w0:
        for f, lab in [(0, "dropped"), (3, "×3")]:
            w = dict(w0)
            w[k] = w0[k] * f
            if not any(v > 0 for v in w.values()):
                continue
            r = M.compare_rankings(base, M.composite(core, w), 10)
            rows.append({"metric": M.METRICS[k][0], "change": lab, "spearman": r["spearman"], "top10_overlap": r["top10_overlap"]})
    d = pd.DataFrame(rows)
    L += [f"## D.3 Sensitivity of the composite ranking to each weight ('{preset}')\n\n", md_table(d, 2), "\n"]
    piv = d.pivot(index="metric", columns="change", values="top10_overlap").sort_values("dropped")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    fig.subplots_adjust(left=0.33, right=0.95, top=0.82, bottom=0.17)
    y = np.arange(len(piv))
    ax.barh(y - 0.18, 1 - piv["dropped"], height=0.34, color="#2a78d6", edgecolor="black", lw=0.6, label="weight dropped")
    ax.barh(y + 0.18, 1 - piv["×3"], height=0.34, color="#eb6834", edgecolor="black", lw=0.6, label="weight ×3")
    ax.set_yticks(y, piv.index)
    ax.set_xlim(0, 1)
    P._style(ax, "Which weight moves the ranking most?",
             "Share of the top 10 that changes when one weight is dropped or tripled (owner preset).",
             "Share of top-10 foods replaced", "")
    ax.legend(loc="lower right", frameon=True, edgecolor="black", fancybox=False)
    fig.savefig(FIG / "d3_weight_tornado.png", dpi=150)
    plt.close(fig)
    L.append("![weights](../figures/v1x/d3_weight_tornado.png)\n\n")


# ---------------------------------------------------------------- D.4 safeguards and targets
def d4(L):
    s = owner()
    t = O.food_table()
    base = O.solve(t, s)
    E = s.energy
    variants = [
        ("protein 1.6 g/kg", replace(s, protein=1.6 * 76)), ("protein 2.2 g/kg", replace(s, protein=2.2 * 76, protein_max=None)),
        ("carbohydrate band 6–10 g/kg (high training)", replace(s, carb_lo=6 * 76, carb_hi=10 * 76)),
        ("carbohydrate band 3–5 g/kg (light)", replace(s, carb_lo=3 * 76, carb_hi=5 * 76)),
        ("fat min 15 % E", replace(s, fat_lo=0.15 * E / 9)), ("fat min 25 % E", replace(s, fat_lo=0.25 * E / 9)),
        ("free sugars ≤ 5 % E", replace(s, free_sugars_max=0.05 * E / 4)),
        ("max 20 % energy per food", replace(s, max_share=0.2)), ("max 50 % energy per food", replace(s, max_share=0.5)),
        ("energy −10 %", replace(s, energy=0.9 * E)), ("energy +10 %", replace(s, energy=1.1 * E)),
        ("food mass ≤ 2,000 g", replace(s, max_mass=2000)), ("food mass ≤ 1,500 g", replace(s, max_mass=1500)),
        ("MILP: ≥ 10 foods, ≥ 50 g each", replace(s, milp=True, min_foods=10, min_portion=50)),
    ]
    rows = [{"variant": "baseline", "status": "optimal", "cost €/day": base.cost_eur, "Δ cost %": 0, "mass g": base.mass_g,
             "same foods (Jaccard)": 1.0, "main foods": ", ".join(base.foods.name.head(4))}]
    for lab, sp in variants:
        sol = O.solve(t, sp)
        ok = sol.status == "optimal"
        rows.append({"variant": lab, "status": sol.status, "cost €/day": sol.cost_eur if ok else np.nan,
                     "Δ cost %": (sol.cost_eur / base.cost_eur - 1) * 100 if ok else np.nan, "mass g": sol.mass_g if ok else np.nan,
                     "same foods (Jaccard)": jaccard(base.foods.index, sol.foods.index) if ok else np.nan,
                     "main foods": ", ".join(sol.foods.name.head(4)) if ok else ", ".join(sol.conflicts.constraint)})
    caps = O.CFG["max_g_eaten"]
    saved = {k: dict(v) if isinstance(v, dict) else v for k, v in caps.items()}
    for f in (0.5, 2.0):
        for sect in ("food", "category"):
            caps[sect] = {k: v * f for k, v in saved[sect].items()}
        caps["default"] = saved["default"] * f
        sol = O.solve(O.food_table(), s)
        rows.append({"variant": f"all per-food caps ×{f}", "status": sol.status, "cost €/day": sol.cost_eur,
                     "Δ cost %": (sol.cost_eur / base.cost_eur - 1) * 100, "mass g": sol.mass_g,
                     "same foods (Jaccard)": jaccard(base.foods.index, sol.foods.index), "main foods": ", ".join(sol.foods.name.head(4))})
    caps.update(saved)
    L += ["## D.4 Safeguard and target sensitivity (owner, minimum cost)\n\n", md_table(pd.DataFrame(rows), 2), "\n"]


# ---------------------------------------------------------------- D.5 Monte Carlo
def perturb(t, grades, rng):
    t = t.copy()
    n = len(t)
    cvc = grades.comp_grade.map(CV_COMP).fillna(0.2).to_numpy()
    cvd = grades.digest_grade.map(CV_DIG).fillna(0.12).to_numpy()
    def ln(cv):  # multiplicative lognormal noise with mean 1
        sig = np.sqrt(np.log(1 + cv ** 2))
        return rng.lognormal(-sig ** 2 / 2, sig, n)
    fk, fp, fc, ff, fd = ln(cvc), ln(cvc), ln(cvc), ln(cvc), np.minimum(ln(cvd), 1 / 0.8)
    t["kcal"] *= fk
    t["protein"] *= fp
    t["carb"] *= fc
    t["fat"] *= ff
    for a in O.AA:
        t[f"dAA_{a}"] *= fp * fd   # amino acids move with protein (same analysis) and digestibility
    lo = grades.price_band_lo.reindex(t.index).to_numpy() / grades.eur_per_kg_edible.reindex(t.index).to_numpy()
    hi = grades.price_band_hi.reindex(t.index).to_numpy() / grades.eur_per_kg_edible.reindex(t.index).to_numpy()
    lo = np.where(np.isfinite(lo), lo, 0.9)
    hi = np.where(np.isfinite(hi), hi, 1.1)
    t["eur"] *= rng.uniform(np.minimum(lo, hi), np.maximum(lo, hi))
    return t


def d5(L):
    s = owner()
    t = O.food_table()
    master = M.load().set_index("food_id")
    grades = master.reindex(t.index)[["comp_grade", "digest_grade", "price_band_lo", "price_band_hi", "eur_per_kg_edible"]]
    base = O.solve(t, s)
    rng = np.random.default_rng(20261007)
    costs, sel, grams, infeas = [], {}, {}, 0
    core = master[(master.role == "core") & master.eur_per_kg_edible.notna()]
    w = M.PRESETS["Hybrid: bulk + endurance fuel"]
    top10 = {}
    for i in range(N_MC):
        tp = perturb(t, grades, rng)
        sol = O.solve(tp, s)
        if sol.status != "optimal":
            infeas += 1
            continue
        costs.append(sol.cost_eur)
        for f, g in sol.foods.g_eaten.items():
            sel[f] = sel.get(f, 0) + 1
            grams.setdefault(f, []).append(g)
        # composite ranking under the same perturbation (per-€ and density metrics move with prices/composition)
        cp = core.copy()
        common = tp.index.intersection(cp.index)
        cp.loc[common, "kcal_per_eur"] = tp.loc[common, "kcal"] / tp.loc[common, "eur"]
        cp.loc[common, "useful_protein_per_eur"] = cp.loc[common, "useful_protein_per_eur"] * (t.loc[common, "eur"] / tp.loc[common, "eur"])
        cp.loc[common, "carb_per_eur"] = tp.loc[common, "carb"] / tp.loc[common, "eur"]
        for f in M.composite(cp, w).nlargest(10).index:
            top10[f] = top10.get(f, 0) + 1
    ok = len(costs)
    c = np.array(costs)
    freq = (pd.Series(sel) / ok).sort_values(ascending=False)
    names = t.name
    tab = pd.DataFrame({"food": names.reindex(freq.index), "selected in % of runs": 100 * freq,
                        "median g eaten when selected": [np.median(grams[f]) for f in freq.index],
                        "in baseline": [f in base.foods.index for f in freq.index]}).head(15)
    t10 = (pd.Series(top10) / ok * 100).sort_values(ascending=False).head(15)
    L += [f"## D.5 Monte Carlo ({N_MC} runs; composition CV A/B/C = 5/10/20 %, digestibility CV 3/6/12 %, prices "
          "uniform within their bands; assumptions [U])\n\n",
          f"Optimal cost: median €{np.median(c):.2f}/day (5–95 %: €{np.percentile(c, 5):.2f}–{np.percentile(c, 95):.2f}); "
          f"baseline €{base.cost_eur:.2f}. Infeasible draws: {infeas}.\n\n",
          "**How often each food is in the optimal diet**\n\n", md_table(tab.reset_index(drop=True), 1),
          "\n**How often each food is in the composite top 10** (owner preset)\n\n",
          md_table(pd.DataFrame({"food": master.name_en.reindex(t10.index), "% of runs": t10}).reset_index(drop=True), 0), "\n"]
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.subplots_adjust(left=0.1, right=0.95, top=0.82, bottom=0.17)
    ax.hist(c, bins=30, color="#2a78d6", edgecolor="black", lw=0.6)
    ax.axvline(base.cost_eur, color="black", ls="--", lw=1)
    ax.annotate(f"baseline €{base.cost_eur:.2f}", (base.cost_eur, ax.get_ylim()[1] * 0.92), xytext=(6, 0),
                textcoords="offset points", fontsize=9)
    P._style(ax, "How certain is the minimum daily cost?",
             f"{ok} Monte Carlo runs perturbing composition, digestibility and prices (owner targets).",
             "Minimum cost per day (€)", "Runs")
    fig.savefig(FIG / "d5_cost_distribution.png", dpi=150)
    plt.close(fig)
    L.append("![mc](../figures/v1x/d5_cost_distribution.png)\n\n")


# ---------------------------------------------------------------- D.6 composition database
def d6(L):
    cmap = pd.read_csv(ROOT / "data/foods/composition_map.csv", dtype=str)
    m = cmap[(cmap.comp_db == "frida") & cmap.yield_usda_raw.notna()]
    rows = []
    for r in m.itertuples():
        f, u = C.lookup("frida", r.comp_id), C.lookup("usda_sr", r.yield_usda_raw)
        rows.append({"food_id": r.food_id, **{f"{k} Frida": f[k] for k in ("kcal", "protein")},
                     **{f"{k} USDA": u[k] for k in ("kcal", "protein")},
                     "kcal diff %": (u.kcal / f.kcal - 1) * 100, "protein diff %": (u.protein / f.protein - 1) * 100})
    d = pd.DataFrame(rows)
    # optimizer with USDA composition for these foods
    t = O.food_table()
    tu = t.copy()
    y = M.load().set_index("food_id").yield_eaten_per_purchased
    for r in m.itertuples():
        if r.food_id not in tu.index:
            continue
        u = C.lookup("usda_sr", r.yield_usda_raw)
        yy = y[r.food_id]
        tu.loc[r.food_id, "kcal"] = u.kcal / 100 / yy
        tu.loc[r.food_id, "protein"] = u.protein / 100 / yy
        tu.loc[r.food_id, "fat"] = u.fat / 100 / yy
        tu.loc[r.food_id, "carb"] = (u.carb - (u.fibre if pd.notna(u.fibre) else 0)) / 100 / yy  # by difference → available
        ratio = (u.protein / f_p) if (f_p := C.lookup("frida", r.comp_id).protein) else 1
        for a in O.AA:
            tu.loc[r.food_id, f"dAA_{a}"] *= ratio
    s = owner()
    a, b = O.solve(t, s), O.solve(tu, s)
    L += ["## D.6 Composition database: Frida 5.5 vs USDA SR Legacy (foods with both, raw state)\n\n",
          f"{len(d)} foods. kcal: median |difference| {d['kcal diff %'].abs().median():.1f} % (max "
          f"{d['kcal diff %'].abs().max():.0f} %); protein: median |difference| {d['protein diff %'].abs().median():.1f} % "
          f"(max {d['protein diff %'].abs().max():.0f} %).\n\n",
          md_table(d.reindex(d["protein diff %"].abs().sort_values(ascending=False).index).head(10).round(1)), "\n",
          f"Owner minimum-cost diet: Frida-based €{a.cost_eur:.2f}/day vs USDA-based €{b.cost_eur:.2f}/day; same foods "
          f"(Jaccard) {jaccard(a.foods.index, b.foods.index):.2f}.\n\n",
          "H7 (Latvian vs generic prices) cannot be tested yet: it needs a second, comparable price source (e.g. another "
          "country's official average prices).\n"]


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    L = ["# v1.x robustness (generated by `src/analysis/robustness.py`)\n\n"]
    for f in (d1, d2, d3, d4, d5, d6):
        f(L)
        print("done", f.__name__, flush=True)
    OUT.write_text("".join(L))
    print(OUT.read_text())


if __name__ == "__main__":
    main()
