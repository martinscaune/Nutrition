"""Price summary per food (task 2.14) → data/processed/prices_summary.csv

Method (data/SCHEMA.md, "Price normalization"):
- price_source = csp: mean of the last 12 monthly CSP averages; band = min–max of those months.
- price_source = own: Cenu Depo observations (personal-use phase, PROJECT.md §17), store-brand + standard tiers,
  regular and all-shopper discount prices; central = median of per-shop medians of €/kg; band = P25–P75.
- All prices are expressed per kg of EDIBLE purchased mass (unit_conversions.csv, then ÷ edible_portion).
- For csp foods that were also collected on Cenu Depo (cross-check), both values are reported.
"""
import csv
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DENSITY = {"milk": 1.03, "soy_drink": 1.03, "kefir": 1.03}  # g/ml for packs sold by volume


def csp_prices(foods, conv):
    rows = list(csv.reader(open(ROOT / "data/raw/csp/PCC010m_food_last24m.csv", encoding="utf-8-sig")))
    months = rows[0][1:]
    series = {r[0]: [float(x) if x.replace(".", "", 1).isdigit() else np.nan for x in r[1:]] for r in rows[1:]}
    out = {}
    for f in foods[foods.price_source == "csp"].itertuples():
        v = np.array(series[f.csp_item][-12:])
        v = v[~np.isnan(v)]
        g = conv.get(f.food_id, 1000.0)  # grams per CSP unit (default: item is priced per kg)
        per_kg = v * 1000.0 / g
        out[f.food_id] = {"csp_eur_per_kg": per_kg.mean(), "csp_lo": per_kg.min(), "csp_hi": per_kg.max(),
                          "csp_months": len(v), "csp_period": f"{months[-12]}–{months[-1]}"}
    return out


def cenudepo_prices():
    files = sorted(glob.glob(str(ROOT / "data/raw/cenudepo/*/observations_raw.csv")))
    if not files:
        return {}, pd.DataFrame()
    d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    d = d[d.tier.isin(["store_brand", "standard"]) & d.price_type.isin(["regular", "discount_all"])].copy()
    grams = d.pack_size.astype(float)
    ml = d.pack_unit == "ml"
    grams[ml] = d.pack_size[ml] * d.food_id[ml].map(DENSITY).fillna(1.0)
    grams[d.pack_unit == "pcs"] = d.pack_count[d.pack_unit == "pcs"].astype(float) * 58.0  # eggs, size M gross
    d["eur_per_kg"] = d.price_eur / grams * 1000.0
    d = d[np.isfinite(d.eur_per_kg) & (d.eur_per_kg > 0)]
    out = {}
    for fid, g in d.groupby("food_id"):
        shop_medians = g.groupby("shop").eur_per_kg.median()
        out[fid] = {"own_eur_per_kg": shop_medians.median(), "own_p25": g.eur_per_kg.quantile(0.25),
                    "own_p75": g.eur_per_kg.quantile(0.75), "own_n_obs": len(g), "own_n_shops": g.shop.nunique(),
                    "own_n_products": g.product_name.nunique(), "own_collected": g.date_collected.max()}
    return out, d


def main():
    foods = pd.read_csv(ROOT / "data/foods/foods.csv")
    conv = pd.read_csv(ROOT / "data/foods/unit_conversions.csv").set_index("food_id").grams_per_unit.to_dict()
    edible = pd.read_csv(ROOT / "data/foods/yields.csv").set_index("food_id").edible_portion.to_dict()
    csp = csp_prices(foods, conv)
    own, obs = cenudepo_prices()
    rows = []
    for f in foods.itertuples():
        r = {"food_id": f.food_id, "price_source": f.price_source, **csp.get(f.food_id, {}), **own.get(f.food_id, {})}
        e = edible.get(f.food_id, 1.0)
        if f.price_source == "csp":
            c, lo, hi, grade = r.get("csp_eur_per_kg"), r.get("csp_lo"), r.get("csp_hi"), "A"
        else:
            c, lo, hi = r.get("own_eur_per_kg"), r.get("own_p25"), r.get("own_p75")
            n = r.get("own_n_obs", 0) or 0
            grade = "A" if n >= 3 and (r.get("own_n_shops", 0) or 0) >= 2 else ("B" if n >= 1 else "")
        r.update({"eur_per_kg_purchased": c, "eur_per_kg_edible": c / e if c else np.nan,
                  "band_lo_edible": lo / e if lo else np.nan, "band_hi_edible": hi / e if hi else np.nan,
                  "edible_portion": e, "price_grade": grade})
        rows.append(r)
    out = pd.DataFrame(rows)
    (ROOT / "data/processed").mkdir(exist_ok=True)
    out.to_csv(ROOT / "data/processed/prices_summary.csv", index=False, float_format="%.4g")
    if len(obs):
        obs.to_csv(ROOT / "data/processed/cenudepo_observations_clean.csv", index=False, float_format="%.4g")
    missing = out[out.eur_per_kg_edible.isna()].food_id.tolist()
    print(f"{len(out)} foods; priced: {out.eur_per_kg_edible.notna().sum()}; missing: {missing}")
    x = out[out.csp_eur_per_kg.notna() & out.own_eur_per_kg.notna()]
    if len(x):
        x = x.assign(diff_pct=(x.own_eur_per_kg / x.csp_eur_per_kg - 1) * 100)
        print("\nCross-check Cenu Depo (median of shop medians) vs CSP 12-month mean, € per purchased kg:")
        print(x[["food_id", "csp_eur_per_kg", "own_eur_per_kg", "diff_pct", "own_n_obs", "own_n_shops"]].round(2).to_string(index=False))
    print("\nOwn-price foods:")
    y = out[out.price_source == "own"]
    print(y[["food_id", "own_eur_per_kg", "own_p25", "own_p75", "own_n_obs", "own_n_shops", "own_n_products", "price_grade"]]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
