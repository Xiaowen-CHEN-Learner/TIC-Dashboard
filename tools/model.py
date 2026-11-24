"""Loads data/*.json and walks every figure in it.

Shared by tools/build_static.py and tools/check.py so that the build and the
checks always read the data the same way.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCREENS = ROOT / "screens"

# Why a value is missing: (short text shown in the cell, long text for the legend).
REASONS = {
    "not_found": ("n/f", "not found in the sources used"),
    "not_applicable": ("n/a", "not applicable"),
    "not_meaningful": ("n/m", "not meaningful"),
}

# Source kind -> evidence label.
KIND_LABEL = {
    "filing": "verified_public_record",
    "company": "company_claim",
    "news": "secondary_report",
    "transcript": "secondary_report",
    "aggregator": "secondary_report",
    "advisory": "secondary_report",
}

LABELS = [
    "verified_public_record",
    "company_claim",
    "secondary_report",
    "computed",
    "not_found_in_scoped_search",
]

KINDS = {"money", "pct", "pct_change", "per_share", "per_share_1", "ratio", "count"}
CHANGES = {"raised", "lowered", "confirmed", "narrowed", "mixed", None}
STATUSES = ["raised", "mixed", "confirmed", "lowered"]

# News types shown on the TIC earnings news screen. Every other type goes to Industry news.
EARNINGS_TYPES = {"result"}
# Calendar entries are split the same way.
CALENDAR_KINDS = {"earnings", "other"}


def load():
    """Return every data file as one dict."""
    d = {}
    for name in ("meta", "companies", "financials", "news", "sources"):
        with open(DATA / f"{name}.json", encoding="utf-8") as f:
            d[name] = json.load(f)
    with open(SCREENS / "screens.json", encoding="utf-8") as f:
        d["screens"] = json.load(f)
    return d


def company_ids(d):
    return d["companies"]["order"]


def label_of(src, sources):
    """Evidence label for a cell source: a source id, 'computed' or a reason."""
    if src == "computed":
        return "computed"
    if src in REASONS:
        return "not_found_in_scoped_search" if src == "not_found" else None
    return KIND_LABEL[sources[src]["kind"]]


def period_src(period, metric):
    """Source of one metric in an interim period row."""
    if metric in (period.get("computed") or {}):
        return "computed"
    return (period.get("srcs") or {}).get(metric, period["src"])


def ytd_figure(fin, key):
    """The newest year-to-date figure for an annual row, as printed in the Latest column.

    Walks latest.ytd_order, newest period first, and returns (value, source, formula, period label)
    from the first period that carries the row key in v or extra. Returns None when no period does.
    """
    periods = {p["label"]: p for p in fin["interim"]["periods"]}
    for label in fin["latest"].get("ytd_order", []):
        per = periods.get(label)
        if per is None:
            continue
        for bag in (per["v"], per.get("extra") or {}):
            if key in bag:
                return bag[key], period_src(per, key), (per.get("computed") or {}).get(key), label
    return None


def iter_figures(d, charts=False):
    """Yield every figure cell as a dict.

    Keys: company, where ('annual' | 'interim' | 'segment' | 'chart'), row, col,
    value (number or None), src (source id, 'computed' or a reason), note.
    """
    fin = d["financials"]
    for cid in company_ids(d):
        co = fin[cid]
        cols = co["annual"]["columns"]
        for row in co["annual"]["rows"]:
            for col, cell in zip(cols, row["cells"]):
                yield {"company": cid, "where": "annual", "row": row["label"], "col": col,
                       "value": cell[0], "src": cell[1], "note": cell[2] if len(cell) > 2 else None}
        for per in co["interim"]["periods"]:
            for m in co["interim"]["metrics"]:
                if m["key"] not in per["v"]:
                    continue
                src = period_src(per, m["key"])
                note = (per.get("computed") or {}).get(m["key"])
                yield {"company": cid, "where": "interim", "row": m["label"], "col": per["label"],
                       "value": per["v"][m["key"]], "src": src, "note": note}
            for key, v in (per.get("extra") or {}).items():
                row = next((r["label"] for r in co["annual"]["rows"] if r["key"] == key), key)
                yield {"company": cid, "where": "interim", "row": row, "col": per["label"],
                       "value": v, "src": period_src(per, key), "note": None}
        for seg in co.get("segments", []):
            for r in seg["rows"]:
                for c in seg["columns"]:
                    v = r.get(c["key"])
                    if v is None:
                        continue
                    yield {"company": cid, "where": "segment", "row": f'{r["name"]}: {c["label"]}',
                           "col": seg["title"], "value": v, "src": seg["src"], "note": None}
        if charts:
            for ch in co.get("charts", []):
                for pt in ch["points"]:
                    yield {"company": cid, "where": "chart", "row": ch["title"], "col": pt[0],
                           "value": pt[1], "src": pt[2], "note": pt[3] if len(pt) > 3 else None}


def tally(d):
    """Count figures by evidence label, and how many a person has checked."""
    sources = d["sources"]["sources"]
    by_label = {k: 0 for k in LABELS}
    sourced = checked = 0
    for f in iter_figures(d):
        label = label_of(f["src"], sources)
        if label is None:
            continue
        by_label[label] += 1
        if f["src"] in sources:
            sourced += 1
            if sources[f["src"]].get("reviewed_by"):
                checked += 1
    return {"by_label": by_label, "sourced": sourced, "checked": checked}


def source_use(d):
    """How many times each source is cited anywhere in the data."""
    use = {k: 0 for k in d["sources"]["sources"]}

    def hit(sid):
        if sid in use:
            use[sid] += 1

    for f in iter_figures(d, charts=True):
        hit(f["src"])
    for cid in company_ids(d):
        co = d["companies"]["companies"][cid]
        for s in co["profile_sources"]:
            hit(s)
        for s in (co.get("status") or {}).get("sources", []):
            hit(s)
        fin = d["financials"][cid]
        for seg in fin.get("segments", []):
            for s in seg.get("srcs", []):
                hit(s)
        o = fin["outlook"]
        hit(o["src"])
        for it in o["items"]:
            if it.get("src"):
                hit(it["src"])
        if o.get("targets"):
            hit(o["targets"]["src"])
    n = d["news"]
    for item in n["news"]:
        for s in item["sources"]:
            hit(s)
    for c in n["calls"]:
        for s in c["links"] + c["sources"]:
            hit(s)
    for c in n["earlier_calls"]:
        hit(c["link"])
    for c in n["calendar"] + n["calendar_windows"]:
        hit(c["src"])
    return use
