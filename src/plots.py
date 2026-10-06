"""Chart builders shared by the static figures (matplotlib) and the app (plotly). PLAN A.5, A.10.

Design rules (dataviz skill): categorical colours in fixed slot order, secondary encoding by marker shape
(scatter with > 3 groups), thin marks with a surface ring, recessive grid, selective direct labels,
text in ink colours (never series colours), every figure carries a data/caveat footer.
"""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import plotly.graph_objects as go  # noqa: E402

from src import metrics as M  # noqa: E402

COLORS = {"Meat & fish": "#2a78d6", "Eggs & dairy": "#eb6834", "Legumes & soy": "#1baf7a",
          "Grains & potatoes": "#eda100", "Nuts & seeds": "#e87ba4", "Fruit & veg": "#008300",
          "Ingredients & snacks": "#8a8984", "Supplements": "#b5b4ae"}
MPL_MARK = dict(zip(M.GROUPS, ["o", "s", "^", "D", "v", "P", "X", "*"]))
PLY_MARK = dict(zip(M.GROUPS, ["circle", "square", "triangle-up", "diamond", "triangle-down", "cross", "x", "star"]))
INK, INK2, MUTED, GRID, SURFACE = "#000000", "#222222", "#666666", "#d9d9d9", "#ffffff"
FOOTER = ("Data: Frida 5.5 / USDA SR Legacy composition; muleya2021 digestibility; prices CSP PCC010m 12-month mean\n"
          "+ Cenu Depo 2026-10-06. Useful protein = protein × min(DIAAS,100)/100.")


def label(col):
    name, unit, _ = M.METRICS[col]
    return f"{name} ({unit})"


# ---------------------------------------------------------------- matplotlib
def _style(ax, title, subtitle, xlabel, ylabel):
    """Scientific style: white background, full black frame, inward ticks on all four sides,
    major + minor ticks, light grid on both axes, black text."""
    fig = ax.figure
    ax.set_facecolor("white")
    fig.set_facecolor("white")
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(True)
        ax.spines[s].set_color("black")
        ax.spines[s].set_linewidth(1.0)
    ax.minorticks_on()
    ax.tick_params(which="both", direction="in", top=True, right=True, colors="black", labelsize=10)
    ax.tick_params(which="major", length=6, width=1.0)
    ax.tick_params(which="minor", length=3, width=0.8)
    ax.grid(True, which="major", axis="both", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_xlabel(xlabel, color="black", fontsize=11)
    ax.set_ylabel(ylabel, color="black", fontsize=11)
    fig.text(0.06, 0.965, title, fontsize=14, color="black", weight="bold", va="top")
    fig.text(0.06, 0.925, subtitle, fontsize=10, color="#333333", va="top")
    fig.text(0.06, 0.008, FOOTER, fontsize=7.5, color=MUTED, va="bottom", linespacing=1.3)


def _declutter(ax, anns, step=3, iters=250):
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    start = {id(a): a.xyann for a in anns}
    for _ in range(iters):
        boxes = [a.get_window_extent(r).expanded(1.02, 1.2) for a in anns]
        moved = False
        for i in range(len(anns)):
            for j in range(i + 1, len(anns)):
                if boxes[i].overlaps(boxes[j]):
                    lo, hi = (i, j) if boxes[i].y0 < boxes[j].y0 else (j, i)
                    for k, d in ((lo, -step), (hi, step)):
                        anns[k].xyann = (anns[k].xyann[0], anns[k].xyann[1] + d)
                    moved = True
        if not moved:
            break
    for a in anns:
        if abs(a.xyann[1] - start[id(a)][1]) > 8:
            ax.annotate("", a.xy, xytext=a.xyann, textcoords="offset points",
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=0, shrinkB=4))


def scatter_png(df, x, y, path, title, subtitle, logx=False, logy=False, size=None, front=True,
                extra_labels=(), groups=None):
    groups = groups or [g for g in M.GROUPS if g in set(df.group)]
    fig, ax = plt.subplots(figsize=(11, 7.5))
    fig.subplots_adjust(left=0.08, right=0.78, top=0.86, bottom=0.12)
    for g in groups:
        s = df[df.group == g]
        ms = 70 if size is None else 30 + s[size].fillna(0).clip(lower=0) * 1.6
        ax.scatter(s[x], s[y], s=ms, c=COLORS[g], marker=MPL_MARK[g], edgecolors="black", linewidths=0.6,
                   label=g, zorder=3, alpha=0.95)
    labelled = set(extra_labels)
    if front:
        eligible = df[~df.group.isin(["Ingredients & snacks", "Supplements"])]
        fr = M.front(eligible, [x, y]).sort_values(x)
        ax.plot(fr[x], fr[y], color=INK2, lw=1, zorder=2, alpha=0.6)
        labelled |= set(fr.food_id)
    from matplotlib.ticker import FuncFormatter
    plain = FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}")
    if logx:
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(plain)
    if logy:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(plain)
    _style(ax, title, subtitle, label(x), label(y))
    to_axes = ax.transData + ax.transAxes.inverted()
    anns = []
    for _, r in df[df.food_id.isin(labelled) & df[x].notna() & df[y].notna() & (df[x] > 0)].iterrows():
        right = to_axes.transform((r[x], r[y]))[0] > 0.8
        anns.append(ax.annotate(r.name_en, (r[x], r[y]), xytext=(-7 if right else 7, 4), textcoords="offset points",
                                ha="right" if right else "left", fontsize=8.5, color=INK))
    _declutter(ax, anns)
    leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=True, fontsize=9, labelcolor="black",
                    title="Food group", title_fontsize=9, edgecolor="black", fancybox=False, framealpha=1)
    leg.get_frame().set_linewidth(0.8)
    if front:
        fig.text(0.79, 0.42, "Line = Pareto front:\nfoods no other food\nbeats on both axes\n"
                             "(ingredients, snacks,\nsupplements excluded)", fontsize=8.5, color="black", va="top")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def bars_png(df, value, path, title, subtitle, annot, xlabel):
    s = df.sort_values(value)
    fig, ax = plt.subplots(figsize=(11, max(6, 0.27 * len(s) + 2)))
    fig.subplots_adjust(left=0.25, right=0.97, top=1 - 1.1 / fig.get_figheight(), bottom=0.9 / fig.get_figheight())
    ax.barh(s.name_en, s[value], height=0.62, color=[COLORS[g] for g in s.group], zorder=3)
    for i, (_, r) in enumerate(s.iterrows()):
        ax.text(r[value] + s[value].max() * 0.01, i, annot(r), va="center", fontsize=8, color=INK2)
    ax.invert_yaxis()
    ax.set_xlim(0, s[value].max() * 1.5)
    _style(ax, title, subtitle, xlabel, "")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[g]) for g in M.GROUPS if g in set(s.group)]
    ax.legend(handles, [g for g in M.GROUPS if g in set(s.group)], loc="lower right", frameon=True, fontsize=9,
              labelcolor="black", edgecolor="black", fancybox=False, framealpha=1)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def dumbbell_png(df, a, b, path, title, subtitle, n=20):
    """Rank shift of the top-n foods by metric a when metric b is used instead (H1 chart)."""
    ra = df[a].rank(ascending=False)
    rb = df[b].rank(ascending=False)
    top = df.assign(ra=ra, rb=rb).nsmallest(n, "ra").sort_values("ra")
    fig, ax = plt.subplots(figsize=(10, 0.36 * n + 2))
    fig.subplots_adjust(left=0.25, right=0.95, top=1 - 1.1 / fig.get_figheight(), bottom=0.9 / fig.get_figheight())
    y = np.arange(len(top))
    for i, (_, r) in enumerate(top.iterrows()):
        ax.plot([r.ra, r.rb], [i, i], color=GRID, lw=2, zorder=2)
        ax.scatter([r.ra], [i], s=60, color=MUTED, zorder=3, edgecolors=SURFACE, linewidths=1.5)
        ax.scatter([r.rb], [i], s=60, color=COLORS[r.group], zorder=3, edgecolors=SURFACE, linewidths=1.5)
        ax.text(max(r.ra, r.rb) + 1, i, f"{r.ra:.0f} → {r.rb:.0f}", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, top.name_en)
    ax.invert_yaxis()
    _style(ax, title, subtitle, "rank (1 = best)", "")
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- plotly (app)
HOVER_COLS = ["name_en", "group", "kcal_100g_eaten", "useful_protein_100g_eaten", "kcal_per_eur",
              "useful_protein_per_eur", "diaas", "limiting_aa", "eur_per_kg_edible", "price_source", "price_grade",
              "comp_grade", "digest_grade"]
HOVER = ("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
         "%{customdata[2]:.0f} kcal and %{customdata[3]:.1f} g useful protein per 100 g eaten<br>"
         "%{customdata[4]:,.0f} kcal/€ · %{customdata[5]:.1f} g useful protein/€<br>"
         "DIAAS %{customdata[6]:.0f} (limiting: %{customdata[7]})<br>"
         "€%{customdata[8]:.2f}/kg edible (%{customdata[9]}, price grade %{customdata[10]})<br>"
         "grades: composition %{customdata[11]}, digestibility %{customdata[12]}<extra></extra>")


AXIS = dict(showline=True, linecolor="black", linewidth=1, mirror="allticks", ticks="inside", ticklen=6,
            tickwidth=1, tickcolor="black", showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False,
            minor=dict(ticks="inside", ticklen=3, tickcolor="black", showgrid=False),
            title_font=dict(size=14, color="black"), tickfont=dict(size=12, color="black"))


def _scientific(fig, height):
    """White background, full black frame with inward ticks on all sides, grid on both axes, black text,
    framed legend. Self-contained, so charts stay readable in Streamlit's dark theme too."""
    fig.update_layout(template="none", height=height, paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(family="Arial, Helvetica, sans-serif", size=13, color="black"),
                      margin=dict(l=75, r=25, t=25, b=70),
                      legend=dict(orientation="h", y=-0.18, bgcolor="white", bordercolor="black", borderwidth=1,
                                  font=dict(color="black")),
                      hoverlabel=dict(bgcolor="white", bordercolor="black", font=dict(color="black", size=12)))
    fig.update_xaxes(**AXIS)
    fig.update_yaxes(**AXIS)
    return fig


def scatter_fig(df, x, y, logx=False, logy=False, size=None, front=True, highlight=None, dark=False):
    fig = go.Figure()
    for g in [g for g in M.GROUPS if g in set(df.group)]:
        s = df[df.group == g]
        ms = 11 if size is None else (7 + s[size].fillna(0).clip(lower=0) * 0.25)
        fig.add_trace(go.Scatter(
            x=s[x], y=s[y], mode="markers", name=g, customdata=s[HOVER_COLS].values, hovertemplate=HOVER,
            marker=dict(color=COLORS[g], symbol=PLY_MARK[g], size=ms, line=dict(width=1, color="black"),
                        opacity=[1.0 if (highlight is None or f in highlight) else 0.2 for f in s.food_id])))
    labelled = set()
    eligible = df[~df.group.isin(["Ingredients & snacks", "Supplements"])]
    if front:
        fr = M.front(eligible, [x, y]).sort_values(x)
        fig.add_trace(go.Scatter(x=fr[x], y=fr[y], mode="lines", line=dict(color="black", width=1, dash="dot"),
                                 name="Pareto front", hoverinfo="skip"))
        labelled |= set(fr.food_id)
    # name the extremes on each axis too, so the chart is readable without hovering
    for col in (x, y):
        hib = M.METRICS.get(col, (None, None, True))[2]
        top = eligible.dropna(subset=[col])
        labelled |= set((top.nlargest(4, col) if hib is not False else top.nsmallest(4, col)).food_id)
    lab = df[df.food_id.isin(labelled) & df[x].notna() & df[y].notna()]
    fig.add_trace(go.Scatter(x=lab[x], y=lab[y], mode="text", text=lab.name_en, textposition="top center",
                             textfont=dict(size=11, color="black"), showlegend=False, hoverinfo="skip"))
    _scientific(fig, 640)
    fig.update_layout(xaxis_title=label(x), yaxis_title=label(y))
    # log axes: label only powers of ten (minor ticks stay unlabeled) → no digit clutter
    fig.update_xaxes(type="log", dtick=1, tickformat=",") if logx else fig.update_xaxes(type="linear")
    fig.update_yaxes(type="log", dtick=1, tickformat=",") if logy else fig.update_yaxes(type="linear")
    return fig


def ranking_bar_fig(df, score_col, n=25, dark=False):
    s = df.nlargest(n, score_col).iloc[::-1]
    fig = go.Figure(go.Bar(x=s[score_col], y=s.name_en, orientation="h",
                           marker=dict(color=[COLORS[g] for g in s.group], line=dict(color="black", width=0.6)),
                           customdata=s[HOVER_COLS].values, hovertemplate=HOVER, showlegend=False))
    _scientific(fig, max(420, 24 * len(s) + 90))
    fig.update_layout(margin=dict(l=210, r=25, t=20, b=60),
                      xaxis_title="Composite score (0–1, higher = better under your weights)")
    fig.update_xaxes(range=[0, 1.02])
    fig.update_yaxes(showgrid=False, minor=dict(ticks=""))
    return fig


def front_fig(fr):
    """Cost vs food-mass Pareto front of optimal diets (v1.0)."""
    fig = go.Figure(go.Scatter(x=fr.mass_g, y=fr.cost_eur, mode="lines+markers",
                               marker=dict(size=9, color="#2a78d6", line=dict(color="black", width=1)),
                               line=dict(color="#2a78d6", width=2), customdata=fr[["n_foods", "main_foods"]].values,
                               hovertemplate="%{x:,.0f} g/day · €%{y:.2f}/day<br>%{customdata[0]} foods: "
                                             "%{customdata[1]}<extra></extra>", showlegend=False))
    _scientific(fig, 420)
    fig.update_layout(xaxis_title="Food eaten per day (g)", yaxis_title="Cost per day (€)")
    fig.update_yaxes(rangemode="tozero")
    return fig
