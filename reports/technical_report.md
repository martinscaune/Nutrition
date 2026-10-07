# Quantitative food value for training: data, methods and first results

**Technical report, draft 4 (2026-10-07; v2.0 addendum in §4b, v2.1 in §4c, v2.2 in §4d).** Personal research project; not peer reviewed. Source keys refer to
[literature/SOURCES.md](../literature/SOURCES.md); detailed outputs are in the other files in `reports/`.

## Summary
We built a reproducible pipeline that (1) assembles composition, protein-quality and Latvian retail-price data for
106 foods, (2) derives sourced daily targets for different athletic goals, and (3) finds the cheapest (or least
bulky) combination of foods that meets every target, including each indispensable amino acid at the diet level.
For a 76 kg hybrid (triathlon + strength) athlete aiming to gain mass (3,300 kcal, 137 g protein, 380–532 g
carbohydrate), the minimum-cost day costs **€1.85** (Monte Carlo 5–95 %: €1.71–1.99) and is ≈ 99 % plant energy:
legumes plus grains, with sulfur amino acids and lysine as the binding constraints. Enforcing protein quality
per food (Σ protein × DIAAS) instead of per amino acid over the whole diet raises that cost by **31 %**; ignoring
quality leaves the diet **14 % short on lysine**. A conventional bodybuilding day meets the same targets at
€7.66 (≈ 4×). The cheapest diet is bulky (2.5 kg/day); the least bulky (0.8 kg) costs €7.50.

## 1. Question
How efficiently do foods, and combinations of foods, meet training-specific nutritional targets per euro and per
gram eaten, once protein *quality* and realistic constraints are taken into account? The work is computational
nutrition / diet optimization, not exercise physiology (PROJECT.md §1–§2).

## 2. Data
| Component | Source | Notes |
|---|---|---|
| Composition (106 foods, per 100 g) | Frida 5.5 (DTU, CC BY 4.0) primary; USDA SR Legacy fallback | Available carbohydrate and free sugars from Frida; mapping in `data/foods/composition_map.csv` |
| Eaten vs bought state | USDA raw↔cooked pairs: yield = protein_raw / protein_cooked | e.g. dry rice ×2.65, oat porridge ×5.2, chicken ×0.73 |
| Edible portion | USDA SR28 refuse % | bone, shell, peel |
| Amino acids | Frida/USDA profiles; 5 implausible profiles replaced (documented) | Plausibility check found USDA ground beef/yogurt Trp, tofu Cys, turkey Ile/Val, Frida split-pea Cys, Frida buckwheat protein |
| Digestibility | muleya2021 dataset (true ileal, per amino acid; human or pig) | 35 foods direct (grade A), 34 same-family proxy (B), 29 cross-family proxy (C) |
| Prices (Latvia) | CSP table PCC010m (official monthly means, 12-month average) for 71 foods; Cenu Depo shop prices (2026-10-06) for 28 | Cenu Depo ≈ 10 % below CSP on cross-checked foods; **Cenu Depo data are for personal use only** |

Every value carries a grade (A analytical/exact, B close proxy, C estimate) and a source.

## 3. Methods
**Protein quality.** DIAAS (fao2013) per food with the FAO 3+ y pattern (young-child pattern as sensitivity);
"useful protein" = protein × min(DIAAS, 100)/100 for food-level views only.

**Targets** (`config/target_rules.yaml`, `src/targets.py`). Resting energy: ten Haaf (tenhaaf2014) or Mifflin;
expenditure = REE × 1.5 + (MET − 1) × kg × training h/day (MET values are an assumption). Goal presets: surplus
0.25–0.5 % body mass/week (iraki2019), deficit 0.7 %/week (garthe2011); protein 1.6–2.2 g/kg for gain (morton2018),
2.3–3.1 g/kg lean mass in a deficit (helms2014), 1.4–2.0 for endurance (thomas2016); carbohydrate by training load
(thomas2016 Table 2); fat 20–35 % E (efsa2010f); free sugars < 10 % E (who2015). Conflicts are reported, not hidden.

**Food-level metrics** (`src/metrics.py`): energy, protein, useful protein and carbohydrate per 100 g eaten and per
euro; g eaten per 1,000 kcal; Pareto fronts; optional composite score (weighted geometric mean of normalized
metrics). The composite is treated as a convenience view because it depends on normalization (scenario D).

**Diet optimization** (`src/optimizer.py`). Linear programme (HiGHS), x = g eaten per food per day; minimize cost
(or mass, or a normalized mix). Constraints: energy ±2 %; protein ≥ target; for each indispensable amino acid,
Σ digestible supply ≥ FAO pattern × protein target (decision D9, handles complementarity); carbohydrate band; fat
band; free-sugar cap; per-food caps and ≤ 30 % of energy per food (judgment calls, `config/optimizer.yaml`).
Outputs include binding constraints (dual values), reduced costs, an elastic relaxation naming conflicting targets
when infeasible, near-optimal alternatives, an ε-constraint cost–mass front, and a "closest valid diet" mode that
changes a usual diet as little as possible (maillot2010).

**Robustness.** Price scenarios; protein pattern; weight and normalization sensitivity; safeguard/target sweeps;
Monte Carlo (300 runs: composition CV 5/10/20 % and digestibility CV 3/6/12 % by grade, prices uniform within their
bands); Frida vs USDA composition.

## 4. Results by hypothesis
| # | Hypothesis | Result | Where |
|---|---|---|---|
| H1 | Quality adjustment changes rankings | Yes for protein per €: ρ = 0.85, 7/10 top foods kept; wheat products fall (couscous 14th → 60th). Barely for protein per 100 g (ρ = 0.97) | v0.1 |
| H2 | Price changes rankings | Strongly: density vs per-€ ρ = 0.32 (protein), 0.06 (energy) | v0.1 |
| H3 | Goals differ | Yes in rankings (top-10 overlap 0–0.7 between goal presets) and diets (fat loss adds lean animal/dairy foods; price-insensitive → compact foods) | scenarios, v1.0 |
| H4 | Legumes/staples dominate cost metrics; animal foods a different region | Grains hold 7/10 of the calorie-per-€ top 10, legumes 5/10 of useful-protein-per-€; meat/fish 10/10 of protein density | v0.1 |
| H5 | Food mass is an independent constraint | Mass and cost almost uncorrelated (ρ = 0.06); diet front: 2.47 kg @ €1.85 ↔ 0.82 kg @ €7.50 | v0.1, v1.0 |
| H6 | Optimization is more informative than single ratios | Greedy diets from any single ratio miss fat, protein or lysine targets; the optimizer meets all | v1.x comparison |
| H7 | Latvian prices change rankings vs generic data | Not testable yet: v2.1 country prices are *derived* from Latvian prices (Eurostat category price levels), so they cannot test it. Under them, rankings barely move (ρ ≥ 0.95, top-10 overlap 8–10/10 for DK and NL) | v2.1 |
| H8 | Simple metrics nearly as good | **Partly.** As a *food filter* yes: the optimizer limited to the top 10 by protein per € reaches the same minimum cost; 100 % of LP-chosen foods are top-quartile on protein per €. As a *diet builder* no (H6) | v1.x comparison |
| H9 | Diet-level amino acids ≠ food-level P × DIAAS | Food-level constraint costs +31 % and buys 22 % more protein than needed; crude protein leaves lysine at 86 % of requirement | v1.0 |
| H10 | Staples dominate cost-optimal energy once fat/sugar are capped | Yes: ≥ 88 % plant energy in every minimum-cost diet; legumes + oats/barley/flour | v1.0 |
| H11 | Without safeguards the optimum degenerates | Yes: split peas + 418 g raw flour at 5 % fat (€1.04); full safeguards €1.85, 9 foods | v1.0 |
| H12 | Price-sensitive vs -insensitive objectives choose different foods | Yes: minimum-mass diet = cornflakes, muesli, peanuts, chicken (≈ 1 kg, €9.66) vs legume–grain diets | v1.0 |

**Stability.** Monte Carlo: split peas, flour and oats appear in ≥ 99 % of optimal diets; cost 5–95 %:
€1.71–1.99. The largest cost drivers are the person's own targets (protein 2.2 vs 1.6 g/kg: +31 % / −12 %;
mass ≤ 1.5 kg: +19 %), more than any safeguard (caps ×0.5: +20 %, ×2: −9 %).

## 4b. v2.0 addendum: vitamins, minerals, fibre, sodium, saturated fat
19 EFSA adult reference values (DRV summary tables 2017) and food-relevant upper limits (UL overview v11, 2025) are
now enforced, with cooking losses from USDA raw↔cooked pairs; vitamin D and iodine are reported only (sunlight /
supplements, iodised salt). The v1.0 minimum-cost diets turned out badly deficient (vitamin B12 0–7 %, vitamin A
1–4 %, vitamin C 2–4 %, calcium 16–46 % of reference). Nutritionally complete minimum-cost diets cost **€2.22–3.10
per day** (€2.22–3.12 with omega-3 in v2.1; **€2.32–3.28, owner €2.78, with the v2.2 fibre maximum of 45 g and trans-fat limit**) and add milk, eggs, a little herring, cabbage
and carrots to the legume–grain core; the binding nutrients are vitamin B12, selenium, vitamins C, E and A, calcium
and (v2.1) EPA + DHA. Typical diets are short of vitamin E
(27–58 % of AI) and, for the bodybuilding template, vitamin C (32 %). Details: `reports/v2.0_nutrients.md`.

## 4c. v2.1 addendum: meals, realistic diets, omega-3, other countries
**Omega-3.** ALA (≥ 0.5 % E) and EPA + DHA (≥ 250 mg/day) from efsa2010f are now enforced, using Frida/USDA fatty-acid
data (EPA/DHA = 0 for plant foods). This adds ≈ 3–11 g/day of herring (≈ 1 portion a week) at ≤ €0.03/day.

**Realistic variant** (`config/optimizer.yaml`, judgment calls): ≤ 400 g eaten of any food, legumes + soy ≤ 500 g,
≤ 20 % of energy per food, every enforced nutrient from ≥ 2 foods (no food > 60 % of it), optional appetite ceiling.
For the owner it costs **+16 %** in Latvia, Denmark and the Netherlands alike (€2.69 → €3.13 LV), with 17–18 foods
instead of 13–14, and kefir enters as a second calcium/B12 source. A MILP then splits the day into ≥ 4 meals (each
≥ 0.4 g protein/kg, schoenfeld2018, and 20–35 % of energy, as few food pieces as possible).

**Meal Nutrient Score** (`src/meals.py`): 100 × (mean adequacy of 20 encourage items scaled to the meal's share of
daily energy − mean excess over 3 limits), after the Nutrient Rich Foods logic (drewnowski2010nrf) but against personal
targets. The improved meal keeps energy (±3 %) and maximizes this score in a MILP, then breaks ties by similarity or
cost. Examples for the owner (score → small tweak → best possible): 4 eggs + 1 can of beans 62 → 95 → 100 (limited by
sodium from canned beans); oat porridge 93 → 99 → 100; chicken, rice and vegetables 77 → 99 → 99; pork, potatoes and
cabbage 75 → 98 → 99. The score saturates at 100 easily, so it separates poor from good meals better than good from
excellent ones.

**Country prices.** Price(country) = Latvian price × PLI(country, food category) / PLI(LV, category), with Eurostat
2024 food price level indices (eurostat_pli). Owner's complete day: LV €2.69, DK €3.00, NL €2.45. Approximation:
captures between-category differences only.

## 4d. v2.2 addendum: fibre, vitamin C, fat quality, personal rankings
Details and sources: `reports/v2.2_feedback.md`. Cooking does not destroy fibre (median true retention 1.06 over
20 USDA raw↔cooked pairs; per-100 g values fall only through water uptake). The fibre maximum is now 45 g/day for
every goal (judgment call; no official UL), which raises the minimum cost by 2–5 %. An optional 200 mg vitamin C
target (levine1996, carr1999) adds 3–8 %. Fat-quality data (SFA, MUFA, PUFA, trans, n-6, n-3) were added, with trans
fat limited to < 1 % E. Food rankings are now person-specific: a weighted geometric mean of percentile ranks of the
nutrient score per 100 kcal against the person's targets, useful protein, carbohydrate share, cost and food mass per
100 kcal (direction by goal). They are paired with an LP-based "optimizer value" (the food's nutrient value at the
person's shadow prices ÷ its price). With price ignored, top foods are lean animal and dairy foods for cutting and
bulking; with price weighted, they are legumes.

## 5. Limitations
- **Not a meal plan.** Taste and meal structure are not modelled (the 'closest valid diet' mode keeps a usual diet
  as unchanged as possible). A legume-heavy ≈ 2.8 kg/day diet at the fibre cap (60 g) may be impractical for bulking.
- Micronutrient values are database means; bioavailability (e.g. non-haem iron, zinc with phytate) is only partly
  reflected (zinc PRI by phytate level as sensitivity). Added salt is not modelled.
- Protein quality uses pig/human ileal digestibility, partly by proxy (29 foods grade C); DIAAS is not a direct
  predictor of muscle gain. Plant-vs-omnivore training studies at ~1.6 g/kg show similar hypertrophy (hevia2021,
  monteyne2023), but the evidence is limited to a few weeks and young adults.
- Energy expenditure for unknown users relies on assumed MET values; the 7,700 kcal/kg rule is crude (hall2011).
- Per-food caps are judgment calls (sensitivity reported).
- Prices are a single Cenu Depo snapshot plus CSP means; Cenu Depo cannot be used for publication without permission.
- Composition databases disagree by a median ≈ 8–9 % (kcal, protein) on overlapping foods; switching to USDA
  values changes the owner's minimum cost from €1.85 to €1.60.

## 6. Questions for an expert reviewer
1. Is enforcing the FAO 2013 adult scoring pattern × the protein *target* (not the WHO 2007 mg/kg requirement) a
   sensible amino-acid constraint for people training for hypertrophy?
2. Which per-food maxima (legumes 600 g cooked/day, oil 40 g, liver 100 g …) are defensible, and should fibre have a
   maximum for people trying to eat a surplus?
3. Are the carbohydrate bands by weekly training hours and the MET assumptions reasonable for hybrid athletes?
4. Which micronutrients and upper limits matter most for a v2.0 (e.g. vitamin A from liver, iron/zinc from
   legume-heavy diets, B12)?
5. Is a per-meal leucine/protein distribution constraint worth adding at the meal-planning stage?

## 7. Reproducibility
Python 3.14, pinned in `requirements-lock.txt`. `sh run_all.sh` rebuilds every dataset, report and figure from
`data/raw` + `data/foods` + `config` in ≈ 1–2 minutes and runs the test suite (85 tests). Raw-data provenance,
checksums and licences: `data/raw/MANIFEST.md`. Decisions: PROJECT.md §17.
