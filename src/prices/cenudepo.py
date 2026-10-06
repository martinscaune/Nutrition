"""Collect per-shop prices from cenudepo.lv for selected food categories (personal-use phase).

Polite by design: one request every DELAY seconds, raw HTML cached (gzipped) under
data/raw/cenudepo/<date>/html/ so pages are never fetched twice in a run and can be re-parsed.

Output: data/raw/cenudepo/<date>/observations_raw.csv  (one row per product × shop)
Mapping: data/prices/cenudepo_map.csv (category slugs + include/exclude regex on product names)

Usage:  python -m src.prices.cenudepo [food_id ...]
"""
import csv
import datetime as dt
import gzip
import hashlib
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://cenudepo.lv"
DELAY = 3.0
MAX_PRODUCTS = 20  # per food; evenly spaced over the listing (sorted by €/kg) when there are more
UA = "Mozilla/5.0 (personal nutrition research; low-rate)"
TODAY = dt.date.today().isoformat()
RAW = ROOT / "data/raw/cenudepo" / TODAY
HTML = RAW / "html"

STORE_BRANDS = {"RIMI", "RIMI BASIC", "RIMI SMART", "MAXIMA", "MAXIMA XXX", "AIBE", "SPAR", "TOP", "TOP!", "CITRO",
                "ELVI", "GOLDEN SUN", "PILOS", "MILBONA", "CROWNFIELD", "FRESHONA", "NIXE", "CHEF SELECT", "ALESTO",
                "VEMONDO", "SNACK DAY", "MCENNEDY", "FAVORIT", "MEGO", "LATS", "PROMO", "FIT&ACTIVE", "BELBAKE"}
_last = 0.0


def fetch(path):
    """GET a cenudepo.lv path, cached on disk; never more often than one request per DELAY seconds."""
    global _last
    HTML.mkdir(parents=True, exist_ok=True)
    f = HTML / (hashlib.sha1(path.encode()).hexdigest()[:16] + ".html.gz")
    if f.exists():
        return gzip.decompress(f.read_bytes()).decode("utf-8", "replace")
    wait = DELAY - (time.time() - _last)
    if wait > 0:
        time.sleep(wait + random.uniform(0, 0.5))
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            body = urllib.request.urlopen(req, timeout=30).read()
            break
        except Exception as e:  # noqa: BLE001
            print(f"  retry {attempt + 1} {path}: {e}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError(f"failed: {path}")
    _last = time.time()
    f.write_bytes(gzip.compress(body))
    with open(RAW / "fetch_log.tsv", "a") as log:
        log.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{path}\t{f.name}\n")
    return body.decode("utf-8", "replace")


def category_products(slug):
    """All products listed in a category (follows ?lapa=N pagination). Returns [(name, href)] in listing order."""
    out, page = [], 1
    while True:
        h = fetch(f"/kategorija/{slug}/" + (f"?lapa={page}" if page > 1 else ""))
        items = re.findall(r'<a class="deal" href="(/product/[^"]+)">.*?<div class="deal-name">(.*?)</div>', h, re.S)
        out += [(unescape(n), href) for href, n in items]
        if f"?lapa={page + 1}" not in h or not items:
            return out
        page += 1


def unescape(s):
    import html
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def product_offers(href):
    """Per-shop offers on a product page: [{shop, date, price, old_price}] + brand."""
    h = fetch(href)
    brand = ""
    m = re.search(r'"brand":\{"@type":"Brand","name":"([^"]*)"', h)
    if m:
        brand = m.group(1)
    offers = []
    for row in re.findall(r'<div class="cmp-row[^"]*">(.*?)</div>\s*</div>\s*(?=<div class="cmp-row|</div>\s*</section>)', h, re.S):
        shop = re.search(r'<span class="nm">([^<]+)', row)
        date = re.search(r'<span class="smeta">([0-9.]+)', row)
        prices = [float(p.replace(",", ".")) for p in re.findall(r"([0-9]+[.,][0-9]{2})\s*&euro;", row)]
        if shop and prices:
            offers.append({"shop": shop.group(1).strip(), "date": date.group(1) if date else "",
                           "price": min(prices), "old_price": max(prices) if len(prices) > 1 else None})
    return brand, offers


PACK = re.compile(r"(?:(\d+)\s*[X×]\s*)?(\d+(?:[.,]\d+)?)\s*(KG|G|L|ML|GAB)\b", re.I)


def pack_size(name):
    """(grams_or_ml, unit, count) parsed from a product name like '4×125G', '1KG', '0,5L', '10GAB'."""
    m = None
    for m in PACK.finditer(name.upper()):
        pass  # take the last size in the name (often the net mass)
    if not m:
        return None, "", None
    n = int(m.group(1)) if m.group(1) else 1
    v = float(m.group(2).replace(",", "."))
    u = m.group(3).upper()
    if u == "GAB":
        return None, "pcs", int(v) * n
    mult = {"KG": 1000, "G": 1, "L": 1000, "ML": 1}[u]
    return v * mult * n, ("ml" if u in ("L", "ML") else "g"), None


def tier(name, brand):
    up = name.upper()
    if re.search(r"\bBIO\b|ORGANIC|\bEKO\b|ECO\b", up):
        return "organic"
    if brand.upper() in STORE_BRANDS:
        return "store_brand"
    return "standard"


def spaced(items, k):
    if len(items) <= k:
        return items
    idx = sorted({round(i * (len(items) - 1) / (k - 1)) for i in range(k)})
    return [items[i] for i in idx]


def main(only=()):
    RAW.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(ROOT / "data/prices/cenudepo_map.csv")))
    out_f = RAW / "observations_raw.csv"
    fields = ["food_id", "purpose", "date_collected", "shop", "price_date", "product_name", "brand", "tier",
              "pack_size", "pack_unit", "pack_count", "price_eur", "old_price_eur", "price_type", "url"]
    new = not out_f.exists()
    w = csv.DictWriter(open(out_f, "a", newline=""), fieldnames=fields)
    if new:
        w.writeheader()
    done = set()
    if not new:
        done = {r["food_id"] for r in csv.DictReader(open(out_f))}
    for r in rows:
        fid = r["food_id"]
        if (only and fid not in only) or fid in done:
            continue
        inc = re.compile(r["include_regex"], re.I) if r["include_regex"] else None
        exc = re.compile(r["exclude_regex"], re.I) if r["exclude_regex"] else None
        seen, cands = set(), []
        for slug in r["categories"].split(";"):
            for name, href in category_products(slug):
                if href in seen or (inc and not inc.search(name)) or (exc and exc.search(name)):
                    continue
                seen.add(href)
                cands.append((name, href))
        chosen = spaced(cands, MAX_PRODUCTS)
        print(f"{fid}: {len(cands)} matching products, fetching {len(chosen)}", flush=True)
        for name, href in chosen:
            brand, offers = product_offers(href)
            size, unit, count = pack_size(name)
            for o in offers:
                w.writerow({"food_id": fid, "purpose": r["purpose"], "date_collected": TODAY, "shop": o["shop"],
                            "price_date": o["date"], "product_name": name, "brand": brand, "tier": tier(name, brand),
                            "pack_size": size or "", "pack_unit": unit, "pack_count": count or "",
                            "price_eur": o["price"], "old_price_eur": o["old_price"] or "",
                            "price_type": "discount_all" if o["old_price"] else "regular", "url": BASE + href})
        sys.stdout.flush()
    print("done →", out_f)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
