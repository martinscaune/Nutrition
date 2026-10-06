# Working Plan: Quantitative Food Value for Training

Legend: `- [ ]` open · `- [x]` done · `- [~]` in progress · `- [-]` dropped (give a reason)
Each stage ends with a **gate**: a checkpoint where we review results before moving on.
Context, definitions and decisions: [PROJECT.md](PROJECT.md). Version roadmap: PROJECT.md §2.1.

**Structure:** Phases 0–2 build the foundation (setup, literature, data). After that the work is organized by **tool version**, from simple to smart: v0.1 → v0.2 → v1.0 → v1.x → v2.0 → v3.0.

---

## Phase 0: Project setup
- [x] 0.1 Extract the handoff docx into PROJECT.md and delete the docx
- [x] 0.2 Write this working plan
- [x] 0.3 Tech stack = Python + Streamlit; host-Python venv `.venv/` with pinned requirements
- [x] 0.4 Create the folder structure: `data/raw`, `data/processed`, `literature/`, `src/`, `notebooks/`, `figures/`, `tests/`, `app/`, `config/`
- [x] 0.5 `git init` + `.gitignore`; first commit
- [x] 0.6 Open questions answered: owner profile (76 kg, 186 cm, ≈3000 kcal, triathlete); prices from as many retailers as feasible, normalized to a median
- [x] 0.7 Owner's training load (6–9 h/week) and goal (76 → 85 kg muscle gain while training for triathlon) recorded
- [x] 0.8 Generalized to a **calculator for any profile** (goal presets + overrides) with a staged roadmap
- [ ] **GATE 0:** owner reviews PROJECT.md §2.1 (roadmap) and §7 (profiles and presets)

## Phase 1: Literature review and accepted measures
- [x] 1.1 Verify and collect all papers in PROJECT.md §13; mark the ones that need university access → `literature/SOURCES.md` (university list at the bottom)
- [x] 1.2 Protein by goal: general adults, strength/hypertrophy, endurance, concurrent (hybrid) training, energy deficit; per-meal dose and leucine
- [~] 1.3 Energy targets by goal: surplus size and rate of gain, deficit size and rate of loss; caveats for endurance athletes (RED-S)
- [x] 1.4 Energy-expenditure estimation (Mifflin-St Jeor, PAL factors, training add-on), for users who don't know their expenditure
- [~] 1.5 **Carbohydrate requirements** by training load (g/kg bands), glycogen restoration; mapping from hours/week + modality to the bands
- [x] 1.6 **Fat range** (% E minimum and maximum) and **free-sugar cap**: the evidence behind the safeguards (§9.1)
- [x] 1.7 Protein quality: DIAAS vs PDCAAS, reference patterns, truncation rules, processing effects
- [~] 1.8 Find sources of measured DIAAS / ileal digestibility per food; list coverage gaps
- [x] 1.9 Choose an IAA requirement pattern for diet-level amino-acid constraints (WHO/FAO/UNU 2007 or FAO 2013)
- [x] 1.10 Diet-optimization literature: LP/MILP formulations, realism constraints, per-food caps, known pitfalls
- [x] 1.11 Earlier work on food cost vs nutrient value (Drewnowski, the 2025 protein cost study, the pulse study)
- [x] 1.12 Write `literature/REVIEW.md`: one summary per source with the numbers we will use and their uncertainty (first pass; proposed decisions D1–D12 in §10)
- [ ] 1.13 Freeze the **goal presets, target rules and accepted measures** (Q, P_eff, bands, caps) in PROJECT.md §7.2
- [ ] 1.14 Originality search in Scopus/Google Scholar (a preliminary PubMed search found no athlete diet-optimization or diet-level DIAAS-LP studies)
- [ ] 1.15 Close the gaps in REVIEW.md §9: thomas2016 full text (owner, via university), REVIEW of mountjoy2023 energy-availability thresholds
- [ ] **GATE 1:** owner approves decisions D1–D12 in REVIEW.md §10; measures and presets fixed before any scoring is done

## Phase 2: Dataset
### 2a. Schema and food list
- [ ] 2.1 Write the data schema (`data/SCHEMA.md`): fields, units, allowed values, uncertainty grades
- [ ] 2.2 Draft the food list (100–200 items) by category, with emphasis on foods actually sold in Latvia; include an "ingredients" category (oils, sugar, butter)
- [ ] 2.3 Decide the protein-powder and sports-carbohydrate side analysis (kept separate from whole foods)
### 2b. Composition
- [ ] 2.4 Download USDA FDC (Foundation + SR Legacy) into `data/raw/` unmodified, with the download date recorded
- [ ] 2.5 Map each food to its database entry (FDC id); record both raw and cooked entries where available
- [ ] 2.6 Cross-check against Fineli/Frida for Nordic/Baltic-specific foods (kefir, biezpiens/quark, rye bread, …)
- [ ] 2.7 Extract energy, protein, available carbohydrate, sugars (incl. added/free where available), fat and the full IAA profile (incl. leucine); also store the free v2.0 fields (fibre, sodium, micronutrients)
- [ ] 2.8 Yield factors for as-purchased → as-consumed (with source)
- [ ] 2.9 Assign protein-quality values (DIAAS etc.) per food, with source and uncertainty
### 2c. Prices (Latvia)
- [ ] 2.10 List all reachable retailers (Rimi, Maxima/Barbora, Lidl, Top!, Mego, Elvi, …); choose the collection method per retailer; check the terms of use
- [ ] 2.11 Fix the price normalization method (PROJECT.md §12.1): aggregation order, product spec and tier rules
- [ ] 2.12 Build the price-collection template/tool (product spec, brand, pack size, price, €/kg, retailer, date, regular or discount)
- [ ] 2.13 Collect the first price snapshot across as many retailers as feasible
- [ ] 2.14 Compute the central price (median) and IQR per food
- [ ] 2.15 Optional: repeat collection over several weeks to measure price variability
### 2d. Quality control
- [ ] 2.16 Validation script: unit checks, Atwater energy check (4P+4C+9F+2Fibre ≈ kcal), outliers, missing fields
- [ ] 2.17 Assign an uncertainty grade (A/B/C) to every value
- [ ] **GATE 2:** dataset v1.0 frozen and tagged in git

---

## v0.1: Food explorer (simple tool: foods, metrics, graphs)
- [ ] A.1 Implement the core metrics (E, P, CHO, C, E€, P€, CHO€, P/E, F%E, M1000) in `src/metrics.py`, with unit tests
- [ ] A.2 Implement the protein-quality adjustment (P_eff), allowing several Q definitions side by side
- [ ] A.3 Implement Pareto-front computation (2D and n-D, with dominance ranks)
- [ ] A.4 Implement candidate composite indices (S_bulk etc.) as **hypotheses**, with configurable weights
- [ ] A.5 Graphs: nutrition density, economic value (protein/€ vs kcal/€), carbohydrate economics (CHO/€ vs protein/€), training efficiency, mass (g/1000 kcal), macronutrient ternary plot, 3D exploratory
- [ ] A.6 Descriptive statistics by category, correlation matrix, PCA and clustering
- [ ] A.7 Rank foods under each metric; compare rankings (Spearman, top-k overlap) to check H1, H2, H4 and H5
- [ ] A.8 Streamlit app: dataset table, category filters, price scenario (median / P25 / P75), weight sliders, live rankings + graphs + Pareto highlighting, as-purchased vs as-consumed toggle
- [ ] A.9 Export the configuration and results (CSV/JSON)
- [ ] A.10 Publication-style figure styling (readable labels, colorblind-safe palette)
- [ ] **GATE v0.1:** the owner finds the explorer useful and understands the trade-offs it shows

## v0.2: Target calculator (profile → targets)
- [ ] B.1 Profile schema (body, training, energy goal, priorities, overrides) as YAML; validation
- [ ] B.2 `config/target_rules.yaml`: goal presets and rules from Phase 1, each with its literature source
- [ ] B.3 `src/targets.py`: derive kcal, protein, carbohydrate and fat ranges plus safeguards; every target records where it came from (rule or override)
- [ ] B.4 Energy expenditure: use the user's value if given, otherwise estimate it (BMR × PAL + training)
- [ ] B.5 Feasibility check: detect conflicting targets and explain them (e.g. a high carbohydrate band with a low kcal target)
- [ ] B.6 Archetype profiles in `config/profiles/`: owner, general adult, bodybuilder bulk, fat loss, Ironman athlete, price-insensitive pro
- [ ] B.7 Unit tests: each archetype gives the expected targets
- [ ] B.8 App: profile panel + preset selector + override fields; the food explorer uses the derived targets
- [ ] **GATE v0.2:** targets for all archetypes look sensible to the owner (and later to an expert)

## v1.0: Diet optimizer (food combinations)
- [ ] C.1 LP: chosen objective (cost, mass, or a weighted mix; a cost weight of 0 is allowed) subject to kcal, protein + per-IAA, carbohydrate band, fat band and maximum mass
- [ ] C.2 Run **without** safeguards first and record the degenerate optimum (the expected oil/sugar diet), the baseline for H11
- [ ] C.3 Add the safeguards (§9.1): sugar cap, per-food maximum, maximum energy share per food, minimum number of distinct foods
- [ ] C.4 Infeasibility diagnostics: when no diet satisfies everything, say which constraints conflict
- [ ] C.5 Shadow prices and reduced costs: which constraints drive the objective, and how far each food is from entering the diet
- [ ] C.6 MILP variant with discrete portions/packages
- [ ] C.7 Multi-objective variant (cost vs mass vs protein quality), giving a Pareto set of diets via ε-constraint and/or NSGA-II
- [ ] C.8 Compare amino-acid-constrained diets with Σ(P×Q)-constrained diets (H9)
- [ ] C.9 Generate top-N diverse near-optimal combinations, not only the single optimum
- [ ] C.10 Integrate into the app: profile → targets → optimal diet(s) with explanations
- [ ] **GATE v1.0:** optimized diets are plausible and explainable for every archetype; check H6, H10, H11 and H12

## v1.x: Analysis, comparison and publication
### Robustness
- [ ] D.1 Price sensitivity (median vs P25/P75 scenarios, discount prices, per-retailer prices)
- [ ] D.2 Protein-quality uncertainty (alternative DIAAS values / Q definitions)
- [ ] D.3 Weight sensitivity for the composite indices (tornado plots, rank stability)
- [ ] D.4 Safeguard and preset sensitivity: how optimal diets change with the fat band, sugar cap, per-food caps, protein and carbohydrate bands
- [ ] D.5 Monte Carlo perturbation of composition and prices: how stable are the rankings and optimal diets?
- [ ] D.6 Composition-database comparison (USDA vs Nordic) and Latvian vs generic prices (H7)
### Comparison
- [ ] D.7 Simple baselines: diets built greedily from protein/€, kcal/€ and protein/kcal rankings (H8)
- [ ] D.8 Cross-archetype comparison: how optimal food sets differ by goal (H3)
- [ ] D.9 Typical real diets (bodybuilding templates, endurance-athlete diets, typical Latvian/European diet): cost, mass, macronutrient fit
- [ ] D.10 Real-life test: the owner's optimized diet as an actual shopping basket (prices, practicality)
### Publication
- [ ] D.11 Technical report (methods, data provenance, assumptions, limitations)
- [ ] D.12 Clean reproducible repository (README, how to rerun everything, environment)
- [ ] D.13 Contact a nutrition scientist; send the report and incorporate the feedback
- [ ] D.14 Choose a venue (e.g. Nutrients, Frontiers in Nutrition, Public Health Nutrition, JISSN, PLOS ONE) or a preprint; optionally publish data and code with a DOI (Zenodo/OSF)
- [ ] D.15 Write and submit the manuscript
- [ ] **GATE v1.x:** decide on publication

## v2.0: Nutrition-complete (with a nutrition-science collaborator)
- [ ] E.1 Fibre: minimum and, for bulking, maximum constraints
- [ ] E.2 Sodium and saturated-fat limits
- [ ] E.3 Micronutrient minimums and upper limits (EFSA DRVs by sex and age)
- [ ] E.4 Taste and acceptability (penalty for deviating from typical diets, or preference ratings)
- [ ] E.5 True food volume (ml, bulk density) and satiety (Holt satiety index)
- [ ] E.6 Glycemic index; in-session sports-carbohydrate allowance
- [ ] E.7 Contaminants (mercury in fish, arsenic in rice)
- [ ] E.8 Expert review of all target rules and presets

## v3.0: Smart
- [ ] F.1 Periodization: training-day vs rest-day targets; week-to-week load (e.g. 6 h vs 9 h weeks)
- [ ] F.2 Adaptive energy expenditure: update the estimate from body-weight and intake tracking (e.g. Hall 2011 model)
- [ ] F.3 Recovery and nutrient timing (pre/during/post training)
- [ ] F.4 Meal plans: per-meal protein/leucine distribution, meal count
- [ ] F.5 Exclusions and preferences (vegetarian, vegan, lactose-free, allergies, disliked foods)
- [ ] F.6 Shopping list with real pack sizes and a weekly budget; recipes

---

## Progress log
| Date | Task(s) | Notes |
|---|---|---|
| 2026-10-06 | 0.1, 0.2 | Handoff converted; plan written |
| 2026-10-06 | 0.3–0.6 | Python/Streamlit, venv on host Python 3.14, folders, git; owner profile and price policy recorded; carbohydrates, safeguards and v2.0 scope added |
| 2026-10-06 | 0.7, 0.8 | Generalized to a calculator for any profile (presets + overrides); plan reorganized around the roadmap v0.1 → v3.0 |
| 2026-10-06 | 1.1–1.12 (first pass) | 47 sources verified (PubMed/Crossref/agency PDFs); REVIEW.md with numbers, evidence tags and decisions D1–D12; 2 handoff errors corrected; university list: thomas2016 (high), chungchunlam2020, burke2011 (manual download), garthe2011, mifflin1990, stigler1945 |
