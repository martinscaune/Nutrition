"""Food-level metrics, Pareto fronts and composite indices (v0.1, PLAN A.1–A.4).

Everything works on data/processed/foods_master.csv (one row per food). Nothing here decides which
food "wins": functions compute objective metrics, non-dominated sets and *hypothetical* composite
scores whose weights are user-chosen (PROJECT.md §2, §8).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/processed/foods_master.csv"

# ---------------------------------------------------------------- display groups (≤ 6 colours + grey)
GROUP_OF = {"meat": "Meat & fish", "processed_meat": "Meat & fish", "fish": "Meat & fish",
            "eggs": "Eggs & dairy", "dairy": "Eggs & dairy",
            "legumes": "Legumes & soy", "soy": "Legumes & soy",
            "cereals": "Grains & potatoes", "bread": "Grains & potatoes", "potatoes": "Grains & potatoes",
            "nuts_seeds": "Nuts & seeds", "fruit": "Fruit & veg", "vegetables": "Fruit & veg"}
GROUPS = ["Meat & fish", "Eggs & dairy", "Legumes & soy", "Grains & potatoes", "Nuts & seeds", "Fruit & veg",
          "Ingredients & snacks", "Supplements"]

# ---------------------------------------------------------------- protein-quality definitions (PLAN A.2)
QUALITY = {
    "diaas": "DIAAS (FAO 2013 adult pattern), capped at 100 — default (decision D9/D10)",
    "diaas_child": "DIAAS (FAO 2013 0.5–3 y 'regulatory' pattern), capped at 100 — stricter sensitivity case",
    "crude": "No quality adjustment (all protein counts fully)",
}

# ---------------------------------------------------------------- metric catalogue
# name: (label, unit, higher_is_better)
METRICS = {
    "kcal_100g_eaten": ("Energy density (eaten)", "kcal/100 g", True),
    "useful_protein_100g_eaten": ("Useful protein density (eaten)", "g/100 g", True),
    "protein_100g_eaten": ("Protein density (eaten)", "g/100 g", True),
    "carb_100g_eaten": ("Carbohydrate density (eaten)", "g/100 g", True),
    "kcal_per_eur": ("Calories per euro", "kcal/€", True),
    "useful_protein_per_eur": ("Useful protein per euro", "g/€", True),
    "protein_per_eur": ("Protein per euro", "g/€", True),
    "carb_per_eur": ("Carbohydrate per euro", "g/€", True),
    "useful_protein_per_1000kcal": ("Useful protein per 1000 kcal", "g/1000 kcal", True),
    "g_eaten_per_1000kcal": ("Food mass for 1000 kcal (eaten)", "g", False),
    # same quantity, opposite direction: for cutting, more food per kcal = more filling (satiety proxy, v2.0 refines)
    "fullness_g_per_1000kcal": ("Fullness: food mass per 1000 kcal (eaten)", "g", True),
    "eur_per_1000kcal": ("Cost of 1000 kcal", "€", False),
    "eur_per_kg_edible": ("Price", "€/kg edible", False),
    "fat_energy_pct": ("Energy from fat", "% kcal", None),
    "diaas": ("DIAAS", "%", True),
}


def load(path=MASTER):
    df = pd.read_csv(path)
    extra = pd.DataFrame({
        "group": [("Supplements" if r == "supplement" else "Ingredients & snacks" if r in ("ingredient", "snack")
                   else GROUP_OF.get(c, "Ingredients & snacks")) for c, r in zip(df.category, df.role)],
        "fullness_g_per_1000kcal": df.g_eaten_per_1000kcal}, index=df.index)
    return with_quality(pd.concat([df, extra], axis=1), "diaas")


def with_quality(df, quality="diaas"):
    """Recompute 'useful protein' metrics for a protein-quality definition (see QUALITY)."""
    if quality not in QUALITY:
        raise ValueError(f"unknown quality definition {quality!r}; choose from {list(QUALITY)}")
    d = df.copy()  # (copy also de-fragments the wide frame)
    if quality == "crude":
        q = np.where(d.protein_100g_purchased.fillna(0) > 0, 1.0, 0.0)
    else:
        q = (d[quality].clip(upper=100) / 100).fillna(0.0).to_numpy()
    d["quality_factor"] = q
    d["quality_definition"] = quality
    d["useful_protein_100g_eaten"] = d.protein_100g_eaten * q
    d["useful_protein_per_eur"] = d.protein_100g_purchased * q * 10 / d.eur_per_kg_edible
    d["useful_protein_per_1000kcal"] = d.protein_100g_purchased * q / d.kcal_100g_purchased * 1000
    return d


PRICE_SCENARIOS = {"central": "eur_per_kg_edible", "low (band lower edge)": "price_band_lo",
                   "high (band upper edge)": "price_band_hi"}


def with_price(df, scenario="central"):
    """Recompute every per-€ metric for a price scenario (central price or the lower/upper band edge)."""
    col = PRICE_SCENARIOS[scenario]
    d = df.copy()
    price = d[col].where(d[col].notna(), d.eur_per_kg_edible)
    d["eur_per_kg_used"] = price
    d["kcal_per_eur"] = d.kcal_100g_purchased * 10 / price
    d["protein_per_eur"] = d.protein_100g_purchased * 10 / price
    d["useful_protein_per_eur"] = d.protein_100g_purchased * d.quality_factor * 10 / price
    d["carb_per_eur"] = d.carb_100g_purchased * 10 / price
    d["eur_per_1000kcal"] = 1000 / d.kcal_per_eur
    return d


# ---------------------------------------------------------------- Pareto analysis (PLAN A.3)
def pareto_mask(values, maximize):
    """Boolean mask of non-dominated rows. values: (n, k) array; maximize: k booleans.

    Row i is dominated if some row j is ≥ on every objective and > on at least one (after orienting
    every objective as 'larger is better'). Rows containing NaN are never on the front.
    """
    v = np.asarray(values, dtype=float) * np.where(maximize, 1.0, -1.0)
    ok = ~np.isnan(v).any(axis=1)
    mask = np.zeros(len(v), dtype=bool)
    idx = np.flatnonzero(ok)
    w = v[idx]
    for a, i in enumerate(idx):
        dominated = np.any(np.all(w >= w[a], axis=1) & np.any(w > w[a], axis=1))
        mask[i] = not dominated
    return mask


def pareto_ranks(values, maximize):
    """Dominance depth: 1 = Pareto front, 2 = front after removing rank 1, … ; NaN rows get 0."""
    v = np.asarray(values, dtype=float)
    ranks = np.zeros(len(v), dtype=int)
    remaining = ~np.isnan(v).any(axis=1)
    r = 1
    while remaining.any():
        sub = np.flatnonzero(remaining)
        m = pareto_mask(v[sub], maximize)
        ranks[sub[m]] = r
        remaining[sub[m]] = False
        r += 1
    return ranks


def front(df, cols, maximize=None):
    """Rows of df on the Pareto front of the given metric columns (directions from METRICS by default)."""
    maximize = maximize or [METRICS[c][2] for c in cols]
    return df[pareto_mask(df[cols].to_numpy(), maximize)]


# ---------------------------------------------------------------- composite indices (PLAN A.4; hypotheses!)
NORMALIZATIONS = {
    "log": "Log-ratio: min-max on log scale. Twice as good counts the same anywhere on the scale (ratio metrics)",
    "percentile": "Percentile rank: robust to outliers, but discards how big differences are",
    "minmax": "Linear min-max: proportional, but one extreme food (e.g. split peas) squeezes everyone else",
}


def normalize(s, higher_is_better=True, method="percentile"):
    """Map a metric to (0.01, 1], 1 = best, using one of NORMALIZATIONS."""
    x = s.astype(float)
    if method == "log":
        v = np.log(x.where(x > 0))           # zero/negative values (e.g. no protein) → worst
        if not higher_is_better:
            v = -v
        lo, hi = v.min(), v.max()
        out = ((v - lo) / (hi - lo) if hi > lo else v * 0 + 1).fillna(0)
        return out.clip(lower=0.01)
    if not higher_is_better:
        x = -x
    if method == "percentile":
        out = x.rank(pct=True)
    elif method == "minmax":
        lo, hi = x.min(), x.max()
        out = (x - lo) / (hi - lo) if hi > lo else x * 0 + 1
    else:
        raise ValueError(method)
    return out.clip(lower=0.01)  # keep the geometric mean defined


def composite(df, weights, method="percentile"):
    """Weighted geometric mean of normalized metrics: Π x_i^(w_i / Σw). weights: {metric_column: weight ≥ 0}.

    This is the S_bulk family from the handoff (PROJECT.md §4). The geometric mean penalizes a food that is
    terrible on any weighted metric, so a single extreme value cannot dominate. Rows with a NaN in a
    weighted metric get NaN.
    """
    w = {k: float(v) for k, v in weights.items() if v and float(v) > 0}
    if not w:
        raise ValueError("at least one positive weight is needed")
    total = sum(w.values())
    log_sum = 0.0
    for col, wi in w.items():
        hib = METRICS[col][2]
        if hib is None:
            raise ValueError(f"{col} has no direction; cannot be weighted")
        log_sum = log_sum + (wi / total) * np.log(normalize(df[col], hib, method))
    return np.exp(log_sum)


# Rule for presets: never weight two metrics that measure the same thing. kcal_100g_eaten and g_eaten_per_1000kcal
# are exact reciprocals (weighting both counts compactness twice); carb_100g_eaten mostly measures dryness.
PRESETS = {
    "Bulking: balanced": {"kcal_per_eur": 1, "useful_protein_per_eur": 1, "useful_protein_100g_eaten": 1,
                          "g_eaten_per_1000kcal": 1},
    "Bulking: cheapest calories": {"kcal_per_eur": 3, "useful_protein_per_eur": 1, "g_eaten_per_1000kcal": 1},
    "Bulking: compact food": {"g_eaten_per_1000kcal": 3, "kcal_per_eur": 1, "useful_protein_100g_eaten": 1},
    "Protein on a budget": {"useful_protein_per_eur": 3, "useful_protein_per_1000kcal": 1},
    "Price doesn't matter": {"useful_protein_100g_eaten": 1, "g_eaten_per_1000kcal": 1},
    "Endurance carbs on a budget": {"carb_per_eur": 3, "useful_protein_per_eur": 1, "g_eaten_per_1000kcal": 1},
    "Hybrid: bulk + endurance fuel": {"kcal_per_eur": 1, "useful_protein_per_eur": 1, "carb_per_eur": 1,
                                      "useful_protein_100g_eaten": 1, "g_eaten_per_1000kcal": 1},
    "Cutting: filling protein on a budget": {"useful_protein_per_1000kcal": 3, "useful_protein_per_eur": 1,
                                             "fullness_g_per_1000kcal": 1},
    "Everyday budget": {"kcal_per_eur": 1, "useful_protein_per_eur": 1},
}


# ---------------------------------------------------------------- ranking comparison (PLAN A.7)
def compare_rankings(a, b, k=10):
    """Spearman rank correlation and top-k overlap between two score Series (higher = better)."""
    j = pd.concat([a, b], axis=1).dropna()
    rho = j.iloc[:, 0].rank().corr(j.iloc[:, 1].rank())
    top_a = set(j.iloc[:, 0].nlargest(k).index)
    top_b = set(j.iloc[:, 1].nlargest(k).index)
    return {"spearman": rho, f"top{k}_overlap": len(top_a & top_b) / k, "n": len(j)}
