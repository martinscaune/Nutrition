"""Build data/processed/foods_master.csv: the single input for graphs, app and optimizer.

Pipeline: composition_resolved (purchased, per 100 g edible) → eaten state (÷ cooking yield)
→ DIAAS (FAO 2013 adult pattern; AA profile × muleya2021 true ileal digestibility) → useful protein
→ prices (€/kg edible purchased) → metrics (PROJECT.md §4) + data-quality flags (task 2.16).

Run after src/data/resolve.py and src/prices/summary.py:
    .venv/bin/python src/build_master.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import composition as C  # noqa: E402

# FAO 2013 Table 5, older child / adolescent / adult scoring pattern, mg per g protein (decision D10)
PATTERN = {"HIS": 16, "ILE": 30, "LEU": 61, "LYS": 48, "SAA": 23, "AAA": 41, "THR": 25, "TRP": 6.6, "VAL": 40}
# FAO 2013 Table 5, young child (0.5–3 y) pattern: FAO's "regulatory" pattern; used as a stricter sensitivity case
PATTERN_CHILD = {"HIS": 20, "ILE": 32, "LEU": 66, "LYS": 57, "SAA": 27, "AAA": 52, "THR": 31, "TRP": 8.5, "VAL": 43}
# Plausible range of each AA in food protein, mg/g (outside → flag). Wide on purpose: catches unit/entry errors
# like the USDA ground-beef Trp (5 mg/g) or tofu Cys (3 mg/g) found in the preview.
PLAUSIBLE = {"TRP": (6, 25), "THR": (20, 60), "ILE": (30, 70), "LEU": (50, 140), "LYS": (15, 110), "MET": (8, 40),
             "CYS": (4, 45), "PHE": (25, 80), "TYR": (15, 70), "VAL": (35, 90), "HIS": (15, 50), "SAA": (15, 70)}
MIN_PROTEIN_FOR_AA_CHECK = 3.5  # g/100 g; AA profiles of near-protein-free foods are noisy and irrelevant


RETAINED = [k for k in C.MICRO if k not in ("sat_fat", "mercury_ug", "cadmium_ug", "ala_g", "epa_g", "dha_g")]  # fats: mass-based only


def retention(m):
    """Nutrient retention on cooking from the food's USDA raw↔cooked pair ('true retention', USDA method):
    R = (nutrient per g cooked × cooked mass) / (nutrient per g raw × raw mass), with cooked/raw mass = the yield.
    Only vitamins and minerals; capped to [0, 1] (gains are analytical noise for unsalted preparations)."""
    if not (isinstance(m.yield_usda_raw, str) and isinstance(m.yield_usda_cooked, str)):
        return {}
    raw, ck = C.usda().loc[int(m.yield_usda_raw)], C.usda().loc[int(m.yield_usda_cooked)]
    y = raw.protein / ck.protein
    out = {}
    for k in RETAINED:
        if pd.notna(raw[k]) and pd.notna(ck[k]) and raw[k] > 0:
            out[k] = float(min(max(ck[k] * y / raw[k], 0.0), 1.0))
    return out


def digestibility():
    d = pd.read_excel(C.MULEYA, "IAA digestibility", header=0)
    return d[C.AA].apply(pd.to_numeric, errors="coerce")


def diaas(mg_per_g, dig, pattern=None):
    """DIAAS (%) and limiting AA from an AA profile (mg/g protein) and per-AA digestibility (FAO 2013, untruncated)."""
    if mg_per_g.isna().any() or dig.isna().any():
        return np.nan, ""
    d = mg_per_g * dig
    digestible = {"HIS": d.HIS, "ILE": d.ILE, "LEU": d.LEU, "LYS": d.LYS, "SAA": d.MET + d.CYS,
                  "AAA": d.PHE + d.TYR, "THR": d.THR, "TRP": d.TRP, "VAL": d.VAL}
    pattern = pattern or PATTERN
    ratios = {k: v / pattern[k] for k, v in digestible.items()}
    lim = min(ratios, key=ratios.get)
    return ratios[lim] * 100, lim


def main():
    foods = pd.read_csv(ROOT / "data/foods/foods.csv")
    comp = pd.read_csv(ROOT / "data/processed/composition_resolved.csv").set_index("food_id")
    cmap = pd.read_csv(ROOT / "data/foods/composition_map.csv", dtype=str).set_index("food_id")
    dmap = pd.read_csv(ROOT / "data/foods/digestibility_map.csv").set_index("food_id")
    prices = pd.read_csv(ROOT / "data/processed/prices_summary.csv").set_index("food_id")
    dig = digestibility()
    reviewed = pd.read_csv(ROOT / "data/foods/qc_reviewed.csv")
    rows = []
    for f in foods.itertuples():
        c = comp.loc[f.food_id]
        r = {"food_id": f.food_id, "name_en": f.name_en, "name_lv": f.name_lv, "category": f.category, "role": f.role,
             "comp_source": f"{c.comp_db}:{c.comp_id}", "comp_description": c.get("description", ""),
             "comp_grade": c.grade}
        flags = []
        if pd.isna(c.get("kcal")):
            flags.append("no composition")
        # ---- purchased state (per 100 g edible) and eaten state
        y = c.yield_eaten_per_purchased
        ret = retention(cmap.loc[f.food_id])
        for k in ["kcal", "protein", "fat", "carb", "sugars", "free_sugars", "fibre", "water", "sodium_mg"] + C.MICRO:
            r[f"{k}_100g_purchased"] = c.get(k)
            r[f"{k}_100g_eaten"] = c.get(k) / y * ret.get(k, 1.0) if pd.notna(c.get(k)) else np.nan
        r["micronutrient_retention"] = "USDA raw↔cooked pair" if ret else "none (eaten as bought or no pair)"
        r["yield_eaten_per_purchased"] = y
        r["edible_portion"] = c.edible_portion
        # ---- amino-acid profile (mg/g protein), possibly borrowed
        m = cmap.loc[f.food_id]
        if isinstance(m.aa_override_db, str) and m.aa_override_db in ("frida", "usda_sr"):
            src = C.lookup(m.aa_override_db, m.aa_override_id)
            r["aa_source"] = f"{m.aa_override_db}:{m.aa_override_id}"
        else:
            src = c
            r["aa_source"] = r["comp_source"]
        prot = src["protein"] if pd.notna(src.get("protein")) else np.nan
        mg = pd.Series({a: (src[a] / prot * 1000 if prot and pd.notna(src[a]) else np.nan) for a in C.AA})
        for a in C.AA:
            r[f"{a}_mg_per_g_protein"] = mg[a]
        if pd.notna(c.get("protein")) and c.protein >= MIN_PROTEIN_FOR_AA_CHECK:
            mg_chk = pd.concat([mg, pd.Series({"SAA": mg.MET + mg.CYS})])
            bad = [a for a, (lo, hi) in PLAUSIBLE.items() if pd.notna(mg_chk[a]) and not lo <= mg_chk[a] <= hi]
            if bad:
                txt = "AA implausible: " + ",".join(f"{a}={mg_chk[a]:.1f}" for a in bad)
                rv = reviewed[(reviewed.food_id == f.food_id) & reviewed.flag_contains.apply(lambda s: txt.startswith(s))]
                flags.append(("reviewed-genuine " if len(rv) else "") + txt)
        # ---- DIAAS and useful protein
        if f.food_id in dmap.index and pd.notna(dmap.loc[f.food_id, "source_row"]):
            drow = dig.loc[int(dmap.loc[f.food_id, "source_row"])]
            score, lim = diaas(mg, drow)
            r["diaas_child"] = diaas(mg, drow, PATTERN_CHILD)[0]
            for a_ in C.AA:  # per-AA true ileal digestibility, needed by the diet optimizer (decision D9)
                r[f"dig_{a_}"] = drow[a_]
            # digestible leucine (mg per g protein): relevant to muscle protein synthesis
            r["digestible_leu_mg_per_g"] = mg.LEU * drow.LEU if pd.notna(mg.LEU) else np.nan
            r["digest_grade"] = dmap.loc[f.food_id, "grade"]
            r["digest_note"] = dmap.loc[f.food_id, "notes"]
        else:
            score, lim = np.nan, ""
            r["digest_grade"] = ""
        r["diaas"], r["limiting_aa"] = score, lim
        q = min(score, 100) / 100 if pd.notna(score) else 0.0
        r["quality_factor"] = q
        r["useful_protein_100g_eaten"] = r["protein_100g_eaten"] * q if pd.notna(r["protein_100g_eaten"]) else np.nan
        # ---- prices (€/kg edible purchased)
        p = prices.loc[f.food_id] if f.food_id in prices.index else None
        price = p.eur_per_kg_edible if p is not None else np.nan
        r["eur_per_kg_edible"] = price
        r["price_band_lo"] = p.band_lo_edible if p is not None else np.nan
        r["price_band_hi"] = p.band_hi_edible if p is not None else np.nan
        r["price_source"] = f.price_source
        r["price_grade"] = p.price_grade if p is not None else ""
        if pd.isna(price):
            flags.append("no price")
        # ---- metrics (PROJECT.md §4)
        kc, pr = r["kcal_100g_purchased"], r["protein_100g_purchased"]
        r["kcal_per_eur"] = kc * 10 / price if price else np.nan
        r["protein_per_eur"] = pr * 10 / price if price else np.nan
        r["useful_protein_per_eur"] = pr * q * 10 / price if price else np.nan
        r["carb_per_eur"] = r["carb_100g_purchased"] * 10 / price if price else np.nan
        r["protein_per_kcal"] = pr / kc if kc else np.nan
        r["fat_energy_pct"] = 9 * r["fat_100g_purchased"] / kc * 100 if kc else np.nan
        r["g_eaten_per_1000kcal"] = 1000 / r["kcal_100g_eaten"] * 100 if r["kcal_100g_eaten"] else np.nan
        r["eur_per_1000kcal"] = 1000 / r["kcal_per_eur"] if r["kcal_per_eur"] else np.nan
        r["flags"] = "; ".join(flags)
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "data/processed/foods_master.csv", index=False, float_format="%.5g")
    print(f"foods_master: {len(out)} foods, {out["flags"].astype(bool).sum()} flagged")
    for _, x in out[out["flags"].astype(bool)].iterrows():
        print(f"  {x.food_id}: {x['flags']}")
    show = ["food_id", "kcal_100g_eaten", "useful_protein_100g_eaten", "diaas", "limiting_aa", "eur_per_kg_edible",
            "kcal_per_eur", "useful_protein_per_eur", "g_eaten_per_1000kcal"]
    print(out[out.role == "core"][show].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
