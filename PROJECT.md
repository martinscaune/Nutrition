# Quantitative Food Value for Training (computational nutrition project)

> Single source of truth for scope, definitions, methods and decisions.
> Replaces the original handoff `food_value_training_research_handoff.docx` (all content carried over below; §1–§16 of that document map to the sections marked *[H]*).
> Working task list: [PLAN.md](PLAN.md). Change this file when a decision is made, and log it in §12.

---

## 1. Goal

Build a **reproducible computational-nutrition framework** that evaluates whole foods and food *combinations* for athletes. The primary focus is **bulking (energy surplus) for an endurance/triathlon athlete** (reference athlete in §7); **cutting** comes later. It uses protein quantity and quality, **carbohydrate**, fat, energy density, food mass, retail price (Latvia), and nutrient constraints.

End products, in order:
1. A curated, versioned **food dataset** (composition + protein quality + Latvian prices + uncertainty).
2. **Food-level metrics and graphs** that go beyond "price per kcal" (Pareto fronts, quality-adjusted protein, volume).
3. An **interactive program** in which variables, weights and constraints can be changed and the results update.
4. A **diet-combination optimizer** (linear / multi-objective programming).
5. A **comparison** of optimized diets with real diets and simple baselines.
6. If the results are strong: **expert review** by a nutrition scientist, then a technical report or publication.

**Research question [H §1]:** Given nutritional composition, protein quality, physical food mass/volume and price, how efficiently does a food satisfy a specified training objective?
**Applied question:** Which combination of foods minimizes cost and/or food volume while it satisfies energy, protein, macro- and micronutrient constraints for bulking (and cutting)?
**Positioning:** computational nutrition / quantitative diet optimization, **not** new exercise physiology.

## 2. Guiding principles [H §16, §14]

- **Do not decide which food should win and then build a formula around it.** Define objectives and constraints, collect defensible data, compare competing metrics, quantify uncertainty, and let the analysis decide.
- If a simple metric performs as well as a complicated index, **that is a valid and useful result**.
- Do **not** claim that any score predicts muscle gain, performance or fat loss without human validation.
- Every number needs **provenance**: a source, a date, a preparation state and an uncertainty.
- Biological assumptions must be checked by sports-nutrition experts. The modeling can be done independently.
- A strong paper needs transparent methods, data provenance, stated assumptions, uncertainty and sensitivity analysis, and reproducible code.

## 2.1 Version scope (v1.0 vs v2.0)

**v1.0 (now):** energy, protein (incl. amino-acid profile and quality), **carbohydrate**, fat, price, and food mass as consumed (g/1000 kcal as a simple metric), plus the **safeguards** in §9.1 that stop absurd results (pure oil, pure sugar).

**v2.0 (with a nutrition-science collaborator):** fibre (both a minimum and, for bulking, a maximum), sodium, micronutrient minimums and upper limits, taste and acceptability, true volume and satiety, glycemic index and carbohydrate timing, meal structure and per-meal leucine, saturated fat, and contaminants (Hg in fish, As in rice).

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

## 7. Reference athlete, macronutrient framework, bulking vs cutting [H §7]

### 7.1 Reference athlete (default profile; every value is a parameter in the program)
| Parameter | Value | Note |
|---|---|---|
| Body mass | 76 kg | |
| Height | 186 cm | BMI ≈ 22.0 |
| Energy expenditure (maintenance) | ≈ 3000 kcal/day | self-reported average, including training |
| Sport | Triathlon (endurance) | so carbohydrate is a first-class requirement |
| Training load | **TBD** (hours/week) | sets the carbohydrate band (task 0.7) |
| Goal | **TBD**: off-season mass gain vs fueling high load | changes the surplus size (task 0.7) |

### 7.2 Macronutrient bands (PROVISIONAL; verify in Phase 1)
- **Energy target** = maintenance + surplus. Provisional surplus is +10–20 %, about 3300–3600 kcal/day (task 1.3).
- **Protein:** 1.6–2.2 g/kg/day for gaining mass, i.e. 122–167 g/day (Morton 2018). ACSM gives 1.2–2.0 g/kg for endurance athletes.
- **Carbohydrate,** scaled to training load (Thomas, Erdman & Burke 2016, ACSM/AND/DC; Burke et al. 2011):

  | Training load | g/kg/day | for 76 kg |
  |---|---|---|
  | light / skill-based | 3–5 | 228–380 g |
  | moderate (~1 h/day) | 5–7 | 380–532 g |
  | endurance, 1–3 h/day moderate–high intensity | 6–10 | 456–760 g |
  | extreme, >4–5 h/day | 8–12 | 608–912 g |
- **Fat:** 20–35 % of energy (EFSA reference intake; ACSM advises not going below 20 %).
- **The constraints can conflict.** At 3400 kcal, protein at 1.6 g/kg plus fat at 20 % leaves at most about 558 g of carbohydrate (≈ 7.3 g/kg). A high carbohydrate band therefore needs a higher energy target. The program must **detect infeasible combinations and report which constraint conflicts**; it must not fail silently.

### 7.3 Goals
**BULKING (primary scope):** meet the energy target with a surplus, protein at or above target (amino-acid complete), carbohydrate in the training-load band and fat in its band, while minimizing cost and food mass. Ranking signals: high kcal/€, protein/€ and CHO/€; high effective protein; low g/1000 kcal.
- For the endurance athlete, **carbohydrate is a requirement, not a filler**. It restores glycogen and supports training quality. The cheapest kcal are only useful if they come with the right macronutrient mix.
- Note for v2.0: high fibre and low energy density limit how much a person can eat, which works against bulking.

**CUTTING (later phase):** favor high effective protein per kcal, high protein quality, low energy density, adequate fibre and micronutrients, and possibly cost efficiency. Cheap calories are not inherently desirable during a deficit. Protein/kcal should probably dominate, with energy density and volume as practical constraints (satiety proxies, e.g. the Holt 1995 satiety index).

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
- H3: Bulking and cutting have different Pareto frontiers.
- H4: Legumes and staples dominate simple cost metrics, while high-quality animal and dairy proteins occupy a different region after quality adjustment.
- H5: Food volume is an important independent constraint for realistic energy targets.
- H6: Multi-objective optimization is more informative than a single ratio.
- H7: Latvian prices alter rankings materially compared with generic food databases.
- H8: For some objectives, simple metrics perform nearly as well as complex indices.
- H9 (added): Diet-level amino-acid constraints give different optimal diets than food-level P × DIAAS scoring (complementarity effect).
- H10 (added): Once fat and sugar are capped, starchy staples (oats, rice, pasta, potatoes, bread, flour) dominate cost-optimal energy supply for an endurance athlete.
- H11 (added): Without the fat and sugar safeguards, cost-optimal diets degenerate (oil and sugar dominate); with them, the safeguards are binding and their shadow prices measure their cost.

## 12. Dataset design [H §12]

- **Initial target:** 100–200 foods. Categories: meat, fish, eggs, dairy, legumes, grains, potatoes/starches, nuts/seeds, soy foods, minimally processed plant foods (plus common fats/oils and calorie-dense staples relevant to bulking).
- **Protein powders and isolates** stay out of the primary whole-food analysis and may be analyzed separately.
- **Fields:** food, category, brand/product, preparation state, kcal/100 g, protein/100 g, fat, carbohydrate, fibre, sugars, saturated fat, sodium, relevant micronutrients, IAA profile (incl. leucine), digestibility/DIAAS (and its source), yield factor, price/kg, retailer, date, regular or discount price, source, uncertainty grade.
- **Uncertainty grade (proposed):** A = analytical national database value with n/SD reported; B = database value without variance or a product label; C = derived from a similar food or imputed. Prices are graded by number of observations and retailers.
- **Sources:** authoritative composition databases (USDA FDC; regional databases such as Fineli (FI) and Frida (DK) to check against Nordic/Baltic foods), product labels for branded items, and **time-stamped Latvian retail prices from as many retailers as feasible** (e.g. Rimi, Maxima/Barbora, Lidl, Top!, Mego, Elvi). Check each retailer's terms before any automated price collection.

### 12.1 Price normalization (decided 2026-10-06: "a typical price, neither the cheapest nor the most expensive")
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

- The project owner is the reference athlete (§7.1): a triathlete with a telecommunications/engineering background, based in Latvia. Domain knowledge is the main gap, so expert review is planned.
- The owner has university access to paywalled papers.
- Even if it is never published, the project can become a rigorous technical report or public analysis.

---

## 17. Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-10-06 | Primary scope = **bulking**; cutting is a later extension | Owner's stated priority |
| 2026-10-06 | Handoff docx converted into this file and deleted | Single source of truth |
| 2026-10-06 | Diet-level protein quality is modeled through summed digestible IAA, not Σ(P×Q) | Complementarity makes P×Q non-additive |
| 2026-10-06 | Python; Streamlit for the interactive program; git for version control | Owner's preference |
| 2026-10-06 | Reference athlete = the owner: 76 kg, 186 cm, ≈3000 kcal/day, triathlete | Owner's input |
| 2026-10-06 | Carbohydrate becomes a first-class requirement (g/kg band by training load) | Endurance athlete; glycogen restoration |
| 2026-10-06 | Oil/sugar handled by safeguards (§9.1), mainly macronutrient bands | Avoid degenerate optima |
| 2026-10-06 | Prices: as many retailers as feasible; central price = median of regular prices, IQR as uncertainty | Owner: "not the cheapest, not the most expensive" |
| 2026-10-06 | Fibre, sodium, taste, true volume, micronutrient constraints deferred to v2.0 (§2.1) | Need a nutrition-science collaborator |

## 18. Open questions

- **Training load** (typical hours/week of swim/bike/run), which sets the carbohydrate band (task 0.7).
- **Goal type:** off-season mass gain, or fueling a high training load while slowly gaining? This sets the surplus size (task 0.7).
- Exact price aggregation order (task 2.11) and how often to collect (one snapshot vs repeated).
- Which DIAAS reference pattern to use (older child/adolescent/adult) and how to handle foods without measured DIAAS?
- Default per-food caps and the maximum energy share for one food (§9.1): which values, and how to justify them.
- Sex and age are not needed for v1.0 (the energy target is given directly), but they will be for v2.0 micronutrient DRVs.
