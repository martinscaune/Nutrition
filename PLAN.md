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
- [x] 1.3 Energy targets by goal: surplus size and rate of gain, deficit size and rate of loss; caveats for endurance athletes (RED-S)
- [x] 1.4 Energy-expenditure estimation (Mifflin-St Jeor, PAL factors, training add-on), for users who don't know their expenditure
- [x] 1.5 **Carbohydrate requirements** by training load (g/kg bands), glycogen restoration; mapping from hours/week + modality to the bands
- [x] 1.6 **Fat range** (% E minimum and maximum) and **free-sugar cap**: the evidence behind the safeguards (§9.1)
- [x] 1.7 Protein quality: DIAAS vs PDCAAS, reference patterns, truncation rules, processing effects
- [x] 1.8 Find sources of measured DIAAS / ileal digestibility per food; list coverage gaps
- [x] 1.9 Choose an IAA requirement pattern for diet-level amino-acid constraints (WHO/FAO/UNU 2007 or FAO 2013)
- [x] 1.10 Diet-optimization literature: LP/MILP formulations, realism constraints, per-food caps, known pitfalls
- [x] 1.11 Earlier work on food cost vs nutrient value (Drewnowski, the 2025 protein cost study, the pulse study)
- [x] 1.12 Write `literature/REVIEW.md`: one summary per source with the numbers we will use and their uncertainty (first pass; proposed decisions D1–D12 in §10)
- [x] 1.13 Freeze the **goal presets, target rules and accepted measures** (Q, P_eff, bands, caps) in PROJECT.md §7.2
- [x] 1.14 Originality search (PubMed + OpenAlex): athlete LP diets exist (magdic2013 etc.), but not with diet-level digestible IAA + sourced presets + mass + local prices; claim narrowed (REVIEW §7). Scopus optional
- [x] 1.15 Close the gaps in REVIEW.md §9: thomas2016 read (all bands [P]); EA thresholds 45/30 kcal/kg FFM from thomas2016; mountjoy2023 qualification left as low-priority (warning only)
- [x] **GATE 1:** owner approved decisions D1–D12 (2026-10-06); presets frozen in PROJECT.md §7.2

## Phase 2: Dataset
### 2a. Schema and food list
- [x] 2.1 Write the data schema (`data/SCHEMA.md`): fields, units, allowed values, uncertainty grades
- [~] 2.2 Draft the food list (100–200 items) by category, with emphasis on foods actually sold in Latvia; include an "ingredients" category (oils, sugar, butter) → `data/foods/foods.csv` (106 foods), awaiting owner review
- [x] 2.3 Decide the protein-powder and sports-carbohydrate side analysis (kept separate from whole foods): 4 items with `role = supplement` (whey, pea protein, gainer, maltodextrin)
### 2b. Composition
- [x] 2.4 Download USDA FDC (Foundation + SR Legacy) into `data/raw/` unmodified, with the download date recorded (SR Legacy + muleya2021 done 2026-10-06, see `data/raw/MANIFEST.md`; Foundation pending)
- [x] 2.5 Map each food to its database entry: `data/foods/composition_map.csv` (Frida 5.5 primary, USDA fallback), resolved by `src/data/resolve.py`; 0 ID errors, all Atwater checks within 12 %
- [x] 2.6 Nordic/Baltic foods: Frida 5.5 downloaded (CC BY 4.0) and used as primary; Fineli blocks automated download (not needed now)
- [x] 2.7 Extract energy, protein, available carbohydrate, sugars (incl. added/free where available), fat and the full IAA profile (incl. leucine); also store the free v2.0 fields (fibre, sodium, micronutrients)
- [x] 2.8 Yield factors for as-purchased → as-consumed: USDA raw↔cooked protein ratio; edible portions from USDA SR28 refuse (`yields.csv`)
- [x] 2.9 Assign protein-quality values: `data/foods/digestibility_map.csv` (muleya2021 rows; 35 A / 34 B / 29 C; 8 foods without protein)
### 2c. Prices (Latvia)
- [x] 2.10 List all reachable retailers (Rimi, Maxima/Barbora, Lidl, Top!, Mego, Elvi, …); choose the collection method per retailer; check the terms of use → CSP PCC010m official averages found (71 foods); comparison sites not reusable without permission; own collection for 35 foods
- [x] 2.11 Fix the price normalization method (PROJECT.md §12.1): aggregation order, product spec and tier rules
- [x] 2.12 Build the price-collection template/tool (product spec, brand, pack size, price, €/kg, retailer, date, regular or discount)
- [x] 2.13 Collect the first price snapshot: Cenu Depo 2026-10-06, ~570 shop-level observations, 17 shops (`src/prices/cenudepo.py`); 7 foods not listed there (soy drink, chicken liver, 3 seeds, gainer, maltodextrin) remain unpriced across as many retailers as feasible
- [x] 2.14 Compute the central price and band per food (`src/prices/summary.py` → `data/processed/prices_summary.csv`); cross-check: Cenu Depo median ≈ 10 % below CSP (rice +12 %, chicken −10 %, curd −11 %, pasta −14 %, oats −32 %)
- [ ] 2.15 Optional: repeat collection over several weeks to measure price variability
### 2d. Quality control
- [x] 2.16 Validation script: unit checks, Atwater energy check (4P+4C+9F+2Fibre ≈ kcal), outliers, missing fields, **amino-acid plausibility** (the preview found implausible USDA SR Legacy profiles: ground beef 80/20 Trp 5.1 mg/g, plain whole-milk yogurt Trp 5.8 mg/g, firm tofu Cys 3.3 mg/g; and no amino-acid data for pollock, kefir, white bread)
- [x] 2.17 Assign an uncertainty grade (A/B/C) to every value: composition, digestibility and price grades in `foods_master.csv`; reviewed QC flags in `data/foods/qc_reviewed.csv`
- [ ] **GATE 2:** owner reviews `data/processed/foods_master.csv`; then dataset v1.0 is frozen and tagged in git

---

## v0.1: Food explorer (simple tool: foods, metrics, graphs)
- [x] A.1 Implement the core metrics (E, P, CHO, C, E€, P€, CHO€, P/E, F%E, M1000) in `src/metrics.py`, with unit tests
- [x] A.2 Implement the protein-quality adjustment (P_eff), allowing several Q definitions side by side
- [x] A.3 Implement Pareto-front computation (2D and n-D, with dominance ranks)
- [x] A.4 Implement candidate composite indices (S_bulk etc.) as **hypotheses**, with configurable weights
- [x] A.5 Graphs: nutrition density, economic value (protein/€ vs kcal/€), carbohydrate economics (CHO/€ vs protein/€), training efficiency, mass (g/1000 kcal), macronutrient ternary plot, 3D exploratory
- [x] A.6 Descriptive statistics by category, correlation matrix, PCA and clustering
- [x] A.7 Rank foods under each metric; compare rankings (Spearman, top-k overlap) to check H1, H2, H4 and H5
- [x] A.8 Streamlit app: dataset table, category filters, price scenario (median / P25 / P75), weight sliders, live rankings + graphs + Pareto highlighting, as-purchased vs as-consumed toggle
- [x] A.9 Export the configuration and results (CSV/JSON)
- [x] A.10 Publication-style figure styling (readable labels, colorblind-safe palette)
- [ ] **GATE v0.1:** the owner finds the explorer useful and understands the trade-offs it shows (owner to try `app/app.py` and comment on graphs)

## v0.2: Target calculator (profile → targets)
- [x] B.1 Profile schema (body, training, energy goal, priorities, overrides) as YAML; validation
- [x] B.2 `config/target_rules.yaml`: goal presets and rules from Phase 1, each with its literature source
- [x] B.3 `src/targets.py`: derive kcal, protein, carbohydrate and fat ranges plus safeguards; every target records where it came from (rule or override)
- [x] B.4 Energy expenditure: use the user's value if given, otherwise estimate it (BMR × PAL + training)
- [x] B.5 Feasibility check: detect conflicting targets and explain them (e.g. a high carbohydrate band with a low kcal target)
- [x] B.6 Archetype profiles in `config/profiles/`: owner, general adult, bodybuilder bulk, fat loss, Ironman athlete, price-insensitive pro
- [x] B.7 Unit tests: each archetype gives the expected targets
- [x] B.8 App: profile panel + preset selector + override fields; the food explorer uses the derived targets
- [x] B.9 AI export (owner request): `src/export.py` + app tab → `foods_ranked.csv` + `brief.md` (+ ZIP) for an LLM meal planner
- [ ] **GATE v0.2:** targets for all archetypes look sensible to the owner (and later to an expert)

## v1.0: Diet optimizer (food combinations)
- [x] C.1 LP: chosen objective (cost, mass, or a weighted mix; a cost weight of 0 is allowed) subject to kcal, protein + per-IAA, carbohydrate band, fat band and maximum mass
- [x] C.2 Run **without** safeguards first and record the degenerate optimum (the expected oil/sugar diet), the baseline for H11
- [x] C.3 Add the safeguards (§9.1): sugar cap, per-food maximum, maximum energy share per food, minimum number of distinct foods
- [x] C.4 Infeasibility diagnostics: when no diet satisfies everything, say which constraints conflict
- [x] C.5 Shadow prices and reduced costs: which constraints drive the objective, and how far each food is from entering the diet
- [x] C.6 MILP variant with discrete portions/packages
- [x] C.7 Multi-objective variant (cost vs mass vs protein quality), giving a Pareto set of diets via ε-constraint and/or NSGA-II
- [x] C.8 Compare amino-acid-constrained diets with Σ(P×Q)-constrained diets (H9)
- [x] C.9 Generate top-N diverse near-optimal combinations, not only the single optimum
- [x] C.10 Integrate into the app: profile → targets → optimal diet(s) with explanations
- [ ] **GATE v1.0:** optimized diets are plausible and explainable for every archetype; check H6, H10, H11 and H12

## v1.x: Analysis, comparison and publication
### Robustness
- [x] D.1 Price sensitivity (median vs P25/P75 scenarios, discount prices, per-retailer prices)
- [x] D.2 Protein-quality uncertainty (alternative DIAAS values / Q definitions)
- [x] D.3 Weight sensitivity for the composite indices (tornado plots, rank stability)
- [x] D.4 Safeguard and preset sensitivity: how optimal diets change with the fat band, sugar cap, per-food caps, protein and carbohydrate bands
- [x] D.5 Monte Carlo perturbation of composition and prices: how stable are the rankings and optimal diets?
- [x] D.6 Composition-database comparison (USDA vs Nordic) and Latvian vs generic prices (H7) (H7 not testable yet: needs a second country's prices)
### Comparison
- [x] D.7 Simple baselines: diets built greedily from protein/€, kcal/€ and protein/kcal rankings (H8)
- [x] D.8 Cross-archetype comparison: how optimal food sets differ by goal (H3)
- [x] D.9 Typical real diets (bodybuilding templates, endurance-athlete diets, typical Latvian/European diet): cost, mass, macronutrient fit
- [ ] D.10 (owner) Real-life test: the owner's optimized diet as an actual shopping basket (prices, practicality)
### Publication
- [x] D.11 Technical report (methods, data provenance, assumptions, limitations) → `reports/technical_report.md` (draft 1)
- [x] D.12 Clean reproducible repository (README, how to rerun everything, environment) → `run_all.sh` (< 1 min), README
- [ ] D.13 (owner, deferred: personal use for now) Contact a nutrition scientist; send the report and incorporate the feedback
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
| 2026-10-06 | 1.1–1.12 (first pass) | 63 sources verified (PubMed/Crossref/agency PDFs); REVIEW.md with numbers, evidence tags and decisions D1–D12; 2 handoff errors corrected; university list: thomas2016 (high), chungchunlam2020, burke2011 (manual download), garthe2011, mifflin1990, stigler1945 |
| 2026-10-06 | side exploration | Preview graphs (`notebooks/preview_graphs.py` → `figures/preview/`): 40 foods, prototype pipeline USDA × muleya2021 → DIAAS → useful protein; placeholder prices; found USDA amino-acid errors (→ task 2.16). Owner profile: male, 22 y |
| 2026-10-06 | 1.3, 1.5, 1.8, 1.13–1.15, GATE 1 | University PDFs read (Thomas 2016 confirms all CHO bands, fat 20–35 %, EA 45/30); OpenAlex originality search found prior athlete LP work → novelty narrowed to the combination; D1–D12 approved, presets frozen |
| 2026-10-06 | 2.1, 2.3, 2.10–2.12 (2.2 draft) | SCHEMA.md; 106-food list (71 CSP-priced, 35 own); CSP PCC010m 24 months downloaded; price normalization fixed; collection template + guide |
| 2026-10-06 | 2.4–2.9 (2.13 running) | Owner: Cenu Depo OK for personal use → polite collector `src/prices/cenudepo.py`; Frida 5.5 + SR28 downloaded; composition, yields, edible portions, digestibility maps for all 106 foods; unit conversions; price summary script |
| 2026-10-06 | 2.13–2.17 | Prices for 99/106 foods (CSP + Cenu Depo); parser handles single-shop pages, sold-by-weight items, loyalty rows; AA overrides for turkey, split peas, canned peas, smoked sausage; `src/build_master.py` → `foods_master.csv`; 14 tests pass. Finding: split peas ≈ €0.94/kg |
| 2026-10-07 | A.1–A.10 (v0.1) | `src/metrics.py` (quality definitions, price scenarios, Pareto masks/ranks, composite index, rank comparison), `src/analysis/explore.py` → `reports/v0.1_exploration.md`, 7 figures in `figures/v0.1/`, Streamlit app `app/app.py` (rankings, explorer, one-food day, food details, CSV/JSON export); 26 tests pass |
| 2026-10-07 | chart style | Owner feedback: graphs unreadable in dark theme → scientific style (white, full frame, inward ticks, grids both axes, framed legend), light app theme |
| 2026-10-07 | B.1–B.9 (v0.2) | `config/target_rules.yaml` (sourced), 6 archetype profiles, `src/targets.py` (REE → TDEE, surplus/deficit, protein, carb bands, fat, free sugars, conflicts, energy availability), app tab with profile form, AI export (CSV + brief + ZIP, also CLI); 39 tests pass |
| 2026-10-07 | v0.2 scenarios | 6 profiles × presets, robustness (quality × price) and normalization sensitivity → `reports/scenarios_v0.2.md`; found and fixed double-counting in 3 presets; goal-default ranking presets |
| 2026-10-07 | C.1–C.10 (v1.0) | `src/optimizer.py` (LP/MILP via HiGHS, per-AA digestible constraints, safeguards from `config/optimizer.yaml`, shadow prices, reduced costs, elastic conflict report, alternatives, cost–mass ε-front); `reports/v1.0_optimizer.md` for 6 profiles (H5, H9, H10, H11); app tab 'Diet optimizer'; 45 tests pass |
| 2026-10-07 | export | AI export gains `optimal_diet.csv` + baseline-diet section in the brief |
| 2026-10-07 | D.1–D.9, D.11, D.12 | `reports/v1x_robustness.md` (prices, pattern, weights, safeguards, Monte Carlo, Frida vs USDA → fixed Frida buckwheat protein), `reports/v1x_comparison.md` (H8 baselines, typical diets + closest-valid-diet mode), `reports/technical_report.md`, `run_all.sh`; 45 tests pass |
