# Data schema (task 2.1)

**Principles:**
- **Curated** files (`data/foods/`) are edited by hand or by documented scripts. **Generated** files (`data/processed/`) are rebuilt by code and never edited by hand.
- **Raw** files (`data/raw/`) are never modified; see [raw/MANIFEST.md](raw/MANIFEST.md).
- Every value traces back to a source and carries an uncertainty grade.
- Units are fixed per column and written into the column name (`_g`, `_kcal`, `_eur`, `_per_100g`, …).

## Uncertainty grades (used in every `grade` column)
| Grade | Composition / digestibility | Price |
|---|---|---|
| **A** | analytical value from a national composition database for this exact food and state; digestibility measured in humans or pigs for this food | CSP official monthly average (≥ 6 of the last 12 months available), or ≥ 3 own observations from ≥ 2 retailers |
| **B** | database value for a closely matching food or state, or a product label; digestibility measured for the same food in another form | 1–2 own observations, or CSP with < 6 months |
| **C** | borrowed from a related food, imputed, or a food-group average (always with a note saying why) | estimate (never used in final analysis) |

## Curated files

### `foods/foods.csv`: master food list
| Column | Type | Meaning |
|---|---|---|
| `food_id` | str, unique, snake_case | stable key used everywhere |
| `name_en`, `name_lv` | str | display names |
| `category` | enum | cereals · bread · potatoes · legumes · soy · meat · processed_meat · fish · eggs · dairy · nuts_seeds · fruit · vegetables · ingredients · sweets_snacks · supplements |
| `role` | enum | `core` (ranked and optimized) · `ingredient` (shown, excluded from rankings; PROJECT §9.1) · `snack` (shown for comparison) · `supplement` (side analysis; PROJECT §12) |
| `product_spec` | str | the comparable product definition used for prices (e.g. "rolled oats, plain, non-organic") |
| `purchase_state` | str | how it is bought (dry, raw, canned drained, ready-to-eat, …) |
| `eaten_state` | str | how it is eaten (boiled, roasted, as is, …) |
| `price_source` | enum | `csp` (official CSP average, table PCC010m) · `own` (our own observations) |
| `csp_item` | str | exact CSP item name (codes were renumbered in Feb 2026, so names are the key) |
| `notes` | str | free text |

### `foods/composition_map.csv`: which database entry describes each food (one row per food)
`food_id, comp_db {frida, usda_sr, label}, comp_id, yield_usda_raw, yield_usda_cooked, aa_override_db, aa_override_id, grade, notes`
- **Purchased-state composition** comes from `comp_db/comp_id`. Priority: **Frida 5.5** (Danish, analytical, Nordic foods, full amino acids, *available* carbohydrate and *free sugars*) > USDA SR Legacy > product label.
- **Eaten state** = purchased composition ÷ cooking yield. The yield is `protein_raw / protein_cooked` of the USDA raw↔cooked pair (`yield_usda_raw`, `yield_usda_cooked`), since protein is conserved; it can be overridden in `yields.csv`. Known limitation: fat dripping from meat is ignored, which slightly overestimates kcal of eaten fatty meat.
- `aa_override_*`: amino-acid profile (mg per g protein) borrowed from another entry when the own profile is missing or implausible (task 2.16).
- Resolved and checked by `src/data/resolve.py` → `data/processed/composition_resolved.csv` (descriptions, yields, Atwater check, flags).

### `foods/digestibility_map.csv`: per-amino-acid true ileal digestibility (D11)
`food_id, source {muleya2021}, source_row, source_food_name, model {human, pig, human_predicted}, is_proxy, grade, notes`

### `foods/yields.csv`: edible portion and yield overrides (only foods that need them)
`food_id, edible_portion, edible_source, yield_override, yield_note`
- Edible portions come from **USDA SR28 refuse %** (`data/raw/usda/sr28`) where available, otherwise marked ESTIMATE (grade C).
- `edible_portion` = 1 − refuse (bone, shell, peel), as a fraction of the purchased mass.
- `yield_eaten_per_purchased` = eaten mass / purchased edible mass (e.g. dry rice → boiled ≈ 2.5–3; raw meat → roasted ≈ 0.7). It is derived from the matching USDA raw/cooked pair or the USDA Table of Cooking Yields (2012).

### `foods/unit_conversions.csv`: non-kg price units
`food_id, unit {pcs, l, pack}, grams_per_unit, basis {gross, drained, edible}, source, grade`
Examples: eggs per 10 pcs, milk and oil per litre (density), CSP pasta per 500 g, canned food drained weight, ice cream per 1000 ml.

### `prices/csp_map.csv`
`food_id, csp_item, csp_unit, grams_per_csp_unit, notes`

### `prices/observations.csv`: our own price observations (task 2.12)
| Column | Meaning |
|---|---|
| `obs_id` | running integer |
| `food_id` | key into foods.csv |
| `date` | ISO date of observation |
| `retailer` | rimi · maxima · lidl · top · mego · elvi · citro · other |
| `channel` | `store` · `online` · `leaflet` |
| `product_name`, `brand` | as shown on the shelf or page |
| `tier` | `store_brand` · `standard` · `premium` · `organic` |
| `pack_size_g` | net mass in g (drained mass for canned food if declared; note which) |
| `price_eur` | shelf price paid for the pack |
| `price_type` | `regular` · `discount_all` (sale for everyone) · `loyalty` (card-only) |
| `unit_price_eur_per_kg_shown` | the €/kg printed on the label, used as a cross-check |
| `url` | product page if online |
| `collector` | who recorded it |
| `notes` | |

## Generated files (`data/processed/`)
- `prices_summary.csv`: per food: central €/kg (as purchased, edible portion), uncertainty band, n, source, grade.
- `foods_master.csv`: one row per food with composition (purchased and eaten), DIAAS, useful protein, prices and every metric in PROJECT §4. **This is the input to the app and the optimizer.**

## Price normalization (task 2.11; supersedes the first draft in PROJECT §12.1)
1. **CSP foods:** central price = **mean of the last 12 monthly CSP averages**, which smooths seasonality. Band = min–max of those 12 months. CSP averages already pool about 2,000 outlets, include sales offered to all shoppers, and exclude loyalty-only prices (CSP CPI methodology).
2. **Own-observation foods:** central price = **median of regular and all-shopper discount prices**, aggregated by retailer first (median of retailer medians), store brand and standard tiers only. Band = P25–P75 of the observations. Loyalty and premium/organic prices are kept for scenarios only.
3. **Cross-check:** for 5–10 CSP foods we also collect our own observations to quantify how far the two methods differ.
4. All prices are converted to **€ per kg of edible purchased mass** via `unit_conversions.csv` and `yields.csv`.
