"""Preview graphs: a side exploration, NOT project results.

Prototype of the v0.1 pipeline on ~40 foods:
    USDA SR Legacy composition -> per-food DIAAS (USDA amino acids x Muleya 2021
    true ileal digestibility / FAO 2013 adult pattern) -> useful protein -> metrics -> graphs.

Caveats (also printed on every figure):
- Prices are PLACEHOLDER ESTIMATES of Latvian retail prices, not observations (Phase 2 replaces them).
- Several digestibility values are proxies (marked "PROXY" in data/preview/foods_preview.csv).
- "Useful protein" = protein x min(DIAAS, 100)/100 for the food eaten alone. In a mixed diet,
  complementary proteins make the whole better than this per-food view (PROJECT.md §5).

Run:  .venv/bin/python notebooks/preview_graphs.py
"""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import plotly.graph_objects as go  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SR = ROOT / "data/raw/usda/sr_legacy/FoodData_Central_sr_legacy_food_csv_2018-04"
MULEYA = ROOT / "data/raw/muleya2021/muleya2021_diaas.xlsx"
FOODS = ROOT / "data/preview/foods_preview.csv"
OUT = ROOT / "figures/preview"

TARGET_KCAL = 3400  # owner profile, mid-point of the provisional 3300-3500 kcal surplus target

NUTRIENTS = {1008: "kcal", 1003: "protein", 1004: "fat", 1005: "carb", 1051: "water", 1079: "fibre",
             1210: "TRP", 1211: "THR", 1212: "ILE", 1213: "LEU", 1214: "LYS", 1215: "MET",
             1216: "CYS", 1217: "PHE", 1218: "TYR", 1219: "VAL", 1221: "HIS"}
AA = ["TRP", "THR", "ILE", "LEU", "LYS", "MET", "CYS", "PHE", "TYR", "VAL", "HIS"]
# FAO 2013, Table 5: older child, adolescent, adult scoring pattern (mg/g protein)
PATTERN = {"HIS": 16, "ILE": 30, "LEU": 61, "LYS": 48, "SAA": 23, "AAA": 41, "THR": 25, "TRP": 6.6, "VAL": 40}

CATEGORIES = ["Meat & fish", "Eggs & dairy", "Legumes & soy", "Grains & starches", "Nuts & seeds", "Ingredients"]
# Reference palette slots 1-5 (dataviz skill); fats & sugar recede in neutral gray because
# they are "ingredients", shown but excluded from rankings (PROJECT.md §9.1, safeguard 5).
COLORS = {"Meat & fish": "#2a78d6", "Eggs & dairy": "#eb6834", "Legumes & soy": "#1baf7a",
          "Grains & starches": "#eda100", "Nuts & seeds": "#e87ba4", "Ingredients": "#8a8984"}
# Secondary encoding: >3 categories in a scatter cannot rely on color alone.
MPL_MARKERS = dict(zip(CATEGORIES, ["o", "s", "^", "D", "v", "X"]))
PLOTLY_MARKERS = dict(zip(CATEGORIES, ["circle", "square", "triangle-up", "diamond", "triangle-down", "x"]))

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
CAVEAT = "PREVIEW · prices are placeholder estimates (not observed) · some digestibility values are proxies"


# ---------------------------------------------------------------- data
def load_composition(ids):
    fn = pd.read_csv(SR / "food_nutrient.csv", usecols=["fdc_id", "nutrient_id", "amount"])
    fn = fn[fn.fdc_id.isin(ids) & fn.nutrient_id.isin(NUTRIENTS)]
    comp = fn.pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="first")
    return comp.rename(columns=NUTRIENTS)


def load_digestibility():
    d = pd.read_excel(MULEYA, "IAA digestibility", header=0)
    return d[AA].apply(pd.to_numeric, errors="coerce")


def diaas(aa_g_per_100g, protein_g_per_100g, dig):
    """DIAAS (%) and limiting amino acid for one food (FAO 2013 definition, untruncated)."""
    if not protein_g_per_100g or aa_g_per_100g.isna().any() or dig.isna().any():
        return np.nan, ""
    mg = aa_g_per_100g / protein_g_per_100g * 1000  # mg AA per g protein
    d = mg * dig
    digestible = {"HIS": d.HIS, "ILE": d.ILE, "LEU": d.LEU, "LYS": d.LYS, "SAA": d.MET + d.CYS,
                  "AAA": d.PHE + d.TYR, "THR": d.THR, "TRP": d.TRP, "VAL": d.VAL}
    ratios = {k: v / PATTERN[k] for k, v in digestible.items()}
    lim = min(ratios, key=ratios.get)
    return ratios[lim] * 100, lim


def build_table():
    foods = pd.read_csv(FOODS)
    profiles = set(foods.fdc_aa_profile.dropna().astype(int))
    comp = load_composition(set(foods.fdc_purchased) | set(foods.fdc_eaten) | profiles)
    dig = load_digestibility()
    rows = []
    for f in foods.itertuples():
        p, e = comp.loc[f.fdc_purchased], comp.loc[f.fdc_eaten]
        # amino-acid profile: a borrowed profile if USDA's is missing/implausible (see aa_profile_note),
        # else the eaten state if available, else the purchased state
        if not pd.isna(f.fdc_aa_profile):
            src = comp.loc[int(f.fdc_aa_profile)]
        else:
            src = e if not e[AA].isna().any() else p
        if pd.isna(f.digest_row):
            score, lim = np.nan, ""
        else:
            score, lim = diaas(src[AA], src.protein, dig.loc[int(f.digest_row)])
        q = min(score, 100) / 100 if not np.isnan(score) else 0.0
        price = f.price_eur_per_kg_purchased
        rows.append({
            "food": f.food, "category": f.category,
            "kcal_100g_eaten": e.kcal, "protein_100g_eaten": e.protein,
            "useful_protein_100g_eaten": e.protein * q,
            "diaas": score, "limiting_aa": lim, "digest_note": f.digest_note,
            "price_eur_kg_placeholder": price,
            "kcal_per_eur": p.kcal * 10 / price,
            "useful_protein_per_eur": p.protein * q * 10 / price,
            "g_eaten_per_1000kcal": 1000 / e.kcal * 100,
            "eur_per_1000kcal": price / (p.kcal * 10) * 1000,
            "useful_protein_per_1000kcal": p.protein * q / p.kcal * 1000,
        })
    t = pd.DataFrame(rows)
    # equal-weight geometric index of "per gram eaten" and "per euro" (see README note)
    t["kcal_combined"] = np.sqrt(t.kcal_100g_eaten * t.kcal_per_eur)
    t["protein_combined"] = np.sqrt(t.useful_protein_100g_eaten * t.useful_protein_per_eur)
    t["kg_eaten_for_target"] = TARGET_KCAL / t.kcal_100g_eaten / 10
    t["eur_for_target"] = t.eur_per_1000kcal * TARGET_KCAL / 1000
    t["useful_protein_at_target"] = t.useful_protein_per_1000kcal * TARGET_KCAL / 1000
    return t


def pareto(t, x, y):
    """Foods not beaten on both axes at once (maximize x and y); pure fats & sugar excluded."""
    c = t[t.category != "Ingredients"].sort_values([x, y], ascending=False)
    front, best_y = [], -np.inf
    for i, r in c.iterrows():
        if r[y] > best_y:
            front.append(i)
            best_y = r[y]
    return t.loc[front].sort_values(x)


# ---------------------------------------------------------------- static PNGs (matplotlib)
def style(ax, title, subtitle, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.set_xlabel(xlabel, color=INK2, fontsize=10)
    ax.set_ylabel(ylabel, color=INK2, fontsize=10)
    ax.figure.text(0.06, 0.965, title, fontsize=14, color=INK, weight="semibold", va="top")
    ax.figure.text(0.06, 0.925, subtitle, fontsize=9.5, color=INK2, va="top")
    ax.figure.text(0.06, 0.015, CAVEAT, fontsize=8, color=MUTED)


def declutter(ax, anns, step=3, iters=200):
    """Nudge overlapping labels apart vertically; draw a thin leader line to labels that moved far."""
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    start = {id(a): a.xyann for a in anns}
    for _ in range(iters):
        boxes = [a.get_window_extent(r).expanded(1.02, 1.15) for a in anns]
        moved = False
        for i in range(len(anns)):
            for j in range(i + 1, len(anns)):
                if boxes[i].overlaps(boxes[j]):
                    lower, upper = (i, j) if boxes[i].y0 < boxes[j].y0 else (j, i)
                    for k, d in ((lower, -step), (upper, step)):
                        xo, yo = anns[k].xyann
                        anns[k].xyann = (xo, yo + d)
                    moved = True
        if not moved:
            break
    for a in anns:
        if abs(a.xyann[1] - start[id(a)][1]) > 8:
            a.arrow_patch = None
            a.set_annotation_clip(False)
            ax.annotate("", a.xy, xytext=a.xyann, textcoords="offset points",
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=0, shrinkB=4))


def scatter_png(t, x, y, fname, title, subtitle, xlabel, ylabel, label_extra=(), logx=False, logy=False,
                size=None, front=True):
    fig, ax = plt.subplots(figsize=(11, 7.5))
    fig.subplots_adjust(left=0.08, right=0.8, top=0.86, bottom=0.1)
    for cat in CATEGORIES:
        s = t[t.category == cat]
        ms = 70 if size is None else 40 + s[size].fillna(0) * 2.2
        ax.scatter(s[x], s[y], s=ms, c=COLORS[cat], marker=MPL_MARKERS[cat], edgecolors=SURFACE,
                   linewidths=1.5, label=cat, zorder=3, alpha=0.95)
    labelled = set(label_extra)
    if front:
        fr = pareto(t, x, y)
        ax.plot(fr[x], fr[y], color=INK2, linewidth=1, linestyle="-", zorder=2, alpha=0.6)
        labelled |= set(fr.food)
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    style(ax, title, subtitle, xlabel, ylabel)
    to_axes = ax.transData + ax.transAxes.inverted()
    anns = []
    for _, r in t[t.food.isin(labelled) & (t[x] > 0)].iterrows():
        right_edge = to_axes.transform((r[x], r[y]))[0] > 0.8  # flip labels near the right edge to the left
        anns.append(ax.annotate(r.food, (r[x], r[y]), xytext=(-7 if right_edge else 7, 4), textcoords="offset points",
                                ha="right" if right_edge else "left", fontsize=8.5, color=INK))
    declutter(ax, anns)
    leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, fontsize=9, labelcolor=INK2,
                    title="Category", title_fontsize=9)
    leg.get_title().set_color(INK2)
    if front:
        fig.text(0.815, 0.45, "Line = Pareto front:\nfoods no other food\nbeats on both axes\n(ingredients excluded)",
                 fontsize=8.5, color=INK2, va="top")
    fig.savefig(OUT / fname, dpi=150)
    plt.close(fig)


def day_png(t, fname):
    s = t.sort_values("kg_eaten_for_target")
    fig, ax = plt.subplots(figsize=(11, 12))
    fig.subplots_adjust(left=0.22, right=0.97, top=0.92, bottom=0.075)
    ax.barh(s.food, s.kg_eaten_for_target, height=0.6, color=[COLORS[c] for c in s.category], zorder=3)
    for i, r in enumerate(s.itertuples()):
        ax.text(r.kg_eaten_for_target + 0.05, i,
                f"{r.kg_eaten_for_target:.1f} kg · €{r.eur_for_target:.2f} · {r.useful_protein_at_target:.0f} g useful protein",
                va="center", fontsize=8, color=INK2)
    ax.invert_yaxis()
    ax.set_xlim(0, s.kg_eaten_for_target.max() * 1.45)
    style(ax, f"How much would you eat to get {TARGET_KCAL:,} kcal from one food alone?",
          "Mass as eaten (cooked where relevant) · cost · useful protein you would get", "kg of food eaten", "")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[c]) for c in CATEGORIES]
    ax.legend(handles, CATEGORIES, loc="upper right", frameon=False, fontsize=9, labelcolor=INK2)
    fig.savefig(OUT / fname, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- interactive page (plotly)
HOVER = ("<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
         "kcal/100 g eaten: %{customdata[2]:.0f}<br>useful protein/100 g eaten: %{customdata[3]:.1f} g<br>"
         "kcal per €: %{customdata[4]:,.0f}<br>useful protein per €: %{customdata[5]:.0f} g<br>"
         "DIAAS: %{customdata[6]:.0f} (limiting: %{customdata[7]})<br>"
         "price (placeholder): €%{customdata[8]:.2f}/kg<br>digestibility: %{customdata[9]}<extra></extra>")
CD = ["food", "category", "kcal_100g_eaten", "useful_protein_100g_eaten", "kcal_per_eur",
      "useful_protein_per_eur", "diaas", "limiting_aa", "price_eur_kg_placeholder", "digest_note"]


def scatter_fig(t, x, y, xlabel, ylabel, logx=False, logy=False, size=None, front=True):
    fig = go.Figure()
    for cat in CATEGORIES:
        s = t[t.category == cat]
        ms = 11 if size is None else (8 + s[size].fillna(0) * 0.35)
        fig.add_trace(go.Scatter(x=s[x], y=s[y], mode="markers", name=cat, customdata=s[CD].values,
                                 hovertemplate=HOVER,
                                 marker=dict(color=COLORS[cat], symbol=PLOTLY_MARKERS[cat], size=ms,
                                             line=dict(width=1.5, color=SURFACE))))
    if front:
        fr = pareto(t, x, y)
        fig.add_trace(go.Scatter(x=fr[x], y=fr[y], mode="lines+text", text=fr.food, textposition="top left",
                                 textfont=dict(size=11), name="Pareto front", hoverinfo="skip",
                                 line=dict(color=INK2, width=1)))
    fig.update_layout(xaxis_title=xlabel, yaxis_title=ylabel, height=600, margin=dict(l=60, r=20, t=20, b=60),
                      legend=dict(orientation="h", y=-0.15), hoverlabel=dict(bgcolor="white"))
    if logx:
        fig.update_xaxes(type="log")
    if logy:
        fig.update_yaxes(type="log")
    return fig


def fig3d(t):
    fig = go.Figure()
    for cat in CATEGORIES:
        s = t[t.category == cat]
        fig.add_trace(go.Scatter3d(x=s.useful_protein_100g_eaten, y=s.kcal_100g_eaten, z=s.eur_per_1000kcal,
                                   mode="markers", name=cat, customdata=s[CD].values, hovertemplate=HOVER,
                                   marker=dict(color=COLORS[cat], size=6, symbol="circle")))
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"),
                      scene=dict(xaxis_title="useful protein g/100 g eaten", yaxis_title="kcal/100 g eaten",
                                 zaxis_title="€ per 1000 kcal", zaxis_type="log"))
    return fig


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food Value Preview</title>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<style>
:root{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--grid:#e6e5e1;--warn-bg:#fff6e0}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#8f8e88;--grid:#33332f;--warn-bg:#3a3020}}
:root[data-theme="dark"]{--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#8f8e88;--grid:#33332f;--warn-bg:#3a3020}
body{margin:0;background:var(--surface);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:40px 0 4px}
p{color:var(--ink2);margin:4px 0 12px}.warn{background:var(--warn-bg);padding:10px 14px;border-radius:8px;color:var(--ink)}
details{margin-top:32px}table{border-collapse:collapse;font-size:13px;width:100%}
th,td{padding:4px 8px;border-bottom:1px solid var(--grid);text-align:right}th:first-child,td:first-child{text-align:left}
.scroll{overflow-x:auto}
</style></head><body><main>
<h1>Food value preview</h1>
<p>A side exploration of about 40 foods. Hover any point for its details. Not project results.</p>
<p class="warn"><b>Caveats:</b> prices are <b>placeholder estimates</b> of Latvian prices, not observations.
Some protein digestibility values are proxies. "Useful protein" = protein × min(DIAAS,100)/100 for the food eaten
<i>alone</i>; in a mixed diet, complementary proteins do better. Calories and grams per 100 g are for the food
<b>as eaten</b> (cooked rice, not dry). Per-euro values don't depend on cooking, since water adds neither calories nor cost.</p>
{sections}
<details><summary>Data table</summary><div class="scroll">{table}</div></details>
</main>
<script>
function themeAll(){const cs=getComputedStyle(document.documentElement);const ink=cs.getPropertyValue('--ink2').trim(),grid=cs.getPropertyValue('--grid').trim();
document.querySelectorAll('.js-plotly-plot').forEach(g=>Plotly.relayout(g,{'paper_bgcolor':'rgba(0,0,0,0)','plot_bgcolor':'rgba(0,0,0,0)','font.color':ink,
'xaxis.gridcolor':grid,'yaxis.gridcolor':grid,'xaxis.zerolinecolor':grid,'yaxis.zerolinecolor':grid,
'scene.xaxis.gridcolor':grid,'scene.yaxis.gridcolor':grid,'scene.zaxis.gridcolor':grid}));}
window.addEventListener('load',themeAll);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',themeAll);
</script></body></html>"""


def section(title, text, fig):
    return f"<h2>{title}</h2><p>{text}</p>" + fig.to_html(full_html=False, include_plotlyjs=False,
                                                         config={"displaylogo": False})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = build_table()
    t.round(3).to_csv(ROOT / "data/preview/foods_preview_computed.csv", index=False)

    specs = [
        ("1_density", "useful_protein_100g_eaten", "kcal_100g_eaten",
         "Calories vs useful protein, per 100 g eaten",
         "Upper right = dense in both. Useful protein = protein adjusted for quality (DIAAS, capped at 100).",
         "useful protein (g per 100 g eaten)", "kcal per 100 g eaten", {}),
        ("2_economy", "useful_protein_per_eur", "kcal_per_eur",
         "Calories per euro vs useful protein per euro",
         "Upper right = cheap calories and cheap quality protein. Independent of cooking.",
         "useful protein per € (g)", "kcal per € (log scale)", dict(logy=True)),
        ("3_combined", "protein_combined", "kcal_combined",
         "Density and price combined",
         "Each axis = √(per-100 g value × per-€ value): rewards foods that are both dense and cheap, equally weighted.",
         "useful protein: √(g/100 g × g/€)", "calories: √(kcal/100 g × kcal/€)", {}),
        ("4_volume", "g_eaten_per_1000kcal", "eur_per_1000kcal",
         "Food mass vs cost for 1000 kcal",
         "Lower left = compact and cheap calories (good for bulking). Marker size = useful protein per 1000 kcal.",
         "grams eaten per 1000 kcal (log)", "€ per 1000 kcal (log)",
         dict(logx=True, logy=True, size="useful_protein_per_1000kcal", front=False)),
    ]
    sections = []
    for fname, x, y, title, sub, xl, yl, kw in specs:
        extra = {
            "1_density": ("Chicken breast", "Eggs", "Cottage cheese / quark", "Tofu (firm)", "Lentils (dry)",
                          "Rolled oats"),
            "2_economy": ("Chicken breast", "Chicken liver", "Eggs", "Milk 2%", "Minced pork", "Lentils (dry)",
                          "Sunflower seeds", "White rice", "Pasta"),
            "3_combined": ("Chicken breast", "Eggs", "Milk 2%", "Rolled oats", "Lentils (dry)"),
            "4_volume": ("Rolled oats", "Split peas (dry)", "White rice", "Potatoes", "Eggs", "Milk 2%",
                         "Sunflower oil", "Sugar", "Wheat flour", "Butter", "Pasta", "Peanut butter", "Lentils (dry)",
                         "Chicken breast", "Cottage cheese / quark", "Canned tuna (drained)", "Beef top round steak",
                         "Salmon (farmed)", "Pollock fillet"),
        }[fname]
        scatter_png(t, x, y, f"{fname}.png", title, sub, xl, yl, label_extra=extra, **kw)
        sections.append(section(title, sub, scatter_fig(t, x, y, xl, yl, **kw)))
    day_png(t, "5_single_food_day.png")
    s = t.sort_values("kg_eaten_for_target", ascending=False)
    bar = go.Figure(go.Bar(x=s.kg_eaten_for_target, y=s.food, orientation="h",
                           marker_color=[COLORS[c] for c in s.category],
                           customdata=np.c_[s.eur_for_target, s.useful_protein_at_target],
                           hovertemplate="<b>%{y}</b><br>%{x:.2f} kg eaten<br>€%{customdata[0]:.2f}"
                                         "<br>%{customdata[1]:.0f} g useful protein<extra></extra>"))
    bar.update_layout(height=1000, margin=dict(l=180, r=20, t=10, b=50), xaxis_title="kg of food eaten")
    sections.append(section(f"How much would you eat to get {TARGET_KCAL:,} kcal from one food?",
                            "Mass as eaten · hover for cost and useful protein.", bar))
    sections.append(section("3D explorer", "Drag to rotate. Useful protein × calories per 100 g eaten × € per 1000 kcal.",
                            fig3d(t)))
    cols = ["food", "category", "kcal_100g_eaten", "useful_protein_100g_eaten", "diaas", "limiting_aa",
            "kcal_per_eur", "useful_protein_per_eur", "g_eaten_per_1000kcal", "eur_per_1000kcal",
            "price_eur_kg_placeholder", "digest_note"]
    table = t[cols].round(1).to_html(index=False, border=0)
    (OUT / "preview.html").write_text(PAGE.replace("{sections}", "\n".join(sections)).replace("{table}", table))
    print(t[["food", "diaas", "limiting_aa", "useful_protein_100g_eaten", "kcal_per_eur",
             "useful_protein_per_eur"]].round(1).to_string())


if __name__ == "__main__":
    main()
