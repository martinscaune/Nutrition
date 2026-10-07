"""Resolve data/foods/composition_map.csv against the databases (task 2.5 / 2.8).

Writes data/processed/composition_resolved.csv: one row per food with the matched description,
purchased-state composition (per 100 g edible), cooking yield and flags for review.

Yield (eaten mass per purchased edible mass) = protein_raw / protein_cooked of the USDA raw↔cooked pair
(protein is conserved during cooking; water uptake/loss changes the mass), unless yields.csv overrides it.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.data import composition as C  # noqa: E402


def main():
    foods = pd.read_csv(ROOT / "data/foods/foods.csv")
    cmap = pd.read_csv(ROOT / "data/foods/composition_map.csv", dtype=str)
    ylds = pd.read_csv(ROOT / "data/foods/yields.csv").set_index("food_id")
    missing = set(foods.food_id) - set(cmap.food_id)
    extra = set(cmap.food_id) - set(foods.food_id)
    rows, flags = [], []
    for m in cmap.itertuples():
        r = {"food_id": m.food_id, "comp_db": m.comp_db, "comp_id": m.comp_id, "grade": m.grade}
        f = []
        if m.comp_db in ("usda_sr", "frida"):
            try:
                x = C.lookup(m.comp_db, m.comp_id)
            except KeyError:
                f.append("ID NOT FOUND")
                x = None
            if x is not None:
                r["description"] = x.description
                for c in C.COLS:
                    r[c] = x[c]
                if pd.isna(x[C.AA]).any() and pd.isna(m.aa_override_id):
                    f.append("no AA profile")
                if pd.isna(x.kcal) or pd.isna(x.protein):
                    f.append("missing kcal/protein")
        else:
            f.append("PENDING label values")
        # cooking yield from USDA pair
        y = np.nan
        if isinstance(m.yield_usda_raw, str) and isinstance(m.yield_usda_cooked, str):
            try:
                a, b = C.usda().loc[int(m.yield_usda_raw)], C.usda().loc[int(m.yield_usda_cooked)]
                y = a.protein / b.protein
                r["yield_pair"] = f"{a.description[:40]} → {b.description[:40]}"
                enr = lambda d: "enriched" in d.lower().replace("unenriched", "")  # noqa: E731
                if enr(a.description) != enr(b.description) or ("with salt" in b.description.lower()) != ("with salt" in a.description.lower()):
                    f.append("yield pair mixes enriched/unenriched or salted/unsalted entries (distorts nutrient retention)")
            except KeyError:
                f.append("yield pair ID NOT FOUND")
        if m.food_id in ylds.index and not pd.isna(ylds.loc[m.food_id, "yield_override"]):
            y = float(ylds.loc[m.food_id, "yield_override"])
        r["yield_eaten_per_purchased"] = 1.0 if np.isnan(y) else round(y, 3)
        r["edible_portion"] = float(ylds.loc[m.food_id, "edible_portion"]) if m.food_id in ylds.index else 1.0
        if not np.isnan(y) and not 0.4 < y < 8:  # porridges (oats ≈ 5.2, semolina ≈ 6.4) are watery
            f.append(f"implausible yield {y:.2f}")
        # Atwater check (4P + 4C + 9F + 2 fibre) vs stated kcal
        if "kcal" in r and not pd.isna(r.get("kcal")):
            atw = 4 * np.nan_to_num(r["protein"]) + 4 * np.nan_to_num(r["carb"]) + 9 * np.nan_to_num(r["fat"]) + 2 * np.nan_to_num(r["fibre"])
            if m.comp_db == "usda_sr":  # USDA carb is by difference (includes fibre)
                atw = 4 * np.nan_to_num(r["protein"]) + 4 * (np.nan_to_num(r["carb"]) - np.nan_to_num(r["fibre"])) + 9 * np.nan_to_num(r["fat"]) + 2 * np.nan_to_num(r["fibre"])
            r["atwater_kcal"] = round(atw, 1)
            if r["kcal"] > 20 and abs(atw / r["kcal"] - 1) > 0.12:
                f.append(f"Atwater mismatch {atw:.0f} vs {r['kcal']:.0f}")
        r["flags"] = "; ".join(f)
        rows.append(r)
        if f:
            flags.append((m.food_id, r["flags"]))
    out = pd.DataFrame(rows)
    (ROOT / "data/processed").mkdir(exist_ok=True)
    out.to_csv(ROOT / "data/processed/composition_resolved.csv", index=False, float_format="%.4g")
    print(f"{len(out)} foods resolved; missing in map: {sorted(missing)}; extra: {sorted(extra)}")
    print(f"{len(flags)} flagged:")
    for fid, fl in flags:
        print(f"  {fid}: {fl}")
    print(out[["food_id", "description", "kcal", "protein", "yield_eaten_per_purchased", "edible_portion"]]
          .to_string(max_colwidth=45))


if __name__ == "__main__":
    main()
