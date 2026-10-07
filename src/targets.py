"""Target calculator (v0.2, PLAN B.1–B.5): profile + goal preset → daily energy and macronutrient targets.

Every target records the rule and literature source it came from (config/target_rules.yaml) or that it is
a user override. Conflicts between targets (e.g. a carbohydrate band that does not fit the energy target)
are reported, never silently resolved.

    from src.targets import load_profile, compute
    r = compute(load_profile("config/profiles/owner.yaml"))
    print(r.to_markdown())
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES = yaml.safe_load(open(ROOT / "config/target_rules.yaml"))
MICRO_RULES = yaml.safe_load(open(ROOT / "config/micronutrients.yaml"))
KCAL = {"protein": 4.0, "carb": 4.0, "fat": 9.0}


@dataclass
class Profile:
    name: str
    sex: str                       # "male" / "female"
    age: float
    mass_kg: float
    height_cm: float
    goal: str                      # preset key in target_rules.yaml
    training: dict = field(default_factory=lambda: {"modality": "none", "hours_per_week": 0})
    body_fat_pct: float | None = None
    target_mass_kg: float | None = None
    experience: str = "novice_intermediate"   # or "advanced"
    tdee_kcal: float | None = None            # measured / known energy expenditure (overrides the estimate)
    overrides: dict = field(default_factory=dict)  # energy_kcal, protein_g, carb_g, fat_g
    priorities: dict = field(default_factory=dict)
    appetite_max_g: float | None = None       # most food (g eaten/day) the person can comfortably eat; None = no limit
    dislikes: list = field(default_factory=list)  # food_ids never to use (optimizer, meal tool, AI export)

    @property
    def hours_per_day(self):
        return float(self.training.get("hours_per_week", 0)) / 7

    @property
    def modality(self):
        return self.training.get("modality", "none")


def load_profile(path):
    d = yaml.safe_load(open(path))
    d = {k: v for k, v in d.items() if k in Profile.__dataclass_fields__}
    return Profile(**d)


@dataclass
class Target:
    value: float | None            # recommended default
    low: float | None = None
    high: float | None = None
    unit: str = ""
    source: str = ""               # literature key, "user override" or "derived"
    rule: str = ""                 # human-readable derivation


@dataclass
class Micro:
    key: str
    label: str
    unit: str
    min: float | None
    max: float | None
    enforce: bool
    source: str
    note: str = ""


@dataclass
class Result:
    profile: Profile
    targets: dict
    warnings: list
    conflicts: list
    notes: list
    micros: dict = field(default_factory=dict)

    def micro_markdown(self):
        L = ["| Nutrient | Minimum | Maximum | Enforced | Source |\n|---|---|---|---|---|\n"]
        for m in self.micros.values():
            L.append(f"| {m.label} | {_f(m.min) + ' ' + m.unit if m.min is not None else '–'} | "
                     f"{_f(m.max) + ' ' + m.unit if m.max is not None else '–'} | {'yes' if m.enforce else 'report only'} | "
                     f"{m.source}{' (' + m.note + ')' if m.note else ''} |\n")
        return "".join(L)

    def to_markdown(self):
        p = self.profile
        L = [f"### Daily targets: {p.name}\n",
             f"{p.sex}, {p.age:g} y, {p.mass_kg:g} kg, {p.height_cm:g} cm; goal **{RULES['presets'][p.goal]['label']}**; "
             f"training {p.modality} {p.training.get('hours_per_week', 0):g} h/week\n\n",
             "| Target | Default | Range | Source | How |\n|---|---|---|---|---|\n"]
        for k, t in self.targets.items():
            rng = ("" if t.low is None and t.high is None else f"≥ {_f(t.low)}" if t.high is None
                   else f"≤ {_f(t.high)}" if t.low is None else f"{_f(t.low)}–{_f(t.high)}")
            L.append(f"| {k} | {_f(t.value)} {t.unit} | {rng} | {t.source} | {t.rule} |\n")
        for title, items in (("Conflicts", self.conflicts), ("Warnings", self.warnings), ("Notes", self.notes)):
            if items:
                L.append(f"\n**{title}**\n" + "".join(f"- {x}\n" for x in items))
        return "".join(L)


def _f(x):
    if x is None:
        return "–"
    return f"{x:,.0f}" if abs(x) >= 10 else f"{x:.2f}"


# ---------------------------------------------------------------- energy
def ree(p):
    """Resting energy expenditure (kcal/day) and which equation was used (decision D5)."""
    male = 1 if p.sex == "male" else 0
    if p.body_fat_pct is not None:
        ffm = p.mass_kg * (1 - p.body_fat_pct / 100)
        return 22.771 * ffm + 484.264, "ten Haaf FFM-based (tenhaaf2014)"
    if 18 <= p.age <= 35 and p.training.get("hours_per_week", 0) >= 3:
        v = 11.936 * p.mass_kg + 587.728 * p.height_cm / 100 - 8.129 * p.age + 191.027 * male + 29.279
        return v, "ten Haaf weight-based, recreational athletes (tenhaaf2014)"
    v = 10 * p.mass_kg + 6.25 * p.height_cm - 5 * p.age + (5 if male else -161)
    return v, "Mifflin-St Jeor (mifflin1990)"


def estimate_tdee(p):
    """REE × non-exercise PAL + net exercise energy ((MET − 1) × kg × h/day). Returns (tdee, exercise_kcal, info)."""
    e = RULES["energy"]
    r, eq = ree(p)
    met = e["exercise_met"][p.modality]
    ex = max(met - 1, 0) * p.mass_kg * p.hours_per_day
    tdee = r * e["non_exercise_pal"] + ex
    return tdee, met * p.mass_kg * p.hours_per_day, (
        f"REE {r:,.0f} kcal ({eq}) × PAL {e['non_exercise_pal']} + exercise {ex:,.0f} kcal "
        f"(MET {met} × {p.hours_per_day:.2f} h/day; MET values are an assumption)")


def ffm_kg(p):
    if p.body_fat_pct is not None:
        return p.mass_kg * (1 - p.body_fat_pct / 100), "from body fat %"
    bf = 15 if p.sex == "male" else 25
    return p.mass_kg * (1 - bf / 100), f"assumed {bf} % body fat (no body-fat value given)"


# ---------------------------------------------------------------- main computation
def compute(p: Profile) -> Result:
    if p.goal not in RULES["presets"]:
        raise ValueError(f"unknown goal {p.goal!r}; choose from {list(RULES['presets'])}")
    pre = RULES["presets"][p.goal]
    sg = RULES["safeguards"]
    T, W, C, N = {}, [], [], []
    o = p.overrides or {}

    # ---- energy expenditure
    est, ex_gross, how = estimate_tdee(p)
    if p.tdee_kcal:
        tdee, src = float(p.tdee_kcal), "user value"
        diff = tdee / est - 1
        if abs(diff) > 0.15:
            W.append(f"Your energy expenditure ({tdee:,.0f} kcal) differs {diff:+.0%} from the estimate "
                     f"({est:,.0f} kcal: {how}).")
            W.append("If your body mass does not change as planned within 2–3 weeks, adjust the expenditure value "
                     "(v3.0 will learn it from a weight log).")
    else:
        tdee, src = est, "estimate"
    pal = tdee / ree(p)[0]
    if pal > RULES["energy"]["pal_max_sustainable"]:
        W.append(f"Implied PAL {pal:.2f} > {RULES['energy']['pal_max_sustainable']} is hard to sustain (fao2004).")
    T["energy expenditure"] = Target(tdee, unit="kcal", source=src if p.tdee_kcal else "tenhaaf2014 / mifflin1990",
                                     rule=how if not p.tdee_kcal else f"user value (estimate {est:,.0f})")

    # ---- energy target
    en = pre["energy"]
    if "energy_kcal" in o:
        E, rule, source = float(o["energy_kcal"]), "user override", "user override"
    elif en["mode"] in ("maintain", "fit_macros"):
        E, rule, source = tdee, "maintenance = energy expenditure", "–"
    elif en["mode"] == "surplus":
        pct = en["pct_of_tdee_advanced"] if p.experience == "advanced" else en["pct_of_tdee"]
        E = tdee * (1 + pct / 100)
        lo, hi = en["rate_pct_bm_week"]
        rule = f"+{pct} % surplus; aim to gain {lo}–{hi} % body mass/week ≈ {p.mass_kg * lo / 100:.2f}–{p.mass_kg * hi / 100:.2f} kg/week"
        source = en["source"]
        if p.target_mass_kg and p.target_mass_kg > p.mass_kg:
            wk = (p.target_mass_kg - p.mass_kg) / (p.mass_kg * hi / 100), (p.target_mass_kg - p.mass_kg) / (p.mass_kg * lo / 100)
            N.append(f"Reaching {p.target_mass_kg:g} kg at {lo}–{hi} %/week takes ≈ {wk[0]:.0f}–{wk[1]:.0f} weeks; "
                     "part of the gain will be fat (helms2023, garthe2013).")
    else:  # deficit
        rate = en["rate_pct_bm_week"]
        deficit = p.mass_kg * rate / 100 * RULES["energy"]["kcal_per_kg_tissue_loss"] / 7
        E = tdee - deficit
        rule = f"−{deficit:,.0f} kcal/day for {rate} % body mass/week (7700 kcal/kg approximation)"
        source = en["source"]
    T["energy"] = Target(E, unit="kcal", source=source, rule=rule)

    # ---- protein
    pr = pre["protein_g_per_kg"]
    if "protein_g" in o:
        P = float(o["protein_g"])
        T["protein"] = Target(P, unit="g", source="user override", rule=f"= {P / p.mass_kg:.2f} g/kg")
    elif "lbm_range" in pr and p.body_fat_pct is not None:
        lbm = p.mass_kg * (1 - p.body_fat_pct / 100)
        lo, hi = pr["lbm_range"]
        P = lbm * (lo + hi) / 2
        T["protein"] = Target(P, lbm * lo, lbm * hi, "g", pr["source"],
                              f"{lo}–{hi} g/kg lean mass ({lbm:.0f} kg lean)")
    else:
        P = pr["default"] * p.mass_kg
        T["protein"] = Target(P, pr["min"] * p.mass_kg, pr["max"] * p.mass_kg if pr["max"] else None, "g",
                              pr["source"], f"{pr['default']} g/kg (range {pr['min']}–{pr['max'] or 'open'})")

    # ---- fat range (% of energy)
    fat_pct = sg[pre.get("fat_pct_key", "fat_pct_energy")]
    fat_lo, fat_hi = E * fat_pct[0] / 100 / 9, E * fat_pct[1] / 100 / 9

    # ---- carbohydrate range (band = minimum/maximum the training calls for; None = open)
    cb = pre["carbohydrate"]
    c_lo = c_hi = None
    if cb["mode"] == "pct_energy":
        c_lo, c_hi = E * cb["pct"][0] / 100 / 4, E * cb["pct"][1] / 100 / 4
        c_rule, c_src = f"{cb['pct'][0]}–{cb['pct'][1]} % of energy", cb["source"]
    elif cb["mode"] == "g_per_kg":
        c_lo, c_hi = cb["g_per_kg"][0] * p.mass_kg, cb["g_per_kg"][1] * p.mass_kg
        c_rule, c_src = f"{cb['g_per_kg'][0]}–{cb['g_per_kg'][1]} g/kg", cb["source"]
        if en["mode"] == "fit_macros" and "energy_kcal" not in o:   # carbohydrate loading needs room: raise energy
            need = (P * 4 + c_lo * 4) / (1 - fat_pct[0] / 100)
            if need > E:
                E = need
                T["energy"] = Target(E, unit="kcal", source=en["source"],
                                     rule=f"raised above expenditure ({tdee:,.0f}) to fit {cb['g_per_kg'][0]} g/kg "
                                          f"carbohydrate + protein + fat ≥ {fat_pct[0]} % E")
                fat_lo, fat_hi = E * fat_pct[0] / 100 / 9, E * fat_pct[1] / 100 / 9
    elif p.modality in ("endurance", "hybrid"):
        hpd = p.hours_per_day
        band = next(b for b in RULES["carbohydrate_bands"] if hpd <= b["max_h_per_day"])
        c_lo, c_hi = band["g_per_kg"][0] * p.mass_kg, band["g_per_kg"][1] * p.mass_kg
        c_rule, c_src = (f"training load '{band['name']}' ({hpd:.1f} h/day): "
                         f"{band['g_per_kg'][0]}–{band['g_per_kg'][1]} g/kg"), band["source"]
    elif p.modality == "strength" and "min_g_per_kg" in cb:
        c_lo = cb["min_g_per_kg"] * p.mass_kg
        c_rule, c_src = f"strength training, gaining: ≥ {cb['min_g_per_kg']}–5 g/kg (rest of energy)", cb["source"]
    else:
        c_rule = ("rest of energy after protein and fat (strength training in a deficit)" if p.modality == "strength"
                  else "rest of energy after protein and fat (no endurance-training band applies)")
        c_src = "helms2014" if p.modality == "strength" else "derived"

    # ---- default split: protein → fat at the middle of its % range → carbohydrate = rest; then fit the band
    mid_pct = (fat_pct[0] + fat_pct[1]) / 2
    if "fat_g" in o:
        Fg = float(o["fat_g"])
    else:
        Fg = E * mid_pct / 100 / 9
    if "carb_g" in o:
        Cg, c_rule, c_src = float(o["carb_g"]), "user override", "user override"
        if "fat_g" not in o:
            Fg = (E - P * 4 - Cg * 4) / 9
    else:
        Cg = (E - P * 4 - Fg * 9) / 4
        if c_lo is not None and Cg < c_lo:        # training needs more carbohydrate: take it from fat
            Cg = c_lo
            Fg = (E - P * 4 - Cg * 4) / 9 if "fat_g" not in o else Fg
        elif c_hi is not None and Cg > c_hi:      # more energy than the band needs: give it to fat
            Cg = c_hi
            Fg = (E - P * 4 - Cg * 4) / 9 if "fat_g" not in o else Fg
    T["carbohydrate"] = Target(Cg, c_lo, c_hi, "g", c_src, c_rule)
    fat_src = {"fat_pct_energy": "efsa2010f / thomas2016", "fat_pct_energy_fat_loss": "helms2014"}.get(
        pre.get("fat_pct_key", "fat_pct_energy"), "JUDGMENT CALL")
    T["fat"] = Target(Fg, fat_lo, fat_hi, "g", fat_src,
                      f"{fat_pct[0]}–{fat_pct[1]} % of energy (default {mid_pct:g} % unless the carbohydrate band needs room)")
    fs = pre.get("free_sugars_max_pct_energy", sg["free_sugars_max_pct_energy"])
    T["free sugars (max)"] = Target(E * fs / 100 / 4, unit="g", source="who2015" if fs == sg["free_sugars_max_pct_energy"]
                                    else "JUDGMENT CALL (race week)", rule=f"< {fs} % of energy")

    # ---- feasibility (B.5)
    if Cg < 0:
        C.append(f"Energy target {E:,.0f} kcal does not even cover protein {P:.0f} g + fat ≥ {fat_pct[0]} % E.")
    if Fg < fat_lo - 1e-6:
        need = P * 4 + (c_lo or 0) * 4 + fat_lo * 9
        C.append(f"Energy target {E:,.0f} kcal is too low for protein {P:.0f} g + carbohydrate ≥ {c_lo or 0:.0f} g + "
                 f"fat ≥ {fat_pct[0]} % E (needs ≈ {need:,.0f} kcal). Options: raise energy, lower the carbohydrate "
                 "band (less training) or accept less fat.")
    if Fg > fat_hi + 1e-6:
        C.append(f"Fat would be {Fg * 9 / E:.0%} of energy even with carbohydrate at the band maximum "
                 f"({c_hi:.0f} g). Options: more protein (up to {T['protein'].high or P:.0f} g), more carbohydrate "
                 "than the training band, or a smaller surplus.")

    # ---- energy availability warning (thomas2016, mountjoy2023)
    ffm, ffm_how = ffm_kg(p)
    ea = (E - ex_gross) / ffm
    if ea < sg["energy_availability_warn_kcal_per_kg_ffm"]:
        W.append(f"Low energy availability: ≈ {ea:.0f} kcal/kg fat-free mass/day (< 30 risks health and performance; "
                 f"45 ≈ balance). Fat-free mass {ffm:.0f} kg ({ffm_how}).")
    elif ea < sg["energy_availability_optimal_kcal_per_kg_ffm"]:
        N.append(f"Energy availability ≈ {ea:.0f} kcal/kg FFM/day (between 30 and 45; fine short-term, monitor).")
    N.append(f"Macro energy check: {P * 4 + Cg * 4 + Fg * 9:,.0f} kcal from protein/carb/fat vs target {E:,.0f} kcal.")

    # ---- training fuel: extra free sugars allowed for sugar taken during long sessions (burke2011; PLAN E.6)
    tf = MICRO_RULES["training_fuel"]
    if p.modality in tf["applies_to"] and p.hours_per_day > 0:
        extra = tf["g_per_hour"] * p.hours_per_day
        t = T["free sugars (max)"]
        T["free sugars (max)"] = Target(t.value + extra, unit="g", source=f"who2015 + {tf['source']}",
                                        rule=f"{t.rule} + {extra:.0f} g training fuel ({tf['g_per_hour']} g/h × "
                                             f"{p.hours_per_day:.1f} h/day)")
    return Result(p, T, W, C, N, micros=micro_targets(p, E))


def micro_targets(p: Profile, energy_kcal: float) -> dict:
    """Micronutrient, fibre, sodium and saturated-fat targets for an adult (config/micronutrients.yaml)."""
    if p.age < 18:
        raise ValueError("micronutrient targets are defined for adults (≥ 18 y) only")
    sex = "male" if p.sex == "male" else "female"
    mj = energy_kcal * 4.184 / 1000
    out = {}
    for k, r in MICRO_RULES["nutrients"].items():
        if "per_mj" in r:
            lo, note = r["per_mj"] * mj, f"{r['per_mj']} {r['unit']}/MJ × {mj:.1f} MJ"
        elif "pct_energy" in r:   # fatty acid as % of energy (9 kcal/g)
            lo, note = r["pct_energy"] / 100 * energy_kcal / 9, f"{r['pct_energy']} % of energy; {r.get('note', '')}"
        elif "min" in r:
            lo = r["min_18_24"] if (p.age <= 24 and "min_18_24" in r) else r["min"][sex]
            note = r.get("note", "") if not (k == "iron_mg" and sex == "male") else ""
        else:
            lo, note = None, r.get("note", "")
        out[k] = Micro(k, r["label"], r["unit"], lo, r.get("max"), r.get("enforce", True), r["source"], note)
    lim = MICRO_RULES["limits"]
    out["sodium_mg"] = Micro("sodium_mg", "Sodium", "mg", None, lim["sodium_mg"]["max"], True, lim["sodium_mg"]["source"],
                             lim["sodium_mg"]["note"])
    sf = lim["saturated_fat_pct_energy"]
    out["sat_fat"] = Micro("sat_fat", "Saturated fat", "g", None, energy_kcal * sf["max"] / 100 / 9, True, sf["source"],
                           f"< {sf['max']} % of energy")
    for k, ov in RULES["presets"][p.goal].get("micro_overrides", {}).items():
        out[k].min, out[k].max = ov.get("min", out[k].min), ov.get("max", out[k].max)
        out[k].note = "race-week override (JUDGMENT CALL)"
    if RULES["presets"][p.goal].get("micro_minimums") == "report":
        for m in out.values():
            if m.min is not None and m.key != "fibre_g":
                m.enforce, m.note = False, (m.note + "; " if m.note else "") + "reported only for this short phase"
    if p.goal in ("muscle_gain", "hybrid_gain"):
        fm = lim["fibre_max_g_bulking"]
        out["fibre_g"].max = fm["max"]
        out["fibre_g"].note = f"max {fm['max']} g while gaining: {fm['source']}"
    for k, r in MICRO_RULES["contaminants"].items():
        out[k] = Micro(k, r["label"], "µg", None, r["twi_ug_per_kg_week"] * p.mass_kg / 7, False, r["source"],
                       "tolerable weekly intake ÷ 7; reported only (data coverage ≈ 50–60 %)")
    return out


if __name__ == "__main__":
    import sys
    for f in sys.argv[1:] or sorted((ROOT / "config/profiles").glob("*.yaml")):
        print(compute(load_profile(f)).to_markdown(), "\n")
