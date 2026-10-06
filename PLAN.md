# Working Plan: Quantitative Food Value for Training

Legend: `- [ ]` open · `- [x]` done · `- [~]` in progress · `- [-]` dropped (give a reason)
Each phase ends with a **gate**: a checkpoint where we review results before moving on.
Context, definitions and decisions: [PROJECT.md](PROJECT.md). Scope: **v1.0**. Deferred items are in the v2.0 backlog at the bottom.

---

## Phase 0: Project setup
- [x] 0.1 Extract the handoff docx into PROJECT.md and delete the docx
- [x] 0.2 Write this working plan
- [x] 0.3 Tech stack = Python + Streamlit; host-Python venv `.venv/` with pinned requirements
- [x] 0.4 Create the folder structure: `data/raw`, `data/processed`, `literature/`, `src/`, `notebooks/`, `figures/`, `tests/`, `app/`, `config/`
- [x] 0.5 `git init` + `.gitignore`; first commit
- [x] 0.6 Open questions answered: reference athlete (76 kg, 186 cm, ≈3000 kcal, triathlete); prices from as many retailers as feasible, normalized to a median
- [ ] 0.7 Owner to specify: typical training hours/week, and goal type (off-season mass gain vs fueling high load)
- [ ] **GATE 0:** environment works, structure agreed

## Phase 1: Literature review and accepted measures
- [ ] 1.1 Verify and collect all papers in PROJECT.md §13; mark the ones that need university access
- [ ] 1.2 Protein for concurrent endurance + strength training: daily g/kg range, per-meal dose, leucine threshold
- [ ] 1.3 Energy surplus for gaining mass: recommended size and rate of gain; caveats for endurance athletes (power-to-weight, RED-S)
- [ ] 1.4 **Carbohydrate requirements** by training load (g/kg bands), glycogen restoration; confirm the provisional bands in PROJECT.md §7.2
- [ ] 1.5 **Fat range** (% E minimum and maximum) and **free-sugar cap**: the evidence behind safeguards 1–2 (§9.1)
- [ ] 1.6 Protein quality: DIAAS vs PDCAAS, reference patterns, truncation rules, processing effects
- [ ] 1.7 Find sources of measured DIAAS / ileal digestibility per food; list coverage gaps
- [ ] 1.8 Choose an IAA requirement pattern for diet-level amino-acid constraints (WHO/FAO/UNU 2007 or FAO 2013)
- [ ] 1.9 Diet-optimization literature: LP/MILP formulations, realism constraints, per-food caps, known pitfalls
- [ ] 1.10 Earlier work on food cost vs nutrient value (Drewnowski, the 2025 protein cost study, the pulse study)
- [ ] 1.11 Write `literature/REVIEW.md`: one summary per source with the numbers we will use and their uncertainty
- [ ] 1.12 Freeze the **accepted measures and constraint bands** (Q, P_eff, macro bands, caps, mass proxy) in PROJECT.md
- [ ] **GATE 1:** measures fixed before any scoring is done

## Phase 2: Dataset
### 2a. Schema and food list
- [ ] 2.1 Write the data schema (`data/SCHEMA.md`): fields, units, allowed values, uncertainty grades
- [ ] 2.2 Draft the food list (100–200 items) by category, with emphasis on foods actually sold in Latvia; include an "ingredients" category (oils, sugar, butter)
- [ ] 2.3 Decide the protein-powder and sports-carbohydrate side analysis (kept separate from whole foods)
### 2b. Composition
- [ ] 2.4 Download USDA FDC (Foundation + SR Legacy) into `data/raw/` unmodified, with the download date recorded
- [ ] 2.5 Map each food to its database entry (FDC id); record both raw and cooked entries where available
- [ ] 2.6 Cross-check against Fineli/Frida for Nordic/Baltic-specific foods (kefir, biezpiens/quark, rye bread, …)
- [ ] 2.7 Extract energy, protein, **available carbohydrate, sugars (incl. added/free where available)**, fat and the full IAA profile (incl. leucine); also store the free v2.0 fields (fibre, sodium, micronutrients)
- [ ] 2.8 Yield factors for as-purchased → as-consumed (with source)
- [ ] 2.9 Assign protein-quality values (DIAAS etc.) per food, with source and uncertainty
### 2c. Prices (Latvia)
- [ ] 2.10 List all reachable retailers (Rimi, Maxima/Barbora, Lidl, Top!, Mego, Elvi, …); choose the collection method per retailer (online shop, flyers, in-store, receipts); check the terms of use
- [ ] 2.11 Fix the price normalization method (PROJECT.md §12.1): aggregation order, product spec and tier rules
- [ ] 2.12 Build the price-collection template/tool (product spec, brand, pack size, price, €/kg, retailer, date, regular or discount)
- [ ] 2.13 Collect the first price snapshot across as many retailers as feasible
- [ ] 2.14 Compute the central price (median) and IQR per food
- [ ] 2.15 Optional: repeat collection over several weeks to measure price variability
### 2d. Quality control
- [ ] 2.16 Validation script: unit checks, Atwater energy check (4P+4C+9F+2Fibre ≈ kcal), outliers, missing fields
- [ ] 2.17 Assign an uncertainty grade (A/B/C) to every value
- [ ] **GATE 2:** dataset v1.0 frozen and tagged in git

## Phase 3: Food-level metrics
- [ ] 3.1 Load the reference-athlete profile from config (body mass, kcal, training load, bands), not hard-coded
- [ ] 3.2 Implement the core metrics (E, P, CHO, C, E€, P€, CHO€, P/E, F%E, M1000) in `src/metrics.py`, with unit tests
- [ ] 3.3 Implement the protein-quality adjustment (P_eff), allowing several Q definitions side by side
- [ ] 3.4 Implement Pareto-front computation (2D and n-D, with dominance ranks)
- [ ] 3.5 Implement candidate composite indices (S_bulk etc.) as **hypotheses**, with configurable weights
- [ ] 3.6 Rank foods under each metric; compare rankings (Spearman, top-k overlap)
- [ ] **GATE 3:** metrics reviewed; check H1, H2 and H4

## Phase 4: Graphs and exploratory statistics
- [ ] 4.1 Nutrition-density plot with Pareto front
- [ ] 4.2 Economic-value plot (protein/€ vs kcal/€) with Pareto front
- [ ] 4.3 **Carbohydrate economics plot** (CHO/€ vs protein/€)
- [ ] 4.4 Training-efficiency plot
- [ ] 4.5 Mass plot (g/1000 kcal vs effective protein)
- [ ] 4.6 Macronutrient-composition view (each food's position in protein/carbohydrate/fat energy shares, ternary plot)
- [ ] 4.7 3D exploratory plot (interactive)
- [ ] 4.8 Descriptive statistics by category; correlation matrix
- [ ] 4.9 PCA and clustering, with interpretation
- [ ] 4.10 Publication-style figure styling (readable labels, colorblind-safe palette)
- [ ] **GATE 4:** graphs answer the questions; check H5

## Phase 5: Interactive program
- [ ] 5.1 Streamlit app: load the dataset, filter by category, price scenario (median / budget P25 / premium P75)
- [ ] 5.2 Athlete profile panel: body mass, kcal, surplus, training-load selector (sets the CHO band), protein g/kg
- [ ] 5.3 Sliders for weights (w1…w4) and Q definition
- [ ] 5.4 Live ranking table + interactive graphs + Pareto highlighting
- [ ] 5.5 Toggle between as-purchased and as-consumed views
- [ ] 5.6 Export the current configuration and results (CSV/JSON) for reproducibility
- [ ] **GATE 5:** the owner is happy with how results respond to the parameters

## Phase 6: Diet-combination optimization
- [ ] 6.1 Formulate the bulking LP: minimize cost subject to kcal, protein + per-IAA, **carbohydrate band**, **fat band** and maximum mass
- [ ] 6.2 Run the LP **without** safeguards first to record the degenerate optimum (the expected oil/sugar diet), the baseline for H11
- [ ] 6.3 Add the safeguards (§9.1): sugar cap, per-food maximum, maximum energy share per food, minimum number of distinct foods
- [ ] 6.4 Infeasibility diagnostics: when constraints conflict, report which ones (e.g. a high CHO band with a low kcal target)
- [ ] 6.5 Shadow prices and reduced costs: which constraints drive the cost, and how far each food is from entering the diet
- [ ] 6.6 MILP variant with discrete portions/packages
- [ ] 6.7 Multi-objective variant (cost vs mass vs protein quality), giving a Pareto set of diets via ε-constraint and/or NSGA-II
- [ ] 6.8 Compare amino-acid-constrained diets with Σ(P×Q)-constrained diets (H9)
- [ ] 6.9 Generate top-N diverse near-optimal combinations, not only the single optimum
- [ ] 6.10 Integrate the optimizer into the interactive app
- [ ] **GATE 6:** optimized diets are plausible and explainable; check H6, H10 and H11

## Phase 7: Robustness and sensitivity
- [ ] 7.1 Price sensitivity (median vs P25/P75 scenarios, discount prices, per-retailer prices)
- [ ] 7.2 Protein-quality uncertainty (alternative DIAAS values / Q definitions)
- [ ] 7.3 Weight sensitivity for the composite indices (tornado plots, rank stability)
- [ ] 7.4 **Safeguard sensitivity:** how optimal diets change with the fat band, sugar cap, per-food caps and training-load band
- [ ] 7.5 Monte Carlo perturbation of composition and prices: how stable are the rankings and optimal diets?
- [ ] 7.6 Composition-database comparison (USDA vs Nordic) and Latvian vs generic prices (H7)
- [ ] **GATE 7:** state which conclusions are robust and which are fragile

## Phase 8: Comparison with real foods and diets
- [ ] 8.1 Simple baselines: diets built greedily from protein/€, kcal/€ and protein/kcal rankings (H8)
- [ ] 8.2 Typical endurance-athlete and bulking diets (literature, common templates): cost, mass, macronutrient fit
- [ ] 8.3 Typical Latvian / European diet as a reference point
- [ ] 8.4 Test the optimizer's best diet against a real shopping basket (actual prices, practicality), with the owner as the test subject
- [ ] 8.5 Cutting extension: rerun the pipeline with cutting objectives (H3)
- [ ] **GATE 8:** decide whether the results justify contacting an expert

## Phase 9: Expert review and publication
- [ ] 9.1 Write a technical report (methods, data provenance, assumptions, limitations)
- [ ] 9.2 Clean the reproducible repository (README, how to rerun everything, environment)
- [ ] 9.3 Contact a nutrition scientist; send the report and incorporate the feedback
- [ ] 9.4 Choose a venue (e.g. Nutrients, Frontiers in Nutrition, Public Health Nutrition, JISSN, PLOS ONE) or a preprint
- [ ] 9.5 Optional: publish the data and code openly (Zenodo/OSF DOI)
- [ ] 9.6 Write and submit the manuscript

---

## v2.0 backlog (with a nutrition-science collaborator; see PROJECT.md §2.1)
- [ ] Fibre: minimum and, for bulking, maximum constraints
- [ ] Sodium and other limits (saturated fat)
- [ ] Micronutrient minimums and upper limits (EFSA DRVs; needs sex and age)
- [ ] Taste and acceptability (penalty for deviating from typical diets, or preference ratings)
- [ ] True food volume (ml, bulk density) and satiety (Holt satiety index)
- [ ] Glycemic index, carbohydrate timing, in-session sports-carbohydrate allowance
- [ ] Meal structure: per-meal protein/leucine distribution
- [ ] Contaminants (mercury in fish, arsenic in rice)

---

## Progress log
| Date | Task(s) | Notes |
|---|---|---|
| 2026-10-06 | 0.1, 0.2 | Handoff converted; plan written |
| 2026-10-06 | 0.3–0.6 | Python/Streamlit, venv on host Python 3.14, folders, git; reference athlete and price policy recorded; carbohydrates, safeguards and v2.0 scope added |
