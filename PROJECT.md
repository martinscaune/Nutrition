# Quantitative Food Value for Training (computational nutrition project)

> Single source of truth for scope, definitions, methods and decisions.
> Replaces the original handoff `food_value_training_research_handoff.docx` (all content carried over below; §1–§16 of that document map to the sections marked *[H]*).
> Working task list: [PLAN.md](PLAN.md). Change this file when a decision is made, and log it in §17.

---

## 1. Goal

Build a **reproducible computational-nutrition framework and general calculator** that evaluates whole foods and food *combinations* for **any user profile**: a person living a normal life, a bodybuilder, someone losing fat, an Ironman athlete, a professional athlete. Every person-specific value (body, training, goal, priorities such as how much price matters) is a parameter (§7). The tool **starts simple and gets smarter in versions** (§2.1). It uses protein quantity and quality, carbohydrate, fat, energy density, food mass, retail price (Latvia), and nutrient constraints.

**First development and test case:** the project owner, who wants muscle gain while training for triathlon (§7.3). Other archetype profiles are used for testing and as case studies.

End products, in order:
1. A curated, versioned **food dataset** (composition + protein quality + Latvian prices + uncertainty).
2. **Food-level metrics and graphs** that go beyond "price per kcal" (Pareto fronts, quality-adjusted protein, volume).
3. An **interactive program** in which variables, weights and constraints can be changed and the results update.
4. A **diet-combination optimizer** (linear / multi-objective programming).
5. A **comparison** of optimized diets with real diets and simple baselines.
6. If the results are strong: **expert review** by a nutrition scientist, then a technical report or publication.

**Research question [H §1]:** Given nutritional composition, protein quality, physical food mass/volume and price, how efficiently does a food satisfy a specified training objective?
**Applied question:** For a given profile and goal, which combination of foods minimizes cost and/or food mass (or another chosen objective) while it satisfies the energy, protein (amino-acid), carbohydrate and fat targets?
**Positioning:** computational nutrition / quantitative diet optimization, **not** new exercise physiology.

## 2. Guiding principles [H §16, §14]

- **Do not decide which food should win and then build a formula around it.** Define objectives and constraints, collect defensible data, compare competing metrics, quantify uncertainty, and let the analysis decide.
- If a simple metric performs as well as a complicated index, **that is a valid and useful result**.
- Do **not** claim that any score predicts muscle gain, performance or fat loss without human validation.
- Every number needs **provenance**: a source, a date, a preparation state and an uncertainty.
- Biological assumptions must be checked by sports-nutrition experts. The modeling can be done independently.
- A strong paper needs transparent methods, data provenance, stated assumptions, uncertainty and sensitivity analysis, and reproducible code.

## 2.1 Roadmap: from a simple tool to a smart one

Each version is **usable on its own**. A later version adds a layer on top of the same pipeline (profile → targets → metrics/optimizer → app) without rewriting earlier ones.

| Version | Name | What it does | User provides |
|---|---|---|---|
| **v0.1** | Food explorer | Food table, metrics, graphs, Pareto fronts, rankings with adjustable weights | weights; targets typed in by hand |
| **v0.2** | Target calculator | Profile + goal preset → kcal, protein, carbohydrate and fat targets, each with its source; every target can be overridden | body, training, goal |
| **v1.0** | Diet optimizer | LP/MILP food combinations under the targets and safeguards (§9.1); selectable objective (cost, mass, or a mix; a cost weight of 0 is allowed); infeasibility diagnostics | + priorities |
| **v1.x** | Analysis & paper | Robustness, archetype comparisons, simple baselines, report/publication | |
| **v2.0** | Nutrition-complete (with a nutrition-science collaborator) | Fibre (minimum, and a maximum for bulking), sodium, saturated fat, micronutrient minimums and upper limits (sex/age DRVs), taste and acceptability, true volume and satiety, glycemic index, contaminants (Hg in fish, As in rice) | sex, age, preferences |
| **v3.0** | Smart | Periodization: training-day vs rest-day targets and week-to-week load variation (e.g. 6 h vs 9 h weeks); adaptive energy-expenditure estimate from body-weight tracking; recovery and nutrient timing; meal plans with per-meal protein/leucine; exclusions (vegetarian, lactose, allergies); shopping lists with pack sizes; recipes | logs, preferences |

**v1.0 nutrient scope:** energy, protein (incl. amino-acid profile and quality), carbohydrate, fat, price, food mass as consumed (g/1000 kcal), plus the safeguards against absurd results (pure oil, pure sugar).

**Data policy:** if a v2.0 field comes free with the same database download (fibre, sodium, micronutrients), collect it in v1.0 anyway so nothing has to be collected twice. It is stored and shown, but not used as a constraint.

## 3. Why the original infographic was inadequate [H §2]

- Its y-axis was *g food per 100 kcal*, so lower meant more energy-dense, which is an unintuitive direction.
- It did not directly show kcal/100 g, protein/100 g, price or protein quality.
- It treated all protein grams as equivalent and did not distinguish training goals.
- It underrepresented the volume constraint: 1000 kcal of a low-energy-density food can require an enormous mass.

## 4. Core variables and formulas [H §3]

| Symbol | Definition | Unit |
|---|---|---|
| E | Energy density | kcal/100 g |
| P | Protein density | g protein/100 g |
| C | Price | €/kg (as purchased) |
| E€ | Calories per euro | kcal/€ |
| P€ | Protein per euro | g protein/€ |
| P/E | Protein-to-energy ratio | g protein/kcal |
| M1000 | Food mass needed for 1000 kcal (as consumed) | g/1000 kcal |
| CHO | Carbohydrate density (available carbohydrate) | g/100 g |
| CHO€ | Carbohydrate per euro | g CHO/€ |
| F%E | Share of energy from fat | % kcal |
| Q | Protein-quality factor, **evidence-based, not arbitrary** | dimensionless |
| P_eff | Quality-adjusted protein = P × Q (e.g. Q = DIAAS/100) | g/100 g |

**Candidate composite bulking index, to TEST and not to assume [H §8]:**
`S_bulk = P_n^w1 × E_n^w2 × C_n^(-w3) × V_n^(-w4)` (normalized variables; a weighted geometric mean stops any one variable from dominating). The weights need justification and sensitivity analysis. **Multiple objective metrics and Pareto frontiers come first. A single score is never the primary result.**

## 5. Protein quality: the central methodological problem [H §4]

- Protein grams are **not** biologically interchangeable. Plant and animal proteins differ in digestible indispensable amino acids (IAA), in their limiting amino acid, and often in leucine.
- **DIAAS** (FAO 2013) is a candidate measure, but it is **not** a muscle-building score. It is computed against a reference pattern for a given age group, and values depend on processing and preparation.
- Sports-specific modeling should look at **DIAAS + the full IAA profile + the limiting amino acid + leucine content** (leucine is relevant to per-meal muscle protein synthesis).
- Do not choose the quality multiplier before the literature review. Record its uncertainty and its dependence on preparation.
- **Key point for combination optimization (added):** protein quality is **not additive across foods**. Complementary proteins (e.g. grains + legumes) compensate for each other's limiting amino acids. At the diet level, quality must therefore come from the **summed digestible amino acids** of the whole combination, not from Σ(P × Q). This can stay linear in an LP: add one constraint per indispensable amino acid (Σ digestible AA ≥ requirement). Food-level P_eff is therefore mainly for ranking and visualization.
- **"Useful" protein saturates (added):** muscle-gain benefits plateau at roughly 1.6 g/kg/day, with an upper confidence bound of about 2.2 g/kg/day (Morton et al. 2018). Above the target, extra protein mostly contributes energy. The natural formulation for bulking is therefore: *meet the protein and amino-acid target as a constraint, then optimize cost/volume for energy*. Verify this against the literature (task 1.x).

## 6. As-purchased vs as-consumed [H §6]

- Keep **two states** for every food. Grocery economics use the **as-purchased** state (dry rice and lentils, raw meat, packaged products). Eating-volume analysis uses the **cooked / as-consumed** state.
- Preparation state is an explicit dataset field. Dry foods look very dense per 100 g because they contain little water.
- Link the states with **yield factors** (e.g. dry rice → cooked mass) and record their source.
- "Volume" is first approximated by **mass as consumed** (g/1000 kcal). True volume (ml) needs bulk-density data, which is rarely available, so treat it as an optional refinement.

## 7. User profiles, goals and target derivation [H §7, generalized]

### 7.1 Design: a general calculator, not a one-person tool
Every person-specific value is an input. The input has five layers:
1. **Body:** mass, height, optional target mass; sex and age (needed only to *estimate* energy expenditure; in v2.0 also for micronutrient DRVs).
2. **Activity/training:** modality {none, strength, endurance, hybrid} plus hours/week, **or** a measured/known energy expenditure entered directly.
3. **Energy goal:** {deficit, maintain, surplus} plus a rate (% body mass/week or kcal/day).
4. **Priorities:** weights on cost, food mass, protein quality, … A **cost weight of 0** is allowed (e.g. a professional athlete who doesn't care about price).
5. **Manual overrides:** any derived target can be overwritten (e.g. a professional athlete whose dietitian prescribes the numbers).

**Pipeline:** profile → **target rules** → targets (kcal; protein, carbohydrate and fat ranges; safeguards) → food ranking and diet optimizer → results.
- Target rules live in **config (`config/target_rules.yaml`), not in code**. Each rule carries its literature source, so a nutrition scientist can review it without reading Python.
- Each output target shows **where it came from** (rule + source, or "user override").
- Protein and carbohydrate per kg use **current** body mass by default; target mass is an option.

### 7.2 Goal presets (named combinations of the layers, not separate code paths). **FROZEN at GATE 1 (2026-10-06)**; evidence and decisions D1–D12 in [literature/REVIEW.md](literature/REVIEW.md) §10. Changes need a new decision-log entry.
| Preset | Training | Energy | Protein g/kg | Carbohydrate | Fat | Cost weight |
|---|---|---|---|---|---|---|
| General adult ("normal life") | none/light | maintain | ≥ 0.83 (EFSA PRI) | 45–60 % E (EFSA) | 20–35 % E | default |
| Muscle gain / bodybuilding off-season | strength | surplus 0.25–0.5 % BM/week (≈ +10 %; +5 % if advanced) (Iraki 2019) | 1.6–2.2, default 1.8 (Morton 2018) | by training band, ≥ 3–5 g/kg | 20–35 % E | default |
| Fat loss (cut) | any | deficit 0.5–1.0 % BM/week, default 0.7 % (Garthe 2011) | 2.3–3.1 g/kg **lean** mass if body fat known (Helms 2014), else 2.2–2.6 g/kg body mass (D3) | by training band | 15–35 % E | default |
| Endurance (triathlon, Ironman) | endurance | maintain | 1.4–2.0, default 1.6 (Thomas 2016, Jäger 2017, Kato 2016) | by training band | 20–35 % E | default |
| Hybrid: muscle gain + endurance | hybrid | surplus (as muscle gain) | 1.6–2.2, default 1.8 | by training band | 20–35 % E | default |
| Professional athlete | any | prescribed | prescribed | prescribed | prescribed | 0 |

**Carbohydrate bands by training load** (Thomas, Erdman & Burke 2016, ACSM/AND/DC; Burke et al. 2011):

| Training load | g/kg/day |
|---|---|
| light / skill-based | 3–5 |
| moderate (~1 h/day) | 5–7 |
| endurance, 1–3 h/day moderate–high intensity | 6–10 |
| extreme, > 4–5 h/day (e.g. Ironman build) | 8–12 |

**The constraints can conflict.** Example: at 3400 kcal, protein at 1.6 g/kg (76 kg) plus fat at 20 % E leaves at most about 558 g of carbohydrate (≈ 7.3 g/kg). The program must **detect infeasible combinations and report which constraint conflicts**; it must not fail silently.

### 7.3 Test profiles
**Profile #1, the project owner (first development case):**
| Parameter | Value | Derived (provisional) |
|---|---|---|
| Sex, age | male, 22 y | |
| Body mass → target | 76 kg → **85 kg** | |
| Height | 186 cm | BMI ≈ 22.0 → 24.6 at 85 kg |
| Energy expenditure | ≈ 3000 kcal/day (self-reported) | probably an underestimate: ten Haaf resting energy ≈ 2040 kcal × PAL 1.70–1.99 ≈ **3470–4060 kcal**; 3000 kcal implies PAL ≈ 1.47 (REVIEW §3). v3.0 learns it from weight tracking |
| Training | triathlon, **6–9 h/week** (≈ 0.9–1.3 h/day) + strength | carbohydrate band "moderate", 5–7 g/kg ≈ 380–530 g/day |
| Goal | hybrid: muscle gain while preparing for triathlon; appearance comes before race performance | surplus ≈ +300–500 kcal → ≈ 3300–3500 kcal/day |
| Protein | 1.6–2.2 g/kg | ≈ 122–167 g/day |
| Priorities | cost matters | cost weight > 0 |
- Rate check (verify in task 1.3): 0.25–0.5 % BM/week ≈ 0.2–0.4 kg/week, so +9 kg takes roughly **6–11 months** at the recommended rates, and part of the gain will be fat.

**Archetype profiles** (for testing, and as case studies in the paper): general adult, bodybuilder bulk, fat loss, Ironman athlete, price-insensitive professional, plus the owner. They are stored as `config/profiles/*.yaml`.

### 7.4 Goal-specific notes
**Muscle gain (bulking):** meet the energy target with a surplus, protein at or above target (amino-acid complete), carbohydrate in the training-load band and fat in its band, while minimizing cost and food mass. Ranking signals: high kcal/€, protein/€ and CHO/€; high effective protein; low g/1000 kcal.
- For endurance and hybrid athletes, **carbohydrate is a requirement, not a filler**. It restores glycogen and supports training quality.
- Note for v2.0: high fibre and low energy density limit how much a person can eat, which works against bulking.

**Fat loss (cutting):** favor high effective protein per kcal, high protein quality, low energy density, adequate fibre and micronutrients, and possibly cost efficiency. Cheap calories are not inherently desirable during a deficit. Protein/kcal should probably dominate, with energy density and volume as practical constraints (satiety proxies, e.g. the Holt 1995 satiety index).

**Price-insensitive users:** with the cost weight at 0, the objective becomes food mass, protein quality or closeness to the targets, under the same constraints.

## 8. Proposed graphs [H §5]

1. **Nutrition density:** X = protein g/100 g, Y = kcal/100 g, with a Pareto frontier.
2. **Economic value:** X = protein g/€, Y = kcal/€, with a Pareto frontier.
3. **Training efficiency:** X = effective protein/kcal, Y = kcal/€ or protein/€.
4. **Volume:** X = effective protein/100 g, Y = g food/1000 kcal (most useful for cutting).
5. **3D exploratory:** protein/100 g × kcal/100 g × €/kg (for exploration; 2D is better for publication).
- Heatmaps and Pareto maps may read better than overloaded scatterplots. Use large markers and readable labels, and show category by color.

## 9. Diet-level optimization [H §9]

- Linear programming (LP), mixed-integer LP (for realistic portions), and multi-objective optimization (ε-constraint, weighted sum, or evolutionary methods such as NSGA-II).
- **Bulking constraints:** target kcal/day, minimum protein and per-IAA amounts, macro/micronutrient/fibre requirements (EFSA DRVs, including **upper limits**), maximum cost, maximum food mass.
- **Cutting constraints:** the same, plus a food-volume or satiety proxy.
- **Realism constraints (added):** maximum amount per food, minimum variety or number of food groups, and optionally a penalty for deviating from a typical diet. Pure cost-minimizing LPs famously give absurd diets (Stigler 1945).
- **Ranking foods in diet context (added):** the LP's *reduced costs* and *shadow prices* show how much cheaper a food would have to be to enter the optimal diet, and which constraints drive the cost. This is a principled food ranking that respects the constraints, unlike stand-alone ratios.
- **Baselines to compare against:** ranking by protein/€, by kcal/€ and by protein/kcal. If a simple metric performs about as well as the full model, report it.

### 9.1 Safeguards against absurd results (v1.0)
Without them, a cost/mass optimizer picks **pure oil** (cheapest, densest kcal) and **pure sugar** (cheapest carbohydrate). Safeguards, in order of scientific defensibility:
1. **Macronutrient bands** (§7.2): fat ≤ 35 % E rules out an oil-based diet; the carbohydrate and protein bands force a realistic mix. These are evidence-based and are the primary safeguard.
2. **Free/added sugar cap:** < 10 % E by default (WHO 2015), adjustable. Sugar is to carbohydrate what oil is to fat. (Sugar taken during training sessions is a v2.0 refinement.)
3. **Per-food maximum daily amount** (e.g. oil ≤ X g/day) as realistic portion ceilings. These are judgment calls, so each is documented and covered by sensitivity analysis.
4. **Maximum share of energy from a single food** (e.g. ≤ 25–30 % E) and a minimum number of distinct foods, for diversity.
5. **Food-level graphs:** pure ingredients (oils, sugar, butter) get their own category. They are shown but kept out of the default "eatable foods" ranking.

Report which safeguards are **binding** in each optimum (H11). This shows how much each one shapes the answer.

## 10. Statistical analysis [H §10]

- Descriptive statistics by food category.
- Pearson and Spearman correlations among density, quality-adjusted protein, price and efficiency metrics.
- PCA to find the main nutritional and economic axes.
- Cluster analysis (lean animal proteins, fatty protein foods, staples, legumes, dairy, fish, nuts/seeds, …).
- Pareto-frontier analysis.
- Sensitivity analysis on prices, protein-quality estimates and objective weights.
- Bootstrap/perturbation (Monte Carlo) analysis of ranking and solution stability.
- Price variability modeling where there are enough observations (several retailers and dates, regular vs discount price).

## 11. Hypotheses to test [H §11]

- H1: Quality-adjusted protein changes rankings materially compared with raw protein grams.
- H2: Retail price materially changes food-efficiency rankings.
- H3: Different goals (general adult, muscle gain, fat loss, endurance) have different Pareto frontiers and different optimal food sets.
- H4: Legumes and staples dominate simple cost metrics, while high-quality animal and dairy proteins occupy a different region after quality adjustment.
- H5: Food volume is an important independent constraint for realistic energy targets.
- H6: Multi-objective optimization is more informative than a single ratio.
- H7: Latvian prices alter rankings materially compared with generic food databases.
- H8: For some objectives, simple metrics perform nearly as well as complex indices.
- H9 (added): Diet-level amino-acid constraints give different optimal diets than food-level P × DIAAS scoring (complementarity effect).
- H10 (added): Once fat and sugar are capped, starchy staples (oats, rice, pasta, potatoes, bread, flour) dominate cost-optimal energy supply for an endurance athlete.
- H11 (added): Without the fat and sugar safeguards, cost-optimal diets degenerate (oil and sugar dominate); with them, the safeguards are binding and their shadow prices measure their cost.
- H12 (added): For the same targets, price-sensitive and price-insensitive objectives select materially different foods.

## 12. Dataset design [H §12]

- **Initial target:** 100–200 foods. Categories: meat, fish, eggs, dairy, legumes, grains, potatoes/starches, nuts/seeds, soy foods, minimally processed plant foods (plus common fats/oils and calorie-dense staples relevant to bulking).
- **Protein powders and isolates** stay out of the primary whole-food analysis and may be analyzed separately.
- **Fields:** food, category, brand/product, preparation state, kcal/100 g, protein/100 g, fat, carbohydrate, fibre, sugars, saturated fat, sodium, relevant micronutrients, IAA profile (incl. leucine), digestibility/DIAAS (and its source), yield factor, price/kg, retailer, date, regular or discount price, source, uncertainty grade.
- **Uncertainty grade (proposed):** A = analytical national database value with n/SD reported; B = database value without variance or a product label; C = derived from a similar food or imputed. Prices are graded by number of observations and retailers.
- **Sources:** authoritative composition databases (USDA FDC; regional databases such as Fineli (FI) and Frida (DK) to check against Nordic/Baltic foods), product labels for branded items, and **time-stamped Latvian retail prices from as many retailers as feasible** (e.g. Rimi, Maxima/Barbora, Lidl, Top!, Mego, Elvi). Check each retailer's terms before any automated price collection.

### 12.1 Price normalization (decided 2026-10-06: "a typical price, neither the cheapest nor the most expensive")

> **Updated 2026-10-06 (Phase 2):** the primary source is now the **official CSP average retail prices** (table PCC010m; about 2,000 outlets, population-weighted, sales for all shoppers included), covering 71 of 106 foods. Own observations cover the rest. The binding method is in [data/SCHEMA.md](data/SCHEMA.md) ("Price normalization"). The text below is the original draft, kept for reference.
- One **observation** = food × product/brand × pack size × retailer × date × {regular, discount}.
- Each food is defined by a **comparable product spec** (e.g. "rolled oats, plain, non-organic"), with a tier flag (standard / store-brand / premium / organic).
- **Central price = median €/kg of regular-price observations.** The aggregation order is still open (task 2.11): (a) median over all observations, or (b) median per retailer, then the median of the retailer medians, so a retailer with many brands does not dominate. Option (b) is preferred.
- **Uncertainty = IQR (P25–P75).** Min/max are kept for scenarios: "budget" = P25, "premium" = P75.
- Discount and loyalty prices are recorded but **left out of the central price**. They are used only as a sensitivity scenario.
- Pack size is recorded because bulk packs are cheaper per kg. Every observation is date-stamped, and collection over a long period may need HICP adjustment.

## 13. Literature and data leads [H §13 + additions]

From the handoff:
- USDA FoodData Central: https://fdc.nal.usda.gov/ (downloads: https://fdc.nal.usda.gov/download-datasets/)
- Herreman et al. (2020), *Nutrients*: plant vs animal protein quality / DIAAS: https://pmc.ncbi.nlm.nih.gov/articles/PMC7590266/
- Jäger et al. (2017), ISSN Position Stand: protein and exercise, EAA, leucine: https://pubmed.ncbi.nlm.nih.gov/28642676/
- 2025 protein-food quality/cost study: https://pubmed.ncbi.nlm.nih.gov/39896728/
- Pulse affordability / nutrient-density study: https://pmc.ncbi.nlm.nih.gov/articles/PMC11377338/
- Affordable nutrient-density literature: https://www.sciencedirect.com/science/article/pii/S0022316622098273
- LP diet-optimization example: https://pubmed.ncbi.nlm.nih.gov/34870073/

Added leads (**citations to verify and obtain during task 1.1**):
- FAO (2013). *Dietary protein quality evaluation in human nutrition.* FAO Food & Nutrition Paper 92 (defines DIAAS and the reference patterns).
- WHO/FAO/UNU (2007). *Protein and amino acid requirements in human nutrition.* TRS 935 (per-kg IAA requirements).
- Morton et al. (2018). Protein supplementation and resistance-training gains: meta-analysis. *Br J Sports Med* 52:376–384.
- Schoenfeld & Aragon (2018). How much protein can the body use in a single meal? *JISSN* 15:10.
- Iraki et al. (2019). Nutrition recommendations for bodybuilders in the off-season. *Sports* 7(7):154.
- Helms, Aragon & Fitschen (2014). Natural bodybuilding contest preparation. *JISSN* 11:20 (cutting).
- Rutherfurd et al. (2015), *J Nutr*; Mathai, Liu & Stein (2017), *Br J Nutr*: measured DIAAS values.
- Gorissen et al. (2018), *Amino Acids*: amino-acid and leucine content of plant vs animal proteins.
- van Dooren (2018). A review of the use of linear programming to optimize diets. *Front Nutr* 5:48.
- Stigler (1945). The cost of subsistence. *J Farm Econ* 27:303–314 (the classic diet problem).
- Drewnowski (2010). The cost of US foods as related to their nutritive value. *Am J Clin Nutr* 92:1181–1188.
- Holt et al. (1995). A satiety index of common foods. *Eur J Clin Nutr* 49:675–690.
- EFSA (2017). Dietary Reference Values for nutrients: summary report.
- Thomas, Erdman & Burke (2016). ACSM/AND/DC joint position statement: Nutrition and athletic performance. *Med Sci Sports Exerc* 48(3):543–568 (carbohydrate, protein and fat for athletes).
- Burke et al. (2011). Carbohydrates for training and competition. *J Sports Sci* 29(S1):S17–S27.
- Mountjoy et al. (2018). IOC consensus statement on Relative Energy Deficiency in Sport (RED-S). *Br J Sports Med* 52:687–697 (energy availability in endurance athletes).
- EFSA (2010). Scientific opinions on DRVs for carbohydrates and dietary fibre, and for fats. *EFSA Journal* 8(3):1462 and 1461 (fat 20–35 % E).
- WHO (2015). *Guideline: Sugars intake for adults and children* (free sugars < 10 % E).
- EFSA (2012). Scientific opinion on DRVs for protein. *EFSA Journal* 10(2):2557 (adult PRI 0.83 g/kg; general-adult preset).
- Mifflin et al. (1990). A new predictive equation for resting energy expenditure in healthy individuals. *Am J Clin Nutr* 51:241–247 (v0.2 energy estimate).
- FAO/WHO/UNU (2004). *Human energy requirements* (physical activity level factors).
- Hall et al. (2011). Quantification of the effect of energy imbalance on bodyweight. *Lancet* 378:826–837 (v3.0 adaptive model).

Papers that cannot be accessed openly: the user can try to get them through university access. PDFs go in `literature/`.

## 14. Recommended workflow [H §15]

1. Literature review and scope definition.
2. Define accepted measures before final scoring.
3. Build a reproducible food + price dataset.
4. Baseline metrics and graphs.
5. Protein-quality adjustment.
6. Correlations, PCA, clustering, Pareto fronts.
7. Bulking/cutting objectives.
8. Sensitivity and robustness analysis.
9. Diet-level linear / multi-objective optimization.
10. Compare the complex model against simple baselines.
11. Write the paper/report with limitations.
12. Expert review before drawing physiological conclusions.

(This is expanded into checkbox tasks in [PLAN.md](PLAN.md).)

## 15. Technical stack (decided 2026-10-06)

**Environment note:** VS Code runs as a Flatpak, so its built-in terminal is sandboxed (Python 3.13). The project venv `.venv/` is built with the **host** Python 3.14. Inside the VS Code terminal, run commands through `host-spawn` (e.g. `host-spawn .venv/bin/python …`), or use a normal system terminal. Top-level dependencies are listed in `requirements.txt`; exact pinned versions are in `requirements-lock.txt`.


- **Python 3** with pandas, numpy, scipy, scikit-learn (PCA, clustering), matplotlib/plotly (graphs).
- Optimization: `scipy.optimize.linprog` (HiGHS) or PuLP/HiGHS for (MI)LP; `pymoo` for multi-objective.
- Interactive app: **Streamlit** (sliders for weights, variables and constraints).
- Data as CSV (human-readable, diff-friendly) with a documented schema; raw downloads stay unmodified in `data/raw/`.
- `git` for version control, a pinned environment, and `pytest` for formula/unit checks.

## 16. Background and context

- The project owner is test profile #1 (§7.3): a triathlete with a telecommunications/engineering background, based in Latvia. Domain knowledge is the main gap, so expert review is planned.
- The owner has university access to paywalled papers.
- Even if it is never published, the project can become a rigorous technical report or public analysis.

---

## 17. Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-10-06 | ~~Primary scope = bulking; cutting is a later extension~~ (superseded: general calculator, see below) | Owner's stated priority |
| 2026-10-06 | Handoff docx converted into this file and deleted | Single source of truth |
| 2026-10-06 | Diet-level protein quality is modeled through summed digestible IAA, not Σ(P×Q) | Complementarity makes P×Q non-additive |
| 2026-10-06 | Python; Streamlit for the interactive program; git for version control | Owner's preference |
| 2026-10-06 | Reference athlete = the owner: 76 kg, 186 cm, ≈3000 kcal/day, triathlete (now test profile #1) | Owner's input |
| 2026-10-06 | Carbohydrate becomes a first-class requirement (g/kg band by training load) | Endurance athlete; glycogen restoration |
| 2026-10-06 | Oil/sugar handled by safeguards (§9.1), mainly macronutrient bands | Avoid degenerate optima |
| 2026-10-06 | Prices: as many retailers as feasible; central price = median of regular prices, IQR as uncertainty | Owner: "not the cheapest, not the most expensive" |
| 2026-10-06 | Fibre, sodium, taste, true volume, micronutrient constraints deferred to v2.0 (§2.1) | Need a nutrition-science collaborator |
| 2026-10-06 | **General calculator:** all person-specific values are parameters; goal presets plus overrides; the owner is test profile #1 | Must serve bodybuilders, fat loss, Ironman, general adults, price-insensitive pros |
| 2026-10-06 | Roadmap v0.1 → v0.2 → v1.0 → v2.0 → v3.0 (§2.1) | Start simple, add intelligence gradually |
| 2026-10-06 | Target rules in config with sources, not hard-coded | Reviewable by a nutrition scientist |
| 2026-10-06 | Owner: 6–9 h/week triathlon, goal 76 → 85 kg muscle gain, appearance before performance | Owner's input |
| 2026-10-06 | **GATE 1 passed:** decisions D1–D12 approved; presets in §7.2 frozen | REVIEW.md §10 |
| 2026-10-06 | Protein-quality constraint = per-IAA digestible supply ≥ FAO 2013 adult pattern × protein target (D9); DIAAS from USDA AA × muleya2021 digestibility (D11) | Complementarity, FAO/Moughan guidance |
| 2026-10-06 | Novelty claim limited to the *combination* (sourced presets + diet-level digestible IAA + mass + local prices + robustness); prior athlete LP work must be cited | Originality search (REVIEW §7) |
| 2026-10-06 | **Prices: CSP PCC010m official averages are primary** (12-month mean, min–max band); own observations (median of retailer medians, P25–P75) only for the 35 foods CSP lacks; 5–10 CSP foods cross-checked | Official, citable, already normalized across ~2,000 outlets; my placeholder guesses were 20–50 % too low for staples |
| 2026-10-06 | No reuse of price-comparison-site data (Cenu Depo, Lēta Pārtika) without written permission | Their terms neither grant reuse nor exclude user-submitted prices |
| 2026-10-06 | **Superseded for the personal-use phase:** Cenu Depo per-shop prices ARE used for the 35 non-CSP foods (polite collection, raw pages archived). Before any publication: replace with licensed data (CSP retailer data / written permission) | Owner: personal use now, real databases when a paper is due |
| 2026-10-06 | Composition: **Frida 5.5 primary** (Nordic, analytical, full AA, available carbs, free sugars), USDA SR Legacy fallback; eaten state via USDA raw↔cooked protein-ratio yields; edible portions from USDA SR28 refuse | Closer to Baltic foods than USDA; protein conserved in cooking |
| 2026-10-07 | Charts: scientific style (white background, full black frame, inward ticks on all sides, grid on both axes, framed legend); app light theme | Owner: dark theme made charts unreadable |
| 2026-10-07 | Energy expenditure (when not given) = REE × 1.5 + (MET − 1) × kg × h/day, MET 5 / 8 / 7 for strength / endurance / hybrid | D5 mapping; MET values are an assumption [U], to verify (Compendium of Physical Activities) |
| 2026-10-07 | Macro split: protein default → fat at the middle of its % range → carbohydrate = rest, then fitted to the training band (endurance/hybrid: thomas2016 bands; strength gaining: ≥ 3 g/kg; strength cutting / no training: rest) | Avoids applying endurance carb bands to lifters; conflicts reported, not hidden |
| 2026-10-07 | AI export ranks core foods only; ingredients included unranked for cooking | Owner request: CSV + brief for an LLM recipe planner |
| 2026-10-07 | Scenario check (reports/scenarios_v0.2.md): food-level rankings do not depend on the person's targets, only on preset/quality/price/cost-priority. Each goal now has a default `ranking_preset`; person-specific choice is the optimizer's job (v1.0) | Owner asked to compare profiles |
| 2026-10-07 | Preset rule: never weight two metrics that measure the same thing (energy density and g/1000 kcal are reciprocals; carb density ≈ dryness). Fixed 'Bulking: balanced', 'Price doesn't matter', 'Endurance carbs' | Double-counting put crispbread/cornflakes on top for endurance |
| 2026-10-07 | Normalization: percentile stays default; log-ratio and min-max selectable; sensitivity reported (top-10 overlap 0.4–1.0 between methods) → composite scores are a convenience view, not a primary result | Scenario D |
| 2026-10-07 | Optimizer: x = g eaten/day; minimize cost, mass or normalized mix; energy ±2 %; protein ≥ target; per-IAA digestible supply ≥ FAO adult pattern × protein target (D9); carb band, fat band, free-sugar cap; per-food caps and ≤ 30 % energy per food (judgment calls in `config/optimizer.yaml`); infeasible → goal-programming slacks report the conflicting targets | PROJECT §9, §9.1; moreno2026 idea for infeasibility |
| 2026-10-07 | First v1.0 results: minimum-cost diets €0.77–2.31/day, ≥ 88 % plant energy, amino acids (SAA, LYS) are the binding constraints; food-level Σ P×DIAAS costs +31 % vs diet-level AA (H9); cost vs mass: 2.47 kg @ €1.85 ↔ 0.82 kg @ €7.50 (H5) | `reports/v1.0_optimizer.md` |
| 2026-10-07 | Buckwheat composition → USDA roasted groats (Frida protein 7.0 g/100 g implausible) | Found by Frida-vs-USDA comparison (D.6) |
| 2026-10-07 | v2.0 started early (owner request) without expert review: EFSA DRV summary tables v4 (2017) and UL overview v11 (2025) adopted; ULs applied only where they concern nutrients naturally in food (not Mg, folate, niacin); vitamin D and iodine report-only (sun/supplement, iodised salt) | config/micronutrients.yaml |
| 2026-10-07 | Cooking losses: nutrient retention from each food's USDA raw↔cooked pair (true retention), capped to [0, 1]; resolver now flags pairs that mix enriched/unenriched or salted entries | USDA retention-factor values not in FDC CSV |
| 2026-10-07 | v2.0 result: v1.0 minimum-cost diets were badly deficient (B12 0–7 %, vitamin A 1–4 %, vitamin C 2–4 %, calcium 16–46 % of reference); complete diets cost €2.22–3.10/day (owner €2.68) and include milk, eggs, a little fish, cabbage, carrots | reports/v2.0_nutrients.md |
| 2026-10-07 | v1.x results: Monte Carlo cost €1.71–1.99 (5–95 %); simple protein/€ ranking is a good *food filter* (restricted LP same cost) but not a diet builder (H6/H8); conventional bodybuilding day meets targets at €7.66 (≈ 4× minimum); 'closest valid diet' mode added | `reports/v1x_*.md`, `reports/technical_report.md` |
| 2026-10-07 | Meal Nutrient Score = 100 × (mean adequacy of 20 encourage items scaled to the meal's energy share − mean excess over free sugars, saturated fat, sodium); improved meal = same energy ±3 %, MILP maximizing that score, ties by similarity or cost; omega-3 not judged per meal | Owner request: rate a staple meal (friend's 4 eggs + beans) and show how much better it can be; transparent, NRF-style (drewnowski2010nrf) |
| 2026-10-07 | Country prices = Latvian price × Eurostat food PLI(country, category) / PLI(LV, category) (2024); LV-only foods removed elsewhere; all prices stay in € | Owner request (friends in DK and NL); no comparable shop data; approximation documented, does not test H7 |
| 2026-10-07 | Realistic variant + meal split (judgment calls in `config/optimizer.yaml`, `config/meals.yaml`) alongside the mathematical minimum; both exported | AI-export feedback: 600 g split peas / 800 g barley per day is not a meal plan |
| 2026-10-07 | Omega-3 enforced: ALA ≥ 0.5 % E, EPA + DHA ≥ 250 mg/day (efsa2010f), EPA/DHA = 0 for plant foods, canned tuna gap filled from USDA (`data/foods/nutrient_fill.csv`) | AI-export feedback; costs ≤ €0.03/day |
| 2026-10-07 | Race-week preset: carbohydrate 10–12 g/kg (thomas2016), energy raised to fit, fat 10–25 % E, free sugars ≤ 25 % E, fibre ≤ 25 g, micronutrient minimums report-only (judgment calls) | AI-export feedback (presets bulking/cutting/endurance base/race week) |
| 2026-10-07 | Sharing: private Streamlit Community Cloud app from a private GitHub repo; owner pushes and deploys; Cenu Depo-derived prices stay private (invite-only) | Owner choice; personal-use terms of the price data |
| 2026-10-07 | Fibre: minimum 25 g kept (EFSA, WHO 2023); maximum 45 g for all goals (was 60 g when gaining), adjustable per profile; soluble/insoluble tracked where analysed (15 foods); cooking does not destroy fibre (median retention 1.06 over 20 USDA pairs) | Friend feedback; reynolds2019, wanders2011, veena1995, njoumi2019; reports/v2.2_feedback.md |
| 2026-10-07 | GI not a target (reynolds2019: low/very low certainty); starch and sugars shown separately | Friend feedback ('fast vs slow carbs') |
| 2026-10-07 | Vitamin C: EFSA PRI default; optional 200 mg per profile (levine1996, carr1999); profiles may override any micronutrient min/max (`overrides: {<key>_min/_max}`) | Friend feedback |
| 2026-10-07 | Fat quality data (SFA, MUFA, PUFA, trans, n-6, n-3) added; trans fat < 1 % E enforced (who2023sfa) | Owner question on oils; schwingshackl2018, hooper2020 |
| 2026-10-07 | Rankings: person-specific score (src/personal.py; goal weights in target_rules.yaml, judgment calls) + optimizer value (food's nutrient value at the person's shadow prices ÷ price); AI export ranks by it | Owner: rankings did not change with the person |
| 2026-10-07 | App: multipage (st.navigation, top bar, 3 sections), cached computations, One-food day removed, formula language in Explorer (ast-whitelisted, safe on the shared app), formulas shown next to results, owner palette + Roboto | Owner comments (speed, navigation, design, transparency) |

## 18. Open questions
- Exact price aggregation order (task 2.11) and how often to collect (one snapshot vs repeated).
- Which DIAAS reference pattern to use (older child/adolescent/adult) and how to handle foods without measured DIAAS?
- Default per-food caps and the maximum energy share for one food (§9.1): which values, and how to justify them.
- Final values of the goal presets (§7.2): verify in Phase 1.
- How to map "hours/week + modality" onto the carbohydrate bands, which are defined in h/day and intensity.
- Owner's sex and age (optional): needed only if v0.2 is to *estimate* energy expenditure rather than use the self-reported 3000 kcal, and for the v2.0 DRVs.
- Real DK/NL prices: match foods to Open Prices (≥ 3 observations) with Eurostat-level fallback? Public use needs openly licensed Latvian prices too.
- Extend composition to ≈ 200 foods (Frida + Fineli fibre fractions); add GI from atkinson2021 (university access)?
