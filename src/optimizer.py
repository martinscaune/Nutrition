"""Diet optimizer (v1.0, PLAN C.1–C.9): which combination of foods meets a person's daily targets at the lowest
cost (or food mass)?

Linear programme (HiGHS via scipy). Decision variable x_i = grams of food i EATEN per day.
  minimize   cost (or mass, or a normalized mix)
  subject to energy within ±tol of target                      (targets: src/targets.py)
             protein ≥ target (≤ upper bound)
             for every indispensable amino acid j:              (decision D9; mode "aa")
                 Σ_i digestible AA_j(i)·x_i ≥ FAO-2013 adult pattern_j × protein target
             carbohydrate within the training band, fat within its % band, free sugars ≤ cap
             safeguards: per-food maximum (config/optimizer.yaml), ≤ 30 % of energy from one food
MILP variant: at least N distinct foods, each eaten in at least a minimum portion.

Every constraint row is named, so results can say which constraints bind (shadow prices) and how far each
unused food is from entering (reduced costs). Infeasible problems are re-solved in "elastic" mode
(goal-programming slacks) to report which targets conflict and by how much.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

from src import metrics as M
from src.build_master import PATTERN
from src.targets import compute

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load(open(ROOT / "config/optimizer.yaml"))
AA = ["TRP", "THR", "ILE", "LEU", "LYS", "MET", "CYS", "PHE", "TYR", "VAL", "HIS"]
PATTERN_SPLIT = {"HIS": ["HIS"], "ILE": ["ILE"], "LEU": ["LEU"], "LYS": ["LYS"], "SAA": ["MET", "CYS"],
                 "AAA": ["PHE", "TYR"], "THR": ["THR"], "TRP": ["TRP"], "VAL": ["VAL"]}


# ---------------------------------------------------------------- inputs
def food_table(quality="diaas", price_scenario="central", roles=None, exclude=(), include_only=None):
    """Per-gram-eaten coefficients for every eligible food."""
    df = M.with_price(M.with_quality(M.load(), quality), price_scenario)
    roles = roles or CFG["include_roles"]
    df = df[df.role.isin(roles) & df.eur_per_kg_used.notna() & df.kcal_100g_eaten.notna()]
    df = df[~df.food_id.isin(exclude)]
    if include_only is not None:
        df = df[df.food_id.isin(include_only)]
    t = pd.DataFrame({"food_id": df.food_id, "name": df.name_en, "category": df.category, "group": df.group,
                      "role": df.role}).set_index("food_id")
    y = df.set_index("food_id").yield_eaten_per_purchased
    d = df.set_index("food_id")
    t["kcal"] = d.kcal_100g_eaten / 100
    t["protein"] = d.protein_100g_eaten / 100
    t["useful_protein"] = d.useful_protein_100g_eaten / 100
    t["carb"] = d.carb_100g_eaten.fillna(0) / 100
    t["fat"] = d.fat_100g_eaten.fillna(0) / 100
    t["free_sugars"] = d.free_sugars_100g_eaten.fillna(0) / 100
    t["fibre"] = d.fibre_100g_eaten.fillna(0) / 100
    t["eur"] = d.eur_per_kg_used / 1000 / y            # € per g eaten (1 g eaten = 1/yield g bought)
    t["g_bought_per_g_eaten"] = 1 / y / d.edible_portion  # gross purchase mass incl. bone/peel
    for a in AA:  # digestible amino acid, g per g eaten (missing data → 0: conservative)
        t[f"dAA_{a}"] = (d[f"{a}_mg_per_g_protein"] * d[f"dig_{a}"] * d.protein_100g_eaten / 100 / 1000).fillna(0)
    t["cap"] = [cap_g(f, c) for f, c in zip(t.index, t.category)]
    return t


def cap_g(food_id, category):
    caps = CFG["max_g_eaten"]
    return float(caps["food"].get(food_id, caps["category"].get(category, caps["default"])))


@dataclass
class Spec:
    energy: float
    protein: float
    protein_max: float | None = None
    carb_lo: float | None = None
    carb_hi: float | None = None
    fat_lo: float | None = None
    fat_hi: float | None = None
    free_sugars_max: float | None = None
    protein_mode: str = "aa"            # "aa" (D9), "pq" (Σ protein × quality ≥ target), "crude"
    safeguards: str = "full"            # "none" | "macros" | "full"
    objective: str = "cost"             # "cost" | "mass" | "mix"
    mix_weight_cost: float = 0.5
    energy_tol: float = CFG["energy_tolerance_pct"] / 100
    max_share: float = CFG["max_energy_share_per_food"]
    max_mass: float | None = CFG["max_total_mass_g_eaten"]
    milp: bool = False
    min_foods: int = CFG["min_distinct_foods"]
    min_portion: float = CFG["min_portion_g_eaten"]
    fixed_cost_norm: float | None = None   # for "mix": normalizers (cost*, mass*) from single-objective runs
    fixed_mass_norm: float | None = None


def spec_from_profile(profile, **kw):
    r = compute(profile)
    t = r.targets
    return Spec(energy=t["energy"].value, protein=t["protein"].value, protein_max=t["protein"].high,
                carb_lo=t["carbohydrate"].low, carb_hi=t["carbohydrate"].high, fat_lo=t["fat"].low,
                fat_hi=t["fat"].high, free_sugars_max=t["free sugars (max)"].value,
                **({"objective": "mass"} if (profile.priorities or {}).get("cost", 1) == 0 else {}), **kw), r


# ---------------------------------------------------------------- model building
def _rows(t, s):
    """Inequality rows A x ≤ b as list of (name, coefficient vector, rhs, kind, target value)."""
    R = []

    def ge(name, coef, val):
        R.append((name, -coef.to_numpy(float), -val, "≥", val))

    def le(name, coef, val):
        R.append((name, coef.to_numpy(float), val, "≤", val))

    ge("energy (min)", t.kcal, s.energy * (1 - s.energy_tol))
    le("energy (max)", t.kcal, s.energy * (1 + s.energy_tol))
    if s.protein_mode == "pq":
        ge("useful protein (Σ protein × quality)", t.useful_protein, s.protein)
    else:
        ge("protein (min)", t.protein, s.protein)
    if s.protein_mode == "aa":
        for k, parts in PATTERN_SPLIT.items():
            ge(f"amino acid {k}", sum(t[f"dAA_{p}"] for p in parts), PATTERN[k] * s.protein / 1000)
    if s.safeguards in ("macros", "full"):
        if s.protein_max:
            le("protein (max)", t.protein, s.protein_max)
        if s.carb_lo is not None:
            ge("carbohydrate (min)", t.carb, s.carb_lo)
        if s.carb_hi is not None:
            le("carbohydrate (max)", t.carb, s.carb_hi)
        if s.fat_lo is not None:
            ge("fat (min)", t.fat, s.fat_lo)
        if s.fat_hi is not None:
            le("fat (max)", t.fat, s.fat_hi)
        if s.free_sugars_max is not None:
            le("free sugars (max)", t.free_sugars, s.free_sugars_max)
    if s.safeguards == "full":
        for f in t.index:
            e = pd.Series(0.0, index=t.index)
            e[f] = t.kcal[f]
            le(f"energy share {f}", e, s.max_share * s.energy)
    if s.max_mass:
        le("total food mass (max)", pd.Series(1.0, index=t.index), s.max_mass)
    return R


def _objective(t, s):
    if s.objective == "cost":
        return t.eur.to_numpy(float)
    if s.objective == "mass":
        return np.ones(len(t))
    cn = s.fixed_cost_norm or 1.0
    mn = s.fixed_mass_norm or 1.0
    return s.mix_weight_cost * t.eur.to_numpy(float) / cn + (1 - s.mix_weight_cost) * np.ones(len(t)) / mn


@dataclass
class Solution:
    status: str
    spec: Spec
    foods: pd.DataFrame = field(default_factory=pd.DataFrame)
    totals: pd.DataFrame = field(default_factory=pd.DataFrame)
    binding: pd.DataFrame = field(default_factory=pd.DataFrame)
    reduced_costs: pd.DataFrame = field(default_factory=pd.DataFrame)
    conflicts: pd.DataFrame = field(default_factory=pd.DataFrame)
    objective_value: float = np.nan
    cost_eur: float = np.nan
    mass_g: float = np.nan


def solve(t, s: Spec) -> Solution:
    rows = _rows(t, s)
    A = np.array([r[1] for r in rows])
    b = np.array([r[2] for r in rows])
    caps = t.cap.to_numpy(float) if s.safeguards == "full" else np.full(len(t), 5000.0)
    c = _objective(t, s)
    n = len(t)
    if not s.milp:
        res = linprog(c, A_ub=A, b_ub=b, bounds=list(zip(np.zeros(n), caps)), method="highs")
        ok, x = res.status == 0, (res.x if res.status == 0 else None)
    else:  # x (n) and binary y (n): x ≤ cap·y, x ≥ min_portion·y, Σy ≥ min_foods
        cc = np.concatenate([c, np.zeros(n)])
        A1 = np.hstack([A, np.zeros((len(A), n))])
        link_up = np.hstack([np.eye(n), -np.diag(caps)])
        link_lo = np.hstack([-np.eye(n), np.diag(np.full(n, s.min_portion))])
        cnt = np.concatenate([np.zeros(n), -np.ones(n)])[None, :]
        cons = [LinearConstraint(A1, -np.inf, b), LinearConstraint(link_up, -np.inf, 0),
                LinearConstraint(link_lo, -np.inf, 0), LinearConstraint(cnt, -np.inf, -s.min_foods)]
        res = milp(cc, constraints=cons, integrality=np.concatenate([np.zeros(n), np.ones(n)]),
                   bounds=Bounds(np.zeros(2 * n), np.concatenate([caps, np.ones(n)])), options={"time_limit": 60})
        ok, x = res.status == 0, (res.x[:n] if res.x is not None and res.status == 0 else None)
    if not ok:
        return Solution("infeasible", s, conflicts=elastic(t, s, rows, caps, c))
    sol = Solution("optimal", s, objective_value=float(c @ x))
    _report(sol, t, s, x, rows, res if not s.milp else None)
    return sol


def _report(sol, t, s, x, rows, res):
    x = np.where(x < 1e-6, 0.0, x)
    used = x > 0.5
    f = t[used].copy()
    f["g_eaten"] = x[used]
    f["g_bought"] = f.g_eaten * f.g_bought_per_g_eaten
    f["cost_eur"] = f.g_eaten * f.eur
    for k in ["kcal", "protein", "carb", "fat", "free_sugars", "fibre"]:
        f[f"{k}_total"] = f.g_eaten * f[k]
    f["energy_share"] = f.kcal_total / f.kcal_total.sum()
    sol.foods = f.sort_values("kcal_total", ascending=False)[
        ["name", "group", "role", "g_eaten", "g_bought", "cost_eur", "kcal_total", "protein_total", "carb_total",
         "fat_total", "free_sugars_total", "fibre_total", "energy_share"]].round(2)
    tot = {k: float((t[k].to_numpy() * x).sum()) for k in ["kcal", "protein", "carb", "fat", "free_sugars", "fibre"]}
    targets = {"kcal": s.energy, "protein": s.protein, "carb": (s.carb_lo, s.carb_hi), "fat": (s.fat_lo, s.fat_hi),
               "free_sugars": (None, s.free_sugars_max), "fibre": (None, None)}
    sol.totals = pd.DataFrame([{"nutrient": k, "diet": v, "target": targets[k]} for k, v in tot.items()])
    sol.cost_eur = float((t.eur.to_numpy() * x).sum())
    sol.mass_g = float(x.sum())
    if res is not None:  # LP duals → which constraints bind and what they cost
        marg = res.ineqlin.marginals  # ∂objective/∂b for A x ≤ b (≤ 0 when binding)
        b = [r[2] for r in rows]
        Ax = np.array([r[1] for r in rows]) @ x
        # marginal m = ∂objective/∂b ≤ 0. Tightening a row by one unit (raising a minimum or lowering a maximum)
        # changes the objective by −m in both cases.
        bind = [{"constraint": r[0], "type": r[3], "target": r[4], "objective_per_unit_tighter": -m,
                 "slack": b_ - ax} for r, m, b_, ax in zip(rows, marg, b, Ax) if abs(m) > 1e-9]
        sol.binding = (pd.DataFrame(bind).sort_values("objective_per_unit_tighter", ascending=False)
                       if bind else pd.DataFrame())
        rc = res.lower.marginals  # reduced cost at lower bound 0: how much cheaper a food must get to enter
        sol.reduced_costs = pd.DataFrame({"name": t.name, "reduced_cost_per_g": rc, "used": used},
                                         index=t.index).sort_values("reduced_cost_per_g")


def elastic(t, s, rows, caps, c):
    """Goal-programming relaxation: every target row gets a penalized slack; report which ones must give."""
    target_rows = [i for i, r in enumerate(rows) if not r[0].startswith("energy share")]
    n, k = len(t), len(target_rows)
    A = np.array([r[1] for r in rows])
    b = np.array([r[2] for r in rows])
    scale = np.array([max(abs(rows[i][4]), 1.0) for i in target_rows])
    S = np.zeros((len(rows), k))
    for j, i in enumerate(target_rows):
        S[i, j] = -1.0  # A x − s ≤ b
    cc = np.concatenate([c * 1e-6, 1e3 / scale])  # slacks dominate; small tie-break on the real objective
    res = linprog(cc, A_ub=np.hstack([A, S]), b_ub=b,
                  bounds=list(zip(np.zeros(n), caps)) + [(0, None)] * k, method="highs")
    if res.status != 0:
        return pd.DataFrame([{"constraint": "model", "violation": np.nan, "note": "even the relaxed model failed"}])
    sl = res.x[n:]
    out = [{"constraint": rows[i][0], "type": rows[i][3], "target": rows[i][4],
            "violation": sl[j], "violation_pct": sl[j] / max(abs(rows[i][4]), 1e-9) * 100}
           for j, i in enumerate(target_rows) if sl[j] > 1e-6]
    return pd.DataFrame(out)


# ---------------------------------------------------------------- higher-level helpers
def alternatives(t, s, base: Solution, k=5):
    """C.9: near-optimal alternatives: ban each of the k largest contributors in turn and re-solve."""
    out = []
    for fid in base.foods.index[:k]:
        sol = solve(t.drop(index=fid), s)
        out.append({"banned": base.foods.loc[fid, "name"], "status": sol.status,
                    "cost_eur": sol.cost_eur, "cost_change_pct": (sol.cost_eur / base.cost_eur - 1) * 100,
                    "new_foods": ", ".join(sorted(set(sol.foods.name) - set(base.foods.name))) if sol.status == "optimal" else ""})
    return pd.DataFrame(out)


def cost_mass_front(t, s, n=8):
    """C.7: ε-constraint Pareto front of daily cost vs daily food mass."""
    from dataclasses import replace
    cheap = solve(t, replace(s, objective="cost"))
    light = solve(t, replace(s, objective="mass"))
    if "infeasible" in (cheap.status, light.status):
        return pd.DataFrame()
    pts = []
    for eps in np.linspace(light.mass_g, cheap.mass_g, n):
        sol = solve(t, replace(s, objective="cost", max_mass=eps * 1.0001))
        if sol.status == "optimal":
            pts.append({"max_mass_g": eps, "cost_eur": sol.cost_eur, "mass_g": sol.mass_g, "n_foods": len(sol.foods),
                        "main_foods": ", ".join(sol.foods.name[:4])})
    return pd.DataFrame(pts)


def aa_adequacy(t, foods, protein_target):
    """Digestible IAA supplied ÷ required (FAO 2013 adult pattern × protein target) for a solved diet; 1.0 = just enough."""
    g = foods.g_eaten.reindex(t.index).fillna(0)
    out = {}
    for k, parts in PATTERN_SPLIT.items():
        supplied = sum((t[f"dAA_{p}"] * g).sum() for p in parts)
        out[k] = supplied / (PATTERN[k] * protein_target / 1000)
    return pd.Series(out)


def closest_diet(t, s: Spec, template: pd.Series, max_cost=None, base_g=50.0):
    """Smallest change to a usual diet that meets every target (individual diet modelling, maillot2010).

    template: grams eaten per day indexed by food_id. Minimizes Σ w_i |x_i − template_i| with
    w_i = 1 / (template_i + base_g), so changing a large item by 50 g counts less than adding a new food.
    Optionally caps the daily cost (e.g. 'no more expensive than now').
    """
    tmpl = template.reindex(t.index).fillna(0.0).to_numpy(float)
    rows = _rows(t, s)
    A = np.array([r[1] for r in rows])
    b = np.array([r[2] for r in rows])
    n = len(t)
    caps = np.maximum(t.cap.to_numpy(float), tmpl) if s.safeguards == "full" else np.full(n, 5000.0)
    w = 1.0 / (tmpl + base_g)
    c = np.concatenate([np.zeros(n), w, w])                       # variables: x, over, under
    A_ub = np.hstack([A, np.zeros((len(A), 2 * n))])
    b_ub = b
    if max_cost is not None:
        A_ub = np.vstack([A_ub, np.concatenate([t.eur.to_numpy(float), np.zeros(2 * n)])])
        b_ub = np.append(b_ub, max_cost)
    A_eq = np.hstack([np.eye(n), -np.eye(n), np.eye(n)])          # x − over + under = template
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=tmpl,
                  bounds=list(zip(np.zeros(n), caps)) + [(0, None)] * (2 * n), method="highs")
    if res.status != 0:
        return Solution("infeasible", s, conflicts=elastic(t, s, rows, caps, t.eur.to_numpy(float)))
    x = res.x[:n]
    sol = Solution("optimal", s, objective_value=float(res.fun))
    _report(sol, t, s, x, rows, None)
    ch = pd.DataFrame({"name": t.name, "usual_g": tmpl, "new_g": np.where(x < 1e-6, 0, x)}, index=t.index)
    ch["change_g"] = ch.new_g - ch.usual_g
    sol.changes = ch[ch.change_g.abs() > 5].sort_values("change_g")
    return sol
