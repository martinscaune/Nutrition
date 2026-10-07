"""Country prices from Latvian prices × Eurostat food price level indices (PLI), by food category.

price_country(food) = price_LV(food) × PLI_country(category) / PLI_LV(category)

Source: Eurostat prc_ppp_ind, PLI (EU27_2020 = 100), latest year (data/prices/eurostat_pli_food.csv, raw JSON in
data/raw/eurostat/). PLIs compare the price of a whole category basket between countries, so this captures
differences BETWEEN categories (e.g. meat is ~28 % dearer in Denmark than in Latvia relative to EU levels) but not
product-level differences WITHIN a category. Approximate; Latvia remains the observed reference.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PLI_FILE = ROOT / "data/prices/eurostat_pli_food.csv"
RAW = ROOT / "data/raw/eurostat/prc_ppp_ind_food.json"   # JSON-stat 2.0 from the Eurostat dissemination API
BASE = "LV"

# food category (data/foods/foods.csv) → Eurostat ECOICOP food group
CATEGORY_TO_PLI = {
    "cereals": "Bread and cereals", "bread": "Bread and cereals",
    "meat": "Meat", "processed_meat": "Meat", "fish": "Fish",
    "eggs": "Milk, cheese and eggs", "dairy": "Milk, cheese and eggs",
    "potatoes": "Fruits, vegetables, potatoes", "legumes": "Fruits, vegetables, potatoes",  # pulses are vegetables in ECOICOP
    "soy": "Fruits, vegetables, potatoes", "fruit": "Fruits, vegetables, potatoes",
    "vegetables": "Fruits, vegetables, potatoes", "nuts_seeds": "Fruits, vegetables, potatoes",  # nuts are fruit in ECOICOP
    "supplements": "Other food", "sweets_snacks": "Other food", "ingredients": "Other food",
}
FOOD_TO_PLI = {  # overrides by food
    "sunflower_oil": "Oils and fats", "rapeseed_oil": "Oils and fats", "olive_oil": "Oils and fats",
    "butter": "Oils and fats", "margarine": "Oils and fats", "wheat_flour": "Bread and cereals",
    "cake": "Bread and cereals", "crisps": "Fruits, vegetables, potatoes", "ice_cream": "Other food",
}


# Latvian specialities assumed unavailable elsewhere (excluded from other countries' food lists)
LV_ONLY = {"peas_grey", "bread_rye_fine", "curd_snack"}


@lru_cache
def pli():
    d = pd.read_csv(PLI_FILE).set_index("geo")
    cols = [c for c in d.columns if c not in ("country", "year")]
    d = d[d[cols].notna().all(axis=1)]
    return d[~d.index.str.startswith(("EU", "EA", "CPC"))]


def countries():
    """{code: name} of countries with complete food PLIs, base country first."""
    p = pli()
    names = p.country.str.replace(r" \(.*\)$", "", regex=True).to_dict()
    return {BASE: names[BASE], **{k: v for k, v in sorted(names.items(), key=lambda kv: kv[1]) if k != BASE}}


def pli_category(food_id, category):
    return FOOD_TO_PLI.get(food_id, CATEGORY_TO_PLI.get(category, "Food"))


def factors(df, country):
    """Multiplicative price factor per food (Series aligned to df) for a country code."""
    if country == BASE:
        return pd.Series(1.0, index=df.index)
    p = pli()
    if country not in p.index:
        raise ValueError(f"no Eurostat food PLIs for {country!r}")
    cat = [pli_category(f, c) for f, c in zip(df.food_id, df.category)]
    return pd.Series([p.loc[country, k] / p.loc[BASE, k] for k in cat], index=df.index)


def year():
    return int(pli().year.iloc[0])


def build_csv():
    """data/raw/eurostat/prc_ppp_ind_food.json → data/prices/eurostat_pli_food.csv (latest year, one row per geo)."""
    import itertools
    import json
    d = json.load(open(RAW))
    dims = d["id"]
    cats = [list(d["dimension"][k]["category"]["index"]) for k in dims]
    rows = []
    for pos, combo in enumerate(itertools.product(*cats)):
        v = d["value"].get(str(pos))
        if v is not None:
            rows.append(dict(zip(dims, combo), value=v))
    t = pd.DataFrame(rows)
    yr = t.time.max()
    t = t[t.time == yr]
    lab = d["dimension"]["ppp_cat"]["category"]["label"]
    geo = d["dimension"]["geo"]["category"]["label"]
    w = t.pivot_table(index="geo", columns="ppp_cat", values="value").rename(columns=lab)
    order = list(geo)
    w = w.reindex([g for g in order if g in w.index])
    w.insert(0, "year", int(yr))
    w.insert(0, "country", [geo[g] for g in w.index])
    w = w.reindex(columns=["country", "year"] + [lab[k] for k in lab])
    w.index.name = "geo"
    w.to_csv(PLI_FILE)
    return w


if __name__ == "__main__":
    print(build_csv().loc[["LV", "DK", "NL"]])
