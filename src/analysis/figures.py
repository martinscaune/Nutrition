"""Static v0.1 figures → figures/v0.1/*.png (PLAN A.5). Run after src/analysis/explore.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src import metrics as M  # noqa: E402
from src import plots as P  # noqa: E402

OUT = ROOT / "figures/v0.1"
TARGET_KCAL = 3400  # owner profile (PROJECT.md §7.3), illustration only


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = M.load()
    shown = df[df.role.isin(["core", "ingredient", "snack"]) & df.eur_per_kg_edible.notna()
               & df.kcal_100g_purchased.notna()].copy()
    core = shown[shown.role == "core"]
    shown["combined_kcal"] = (shown.kcal_100g_eaten * shown.kcal_per_eur) ** 0.5
    shown["combined_protein"] = (shown.useful_protein_100g_eaten * shown.useful_protein_per_eur) ** 0.5
    M.METRICS["combined_kcal"] = ("Calories: √(kcal/100 g × kcal/€)", "index", True)
    M.METRICS["combined_protein"] = ("Useful protein: √(g/100 g × g/€)", "index", True)

    P.scatter_png(shown, "useful_protein_100g_eaten", "kcal_100g_eaten", OUT / "1_density.png",
                  "Calories vs useful protein, per 100 g as eaten",
                  "Upper right = dense in both. Grey = ingredients and snacks (shown, not ranked).",
                  extra_labels=("eggs", "curd", "tofu", "oats_flaked", "peas_split", "pasta_wheat"))
    P.scatter_png(shown, "useful_protein_per_eur", "kcal_per_eur", OUT / "2_economy.png",
                  "Calories per euro vs useful protein per euro",
                  "Upper right = cheap calories and cheap quality protein (log scales; independent of cooking).",
                  logx=True, logy=True,
                  extra_labels=("chicken_fillet", "eggs", "milk", "pork_minced", "oats_flaked", "rice_white",
                                "lentils_red", "sunflower_oil", "sugar", "skyr", "tuna_canned"))
    P.scatter_png(shown, "combined_protein", "combined_kcal", OUT / "3_combined.png",
                  "Density and price combined",
                  "Each axis = √(per-100 g value × per-€ value): rewards foods that are both dense and cheap.",
                  extra_labels=("chicken_fillet", "eggs", "milk", "oats_flaked", "lentils_red", "rice_white"))
    P.scatter_png(shown, "g_eaten_per_1000kcal", "eur_per_1000kcal", OUT / "4_mass_vs_cost.png",
                  "Food mass vs cost for 1000 kcal",
                  "Lower left = compact and cheap calories. Marker size = useful protein per 1000 kcal.",
                  logx=True, logy=True, size="useful_protein_per_1000kcal", front=False,
                  extra_labels=("peas_split", "rice_white", "pasta_wheat", "oats_flaked", "potatoes", "peanuts",
                                "peanut_butter", "sunflower_oil", "sugar", "butter", "chicken_fillet", "eggs",
                                "milk", "curd", "tuna_canned", "salmon_fillet", "bread_rye", "barley_groats"))
    P.scatter_png(shown, "useful_protein_per_eur", "carb_per_eur", OUT / "5_carbs_economy.png",
                  "Carbohydrate per euro vs useful protein per euro (endurance view)",
                  "Upper right = cheap glycogen fuel that also brings quality protein (log scales).",
                  logx=True, logy=True,
                  extra_labels=("oats_flaked", "rice_white", "pasta_wheat", "potatoes", "bananas", "bread_rye",
                                "honey", "sugar", "lentils_red", "chicken_legs"))
    day = core.assign(kg=TARGET_KCAL / core.kcal_100g_eaten / 10,
                      eur=core.eur_per_1000kcal * TARGET_KCAL / 1000,
                      prot=core.useful_protein_per_1000kcal * TARGET_KCAL / 1000)
    P.bars_png(day, "kg", OUT / "6_single_food_day.png",
               f"How much would you eat to get {TARGET_KCAL:,} kcal from one food alone?",
               "Mass as eaten (cooked where relevant) · cost · useful protein you would get",
               lambda r: f"{r.kg:.1f} kg · €{r.eur:.2f} · {r.prot:.0f} g useful protein", "kg of food eaten")
    crude = M.with_quality(df, "crude").set_index("food_id").loc[core.food_id]
    h1 = core.set_index("food_id").assign(crude_ppe=crude.useful_protein_per_eur).reset_index()
    P.dumbbell_png(h1, "crude_ppe", "useful_protein_per_eur", OUT / "7_h1_quality_rank_shift.png",
                   "H1: how protein quality changes the 'protein per euro' ranking",
                   "Grey = rank by raw protein per €; coloured = rank by useful (DIAAS-adjusted) protein per €. "
                   "Top 20 by raw protein.", n=20)
    print("figures →", OUT)


if __name__ == "__main__":
    main()
