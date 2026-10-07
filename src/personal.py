"""Person-specific food ranking (owner comments 2026-10-07: 'rankings should change with the person').

Every food is judged as a 100 kcal portion against the PERSON's targets (src/targets.py), and the components are
weighted by the person's goal (config/target_rules.yaml → presets.<goal>.personal_weights) and price priority:

  N  nutrient score of 100 kcal: 100 × (mean adequacy − mean excess), exactly the Meal Nutrient Score
     (src/meals.py) of a 100 kcal 'meal' of that food: 20 items (protein, protein quality, fibre, 17 vitamins and
     minerals) capped at 1, minus excess over free sugars, saturated fat, sodium → nutrient density vs YOUR needs
  P  useful protein per 100 kcal (g; protein × DIAAS)          higher is better
  K  carbohydrate share of energy (%)                          higher is better (endurance, race week)
  C  cost of 100 kcal (€, chosen country)                      lower is better; weight × 0 if price does not matter
  V  food mass per 100 kcal (g eaten)                          gaining: lower is better (compact, easy to eat more)
                                                               losing: higher is better (filling)
  score = 100 × Π pct_k ^ (w_k / Σw)       pct = percentile rank among the shown foods (0–1, 1 = best)

A weighted geometric mean, so a food must be decent on every weighted component. A second, independent column comes
from the optimizer: the value of the food's nutrients at the shadow prices of the person's optimal diet ÷ its price
(100 % = worth exactly its price; see optimizer.Solution.food_value).
"""
import numpy as np
import pandas as pd

from src import meals as ML
from src import optimizer as O
from src.targets import RULES

COMPONENTS = {  # key: (label, unit, higher is better (None = depends on goal), formula shown to the user)
    "N": ("Nutrient score of 100 kcal", "0–100", True,
          "100 × (mean of 20 adequacy items − mean of 3 excess items) for a 100 kcal portion vs your daily targets"),
    "P": ("Useful protein per 100 kcal", "g", True, "protein × min(DIAAS, 100)/100 ÷ kcal × 100"),
    "K": ("Energy from carbohydrate", "%", True, "4 × carbohydrate ÷ kcal × 100"),
    "C": ("Cost of 100 kcal", "€", False, "price per g eaten × grams in 100 kcal"),
    "V": ("Food mass per 100 kcal", "g", None, "100 ÷ kcal per g eaten"),
}
DEFAULT_WEIGHTS = {"N": 2, "P": 0.5, "K": 0, "C": 1, "V": 0}


def weights(prof):
    """Goal weights from config, price weight × the profile's cost priority; V's sign from the goal direction."""
    pre = RULES["presets"][prof.goal]
    w = dict(DEFAULT_WEIGHTS, **pre.get("personal_weights", {}))
    w["C"] = w["C"] * float((prof.priorities or {}).get("cost", 1))
    volume_higher_better = pre["energy"]["mode"] == "deficit"     # losing: filling foods; otherwise compact
    return {k: v for k, v in w.items() if v}, volume_higher_better


def components(t, res):
    """Per-food components (index = food_id) for a food table t from optimizer.food_table()."""
    enc, lim, _ = ML.meal_items(res, 100.0)
    g100 = 100.0 / t.kcal.replace(0, np.nan)                     # grams eaten that give 100 kcal
    ade, aa = [], []
    for it in enc:
        a = (ML._coef(t, it.key) * g100 / it.target).clip(upper=1)
        (aa if it.key.startswith("aa:") else ade).append(a)
    ade.insert(1, pd.concat(aa, axis=1).min(axis=1))             # protein quality = most limiting amino acid
    exc = [((ML._coef(t, it.key) * g100 / it.target) - 1).clip(lower=0, upper=1) for it in lim]
    n = 100 * (pd.concat(ade, axis=1).mean(axis=1) - pd.concat(exc, axis=1).mean(axis=1))
    return pd.DataFrame({"name": t.name, "group": t.group, "N": n.clip(lower=0), "P": t.useful_protein * g100,
                         "K": 4 * t.carb / t.kcal * 100, "C": t.eur * g100, "V": g100})


def rank(t, res, prof, solution=None):
    """Personal ranking table (best first) with components, percentiles, score and the optimizer value."""
    w, v_up = weights(prof)
    c = components(t, res)
    pct = pd.DataFrame(index=c.index)
    for k in w:
        hib = COMPONENTS[k][2] if COMPONENTS[k][2] is not None else v_up
        pct[k] = c[k].rank(pct=True, ascending=hib)
    tot = sum(w.values())
    c["score"] = 100 * np.exp(sum(w[k] / tot * np.log(pct[k].clip(lower=1e-3)) for k in w))
    if solution is not None and solution.status == "optimal" and len(solution.food_value):
        coef = t.eur if solution.spec.objective == "cost" else pd.Series(1.0, index=t.index)
        c["optimizer value %"] = 100 * solution.food_value.reindex(t.index) / coef
        c["in optimal diet (g)"] = solution.foods.g_eaten.reindex(t.index).fillna(0)
    c = c.sort_values("score", ascending=False)
    c.insert(0, "rank", range(1, len(c) + 1))
    return c, w, v_up


def formula_text(w, v_up):
    """Human-readable formula with the actual weights (shown next to the ranking)."""
    tot = sum(w.values())
    parts = [f"{COMPONENTS[k][0]}{' (higher better)' if k == 'V' and v_up else ' (lower better)' if k == 'V' else ''}"
             f"^{w[k] / tot:.2f}" for k in w]
    return "score = 100 × " + " × ".join(f"pct({p.split('^')[0]})^{p.split('^')[1]}" for p in parts)
