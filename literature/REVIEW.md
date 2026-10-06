# Literature review: numbers we will use (Phase 1, first pass 2026-10-06)

Source IDs refer to [SOURCES.md](SOURCES.md).
**Evidence tags** (how each number was checked):
- **[P]** read in the primary source (full text, table or equation image)
- **[A]** abstract only
- **[S]** a secondary source quoting the primary
- **[U]** unverified or our own assumption; must be checked or justified

Section numbers match PLAN.md tasks. The decisions this review leads to are collected in **§10 (Proposed decisions for GATE 1)**.

---

## 1. Protein requirements (task 1.2)

| Population / goal | Daily protein | Source | Tag |
|---|---|---|---|
| General adult (sedentary), population reference intake | 0.83 g/kg | efsa2012 | [S] |
| Resistance training, maximizing fat-free-mass gain | breakpoint **1.62 g/kg (95 % CI 1.03–2.20)**; "no further gains beyond 1.62" | morton2018 (49 RCTs, n = 1863) | [P] |
| Same, second meta-analysis | effect on lean mass clear at **≥ 1.6 g/kg** in < 65 y with resistance exercise (SMD 0.30), weaker at 1.2–1.59 (SMD 0.15, n.s.) | nunes2022 (62 studies) | [P] |
| Exercising individuals (ISSN) | **1.4–2.0 g/kg** | jager2017 | [A] |
| Resistance-trained, in an energy deficit | **2.3–3.1 g/kg** (body mass) | jager2017 | [A] |
| Natural bodybuilders, contest preparation | **2.3–3.1 g/kg of lean body mass** | helms2014 | [P] |
| Off-season bodybuilders | **1.6–2.2 g/kg**; 0.40–0.55 g/kg per meal | iraki2019 | [P] |
| Athletes, general (ACSM/AND/DC) | **1.2–2.0 g/kg**; 0.3 g/kg per meal | thomas2016 | [P] |
| Endurance athletes (indicator amino acid oxidation method) | estimated average requirement **1.65**, recommended **1.83 g/kg** (n = 6 men, the day after a 20 km run) | kato2016 | [P] |

**Per-meal distribution** (v3.0 meal planning): 0.4 g/kg/meal × ≥ 4 meals reaches 1.6 g/kg; the 2.2 g/kg upper limit means ≤ 0.55 g/kg/meal (schoenfeld2018 [P]). The 20–25 g/meal "maximum" applies to fast proteins taken alone (schoenfeld2018 [P]). trommelen2023 [A] shows the anabolic response to 100 g has no upper limit in magnitude or duration. A per-meal leucine threshold is plausible (churchward2014) but the exact number is **[U]**, so it is deferred to v3.0.

**Takeaways for the model**
- For muscle gain, 1.6 g/kg is the best-supported point estimate and 2.2 g/kg a sensible upper limit for the range. This matches PROJECT.md §7.2.
- Endurance athletes need more than older guidelines said (1.65–1.83 g/kg, kato2016), so the "hybrid" preset at 1.6–2.2 g/kg is consistent with both literatures.
- **Correction to PROJECT.md §7.2:** the fat-loss preset protein "1.6–2.4 (Helms 2014)" was misattributed. Helms gives 2.3–3.1 g/kg **lean body mass**; Jäger gives 2.3–3.1 g/kg **body mass** for resistance-trained people in a deficit. See decision D3.

## 2. Energy targets: surplus and deficit (task 1.3)

**Surplus (muscle gain)**
- Novice/intermediate: **~10–20 % above maintenance**, gaining **~0.25–0.5 % of body mass per week**. Advanced: **+5–10 %, ~0.25 %/week** (iraki2019 [P]).
- 5 % vs 15 % surplus in trained lifters over 8 weeks: faster gain in body mass mainly increased **fat**, not muscle thickness or squat 1RM (helms2023 [A]).
- Elite athletes with a planned surplus (3585 vs 2964 kcal): body mass +3.9 % vs +1.5 %, **no difference in lean-mass gain**, fat mass +15 % vs +3 % (garthe2013 [A]).
- The optimal surplus has never been validated; textbook "energy content of tissue" calculations are unreliable (slater2019 [A]).
- **Takeaway:** a bigger surplus mostly buys fat. The default should be modest, about 10 % (5–15 %), set as a rate of 0.25–0.5 % of body mass per week.

**Deficit (fat loss)**
- **0.5–1 % of body mass per week** (helms2014 [P]).
- Elite athletes at 0.7 %/week **gained** lean mass (+2.1 %), while those at 1.4 %/week did not (garthe2011 [A]).
- **Takeaway:** default 0.7 %/week, with an allowed range of 0.5–1.0 %.

**Low energy availability (RED-S / REDs)** (mountjoy2018, mountjoy2023 [A]): endurance athletes in a deficit risk health and performance problems. Thomas 2016 [P]: energy availability (EA) of **45 kcal/kg FFM/day** is associated with energy balance, and chronic EA **below 30 kcal/kg FFM/day** with impaired health and performance. The tool should **warn** (not block) when the planned intake implies EA < 30. How the 2023 consensus qualifies these thresholds is not yet checked (the PDF blocks automated download; low priority because v0.2 only uses them for a warning).

## 3. Energy-expenditure estimation (task 1.4)

| Equation | Formula (REE, kcal/day) | Use | Tag |
|---|---|---|---|
| Mifflin-St Jeor | 9.99·W + 6.25·H(cm) − 4.92·A + 166·sex − 161; simplified: men 10·W + 6.25·H − 5·A + 5, women … − 161 | general population | [P] (mifflin1990) |
| ten Haaf weight-based | **11.936·W + 587.728·H(m) − 8.129·A + 191.027·sex + 29.279** | recreational athletes, 18–35 y | [P] (equation image) |
| ten Haaf FFM-based | **22.771·FFM + 484.264** | athletes with known fat-free mass | [P] |
| Cunningham | 22·FFM + 500 | athletes with known fat-free mass | [P] |

- Accuracy in recreational athletes, predictions within ±10 % (tenhaaf2014 [P]): Cunningham 85 % (men) / 78 % (women); ten Haaf weight-based 83 % / 76 %. **Mifflin, Harris-Benedict, WHO, Schofield and Owen were all below 50 %.**
- Physical activity level (PAL) bands (fao2004 [P]): sedentary/light **1.40–1.69**, active **1.70–1.99**, vigorous **2.00–2.40**; PAL above 2.40 is hard to sustain.
- **Example (owner: male, 22 y, 76 kg, 186 cm):** ten Haaf REE = 11.936·76 + 587.728·1.86 − 8.129·22 + 191.027 + 29.279 ≈ **2042 kcal** (Mifflin: 1818 kcal). With PAL 1.70–1.99 ("active"), daily expenditure would be **≈ 3470–4060 kcal**. The self-reported 3000 kcal implies a PAL of about 1.47, which looks low for 6–9 h/week of triathlon training plus strength work. This is a flag, not a conclusion: the user's value is used if given, and weight tracking settles it in v3.0.
- How to map training hours to PAL, or add exercise energy factorially (MET-based), is **[U]** and our modeling choice. See decision D5.

## 4. Carbohydrate (task 1.5)

| Training load | g/kg/day | Source | Tag |
|---|---|---|---|
| Light / low intensity or skill-based | 3–5 | thomas2016 (Table 2) | [P] |
| Moderate exercise, ~1 h/day | **5–7** | thomas2016 (Table 2) | [P] |
| Moderate–high intensity, 1–3 h/day | **6–10** | thomas2016 (Table 2) | [P] |
| Extreme, 4–5 h/day moderate–high intensity | **8–12** | thomas2016 (Table 2) | [P] |
| Strength athletes, off-season | **≥ 3–5** | iraki2019 | [P] |
| General adult | **45–60 % of energy** | efsa2010c | [S] |

- During exercise: 30–60 g/h for longer sessions, **up to 90 g/h for events over 2.5 h** (burke2011 [A]). This becomes a v2.0/v3.0 "training fuel" allowance; it sits outside the daily food optimization.
- **Hours/week → band mapping (our proposal, [U]):** average hours/day = (hours/week) / 7. Under 0.5 h/day = light; 0.5–1.5 h/day = moderate; 1.5–3 h/day = high; over 4 h/day = extreme. Intensity can move a person one band up or down. Owner: 6–9 h/week = 0.86–1.29 h/day → **moderate, 5–7 g/kg (380–530 g/day)**.

## 5. Fat and sugar: the safeguards (task 1.6)

- Fat for adults: **20–35 % of energy** (efsa2010f [S]). Athletes: fat "typically range[s] from 20%–35% of total energy intake"; chronic intakes below 20 % are discouraged (thomas2016 [P]). Off-season bodybuilders: 0.5–1.5 g/kg or 20–35 % (iraki2019 [P]). Contest preparation: 15–30 % (helms2014 [P]).
- Free sugars: **< 10 % of energy** (strong recommendation); further reduction below 5 % is conditional (who2015 [S]). Free sugars = added mono- and disaccharides plus sugars in honey, syrups and fruit juices; **not** sugars in intact fruit or milk. The dataset needs a "free sugar" field, which USDA does not provide directly; see decision D8.
- **Takeaway:** fat 20–35 % E and free sugars < 10 % E are both supported by EU/WHO guidance, so safeguards 1 and 2 (PROJECT.md §9.1) are evidence-based, not arbitrary. Per-food caps (safeguard 3) remain our judgment.

## 6. Protein quality (tasks 1.7–1.9)

**Definitions (fao2013 [P])**
- DIAAS = min over the indispensable amino acids (IAA) of [mg of digestible IAA in 1 g of the food's protein] / [mg of the same IAA in 1 g of the reference protein] × 100.
- Digestibility should be **true ileal digestibility per amino acid**, preferably measured in humans, otherwise in growing pigs, otherwise in rats.
- **Truncation:** values above 100 % are **not** truncated for single foods. They are truncated when calculating mixed diets.
- **For mixed diets, DIAAS is not additive.** Supply has to be calculated from the amounts of each IAA in the foods eaten (moughan2024 [P]). This confirms our approach in PROJECT.md §5.
- FAO itself said in 2013 that digestibility data were "insufficient to support application in practice" (fao2013 [P]). This has improved since (see data below).

**Reference scoring pattern** (fao2013 Table 5 [P]), in mg per g of protein:

| | His | Ile | Leu | Lys | SAA (Met+Cys) | AAA (Phe+Tyr) | Thr | Trp | Val |
|---|---|---|---|---|---|---|---|---|---|
| Older child, adolescent, adult (3+ y) | 16 | 30 | 61 | 48 | 23 | 41 | 25 | 6.6 | 40 |
| Young child (0.5–3 y), "regulatory" pattern | 20 | 32 | 66 | 57 | 27 | 52 | 31 | 8.5 | 43 |

For product labelling, FAO recommends the 0.5–3 y pattern for all foods. For scoring the diets of adults, the 3+ y pattern applies. **Herreman 2020 used the 0.5–3 y pattern, so its values are conservative for adults.**

**Adult IAA requirements, mean** (who2007 Table 23 [P]), mg per kg per day (mg per g protein):
His 10 (15) · Ile 20 (30) · Leu 39 (59) · Lys 30 (45) · Met+Cys 15 (22) · Phe+Tyr 25 (38) · Thr 15 (23) · Trp 4 (6) · Val 26 (39). Total 184 mg/kg/day. Safe intake = mean × **1.24**.
These are for **sedentary maintenance** at 0.66 g protein/kg. For an athlete eating 1.6 g/kg, a reference pattern scaled to the protein target is about twice as strict (e.g. leucine 61 mg/g × 1.6 g/kg ≈ 98 mg/kg vs the WHO safe 48 mg/kg).

**Example DIAAS values**
- Ingredient level, 0.5–3 y pattern (herreman2020 [P]): pork 117, casein 117, egg 101, potato 100, soy 91, whey 85, pea 70, oat 57, wheat 48, rice 47, corn 36. Cereals are limited by **lysine**, legumes by **Met+Cys**.
- Blends reach 100 when complementary (e.g. pea/wheat/potato 25/25/50).
- Cooked beef (pig model): raw, boiled and pan-fried 97–99, roasted 91, grilled 80 (hodgkinson2018 [A]). **Cooking matters.**
- Six cooked pulses, 3+ y pattern (Nutrients 2020;12:3831 [S]): kidney bean 88, mung 86, chickpea 76, pea 68, adzuki 64, broad bean 60.

**Does DIAAS predict muscle building?** Not directly. 30 g pea or corn protein produced the same muscle protein synthesis as 30 g milk protein in young men (pinckaers2024pea, pinckaers2024corn [A]). This suggests **quality matters most when protein intake is marginal and little when it is plentiful**. Prediction for our model: in bulking diets with ≥ 1.6 g/kg, the amino-acid constraints will rarely be binding unless the diet is dominated by cereals (lysine). This is testable (relates to H1 and H9).

**Long-term training studies (added 2026-10-07):** 12 weeks of resistance training with ~1.6 g/kg/day protein from an exclusively plant-based diet (whole foods + soy isolate) produced the same gains in leg lean mass (+1.2 vs +1.2 kg), muscle cross-sectional area and strength as a protein-matched omnivorous diet (hevia2021 [A]). A vegan high-protein diet supported the same daily muscle protein synthesis and hypertrophy as an omnivorous one (monteyne2023 [A]); a plant protein blend matched milk protein acutely (pinckaers2023blend [A]). **Implication:** plant protein is "less useful per gram" (lower DIAAS, which our useful-protein metric already applies), but once total protein is adequate and sources are mixed, muscle gain does not appear to depend on the source.

**Data sources for per-food digestibility (task 1.8)**
- **muleya2021** (Mendeley Data, CC BY 4.0): more than 100 foods from 32 references, per-amino-acid true ileal digestibility, DIAAS for several reference patterns. Where amino acids were missing, averages were imputed and flagged. **Candidate primary source; download and audit in Phase 2.**
- PROTEOS (Riddet Institute): 100 foods as consumed, completed in 2023. A public database was announced but no download was found yet [U].
- moughan2024: more than 400 foods have published ileal data but they are scattered, and "there is a need to bring these … into a single readily accessible database".
- **Takeaway:** USDA amino-acid composition × per-amino-acid digestibility from muleya2021 (matched by food; otherwise the food-group mean, uncertainty grade C).

## 7. Diet optimization (task 1.10)

- The diet problem: stigler1945. Pure cost-minimization gives monotonous, absurd diets.
- 52 LP studies reviewed (vandooren2018 [A]): nutritional, then cost, then **acceptability**, then ecological constraints were added over time. LP "shows weaknesses" with few foods or few constraints. **"No study has provided the ultimate solution to calculating acceptability."**
- 67 studies reviewed (gazan2018 [A]): infeasibility is informative. It signals incompatible recommendations, a too-monotonous food list, or missing nutrient-rich foods. This supports reporting conflicting constraints rather than failing silently (PLAN C.4).
- Acceptability by **minimizing deviation from a person's observed diet**, for 1171 French adults, met 32 nutrient constraints while replacing fewer than 5 foods in half of the diets (maillot2010 [A]). **Strong candidate for v2.0 "taste/acceptability".**
- LP used to **validate a food-level nutrient-profiling metric**: 81 % of foods selected by LP had good "nutritional quality for price" vs 39 % of non-selected foods (maillot2008 [A]). **This is the template for our H8** (do simple food metrics predict what the optimizer picks?).
- Least-cost diets of 883 foods with 29 nutrients for a New Zealand adult cost NZ$3.23/day. The first-limiting nutrients were micronutrients, not protein; the model is publicly available (chungchunlam2021 [A]). In the US, animal foods were needed for minimum cost (chungchunlam2020, title only).
- In French adults, roughly 45–60 % of protein must be animal-based to meet all other nutrient recommendations at no extra cost (vieux2022 [A]). This matters for v2.0, when micronutrients enter.

**Originality check (task 1.14; PubMed + OpenAlex, 2026-10-06).** The first PubMed-only check was too narrow: **athlete diet LP papers exist**, mostly in operations-research and low-tier venues:
- magdic2013: LP weekly menus for a recreational bodybuilder (cost, mass, energy, fixed 43:30:27 C:F:P ratio; LINDO vs Excel).
- mochabonilla2020 (conference chapter) and ijbpas2023: least-cost LP diets for athletes with energy/macro constraints.
- dimina2022: LP to combine plant proteins towards target amino-acid profiles (ingredient blends, no cost, no athletes).
- moreno2026 (arXiv): mixed-integer goal programming for meals (integer servings, soft targets against infeasibility). It reports that none of 56 reviewed diet-optimization papers combined integer and goal programming.
- chungchunlam2020/2021, maillot2008/2010, vieux2022: population least-cost / acceptability LP (no athletic targets).

**What none of them combine** (our defensible contribution): (1) goal presets taken from sports-nutrition position stands, with every target sourced and overridable; (2) **diet-level digestible indispensable amino acid constraints** (DIAAS-consistent, complementarity-aware) instead of crude protein; (3) **food mass** as an objective/constraint next to cost; (4) **observed local (Latvian) prices with normalization and uncertainty**; (5) robustness analysis (Monte Carlo, safeguard sensitivity) and comparison against simple ratio baselines. We must cite the prior athlete LP work and claim only this combination. A Scopus search by the owner (university access) is optional extra assurance.

## 8. Food cost vs nutritional value (task 1.11)

- Cost per nutrient and nutrient density per € (drewnowski2010 [A]); "Affordable Nutrient Density" = NRF9.3 score divided by price per 100 kcal (drewnowski2024 [P]).
- US prices per 100 g protein: pulses $2.51, pork $2.00, chicken $2.16, shellfish $9.22 (drewnowski2024 [P]). **Cheap animal proteins can rival pulses, which is why local prices matter (H7).**
- Protein cost adjusted for PDCAAS: dairy is comparable to eggs and beans (drewnowski2025 [A]). This is a precedent for quality-adjusted protein cost, our P_eff/€.

## 9. Gaps that remain
- ~~thomas2016 full text~~ → done 2026-10-06 (all bands [P]).
- How mountjoy2023 qualifies the EA thresholds (PDF download blocked for automation; owner may download; low priority).
- EFSA statement on safe upper protein intakes [U].
- Inventory of what muleya2021 actually contains (Phase 2, task 2.9).
- ~~Thorough originality search~~ → done via OpenAlex (see §7); Scopus optional.

---

## 10. Decisions for GATE 1. **APPROVED by owner 2026-10-06 (all D1–D12 as proposed)**

| # | Decision | Proposal | Basis |
|---|---|---|---|
| D1 | Protein target, muscle gain | **1.6 g/kg minimum, 2.2 g/kg upper**; default 1.8 | morton2018, nunes2022, iraki2019 |
| D2 | Protein target, endurance / hybrid | endurance 1.4–2.0 (default 1.6); hybrid as muscle gain | thomas2016, jager2017, kato2016 |
| D3 | Protein target, fat loss | 2.3–3.1 g/kg **lean** mass if body fat is known; otherwise **2.2–2.6 g/kg body mass** (≈ Helms' range at ~15 % body fat; our derivation [U]) | helms2014, jager2017 |
| D4 | Protein, general adult | minimum 0.83 g/kg; no upper limit in v1.0 | efsa2012 |
| D5 | Energy expenditure | the user's value if given; otherwise ten Haaf (athletes, 18–35 y) or Mifflin (others) × PAL from training hours (mapping [U]) | tenhaaf2014, fao2004 |
| D6 | Surplus / deficit defaults | gain: 0.25–0.5 % BM/week (default ~10 % surplus; 5 % if advanced); loss: 0.7 %/week (range 0.5–1.0) | iraki2019, helms2023, garthe2011 |
| D7 | Carbohydrate bands | ACSM bands; hours/week → band mapping as in §4; strength-only users ≥ 3–5 g/kg; general adult 45–60 % E | thomas2016, iraki2019, efsa2010c |
| D8 | Fat and sugar safeguards | fat 20–35 % E (fat loss allowed down to 15 %); free sugars < 10 % E; free-sugar content estimated per food (added sugar from product labels/category rules) | efsa2010f, who2015, helms2014 |
| D9 | Protein-quality constraint | **Primary: for each IAA, Σ digestible IAA ≥ (FAO 3+ y pattern) × protein target.** In words: the diet must supply at least as much of every digestible essential amino acid as the target amount of ideal reference protein would. Linear, handles complementarity. Sensitivity runs: (a) crude protein only, (b) Σ P × DIAAS (for H9), (c) the WHO 2007 absolute safe intake (× 1.24) as a floor | fao2013, who2007, moughan2024 |
| D10 | Reference pattern | FAO 2013 "older child, adolescent, adult"; the 0.5–3 y pattern as a sensitivity case | fao2013 |
| D11 | Digestibility data | USDA amino acids × muleya2021 per-AA true ileal digestibility; food-group fallback = grade C | muleya2021, moughan2024 |
| D12 | Per-meal leucine / protein distribution | not in v1.0 (v3.0 meal planning) | schoenfeld2018, trommelen2023 |
