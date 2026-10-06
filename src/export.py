"""Export a person-specific food ranking + nutrition table and an AI brief (for recipe/meal planning by an LLM).

Produces:
  foods_ranked.csv  one row per food: composite score and rank, per-metric ranks, nutrition (eaten + purchased),
                    protein quality, prices, how the food is bought/eaten, data grades
  brief.md          profile, daily targets (with sources), safeguards, column dictionary, caveats, ready prompt

CLI:
    .venv/bin/python -m src.export --profile config/profiles/owner.yaml --preset "Bulking: balanced"
    → exports/<profile>_<date>/{foods_ranked.csv, brief.md, export.zip}
"""
import argparse
import datetime as dt
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import metrics as M  # noqa: E402
from src.targets import RULES, compute, load_profile  # noqa: E402

RANK_METRICS = ["kcal_per_eur", "useful_protein_per_eur", "carb_per_eur", "useful_protein_100g_eaten",
                "kcal_100g_eaten", "useful_protein_per_1000kcal", "g_eaten_per_1000kcal"]

COLUMNS = {  # output column: (source column or None, description for the AI)
    "rank": (None, "Rank of everyday (core) foods by composite score under the chosen weighting (1 = best fit); blank for ingredients/snacks/supplements"),
    "score": ("score", "Composite score 0–1 (weighted geometric mean of percentile-normalized metrics)"),
    "food_id": ("food_id", "Stable identifier"),
    "food": ("name_en", "Food name (English)"),
    "food_lv": ("name_lv", "Food name (Latvian)"),
    "group": ("group", "Food group"),
    "role": ("role", "core = everyday food; ingredient = use sparingly (oil, sugar, flour…); snack; supplement"),
    "bought_as": ("purchase_state", "How it is bought (dry, raw, canned, ready…)"),
    "eaten_as": ("eaten_state", "How the nutrition values 'per 100 g eaten' assume it is prepared"),
    "kcal_100g_eaten": ("kcal_100g_eaten", "Energy per 100 g as eaten (kcal)"),
    "protein_g_100g_eaten": ("protein_100g_eaten", "Protein per 100 g as eaten (g)"),
    "useful_protein_g_100g_eaten": ("useful_protein_100g_eaten", "Quality-adjusted protein per 100 g eaten (g) = protein × min(DIAAS,100)/100"),
    "carb_g_100g_eaten": ("carb_100g_eaten", "Available carbohydrate per 100 g eaten (g)"),
    "fat_g_100g_eaten": ("fat_100g_eaten", "Fat per 100 g eaten (g)"),
    "free_sugars_g_100g_eaten": ("free_sugars_100g_eaten", "Free (added) sugars per 100 g eaten (g); blank = unknown"),
    "fibre_g_100g_eaten": ("fibre_100g_eaten", "Dietary fibre per 100 g eaten (g)"),
    "kcal_100g_bought": ("kcal_100g_purchased", "Energy per 100 g as bought, edible part (kcal)"),
    "protein_g_100g_bought": ("protein_100g_purchased", "Protein per 100 g as bought, edible part (g)"),
    "cooked_mass_per_bought_mass": ("yield_eaten_per_purchased", "Eaten mass ÷ bought mass (e.g. 2.65 for rice: 100 g dry → 265 g cooked)"),
    "edible_portion": ("edible_portion", "Edible fraction of what is bought (bone/shell/peel removed)"),
    "diaas": ("diaas", "Protein quality score (DIAAS, FAO 2013 adult pattern; ≥100 = complete for adults)"),
    "limiting_amino_acid": ("limiting_aa", "Amino acid that limits protein quality; combine foods with different limits (e.g. LYS-limited grains + SAA-limited legumes)"),
    "price_eur_per_kg_edible": ("eur_per_kg_used", "Price per kg of edible food as bought (EUR, Latvia)"),
    "kcal_per_eur": ("kcal_per_eur", "Energy per euro"),
    "useful_protein_g_per_eur": ("useful_protein_per_eur", "Quality-adjusted protein per euro (g)"),
    "carb_g_per_eur": ("carb_per_eur", "Carbohydrate per euro (g)"),
    "g_eaten_per_1000kcal": ("g_eaten_per_1000kcal", "Grams of food (as eaten) needed for 1000 kcal: lower = more compact"),
    "grade_composition": ("comp_grade", "Data quality A/B/C (C = proxy/estimate)"),
    "grade_protein_quality": ("digest_grade", "Data quality of DIAAS A/B/C"),
    "grade_price": ("price_grade", "Data quality of price A/B/C"),
    "flags": ("flags", "Data notes"),
}


def build(profile_path, preset=None, roles=("core", "ingredient"), quality="diaas",
          price_scenario="central", weights=None, groups=None):
    """Return (foods_ranked DataFrame, brief markdown, targets Result)."""
    prof = load_profile(profile_path) if isinstance(profile_path, (str, Path)) else profile_path
    res = compute(prof)
    preset = preset or RULES["presets"][prof.goal].get("ranking_preset", "Bulking: balanced")
    df = M.with_price(M.with_quality(M.load(), quality), price_scenario)
    foods = pd.read_csv(ROOT / "data/foods/foods.csv")[["food_id", "purchase_state", "eaten_state"]]
    df = df.merge(foods, on="food_id", how="left")
    df = df[df.role.isin(roles) & df.eur_per_kg_used.notna() & df.kcal_100g_purchased.notna()]
    if groups:
        df = df[df.group.isin(groups)]
    w = weights or M.PRESETS[preset]
    if (prof.priorities or {}).get("cost", 1) == 0:  # price-insensitive profile: drop all per-€ weights
        w = {k: v for k, v in w.items() if "eur" not in k} or {"useful_protein_100g_eaten": 1, "kcal_100g_eaten": 1}
    # ranks are given to everyday (core) foods only; ingredients/snacks/supplements follow, unranked
    df = df.assign(score=M.composite(df, w), _core=df.role.eq("core"))
    df = df.sort_values(["_core", "score"], ascending=[False, False]).reset_index(drop=True)
    out = pd.DataFrame({k: (df[src] if src else None) for k, (src, _) in COLUMNS.items()})
    n_core = int(df._core.sum())
    out["rank"] = pd.array(list(range(1, n_core + 1)) + [pd.NA] * (len(df) - n_core), dtype="Int64")
    for m in RANK_METRICS:
        out[f"rank_{m}"] = df[m].rank(ascending=not M.METRICS[m][2], method="min").astype("Int64")
    out = out.round(3)
    brief = _brief(prof, res, w, preset if not weights else "custom", quality, price_scenario, out)
    return out, brief, res


def _brief(prof, res, w, preset, quality, price_scenario, out):
    t = res.targets
    today = dt.date.today().isoformat()
    meals_p = prof.mass_kg * 0.4
    top = out[out.role == "core"].head(25)
    L = [f"# Nutrition brief for an AI meal planner: {prof.name}\n\n",
         f"Generated {today} by the food-value project (`src/export.py`). Attached: `foods_ranked.csv`.\n\n",
         "## Person\n",
         f"- {prof.sex}, {prof.age:g} years, {prof.mass_kg:g} kg, {prof.height_cm:g} cm"
         + (f", target body mass {prof.target_mass_kg:g} kg" if prof.target_mass_kg else "") + "\n",
         f"- Training: {prof.modality}, about {prof.training.get('hours_per_week', 0):g} hours per week\n",
         f"- Goal: {RULES['presets'][prof.goal]['label']}\n\n",
         "## Daily targets (hit these on average over a day)\n\n", res.to_markdown().split("\n\n", 1)[1], "\n",
         "## Rules for the meal plan\n",
         f"1. Energy ≈ {t['energy'].value:,.0f} kcal/day; protein ≈ {t['protein'].value:.0f} g "
         f"(at least {t['protein'].low or t['protein'].value:.0f} g); carbohydrate ≈ {t['carbohydrate'].value:.0f} g; "
         f"fat {t['fat'].low:.0f}–{t['fat'].high:.0f} g; free sugars below {t['free sugars (max)'].value:.0f} g.\n",
         f"2. Spread protein over at least 4 meals of about {meals_p:.0f} g each (0.4 g/kg per meal; schoenfeld2018).\n",
         "3. Prefer foods ranked higher in `foods_ranked.csv` (column `rank`), but variety and taste matter: use "
         "at least 8–10 different foods per day and no single food above ~30 % of energy.\n",
         "4. Combine plant proteins with different `limiting_amino_acid` values in the same day (grains are "
         "lysine-limited, legumes are methionine+cysteine-limited; together they complement each other).\n",
         "5. Foods with role `ingredient` (oils, butter, sugar, flour…) are for cooking only: oil ≤ ~40 g/day, "
         "keep free sugars under the limit above.\n",
         "6. Give quantities in grams **as eaten** and the matching grams **as bought** "
         "(as bought = as eaten ÷ `cooked_mass_per_bought_mass`; for bone-in/peeled foods also ÷ `edible_portion`). "
         "Estimate the daily cost with `price_eur_per_kg_edible`.\n",
         "7. Show a daily total of kcal, protein, carbohydrate, fat and cost, and how far it is from the targets.\n\n",
         "## How the ranking was made\n",
         f"Weighting preset **{preset}**: " + ", ".join(f"{M.METRICS[k][0]} ×{v:g}" for k, v in w.items()) +
         f". Protein quality: {M.QUALITY[quality]}. Price scenario: {price_scenario}. "
         "The score is a hypothesis-ranking for convenience, not a nutritional verdict.\n\n",
         "### Top 25 everyday foods under this weighting\n",
         ", ".join(f"{r.rank}. {r.food}" for r in top.itertuples()) + "\n\n",
         "## Column dictionary for foods_ranked.csv\n",
         "".join(f"- `{k}`: {d}\n" for k, (_, d) in COLUMNS.items()),
         "- `rank_<metric>`: rank of the food on that single metric (1 = best)\n\n",
         "## Caveats\n",
         "- Prices: Latvian retail, collected 2026-10-06 (official CSP 12-month means + Cenu Depo shop prices); "
         "personal use only.\n",
         "- Composition mostly from the Danish Frida 5.5 database and USDA; grade C values are proxies.\n",
         "- Not medical advice. Fibre, sodium, vitamins and minerals are not yet optimized (planned v2.0): include "
         "vegetables and fruit for micronutrients even if they rank low here.\n\n",
         "## Ready-to-paste prompt\n```\n",
         f"You are a meal planner. Using ONLY foods from the attached foods_ranked.csv (plus vegetables, herbs and "
         f"spices for flavour), create a 7-day meal plan with recipes for {prof.name.split('(')[0].strip()}. "
         f"Follow every rule in this brief, especially the daily targets ({t['energy'].value:,.0f} kcal, "
         f"{t['protein'].value:.0f} g protein, {t['carbohydrate'].value:.0f} g carbohydrate). Prefer higher-ranked "
         "foods, keep it varied and tasty, list grams as eaten and as bought, and give the daily totals and cost.\n```\n"]
    return "".join(L)


def zip_bytes(csv_text, brief_text):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("foods_ranked.csv", csv_text)
        z.writestr("brief.md", brief_text)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=str(ROOT / "config/profiles/owner.yaml"))
    ap.add_argument("--preset", default=None, choices=list(M.PRESETS), help="default: the goal's ranking preset")
    ap.add_argument("--quality", default="diaas", choices=list(M.QUALITY))
    ap.add_argument("--include", default="core,ingredient", help="roles to include, comma-separated")
    args = ap.parse_args()
    out, brief, _ = build(args.profile, args.preset, tuple(args.include.split(",")), args.quality)
    slug = re.sub(r"[^a-z0-9]+", "_", Path(args.profile).stem.lower())
    d = ROOT / "exports" / f"{slug}_{dt.date.today().isoformat()}"
    d.mkdir(parents=True, exist_ok=True)
    csv_text = out.to_csv(index=False)
    (d / "foods_ranked.csv").write_text(csv_text)
    (d / "brief.md").write_text(brief)
    (d / "export.zip").write_bytes(zip_bytes(csv_text, brief))
    print(f"wrote {d}/ (foods_ranked.csv: {len(out)} foods, brief.md, export.zip)")


if __name__ == "__main__":
    main()
