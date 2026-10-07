"""Safe formulas over the food table for custom charts (friend feedback 2026-10-07).

A formula is an arithmetic expression over food columns, e.g.

    protein / kcal * 100                 protein per 100 kcal (g)
    fibre_sol_g / fibre * 100            soluble share of fibre (%)
    (protein * diaas / 100) / cost       useful protein per € of eaten food
    log10(vitamin_c_mg + 1)
    pct(kcal_per_eur)                    percentile rank 0–100
    dleu / kcal * 100                    digestible leucine per 100 kcal (g)

Filters are formulas that give true/false: `protein > 10 and group != "Supplements"`.

It is NOT Python: only numbers, column names, + − × ÷ ** %, comparisons, and/or/not, and the whitelisted functions
below are accepted (parsed with `ast`, evaluated with numpy/pandas). Nothing else can run, which keeps the shared
cloud app safe.
"""
import ast
import difflib
import re

import numpy as np
import pandas as pd

MAX_LEN = 400


class FormulaError(ValueError):
    pass


def _pct(s):
    return s.rank(pct=True) * 100


FUNCS = {
    "log": (np.log, "natural logarithm"), "log10": (np.log10, "base-10 logarithm"), "sqrt": (np.sqrt, "square root"),
    "exp": (np.exp, "e to the power"), "abs": (np.abs, "absolute value"),
    "min": (np.minimum, "element-wise minimum of two values, e.g. min(protein, 20)"),
    "max": (np.maximum, "element-wise maximum of two values"),
    "clip": (lambda x, lo, hi: np.clip(x, lo, hi), "clip(x, low, high)"),
    "pct": (_pct, "percentile rank among the shown foods (0–100, higher value → higher rank)"),
    "rank": (lambda s: s.rank(ascending=False, method="min"), "rank among the shown foods (1 = largest)"),
    "nz": (lambda s: s.fillna(0) if isinstance(s, pd.Series) else s, "missing → 0"),
    "where": (lambda c, a, b: pd.Series(np.where(c, a, b), index=c.index) if isinstance(c, pd.Series) else (a if c else b),
              "where(condition, if_true, if_false)"),
}
BIN = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide, ast.Pow: np.power,
       ast.Mod: np.mod}
CMP = {ast.Gt: np.greater, ast.Lt: np.less, ast.GtE: np.greater_equal, ast.LtE: np.less_equal, ast.Eq: np.equal,
       ast.NotEq: np.not_equal}


# ---------------------------------------------------------------- variables
NUTRIENT_NAMES = {
    "kcal": ("Energy", "kcal"), "protein": ("Protein", "g"), "useful_protein": ("Useful protein (protein × DIAAS)", "g"),
    "carb": ("Available carbohydrate", "g"), "fat": ("Fat", "g"), "sugars": ("Total sugars", "g"),
    "free_sugars": ("Free (added) sugars", "g"), "starch_g": ("Starch", "g"), "fibre": ("Dietary fibre", "g"),
    "fibre_sol_g": ("Soluble fibre (measured for few foods)", "g"), "fibre_insol_g": ("Insoluble fibre", "g"),
    "water": ("Water", "g"), "sodium_mg": ("Sodium", "mg"), "sat_fat": ("Saturated fat", "g"),
    "mufa_g": ("Monounsaturated fat", "g"), "pufa_g": ("Polyunsaturated fat", "g"), "trans_g": ("Trans fat", "g"),
    "n6_g": ("Omega-6 fat", "g"), "n3_g": ("Omega-3 fat", "g"), "ala_g": ("ALA (plant omega-3)", "g"),
    "epa_g": ("EPA (fish omega-3)", "g"), "dha_g": ("DHA (fish omega-3)", "g"),
}


AA_NAMES = {"HIS": "Histidine", "ILE": "Isoleucine", "LEU": "Leucine", "LYS": "Lysine", "MET": "Methionine",
            "CYS": "Cysteine", "PHE": "Phenylalanine", "TYR": "Tyrosine", "THR": "Threonine", "TRP": "Tryptophan",
            "VAL": "Valine"}


def _describe(col):
    from src import metrics as M
    if col in M.METRICS:
        n, u, _ = M.METRICS[col]
        return n, u
    m = re.fullmatch(r"(.+)_100g_(eaten|purchased)", col)
    if m:
        base, state = m.groups()
        name, unit = NUTRIENT_NAMES.get(base, (base.replace("_", " "), re.findall(r"_(mg|ug|g)(?:_|$)", base + "_")[:1] or [""]))
        unit = unit if isinstance(unit, str) else (unit[0] if unit else "")
        unit = unit.replace("ug", "µg")
        return f"{name} per 100 g {'eaten' if state == 'eaten' else 'as bought'}", f"{unit}/100 g"
    if col.endswith("_mg_per_g_protein"):
        return f"{col.split('_')[0]} per g protein", "mg/g"
    return col.replace("_", " "), ""


def variables(df):
    """{name: (Series, description, unit)} usable in formulas: every numeric column, short aliases for nutrients per
    100 g eaten (`protein` = protein_100g_eaten), `cost` (€ per 100 g eaten) and `price` (€/kg as bought), and the
    text columns `name`, `group`, `category`, `role` for filters."""
    out = {}
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]):
            d, u = _describe(c)
            out[c] = (df[c].astype(float), d, u)
    for c in list(df.columns):
        m = re.fullmatch(r"(.+)_100g_eaten", c)
        if m and m.group(1) not in out and pd.api.types.is_numeric_dtype(df[c]):
            d, u = _describe(c)
            out[m.group(1)] = (df[c].astype(float), d, u)
    # amino acids (owner request): g per 100 g eaten, total and digestible (true ileal digestibility, muleya2021)
    for aa in ["HIS", "ILE", "LEU", "LYS", "MET", "CYS", "PHE", "TYR", "THR", "TRP", "VAL"]:
        col = f"{aa}_mg_per_g_protein"
        if col in df and "protein_100g_eaten" in df:
            tot = (df.protein_100g_eaten * df[col] / 1000).astype(float)
            out[aa.lower()] = (tot, f"{AA_NAMES[aa]} per 100 g eaten", "g/100 g")
            if f"dig_{aa}" in df:
                out[f"d{aa.lower()}"] = ((tot * df[f"dig_{aa}"]).astype(float),
                                         f"Digestible {AA_NAMES[aa].lower()} per 100 g eaten", "g/100 g")
    if "eur_per_kg_used" in df:
        out["price"] = (df.eur_per_kg_used.astype(float), "Price per kg edible, as bought", "€/kg")
        if "yield_eaten_per_purchased" in df:
            out["cost"] = ((df.eur_per_kg_used / df.yield_eaten_per_purchased / 10).astype(float),
                           "Cost of 100 g as eaten", "€/100 g")
    for c, d in (("name_en", "Food name"), ("group", "Food group"), ("category", "Category"), ("role", "Role")):
        if c in df:
            out["name" if c == "name_en" else c] = (df[c], d, "text")
    return out


def reference(df):
    """Table of the variables for the app (name, meaning, unit, range over the shown foods)."""
    rows = []
    for k, (s, d, u) in variables(df).items():
        rng = "" if u == "text" else (f"{s.min():.3g} … {s.max():.3g}" if s.notna().any() else "no data")
        rows.append({"name": k, "meaning": d, "unit": u, "range": rng, "foods with data": int(s.notna().sum())})
    t = pd.DataFrame(rows)
    aas = [a.lower() for a in AA_NAMES] + [f"d{a.lower()}" for a in AA_NAMES]
    alias = t.name.isin(list(NUTRIENT_NAMES) + aas + ["price", "cost", "name", "group", "category", "role"])
    return pd.concat([t[alias], t[~alias]]).reset_index(drop=True)


# ---------------------------------------------------------------- evaluation
def _check(tree):
    depth = 0
    for node in ast.walk(tree):
        depth += 1
        if depth > 300:
            raise FormulaError("formula is too complex")
        ok = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.Call, ast.Name, ast.Load,
              ast.Constant, ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd) + tuple(BIN) + tuple(CMP)
        if not isinstance(node, ok):
            raise FormulaError(f"'{type(node).__name__}' is not allowed (only arithmetic, comparisons and functions)")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, str)) or \
                isinstance(node, ast.Constant) and isinstance(node.value, bool):
            raise FormulaError("only numbers and quoted text are allowed as constants")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in FUNCS or node.keywords):
            raise FormulaError(f"unknown function; available: {', '.join(FUNCS)}")


def evaluate(expr, env):
    """Evaluate a formula. env: {name: Series or number}. Returns a Series (or scalar); ±inf → NaN."""
    expr = (expr or "").strip()
    if not expr:
        raise FormulaError("empty formula")
    if len(expr) > MAX_LEN:
        raise FormulaError(f"formula longer than {MAX_LEN} characters")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"syntax error: {e.msg}") from None
    _check(tree)

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in env:
                return env[n.id]
            near = difflib.get_close_matches(n.id, list(env), n=3)
            raise FormulaError(f"unknown name '{n.id}'" + (f"; did you mean {', '.join(near)}?" if near else ""))
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else (+v if isinstance(n.op, ast.UAdd) else ~_bool(v))
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if _is_text(a) or _is_text(b):
                raise FormulaError("text can only be compared (==, !=), not calculated with")
            with np.errstate(all="ignore"):
                return BIN[type(n.op)](a, b)
        if isinstance(n, ast.Compare):
            out, left = None, ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = ev(comp)
                r = CMP[type(op)](left, right)
                out = r if out is None else (out & r)
                left = right
            return out
        if isinstance(n, ast.BoolOp):
            vals = [_bool(ev(v)) for v in n.values]
            out = vals[0]
            for v in vals[1:]:
                out = (out & v) if isinstance(n.op, ast.And) else (out | v)
            return out
        if isinstance(n, ast.Call):
            try:
                with np.errstate(all="ignore"):
                    return FUNCS[n.func.id][0](*[ev(a) for a in n.args])
            except TypeError as e:
                raise FormulaError(f"{n.func.id}(): {FUNCS[n.func.id][1]} ({e})") from None
        raise FormulaError("unsupported expression")

    v = ev(tree)
    if isinstance(v, pd.Series) and pd.api.types.is_numeric_dtype(v) and not pd.api.types.is_bool_dtype(v):
        v = v.replace([np.inf, -np.inf], np.nan)
    return v


def _is_text(v):
    return isinstance(v, str) or (isinstance(v, pd.Series) and not pd.api.types.is_numeric_dtype(v)
                                  and not pd.api.types.is_bool_dtype(v))


def _bool(v):
    if isinstance(v, pd.Series):
        return v.fillna(False).astype(bool) if v.dtype == object else v.astype(bool) if v.dtype == bool else v.fillna(0) != 0
    return bool(v)


def parse_definitions(text):
    """'name = formula' lines (# comments allowed) → list of (name, formula)."""
    out = []
    for i, line in enumerate((text or "").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line or line.count("==") or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=[^=]", line):
            raise FormulaError(f"line {i}: write 'name = formula'")
        name, f = line.split("=", 1)
        out.append((name.strip(), f.strip()))
    return out


def environment(df, definitions=""):
    """Variables of df plus the user's definitions (each may use earlier ones). Returns (env, meta) where meta maps
    user names to their formula."""
    env = {k: v[0] for k, v in variables(df).items()}
    meta = {}
    for name, f in parse_definitions(definitions):
        try:
            env[name] = evaluate(f, env)
        except FormulaError as e:
            raise FormulaError(f"{name}: {e}") from None
        meta[name] = f
    return env, meta
