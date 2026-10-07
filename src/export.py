"""Export a person-specific food ranking + nutrition table and an AI brief (for recipe/meal planning by an LLM).

Produces:
  foods_ranked.csv  one row per food: composite score and rank, per-metric ranks, nutrition (eaten + purchased),
                    protein quality, prices, how the food is bought/eaten, data grades
  optimal_diet.csv  cheapest diet meeting all targets + amino acids (mathematical minimum; monotonous)
  realistic_diet.csv  cheapest diet under realistic limits (≤ 400 g per food, legumes ≤ 500 g, ≥ 2 sources per nutrient,
                    appetite ceiling), split into ≥ 4 meals (each ≥ 0.4 g/kg protein, 20–35 % of energy)
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
from src import optimizer as O  # noqa: E402
from src.targets import RULES, compute, load_profile  # noqa: E402

RANK_METRICS = ["kcal_per_eur", "useful_protein_per_eur", "carb_per_eur", "useful_protein_100g_eaten",
                "kcal_100g_eaten", "useful_protein_per_1000kcal", "g_eaten_per_1000kcal"]

COLUMNS = {  # output column: (source column or None, description for the AI)
    "rank": (None, "Rank of everyday (core) foods by the person-specific score (1 = best fit); blank for ingredients/snacks/supplements"),
    "score": ("score", "Person-specific score 0–1 (see 'How the ranking was made'; or the chosen composite weighting)"),
    "food_id": ("food_id", "Stable identifier"),
    "food": ("name_en", "Food name (English)"),
    "food_lv": ("name_lv", "Food name (Latvian)"),
    "group": ("group", "Food group"),
    "role": ("role", "core = everyday food; ingredient = use sparingly (oil, sugar, flour…); snack; supplement"),
    "bought_as": ("purchase_state", "How it is bought (dry, raw, canned, ready…)"),
    "eaten_as": ("eaten_state", "How the 'per 100 g eaten' values assume it is prepared: boiled/cooked in unsalted water "
                                "with no added fat unless stated (fat and salt you add are extra)"),
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
    "limiting_amino_acid": ("limiting_aa", "Amino acid that limits protein quality. Combine foods with different limits in the same day: LYS-limited grains + SAA-limited legumes, e.g. rice + lentils, rye bread + pea soup, buckwheat + beans; or add any milk/egg/meat/fish"),
    "price_eur_per_kg_edible": ("eur_per_kg_used", "Price per kg of edible food AS BOUGHT (dry/raw state, EUR, chosen country). "
                                "Cost of a portion = grams as bought × price / 1000 (see the worked example in brief.md)"),
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
    "ala_g_100g_eaten": ("ala_g_100g_eaten", "ALA, plant omega-3 fatty acid, per 100 g eaten (g)"),
    "epa_g_100g_eaten": ("epa_g_100g_eaten", "EPA, fish omega-3, per 100 g eaten (g); 0 for plant foods, blank = unknown (meat/dairy: negligible)"),
    "dha_g_100g_eaten": ("dha_g_100g_eaten", "DHA, fish omega-3, per 100 g eaten (g)"),
    "grade_composition": ("comp_grade", "Data quality A/B/C (C = proxy/estimate)"),
    "grade_protein_quality": ("digest_grade", "Data quality of DIAAS A/B/C"),
    "grade_price": ("price_grade", "Data quality of price A/B/C"),
    "flags": ("flags", "Data notes"),
}


def build(profile_path, preset=None, roles=("core", "ingredient"), quality="diaas",
          price_scenario="central", weights=None, groups=None, country="LV"):
    """Return (foods_ranked DataFrame, brief markdown, targets Result). Foods the person dislikes are left out."""
    from src.prices.countries import LV_ONLY
    prof = load_profile(profile_path) if isinstance(profile_path, (str, Path)) else profile_path
    res = compute(prof)
    df = M.with_price(M.with_quality(M.load(), quality), price_scenario, country)
    df = df[~df.food_id.isin(list(prof.dislikes or [])) & ~(df.food_id.isin(LV_ONLY) & (country != "LV"))]
    foods = pd.read_csv(ROOT / "data/foods/foods.csv")[["food_id", "purchase_state", "eaten_state"]]
    df = df.merge(foods, on="food_id", how="left")
    df = df[df.role.isin(roles) & df.eur_per_kg_used.notna() & df.kcal_100g_purchased.notna()]
    if groups:
        df = df[df.group.isin(groups)]
    personal = preset is None and weights is None
    if personal:   # default: person-specific score (src/personal.py) for core foods
        from src import personal as PS
        t = O.food_table(quality, price_scenario, roles=["core"], exclude=tuple(prof.dislikes or ()), country=country)
        r, w, v_up = PS.rank(t, res, prof)
        df = df.assign(score=df.food_id.map(r.score / 100), _core=df.role.eq("core") & df.food_id.isin(r.index))
        preset = "personal"
        w = {"_formula": PS.formula_text(w, v_up)}
    else:
        preset = preset or RULES["presets"][prof.goal].get("ranking_preset", "Bulking: balanced")
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
    brief = _brief(prof, res, w, preset if not weights else "custom", quality, price_scenario, out, country)
    return out, brief, res


def _price_example(out, country):
    r = out.set_index("food_id")
    if "rice_white" not in r.index:
        return ""
    x = r.loc["rice_white"]
    return (f"**Reading prices (worked example, {country}):** white rice costs €{x.price_eur_per_kg_edible:.2f} per kg *as "
            f"bought* (dry). 100 g dry rice therefore costs €{x.price_eur_per_kg_edible / 10:.2f} and becomes "
            f"{100 * x.cooked_mass_per_bought_mass:.0f} g cooked (`cooked_mass_per_bought_mass` = "
            f"{x.cooked_mass_per_bought_mass:.2f}). So 265 g of cooked rice on a plate ≈ 100 g bought ≈ "
            f"€{x.price_eur_per_kg_edible / 10:.2f}. Always convert eaten → bought before pricing.\n\n")


def _sources_table(prof, res, country):
    """Top-3 sources of each enforced nutrient per realistic portion (gives the planner ≥ 2 options for each)."""
    from src import optimizer as O
    t = O.food_table(roles=["core"], exclude=prof.dislikes or (), country=country)
    st = O.nutrient_status(t, pd.Series(dtype=float), res)
    st = st[st.status.eq("below min")]
    return ("### Where each nutrient comes from (best 3 sources per portion; use at least 2 different ones)\n\n"
            "| nutrient | daily minimum | sources (portion → amount) |\n|---|---|---|\n" +
            "".join(f"| {r.nutrient} | {r.minimum:.3g} {r.unit} | {r['add for more']} |\n" for _, r in st.iterrows()) + "\n")


def _brief(prof, res, w, preset, quality, price_scenario, out, country="LV"):
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
         f"- Goal: {RULES['presets'][prof.goal]['label']}\n"
         + (f"- Never use (dislikes): {', '.join(prof.dislikes)}\n" if prof.dislikes else "")
         + (f"- Appetite ceiling: at most {prof.appetite_max_g:,.0f} g of food per day\n" if prof.appetite_max_g else "")
         + "\n",
         "## Daily targets (hit these on average over a day)\n\n", res.to_markdown().split("\n\n", 1)[1], "\n",
         "### Vitamins, minerals, fibre, omega-3, sodium (EFSA adult reference values)\n\n", res.micro_markdown(), "\n",
         _sources_table(prof, res, country),
         "## Rules for the meal plan\n",
         f"1. Energy ≈ {t['energy'].value:,.0f} kcal/day; protein ≈ {t['protein'].value:.0f} g "
         f"(at least {t['protein'].low or t['protein'].value:.0f} g); carbohydrate ≈ {t['carbohydrate'].value:.0f} g; "
         f"fat {t['fat'].low:.0f}–{t['fat'].high:.0f} g; free sugars below {t['free sugars (max)'].value:.0f} g.\n",
         f"2. Spread protein over at least 4 meals of about {meals_p:.0f} g each (0.4 g/kg per meal; schoenfeld2018).\n",
         "3. Prefer foods ranked higher in `foods_ranked.csv` (column `rank`), but variety and taste matter: use "
         "at least 8–10 different foods per day, no single food above ~30 % of energy or ~400 g eaten, legumes at most "
         "~500 g cooked per day, and no non-staple food on more than 5 days a week (staples that may appear daily: "
         "oats, bread, rice/grains, potatoes, milk/kefir, eggs, cabbage/carrots, oil).\n",
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
         "sunlight/supplements and iodised salt; note them but do not force them with food.\n",
         "9. Omega-3: EPA + DHA ≥ 250 mg/day as a weekly average ≈ 1–2 fatty-fish meals a week (mackerel, herring, "
         "salmon, sprats); ALA from rapeseed oil, walnuts or flaxseed (flaxseed and chia are good but unpriced here).\n",
         "10. Cooking: nutrition values assume foods boiled/cooked in unsalted water with no added fat. Count every "
         "gram of oil/butter you add, and keep added salt low (sodium is already near the limit in canned/processed foods).\n",
         "11. Fermented dairy: kefir and plain yogurt are nutritionally equivalent to milk and may replace it freely "
         "(they cost more per nutrient, which is the only reason the cost-optimal diet prefers milk).\n\n",
         _price_example(out, country),
         "## How the ranking was made\n",
         (("Person-specific score: every food judged as a 100 kcal portion against this person's targets, weighted by "
           f"goal and price priority: `{w['_formula']}` (pct = percentile rank among the foods; components: nutrient "
           "score of 100 kcal, useful protein per 100 kcal, carbohydrate share, cost of 100 kcal, food mass per 100 kcal)")
          if preset == "personal" else
          f"Weighting preset **{preset}**: " + ", ".join(f"{M.METRICS[k][0]} ×{v:g}" for k, v in w.items())) +
         f". Protein quality: {M.QUALITY[quality]}. Price scenario: {price_scenario}. "
         "The score is a hypothesis-ranking for convenience, not a nutritional verdict.\n\n",
         "### Top 25 everyday foods under this weighting\n",
         ", ".join(f"{r.rank}. {r.food}" for r in top.itertuples()) + "\n\n",
         "## Column dictionary for foods_ranked.csv\n",
         "".join(f"- `{k}`: {d}\n" for k, (_, d) in COLUMNS.items()),
         "- `rank_<metric>`: rank of the food on that single metric (1 = best)\n\n",
         "## Caveats\n",
         "- Prices: Latvian retail, collected 2026-10-06 (official CSP 12-month means + Cenu Depo shop prices); "
         "personal use only." + ("" if country == "LV" else f" Converted to {country} with Eurostat food price level "
         "indices by category (approximate; product-level prices differ).") + "\n",
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


def zip_bytes(csv_text, brief_text, diet_csv=None, realistic_csv=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("foods_ranked.csv", csv_text)
        z.writestr("brief.md", brief_text)
        if diet_csv:
            z.writestr("optimal_diet.csv", diet_csv)
        if realistic_csv:
            z.writestr("realistic_diet.csv", realistic_csv)
    return buf.getvalue()


def optimal_diet(prof, quality="diaas", price_scenario="central", exclude=(), country="LV", realistic=False):
    """Cheapest (or, for price-insensitive profiles, lightest) diet meeting the person's targets (src/optimizer.py).
    realistic=True adds the realistic limits and a split into meals (columns meal 1 … meal n)."""
    from src import optimizer as O
    from src import meals as ML
    t = O.food_table(quality, price_scenario, exclude=tuple(exclude) + tuple(prof.dislikes or ()), country=country)
    spec, _ = O.spec_from_profile(prof, realistic=realistic)
    sol = O.solve(t, spec)
    if sol.status != "optimal":
        return None, sol, spec
    if realistic:
        sp = ML.split_day(t, sol.foods.g_eaten, prof.mass_kg)
        sol.meal_split = sp
    d = sol.foods.reset_index().rename(columns={"name": "food", "cost_eur": "cost_eur_per_day", "kcal_total": "kcal",
                                                "protein_total": "protein_g", "carb_total": "carb_g",
                                                "fat_total": "fat_g", "free_sugars_total": "free_sugars_g",
                                                "fibre_total": "fibre_g"})
    d["g_bought"] = d.g_bought.round(0)
    d["g_eaten"] = d.g_eaten.round(0)
    if realistic and sol.meal_split is not None:
        d = d.merge(sol.meal_split.drop(columns="food"), left_on="food_id", right_index=True, how="left")
    return d, sol, spec


def diet_section(d, sol, spec, res=None, realistic=False):
    from src import optimizer as O
    if d is None:
        return (f"\n## {'Realistic' if realistic else 'Optimal baseline'} diet\nNo diet meets all targets with the "
                "current food list; conflicting targets: " + ", ".join(sol.conflicts.constraint) + "\n")
    if realistic:
        return _realistic_section(d, sol, res)
    tot = sol.totals.set_index("nutrient").diet
    rows = "".join(f"| {r.food} | {r.g_eaten:,.0f} | {r.g_bought:,.0f} | {r.cost_eur_per_day:.2f} | {r.kcal:,.0f} | "
                   f"{r.protein_g:.0f} |\n" for r in d.itertuples())
    binding = ", ".join(b for b in sol.binding.constraint if not b.startswith(O.INTERNAL_ROWS)) if len(sol.binding) else "–"
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


def _realistic_section(d, sol, res):
    from src import optimizer as O
    meals = [c for c in d.columns if c.startswith("meal ")]
    tot = sol.totals.set_index("nutrient").diet
    rows = "".join(f"| {r['food']} | {r['g_eaten']:,.0f} | " + " | ".join(f"{r[m]:.0f}" if pd.notna(r[m]) and r[m] else "" for m in meals)
                   + " |\n" for _, r in d.iterrows())
    head = "| food | g eaten/day | " + " | ".join(meals) + " |\n|---|---|" + "---|" * len(meals) + "\n"
    mt = ""
    if meals:
        kc = {m: (d[m] / d.g_eaten.replace(0, 1) * d.kcal).sum() for m in meals}
        pr = {m: (d[m] / d.g_eaten.replace(0, 1) * d.protein_g).sum() for m in meals}
        mt = "| per meal | " + " | ".join(meals) + " |\n|---|" + "---|" * len(meals) + "\n" + \
             "| kcal | " + " | ".join(f"{kc[m]:,.0f}" for m in meals) + " |\n" + \
             "| protein g | " + " | ".join(f"{pr[m]:.0f}" for m in meals) + " |\n\n"
    cont = ""
    if res is not None:
        ns = O.nutrient_status(O.food_table(), d.set_index("food_id").g_eaten, res)
        c = ns[ns.nutrient.str.contains("per week")]
        cont = "Contaminants per week (data incomplete): " + "; ".join(
            f"{r.nutrient.replace(' (per week)', '')} {r.diet:.0f} of {r.maximum:.0f} {r.unit} tolerable" for _, r in c.iterrows()) + ".\n"
    return ("\n## Realistic diet, split into meals (attached as `realistic_diet.csv`)\n"
            "Cheapest day that meets every target under realistic limits: at most 400 g of any food, legumes + soy ≤ 500 g, "
            "no food above 20 % of energy, every vitamin/mineral from at least 2 foods (none supplies > 60 %), "
            "and the person's appetite ceiling. The split gives ≥ 4 meals, each with ≥ 0.4 g protein per kg body mass and "
            "20–35 % of the day's energy. **The split is arithmetic, not cuisine**: regroup foods into dishes that taste "
            "good, keeping each meal's protein and energy roughly as below.\n\n" + head + rows + "\n" + mt +
            f"**Totals:** {tot.kcal:,.0f} kcal, protein {tot.protein:.0f} g, carbohydrate {tot.carb:.0f} g, fat {tot.fat:.0f} g, "
            f"fibre {tot.fibre:.0f} g; €{sol.cost_eur:.2f}/day; {sol.mass_g:,.0f} g eaten. " + cont)


def build_bundle(prof, preset=None, roles=("core", "ingredient"), quality="diaas", price_scenario="central",
                 weights=None, groups=None, exclude=(), country="LV"):
    """Everything for the AI export: ranked foods, optimal and realistic diets, brief (with both diet sections)."""
    if isinstance(prof, (str, Path)):
        prof = load_profile(prof)
    out, brief, res = build(prof, preset, roles, quality, price_scenario, weights, groups, country)
    d, sol, spec = optimal_diet(prof, quality, price_scenario, exclude, country)
    dr, solr, specr = optimal_diet(prof, quality, price_scenario, exclude, country, realistic=True)
    marker = "## How the ranking was made"
    brief = brief.replace(marker, diet_section(d, sol, spec) + diet_section(dr, solr, specr, res, realistic=True)
                          + "\n" + marker)
    brief = brief.replace("Using ONLY foods from the attached foods_ranked.csv",
                          "Starting from the attached realistic_diet.csv (nutritional skeleton split into meals; "
                          "optimal_diet.csv is the cheaper but monotonous minimum) and using ONLY foods from "
                          "the attached foods_ranked.csv")
    return {"foods": out, "brief": brief, "diet": d, "realistic": dr, "targets": res}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=str(ROOT / "config/profiles/owner.yaml"))
    ap.add_argument("--preset", default=None, choices=list(M.PRESETS), help="default: the goal's ranking preset")
    ap.add_argument("--quality", default="diaas", choices=list(M.QUALITY))
    ap.add_argument("--include", default="core,ingredient", help="roles to include, comma-separated")
    ap.add_argument("--country", default="LV", help="price country (Eurostat code, e.g. LV, DK, NL)")
    args = ap.parse_args()
    bundle = build_bundle(args.profile, args.preset, tuple(args.include.split(",")), args.quality, country=args.country)
    out, brief, diet, real = bundle["foods"], bundle["brief"], bundle["diet"], bundle["realistic"]
    slug = re.sub(r"[^a-z0-9]+", "_", Path(args.profile).stem.lower())
    d = ROOT / "exports" / f"{slug}_{dt.date.today().isoformat()}"
    d.mkdir(parents=True, exist_ok=True)
    csv_text = out.to_csv(index=False)
    (d / "foods_ranked.csv").write_text(csv_text)
    (d / "brief.md").write_text(brief)
    diet_csv = diet.to_csv(index=False) if diet is not None else None
    real_csv = real.to_csv(index=False) if real is not None else None
    if diet_csv:
        (d / "optimal_diet.csv").write_text(diet_csv)
    if real_csv:
        (d / "realistic_diet.csv").write_text(real_csv)
    (d / "export.zip").write_bytes(zip_bytes(csv_text, brief, diet_csv, real_csv))
    print(f"wrote {d}/ (foods_ranked.csv: {len(out)} foods, optimal_diet.csv, realistic_diet.csv, brief.md, export.zip)")


if __name__ == "__main__":
    main()
