# Price collection guide (task 2.13)

**Goal:** prices for the foods that the official CSP table does not cover, plus a few CSP foods as a cross-check. The results go into [observations.csv](observations.csv), one row per product seen. The method is in [../SCHEMA.md](../SCHEMA.md).

## Rules
1. **Record what is on the shelf or page; don't pick only the cheapest.** For each food, note **every comparable product** in the store (store brand + standard brands). Mark premium/organic as such: they are kept, but only used for scenarios.
2. **Shops:** at least **2, ideally 3+ retailers** per food (Rimi, Maxima, Lidl, top!, Mego, Elvi, …). Online shops (Barbora, Rimi e-veikals) count; set `channel = online` and paste the URL.
3. **Price type:** `regular` = normal price; `discount_all` = sale price for everyone (also note the regular price in `notes`); `loyalty` = card-only price.
4. **Pack size:** net mass in grams. For canned food, use the drained weight if printed, and say which in `notes`.
5. Copy the **€/kg printed on the label** into `unit_price_eur_per_kg_shown` (we use it to cross-check).
6. **Date** as YYYY-MM-DD. `obs_id` is just 1, 2, 3, …

## Foods to collect (own price source)
| food_id | product spec |
|---|---|
| rice_brown | brown rice, plain |
| millet | hulled millet |
| bulgur | bulgur wheat |
| couscous | plain couscous |
| muesli | muesli, no added sugar |
| crispbread | rye crispbread |
| sweet_potato | sweet potato |
| lentils_red | red split lentils |
| lentils_green | green or brown lentils |
| peas_split | yellow or green split peas |
| peas_grey | Latvian grey peas, dry |
| chickpeas_dried | dried chickpeas |
| beans_canned | canned beans, drained |
| chickpeas_canned | canned chickpeas, drained |
| tofu | firm tofu, plain |
| soy_chunks | dry textured soy protein |
| soy_drink | soy drink, unsweetened |
| chicken_thigh_fillet | boneless chicken thigh |
| turkey_fillet | turkey breast fillet |
| chicken_liver | chicken liver |
| beef_steak | lean beef steak (round/sirloin) |
| tuna_canned | tuna in water/brine, drained |
| skyr | skyr or high-protein plain yogurt |
| cottage_cheese | granular cottage cheese |
| peanut_butter | peanut butter, 100 % peanuts |
| sunflower_seeds | hulled sunflower seeds |
| pumpkin_seeds | hulled pumpkin seeds |
| walnuts | walnut kernels |
| almonds | almonds |
| hazelnuts | hazelnut kernels |
| flaxseed | whole flaxseed |
| whey_protein | whey protein concentrate ~80 %, unflavoured or flavoured |
| pea_protein | pea protein isolate |
| mass_gainer | carbohydrate-protein gainer powder |
| maltodextrin | maltodextrin powder |

## Cross-check foods (also in CSP; 1–2 observations each are enough)
oats_flaked, rice_white, chicken_fillet, eggs, curd, pasta_wheat, pork_minced, milk

## Example rows
```
obs_id,food_id,date,retailer,channel,product_name,brand,tier,pack_size_g,price_eur,price_type,unit_price_eur_per_kg_shown,url,collector,notes
1,lentils_red,2026-10-10,rimi,store,Sarkanās lēcas,Rimi,store_brand,500,1.49,regular,2.98,,martins,
2,lentils_red,2026-10-10,rimi,store,Red lentils,Bonduelle,standard,400,2.19,discount_all,5.48,,martins,regular price 2.79
```
