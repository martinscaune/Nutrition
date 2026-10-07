"""Export a person-specific food ranking + nutrition table and an AI brief (for recipe/meal planning by an LLM).

Produces:
  foods_ranked.csv  one row per food: composite score and rank, per-metric ranks, nutrition (eaten + purchased),
                    protein quality, prices, how the food is bought/eaten, data grades
  optimal_diet.csv  cheapest diet meeting all targets + amino acids (nutritional skeleton for the menu)
  brief.md          profile, daily targets (with sources), safeguards, baseline diet, column dictionary, caveats, prompt

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
    "sat_fat_g_100g_eaten": ("sat_fat_100g_eaten", "Saturated fat per 100 g eaten (g)"),
    "sodium_mg_100g_eaten": ("sodium_mg_100g_eaten", "Sodium per 100 g eaten (mg), before any added salt"),
    "calcium_mg_100g_eaten": ("calcium_mg_100g_eaten", "Calcium per 100 g eaten (mg)"),
    "iron_mg_100g_eaten": ("iron_mg_100g_eaten", "Iron per 100 g eaten (mg)"),
    "zinc_mg_100g_eaten": ("zinc_mg_100g_eaten", "Zinc per 100 g eaten (mg)"),
    "magnesium_mg_100g_eaten": ("magnesium_mg_100g_eaten", "Magnesium per 100 g eaten (mg)"),
    "potassium_mg_100g_eaten": ("potassium_mg_100g_eaten", "Potassium per 100 g eaten (mg)"),
    "selenium_ug_100g_eaten": ("selenium_ug_100g_eaten", "Selenium per 100 g eaten (µg)"),
    "iodine_ug_100g_eaten": ("iodine_ug_100g_eaten", "Iodine per 100 g eaten (µg); blank = unknown"),
    "vitamin_a_ug_re_100g_eaten": ("vitamin_a_ug_re_100g_eaten", "Vitamin A per 100 g eaten (µg retinol equivalents)"),
    "retinol_ug_100g_eaten": ("retinol_ug_100g_eaten", "Preformed vitamin A (retinol) per 100 g eaten (µg); upper limit 3000 µg/day"),
    "vitamin_d_ug_100g_eaten": ("vitamin_d_ug_100g_eaten", "Vitamin D per 100 g eaten (µg)"),
    "vitamin_e_mg_100g_eaten": ("vitamin_e_mg_100g_eaten", "Vitamin E (α-tocopherol) per 100 g eaten (mg)"),
    "thiamin_mg_100g_eaten": ("thiamin_mg_100g_eaten", "Thiamin (B1) per 100 g eaten (mg), after cooking losses"),
    "riboflavin_mg_100g_eaten": ("riboflavin_mg_100g_eaten", "Riboflavin (B2) per 100 g eaten (mg)"),
    "niacin_mg_ne_100g_eaten": ("niacin_mg_ne_100g_eaten", "Niacin per 100 g eaten (mg niacin equivalents)"),
    "vitamin_b6_mg_100g_eaten": ("vitamin_b6_mg_100g_eaten", "Vitamin B6 per 100 g eaten (mg)"),
    "folate_ug_100g_eaten": ("folate_ug_100g_eaten", "Folate per 100 g eaten (µg, natural food folate)"),
    "vitamin_b12_ug_100g_eaten": ("vitamin_b12_ug_100g_eaten", "Vitamin B12 per 100 g eaten (µg)"),
    "vitamin_c_mg_100g_eaten": ("vitamin_c_mg_100g_eaten", "Vitamin C per 100 g eaten (mg), after cooking losses"),
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
         "### Vitamins, minerals, fibre, sodium (EFSA adult reference values)\n\n", res.micro_markdown(), "\n",
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
         "7. Show a daily total of kcal, protein, carbohydrate, fat and cost, and how far it is from the targets.\n",
         "8. Meet the vitamin/mineral minimums marked 'yes' on average over the week (use the per-100 g columns); keep "
         "under the maximums (e.g. retinol from liver, sodium, saturated fat). Vitamin D and iodine come mainly from "
         "sunlight/supplements and iodised salt; note them but do not force them with food.\n\n",
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
         "- Not medical advice. Vitamins and minerals are checked against EFSA adult values; cooking losses are "
         "applied where a USDA raw/cooked pair exists. Taste and meal structure are up to you, the planner.\n\n",
         "## Ready-to-paste prompt\n```\n",
         f"You are a meal planner. Using ONLY foods from the attached foods_ranked.csv (plus vegetables, herbs and "
         f"spices for flavour), create a 7-day meal plan with recipes for {prof.name.split('(')[0].strip()}. "
         f"Follow every rule in this brief, especially the daily targets ({t['energy'].value:,.0f} kcal, "
         f"{t['protein'].value:.0f} g protein, {t['carbohydrate'].value:.0f} g carbohydrate). Prefer higher-ranked "
         "foods, keep it varied and tasty, list grams as eaten and as bought, and give the daily totals and cost.\n```\n"]
    return "".join(L)


def zip_bytes(csv_text, brief_text, diet_csv=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("foods_ranked.csv", csv_text)
        z.writestr("brief.md", brief_text)
        if diet_csv:
            z.writestr("optimal_diet.csv", diet_csv)
    return buf.getvalue()


def optimal_diet(prof, quality="diaas", price_scenario="central", exclude=()):
    """Cheapest (or, for price-insensitive profiles, lightest) diet meeting the person's targets (src/optimizer.py)."""
    from src import optimizer as O
    t = O.food_table(quality, price_scenario, exclude=exclude)
    spec, _ = O.spec_from_profile(prof)
    sol = O.solve(t, spec)
    if sol.status != "optimal":
        return None, sol, spec
    d = sol.foods.reset_index().rename(columns={"name": "food", "cost_eur": "cost_eur_per_day", "kcal_total": "kcal",
                                                "protein_total": "protein_g", "carb_total": "carb_g",
                                                "fat_total": "fat_g", "free_sugars_total": "free_sugars_g",
                                                "fibre_total": "fibre_g"})
    d["g_bought"] = d.g_bought.round(0)
    d["g_eaten"] = d.g_eaten.round(0)
    return d, sol, spec


def diet_section(d, sol, spec):
    if d is None:
        return ("\n## Optimal baseline diet\nNo diet meets all targets with the current food list; conflicting targets: "
                + ", ".join(sol.conflicts.constraint) + "\n")
    tot = sol.totals.set_index("nutrient").diet
    rows = "".join(f"| {r.food} | {r.g_eaten:,.0f} | {r.g_bought:,.0f} | {r.cost_eur_per_day:.2f} | {r.kcal:,.0f} | "
                   f"{r.protein_g:.0f} |\n" for r in d.itertuples())
    binding = ", ".join(b for b in sol.binding.constraint if not b.startswith("energy share")) if len(sol.binding) else "–"
    goal = "lowest cost" if spec.objective == "cost" else "least food mass"
    return ("\n## Optimal baseline diet (attached as `optimal_diet.csv`)\n"
            f"The {goal} combination of foods that meets every daily target, every essential amino acid and the "
            "safeguards (computed by linear programming). **Use it as the nutritional skeleton, not as the menu**: it "
            "is deliberately monotonous. Turn it into varied, tasty meals, swap foods for similar ones when needed "
            "(e.g. one legume for another, one grain for another), and keep the daily totals close.\n\n"
            "| food | g eaten | g bought | €/day | kcal | protein g |\n|---|---|---|---|---|---|\n" + rows +
            f"\n**Totals:** {tot.kcal:,.0f} kcal, protein {tot.protein:.0f} g, carbohydrate {tot.carb:.0f} g, fat "
            f"{tot.fat:.0f} g, fibre {tot.fibre:.0f} g; €{sol.cost_eur:.2f}/day; {sol.mass_g:,.0f} g of food eaten. "
            "It also meets every enforced vitamin/mineral minimum and maximum (v2.0).\n"
            f"Constraints that shape it most: {binding}. Plant proteins in it complement each other (grains supply the "
            "sulfur amino acids legumes lack and legumes the lysine grains lack), so keep both in each day.\n")


def build_bundle(prof, preset=None, roles=("core", "ingredient"), quality="diaas", price_scenario="central",
                 weights=None, groups=None, exclude=()):
    """Everything for the AI export: ranked foods, optimal baseline diet, brief (with the diet section)."""
    if isinstance(prof, (str, Path)):
        prof = load_profile(prof)
    out, brief, res = build(prof, preset, roles, quality, price_scenario, weights, groups)
    d, sol, spec = optimal_diet(prof, quality, price_scenario, exclude)
    marker = "## How the ranking was made"
    brief = brief.replace(marker, diet_section(d, sol, spec) + "\n" + marker)
    brief = brief.replace("Using ONLY foods from the attached foods_ranked.csv",
                          "Starting from the attached optimal_diet.csv (nutritional skeleton) and using ONLY foods from "
                          "the attached foods_ranked.csv")
    return {"foods": out, "brief": brief, "diet": d, "targets": res}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=str(ROOT / "config/profiles/owner.yaml"))
    ap.add_argument("--preset", default=None, choices=list(M.PRESETS), help="default: the goal's ranking preset")
    ap.add_argument("--quality", default="diaas", choices=list(M.QUALITY))
    ap.add_argument("--include", default="core,ingredient", help="roles to include, comma-separated")
    args = ap.parse_args()
    bundle = build_bundle(args.profile, args.preset, tuple(args.include.split(",")), args.quality)
    out, brief, diet = bundle["foods"], bundle["brief"], bundle["diet"]
    slug = re.sub(r"[^a-z0-9]+", "_", Path(args.profile).stem.lower())
    d = ROOT / "exports" / f"{slug}_{dt.date.today().isoformat()}"
    d.mkdir(parents=True, exist_ok=True)
    csv_text = out.to_csv(index=False)
    (d / "foods_ranked.csv").write_text(csv_text)
    (d / "brief.md").write_text(brief)
    diet_csv = diet.to_csv(index=False) if diet is not None else None
    if diet_csv:
        (d / "optimal_diet.csv").write_text(diet_csv)
    (d / "export.zip").write_bytes(zip_bytes(csv_text, brief, diet_csv))
    print(f"wrote {d}/ (foods_ranked.csv: {len(out)} foods, optimal_diet.csv, brief.md, export.zip)")


if __name__ == "__main__":
    main()
