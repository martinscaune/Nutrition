"""Load composition databases into one common per-100 g format.

Common columns: kcal, protein, fat, carb (available), sugars, fibre, water, sodium_mg,
and the 11 amino acids TRP THR ILE LEU LYS MET CYS PHE TYR VAL HIS in g/100 g.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SR = ROOT / "data/raw/usda/sr_legacy/FoodData_Central_sr_legacy_food_csv_2018-04"
FRIDA = ROOT / "data/raw/frida/Frida_5.5_Dataset.xlsx"
MULEYA = ROOT / "data/raw/muleya2021/muleya2021_diaas.xlsx"
AA = ["TRP", "THR", "ILE", "LEU", "LYS", "MET", "CYS", "PHE", "TYR", "VAL", "HIS"]
MICRO = ["sat_fat", "calcium_mg", "iron_mg", "zinc_mg", "magnesium_mg", "potassium_mg", "phosphorus_mg", "selenium_ug",
         "copper_mg", "iodine_ug", "vitamin_a_ug_re", "retinol_ug", "vitamin_d_ug", "vitamin_e_mg", "vitamin_k_ug",
         "thiamin_mg", "riboflavin_mg", "niacin_mg_ne", "vitamin_b6_mg", "folate_ug", "vitamin_b12_ug", "vitamin_c_mg",
         "mercury_ug", "cadmium_ug"]
COLS = ["kcal", "protein", "fat", "carb", "sugars", "free_sugars", "fibre", "water", "sodium_mg"] + AA + MICRO

# USDA "carb" is carbohydrate BY DIFFERENCE (includes fibre); "free_sugars" ≈ USDA added sugars (1235), which
# misses honey/syrup/juice sugars (handled per food).
USDA_IDS = {1008: "kcal", 1003: "protein", 1004: "fat", 1005: "carb", 2000: "sugars", 1235: "free_sugars", 1079: "fibre", 1051: "water",
            1093: "sodium_mg", 1210: "TRP", 1211: "THR", 1212: "ILE", 1213: "LEU", 1214: "LYS", 1215: "MET",
            1216: "CYS", 1217: "PHE", 1218: "TYR", 1219: "VAL", 1221: "HIS",
            1258: "sat_fat", 1087: "calcium_mg", 1089: "iron_mg", 1095: "zinc_mg", 1090: "magnesium_mg",
            1092: "potassium_mg", 1091: "phosphorus_mg", 1103: "selenium_ug", 1098: "copper_mg", 1100: "iodine_ug",
            1105: "retinol_ug", 1107: "_beta_carotene", 1114: "vitamin_d_ug", 1109: "vitamin_e_mg",
            1185: "vitamin_k_ug", 1165: "thiamin_mg", 1166: "riboflavin_mg", 1167: "_niacin", 1175: "vitamin_b6_mg",
            1187: "_folate_food", 1177: "_folate_total", 1178: "vitamin_b12_ug", 1162: "vitamin_c_mg"}
# Frida English parameter names → common names. Carbohydrate = "Available carbohydrates" (USDA has only "by difference").
FRIDA_NAMES = {"Energy (kcal)": "kcal", "Protein": "protein", "Fat": "fat", "Available carbohydrates": "carb",
               "Sum sugars": "sugars", "Free Sugars": "free_sugars", "Dietary fibre": "fibre", "Water": "water", "Sodium": "sodium_mg",
               "Tryptophan": "TRP", "Threonine": "THR", "Isoleucine": "ILE", "Leucine": "LEU", "Lysine": "LYS",
               "Methionine": "MET", "Cystine": "CYS", "Phenylalanine": "PHE", "Tyrosine": "TYR", "Valine": "VAL",
               "Histidine": "HIS", "Sum saturated fatty acids": "sat_fat", "Calcium": "calcium_mg", "Iron": "iron_mg",
               "Zinc": "zinc_mg", "Magnesium": "magnesium_mg", "Potassium": "potassium_mg", "Phosphorus": "phosphorus_mg",
               "Selenium": "selenium_ug", "Copper": "copper_mg", "Iodine": "iodine_ug", "Vitamin A": "vitamin_a_ug_re",
               "Retinol": "retinol_ug", "Vitamin D": "vitamin_d_ug", "alpha-Tocopherol": "vitamin_e_mg",
               "Vitamin K": "vitamin_k_ug", "Thiamin (Vitamin B1)": "thiamin_mg", "Riboflavin (Vitamin B2)": "riboflavin_mg",
               "Niacin equivalent": "niacin_mg_ne", "Vitamin B6": "vitamin_b6_mg", "Folate": "folate_ug",
               "Vitamin B12": "vitamin_b12_ug", "Vitamin C": "vitamin_c_mg", "Mercury": "mercury_ug", "Cadmium": "cadmium_ug"}
FRIDA_KEEP_UNIT = {"sodium_mg", "calcium_mg", "iron_mg", "zinc_mg", "magnesium_mg", "potassium_mg", "phosphorus_mg",
                   "selenium_ug", "copper_mg", "iodine_ug", "vitamin_a_ug_re", "retinol_ug", "vitamin_d_ug", "vitamin_e_mg",
                   "vitamin_k_ug", "thiamin_mg", "riboflavin_mg", "niacin_mg_ne", "vitamin_b6_mg", "folate_ug",
                   "vitamin_b12_ug", "vitamin_c_mg", "mercury_ug", "cadmium_ug"}


@lru_cache
def usda():
    food = pd.read_csv(SR / "food.csv", usecols=["fdc_id", "description"]).set_index("fdc_id")
    fn = pd.read_csv(SR / "food_nutrient.csv", usecols=["fdc_id", "nutrient_id", "amount"])
    fn = fn[fn.nutrient_id.isin(USDA_IDS)]
    t = fn.pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="first").rename(columns=USDA_IDS)
    # harmonize with EFSA/Frida definitions
    t["vitamin_a_ug_re"] = t.retinol_ug.fillna(0) + t._beta_carotene.fillna(0) / 6          # RE = retinol + β-car/6
    t.loc[t.retinol_ug.isna() & t._beta_carotene.isna(), "vitamin_a_ug_re"] = float("nan")
    t["niacin_mg_ne"] = t._niacin + t.TRP.fillna(0) * 1000 / 60                            # NE = niacin + Trp/60
    t["folate_ug"] = t._folate_food.where(t._folate_food.notna(), t._folate_total)          # natural folate (no US fortification)
    t = t.reindex(columns=COLS)
    t.insert(0, "description", food.description.reindex(t.index))
    return t


@lru_cache
def frida():
    d = pd.read_excel(FRIDA, "Data_Table", header=None)
    names, units = list(d.iloc[1]), list(d.iloc[2])
    body = d.iloc[4:].copy()
    body.columns = range(body.shape[1])
    out = pd.DataFrame({"description": body[1].values}, index=pd.Index(body[2].astype(int).values, name="frida_id"))
    for i, (n, u) in enumerate(zip(names, units)):
        if n in FRIDA_NAMES:
            v = pd.to_numeric(body[i], errors="coerce").values
            unit = str(u).lower().replace(" ", "")
            if FRIDA_NAMES[n] in FRIDA_KEEP_UNIT:
                pass  # micronutrients keep their mg / µg per 100 g (column names carry the unit)
            elif unit.startswith("mg/"):
                v = v / 1000  # Frida amino acids are mg/100 g → g/100 g
            out[FRIDA_NAMES[n]] = v
    return out.reindex(columns=["description"] + COLS)


@lru_cache
def muleya_composition():
    """Muleya 2021 'Total and digestible IAA' sheet: protein and total IAA (g/kg) for supplements."""
    d = pd.read_excel(MULEYA, "Total and digestible IAA", header=0)
    return d


def lookup(db, id_):
    if db == "usda_sr":
        return usda().loc[int(id_)]
    if db == "frida":
        return frida().loc[int(id_)]
    raise KeyError(db)
