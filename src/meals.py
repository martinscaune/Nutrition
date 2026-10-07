"""Rate and improve a single meal (owner request 2026-10-07).

Meal Nutrient Score (0–100), personal and transparent (in the spirit of the Nutrient Rich Foods index,
drewnowski2010nrf, but against the person's own targets):
  share      = meal kcal / daily energy target
  adequacy_j = min(1, supply_j / (daily minimum_j × share))     for 20 "encourage" items: protein, protein quality
               (lowest digestible amino-acid ratio, FAO 2013), fibre and the 17 enforced vitamins/minerals with a minimum
  excess_k   = min(1, max(0, supply_k / (daily limit_k × share) − 1))   for free sugars, saturated fat, sodium
  score      = 100 × (mean adequacy − mean excess), floored at 0
The improved meal keeps the same energy (±3 %) and maximizes exactly this score (a linear programme: adequacy and
excess are auxiliary variables), with realistic per-meal portions (config/meals.yaml) and a cap on the number of foods.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import Bounds, LinearConstraint, milp

from src import optimizer as O
from src.build_master import PATTERN

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load(open(ROOT / "config/meals.yaml"))
TEMPLATES = yaml.safe_load(open(ROOT / "config/meal_templates.yaml"))
LIMITS = {"free_sugars": "Free sugars", "sat_fat": "Saturated fat", "sodium_mg": "Sodium"}
NOT_PER_MEAL = {"ala_g", "epa_dha_g"}   # omega-3: weekly-average targets (fatty fish 1–2×/week), not judged per meal


@dataclass
class Item:
    key: str        # column in the food table, or "aa:<pattern key>"
    label: str
    target: float   # meal-level target (minimum for adequacy items, limit for limit items)
    unit: str


def meal_items(res, meal_kcal):
    """Adequacy and limit items for a meal of meal_kcal, from a targets Result (src/targets.py)."""
    share = meal_kcal / res.targets["energy"].value
    prot = res.targets["protein"].value * share
    enc = [Item("protein", "Protein", prot, "g")]
    for k, parts in O.PATTERN_SPLIT.items():  # digestible IAA vs reference protein at the protein target
        enc.append(Item(f"aa:{k}", f"amino acid {k}", PATTERN[k] * prot / 1000, "g"))
    for k, m in res.micros.items():
        if m.enforce and m.min and k not in NOT_PER_MEAL:
            enc.append(Item(O.MICRO_COL.get(k, k), m.label, m.min * share, m.unit))
    lim = [Item("free_sugars", "Free sugars", res.targets["free sugars (max)"].value * share, "g")]
    for k in ("sat_fat", "sodium_mg"):
        m = res.micros[k]
        lim.append(Item(k, m.label, m.max * share, m.unit))
    return enc, lim, share


def _coef(t, key):
    if key.startswith("aa:"):
        return sum(t[f"dAA_{p}"] for p in O.PATTERN_SPLIT[key[3:]]).to_numpy(float)
    return t[key].to_numpy(float)


def score(t, grams, res):
    """Score a meal given as grams eaten per food_id. Returns (score, breakdown DataFrame, totals dict)."""
    g = grams.reindex(t.index).fillna(0).to_numpy(float)
    kcal = float(t.kcal.to_numpy() @ g)
    enc, lim, share = meal_items(res, kcal)
    rows = []
    aa_rows = []
    for it in enc:
        v = float(_coef(t, it.key) @ g)
        a = min(1.0, v / it.target) if it.target > 0 else 1.0
        (aa_rows if it.key.startswith("aa:") else rows).append(
            {"item": it.label, "key": it.key, "kind": "encourage", "meal": v, "meal target": it.target, "unit": it.unit,
             "score": a})
    # protein quality = the most limiting amino acid (one item, not nine)
    q = min(aa_rows, key=lambda r: r["score"])
    q["key"] = "protein_quality"
    rows.insert(1, {"item": f"Protein quality (limiting: {q['item'].split()[-1]})", "key": q["key"], "kind": "encourage",
                    "meal": q["meal"], "meal target": q["meal target"], "unit": "g", "score": q["score"]})
    for it in lim:
        v = float(_coef(t, it.key) @ g)
        e = min(1.0, max(0.0, v / it.target - 1)) if it.target > 0 else 0.0
        rows.append({"item": it.label, "key": it.key, "kind": "limit", "meal": v, "meal target": it.target, "unit": it.unit,
                     "score": -e})
    b = pd.DataFrame(rows)
    adequacy = b[b.kind == "encourage"].score.mean()
    excess = -b[b.kind == "limit"].score.mean()
    sc = max(0.0, 100 * (adequacy - excess))
    totals = {"kcal": kcal, "cost_eur": float(t.eur.to_numpy() @ g), "mass_g": float(g.sum()),
              "protein": float(t.protein.to_numpy() @ g), "share_of_day": share}
    return sc, b, totals


def meal_cap(food_id, category):
    c = CFG["max_g_per_meal"]
    return float(c["food"].get(food_id, c["category"].get(category, c["default"])))


@dataclass
class MealResult:
    status: str
    grams: pd.Series = field(default_factory=pd.Series)
    score: float = np.nan
    breakdown: pd.DataFrame = field(default_factory=pd.DataFrame)
    totals: dict = field(default_factory=dict)


def improve(t, grams, res, mode="best", max_cost=None, exclude=(), tiebreak="cost"):
    """Same-energy meal that maximizes the Meal Nutrient Score (stage 1); among meals within `score_slack` points of
    that maximum, stage 2 picks the cheapest (tiebreak='cost') or the one closest to the original (tiebreak='similar').
    mode 'best': any suggestable food (≤ max_foods_best foods);
    mode 'tweak': keep the user's foods within tweak_range of their amounts, add ≤ max_new_foods_tweak foods."""
    g_all = grams[grams > 0]
    allowed = t.role.isin(CFG["suggest_roles"]) & ~t.index.isin(CFG["never_suggest"]) | t.index.isin(g_all.index)
    t = t[allowed & ~t.index.isin(list(exclude))]
    g0 = g_all.reindex(t.index).fillna(0)
    kcal0 = float(t.kcal.to_numpy() @ g0.to_numpy())
    if kcal0 <= 0:
        return MealResult("empty meal")
    enc, lim, _ = meal_items(res, kcal0)
    aa = [it for it in enc if it.key.startswith("aa:")]      # protein quality = min over amino acids → one variable q
    enc_main = [it for it in enc if not it.key.startswith("aa:")]
    n, ne, nl = len(t), len(enc_main), len(lim)
    tol = CFG["energy_tolerance_pct"] / 100
    caps = np.array([max(meal_cap(f, c), g0[f]) for f, c in zip(t.index, t.category)])
    mins = np.array([min(CFG.get("min_portion_category", {}).get(c, CFG["min_portion_g"]), cap)
                     for c, cap in zip(t.category, caps)])
    # variables: x (n grams), z (ne adequacies), q (protein quality), e (nl excesses), y (n binaries), d (n |x − g0|)
    ix, iz, iq, ie, iy, idv = 0, n, n + ne, n + ne + 1, n + ne + 1 + nl, 2 * n + ne + 1 + nl
    N = 3 * n + ne + 1 + nl
    score_c = np.zeros(N)                     # −score/100 as a linear function
    score_c[iz:iz + ne] = -1.0 / (ne + 1)
    score_c[iq] = -1.0 / (ne + 1)
    score_c[ie:ie + nl] = 1.0 / nl
    A, lo, hi = [], [], []

    def row(coefs, l, h):
        r = np.zeros(N)
        for i, v in coefs:
            r[i] += v
        A.append(r); lo.append(l); hi.append(h)

    kc = t.kcal.to_numpy(float)
    row([(ix + i, kc[i]) for i in range(n)], kcal0 * (1 - tol), kcal0 * (1 + tol))
    for j, it in enumerate(enc_main):          # target·z ≤ supply
        cf = _coef(t, it.key)
        row([(iz + j, it.target)] + [(ix + i, -cf[i]) for i in range(n)], -np.inf, 0)
    for it in aa:                              # target·q ≤ supply, every amino acid
        cf = _coef(t, it.key)
        row([(iq, it.target)] + [(ix + i, -cf[i]) for i in range(n)], -np.inf, 0)
    for k, it in enumerate(lim):               # supply − limit·e ≤ limit
        cf = _coef(t, it.key)
        row([(ix + i, cf[i]) for i in range(n)] + [(ie + k, -it.target)], -np.inf, it.target)
    lb, ub = np.zeros(N), np.concatenate([caps, np.ones(ne + 1 + nl + n), np.full(n, np.inf)])
    for i in range(n):                         # x ≤ cap·y ; x ≥ min_portion·y ; d ≥ |x − g0|
        row([(ix + i, 1), (iy + i, -caps[i])], -np.inf, 0)
        row([(ix + i, -1), (iy + i, mins[i])], -np.inf, 0)
        row([(idv + i, 1), (ix + i, -1)], -g0.iloc[i], np.inf)
        row([(idv + i, 1), (ix + i, 1)], g0.iloc[i], np.inf)
    if mode == "best":
        row([(iy + i, 1) for i in range(n)], 0, CFG["max_foods_best"])
    else:
        r_lo, r_hi = CFG["tweak_range"]
        new = [i for i in range(n) if g0.iloc[i] == 0]
        row([(iy + i, 1) for i in new], 0, CFG["max_new_foods_tweak"])
        for i in range(n):
            if g0.iloc[i] > 0:
                lb[ix + i], ub[ix + i] = g0.iloc[i] * r_lo, g0.iloc[i] * r_hi
                lb[iy + i] = 1
    if max_cost is not None:
        row([(ix + i, t.eur.iloc[i]) for i in range(n)], -np.inf, max_cost)
    integ = np.concatenate([np.zeros(n + ne + 1 + nl), np.ones(n), np.zeros(n)])

    def run(c, extra=None):
        AA, L, H = list(A), list(lo), list(hi)
        if extra is not None:
            AA.append(extra[0]); L.append(extra[1]); H.append(extra[2])
        return milp(c, constraints=LinearConstraint(np.array(AA), L, H), integrality=integ, bounds=Bounds(lb, ub),
                    options={"time_limit": 30})

    s1 = run(score_c + 1e-6 * np.concatenate([np.zeros(idv), np.ones(n)]))   # tiny pull towards the original
    if s1.x is None:
        return MealResult("infeasible")
    best = -s1.fun
    c2 = np.zeros(N)
    if tiebreak == "cost":
        c2[ix:ix + n] = t.eur.to_numpy(float)
    else:
        c2[idv:idv + n] = 1.0
    s2 = run(c2, (score_c, -np.inf, -(best - CFG["score_slack"] / 100)))
    sol = s2 if s2.x is not None else s1
    x = pd.Series(np.where(sol.x[:n] < 0.5, 0, sol.x[:n]), index=t.index)
    sc, b, tot = score(t, x, res)
    return MealResult("optimal", x[x > 0].round(0), sc, b, tot)


def hints(t, grams, breakdown, exclude=(), n=3):
    """Plain-language hints for a scored meal: what is short (and the best sources per portion), what is over the
    limit (and which foods in the meal supply it)."""
    out = []
    core = t[(t.role == "core") & ~t.index.isin(list(exclude))]
    portion = pd.Series([min(meal_cap(f, c), 200.0, 300 / k if k > 0 else 200.0)
                         for f, c, k in zip(core.index, core.category, core.kcal)], index=core.index).round(-1).clip(lower=10)
    g = grams.reindex(t.index).fillna(0)
    for _, r in breakdown.iterrows():
        if r.kind == "encourage" and r.score < 0.999:
            if r.key == "protein_quality":
                out.append(f"**{r['item']}** {r.score:.0%}: add a food with a different limiting amino acid (grains + "
                           "legumes, or any milk, egg, meat or fish).")
                continue
            per = (core[r.key] * portion).sort_values(ascending=False)
            src = ", ".join(f"{core.name[f]} ({portion[f]:.0f} g → {per[f]:.2g} {r.unit})" for f in per.index[:n])
            out.append(f"**{r['item']}** {r.score:.0%} of this meal's share: add e.g. {src}.")
        elif r.kind == "limit" and r.score < -0.001:
            contrib = (t.loc[g.index, r.key] * g).sort_values(ascending=False)
            contrib = contrib[contrib > 0]
            top = ", ".join(f"{t.name[f]} ({c / contrib.sum():.0%})" for f, c in contrib.head(2).items())
            tip = (" Draining and rinsing canned beans lowers their sodium substantially (duyff2011); "
                   "the values here are for drained, unrinsed beans." if r.key == "sodium_mg" and
                   any(f.endswith("_canned") for f in contrib.index[:2]) else "")
            out.append(f"**{r['item']}** {r['meal'] / r['meal target']:.1f}× this meal's share of the daily limit; "
                       f"mostly from {top}.{tip}")
    return out


def split_day(t, day_g, mass_kg, n_meals=None):
    """Split a day's diet (grams eaten per food_id) into meals: each meal ≥ protein_g_per_kg_per_meal × body mass
    protein (or an equal share of the day's protein if that is less) and ≥ min_energy_share of energy, per-meal portion
    caps from max_g_per_meal; minimizes the number of (food, meal) pieces so each food sits in as few meals as possible.
    Returns a DataFrame food × meal (grams eaten), adding meals (up to 6) if 4 cannot satisfy the limits, or None. Food pairing/taste is NOT modelled."""
    S = CFG["split"]
    m = n_meals or S["n_meals"]
    day_g = day_g[day_g > 0]
    tt = t.loc[day_g.index]
    n = len(tt)
    X = day_g.to_numpy(float)
    kcal, prot = tt.kcal.to_numpy(float), tt.protein.to_numpy(float)
    E, P = float(kcal @ X), float(prot @ X)
    p_min = min(S["protein_g_per_kg_per_meal"] * mass_kg, 0.9 * P / m)
    caps = np.array([max(meal_cap(f, c), np.ceil(X[i] / m)) for i, (f, c) in enumerate(zip(tt.index, tt.category))])
    # variables: x[i, j] (n·m) then y[i, j] (n·m); index i*m + j
    nv = n * m
    A, lo, hi = [], [], []

    def row(coefs, l, h):
        r = np.zeros(2 * nv)
        for k, v in coefs:
            r[k] += v
        A.append(r); lo.append(l); hi.append(h)

    for i in range(n):
        row([(i * m + j, 1) for j in range(m)], X[i], X[i])                     # the whole day's amount is eaten
        for j in range(m):
            row([(i * m + j, 1), (nv + i * m + j, -min(caps[i], X[i]))], -np.inf, 0)  # x ≤ cap·y
            row([(i * m + j, -1), (nv + i * m + j, min(S["min_piece_g"], X[i]))], -np.inf, 0)
    for j in range(m):
        row([(i * m + j, prot[i]) for i in range(n)], p_min, np.inf)
        row([(i * m + j, kcal[i]) for i in range(n)], S["min_energy_share"] * E, S["max_energy_share"] * E)
        row([(i * m + j, 1) for i in range(n)], 0, max(S["max_mass_share"], 1 / m) * X.sum())
    for j in range(m - 1):                                                       # symmetry: meal energy descending
        row([(i * m + j, kcal[i]) for i in range(n)] + [(i * m + j + 1, -kcal[i]) for i in range(n)], 0, np.inf)
    c = np.concatenate([np.zeros(nv), np.ones(nv)])
    r = milp(c, constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.concatenate([np.zeros(nv), np.ones(nv)]),
             bounds=Bounds(np.zeros(2 * nv), np.concatenate([np.repeat(X, m), np.ones(nv)])), options={"time_limit": 20})
    if r.x is None:
        if n_meals is None and m < 6:          # too much food for 4 meals within the limits: try more meals
            return split_day(t, day_g, mass_kg, m + 1)
        return None
    g = pd.DataFrame(r.x[:nv].reshape(n, m), index=tt.index, columns=[f"meal {j + 1}" for j in range(m)])
    g = g.where(g >= 0.5, 0).round(0)
    g.insert(0, "food", tt.name)
    return g


def split_summary(t, split):
    """Per-meal kcal, protein, cost for a split_day() result."""
    g = split.drop(columns="food")
    tt = t.loc[g.index]
    return pd.DataFrame({"kcal": tt.kcal @ g, "protein g": tt.protein @ g, "€": tt.eur @ g}).round(1)
