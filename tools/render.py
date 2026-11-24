"""Turns data/*.json into the HTML blocks that the screen templates ask for.

Every block is a plain function of the data. Nothing here invents a number:
figures are printed as stored, with their source, or derived by a formula that
tools/check.py also verifies.
"""
from html import escape as esc

import charts
import stockindex
from charts import ln_month
from model import (EARNINGS_TYPES, LABELS, REASONS, STATUSES, label_of, period_src, review, source_use, tally,
                   ytd_figure)

MINUS = "−"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
EV_CLASS = {"verified_public_record": "public", "company_claim": "claim", "secondary_report": "secondary",
            "computed": "computed", "not_found_in_scoped_search": "missing"}
WORD = {"raised": "Raised", "lowered": "Lowered", "confirmed": "Confirmed", "narrowed": "Narrowed", "mixed": "Mixed"}
LOGO = ('<svg class="logo" width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">'
        '<rect width="28" height="28" rx="7" fill="#1D4ED8"/>'
        '<path d="M7.5 14.5l4.2 4.2 8.8-9.4" fill="none" stroke="#fff" stroke-width="2.6" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>')


# ---------- formatting ----------

def fdate(iso, long=False):
    if not iso:
        return "Undated"
    p = iso.split("-")
    month = MONTHS[int(p[1]) - 1] if long else MONTHS[int(p[1]) - 1][:3]
    return f"{month} {p[0]}" if len(p) == 2 else f"{int(p[2])} {month} {p[0]}"


def _n(v, dp):
    return f"{abs(v):,.{dp}f}"


def f_money(v, dp):
    return f"({_n(v, dp)})" if v < 0 else _n(v, dp)


def f_pct(v):
    return (MINUS if v < 0 else "") + f"{abs(v):.1f}%"


def f_change(v):
    return ("+" if v > 0 else MINUS if v < 0 else "") + f"{abs(v):.1f}%"


def f_ratio(v):
    s = f"{v:.2f}".rstrip("0")
    return (s + "0" if s.endswith(".") else s) + "x"


def fmt(v, kind, dp):
    if kind == "money":
        return f_money(v, dp)
    if kind == "pct":
        return f_pct(v)
    if kind == "pct_change":
        return f_change(v)
    if kind == "per_share":
        return f_money(v, 2)
    if kind == "per_share_1":
        return f_money(v, 1)
    if kind == "ratio":
        return f_ratio(v)
    if kind == "count":
        return f"{v:,.0f}"
    raise ValueError(kind)


def big(co, v):
    """Money with its currency, for tiles and summary tables: $3,053m."""
    s = f'{co["money_prefix"]}{_n(v, co["dp"])}m'
    return f"({s})" if v < 0 else s


# ---------- context ----------

class Ctx:
    def __init__(self, d, single=False):
        self.d, self.single = d, single
        self.src = d["sources"]["sources"]
        self.cos = d["companies"]["companies"]
        self.order = d["companies"]["order"]
        self.fin, self.news, self.meta = d["financials"], d["news"], d["meta"]
        self.screens = d["screens"]["screens"]
        self.as_of = d["meta"]["as_of"]
        self.px = d["prices"]
        self.ix = stockindex.build(self.px, self.order)  # both share-price indexes, computed once

    def href(self, screen_id, frag=None):
        s = next(x for x in self.screens if x["id"] == screen_id)
        if self.single:
            return "#" + (frag or s["id"])
        return s["file"] + (f"#{frag}" if frag else "")

    def label(self, sid):
        return label_of(sid, self.src)

    def ev(self, label):
        return f'<span class="ev ev-{EV_CLASS[label]}">{label}</span>'

    def ext(self, sid, text=None):
        s = self.src[sid]
        return (f'<a href="{esc(s["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
                f'{esc(text or s["publisher"])}</a>')

    def co_name(self, cid):
        return "Industry" if cid == "industry" else self.cos[cid]["short"]

    def fin_link(self, cid, text=None):
        return f'<a href="{self.href("financials", "fin-" + cid)}">{esc(text or self.cos[cid]["short"])}</a>'

    def sec_no(self, cid):
        """Section number of a company on the Company financials screen: 3.1, 3.2 and so on."""
        screen = next(s for s in self.screens if s["id"] == "financials")
        return f'{int(screen["num"])}.{self.order.index(cid) + 1}'


class Refs:
    """Numbered source list for one block; marks link to the list entries."""

    def __init__(self, ctx, prefix):
        self.ctx, self.prefix, self.ids = ctx, prefix, []

    def mark(self, sid):
        if sid not in self.ids:
            self.ids.append(sid)
        n = self.ids.index(sid) + 1
        return (f'<a class="ref" href="#{self.prefix}-{n}" '
                f'title="{esc(self.ctx.src[sid]["title"], quote=True)}">{n}</a>')

    def marks(self, sids):
        seen = []
        for s in sids:
            if s not in seen:
                seen.append(s)
        return " ".join(self.mark(s) for s in seen)

    def render(self):
        items = []
        for i, sid in enumerate(self.ids, 1):
            s = self.ctx.src[sid]
            items.append(f'<li id="{self.prefix}-{i}">{self.ctx.ext(sid, s["title"])}. '
                         f'{esc(s["publisher"])}, {fdate(s["date"])}. {self.ctx.ev(self.ctx.label(sid))}</li>')
        return f'<ol class="src-list">{"".join(items)}</ol>'


# ---------- shared pieces ----------

def role_row(fin, role):
    return next((r for r in fin["annual"]["rows"] if r.get("role") == role), None)


def latest(ctx, cid):
    """The headline interim row, and the row its organic growth comes from."""
    fin = ctx.fin[cid]
    periods = {p["label"]: p for p in fin["interim"]["periods"]}
    row = periods[fin["latest"]["period"]]
    return row, periods[fin["latest"].get("organic_from", fin["latest"]["period"])]


def cell(ctx, co, v, src, kind, note=None, cls="num", under=None):
    """One table cell with its marker and hover text. under is a small line printed below the value."""
    if v is None:
        short, long = REASONS[src]
        return f'<td class="{cls} na" title="{long.capitalize()}">{short}</td>'
    marks, title = "", []
    if src == "computed":
        marks = '<sup class="mk">c</sup>'
        title.append("Computed here" + (f": {note}" if note else ""))
    else:
        s = ctx.src[src]
        title.append(f'{s["publisher"]}: {s["title"]}')
        if ctx.label(src) == "secondary_report":
            marks += '<sup class="mk">s</sup>'
        if note:
            marks += '<sup class="mk">†</sup>'
            title.append(note)
    small = f"<small>{esc(under)}</small>" if under else ""
    return f'<td class="{cls}" title="{esc(". ".join(title), quote=True)}">{fmt(v, kind, co["dp"])}{marks}{small}</td>'


def figure(title, sub, svg, note=None, cls="card chart", level=2):
    sub_html = f'<p class="sub">{esc(sub)}</p>' if sub else ""
    note_html = f'<p class="chart-note">{esc(note)}</p>' if note else ""
    return (f'<figure class="{cls}"><figcaption><h{level}>{esc(title)}</h{level}>{sub_html}</figcaption>'
            f'<div class="chart-box">{svg}</div>{note_html}</figure>')


def status_pill(key):
    return f'<span class="st st-{key}">{WORD[key]}</span>'


DAGGER = '<sup class="mk">†</sup>'
LEGEND = ('<p class="legend"><sup class="mk">c</sup> computed here. <sup class="mk">s</sup> from a secondary '
          'source. <sup class="mk">†</sup> see the notes under the table. n/f: not found in the sources used. '
          'n/a: not applicable. n/m: not meaningful. A dash means not reported for the period, or not captured.</p>')


# ---------- shell ----------

def sidebar(ctx, active):
    nav = []
    for s in ctx.screens:
        cur = ' aria-current="page"' if s["id"] == active else ""
        nav.append(f'<a class="nav-item" data-screen="{s["id"]}" href="{ctx.href(s["id"])}"{cur}>'
                   f'<span class="nav-num">{s["num"]}</span><span>{esc(s["label"])}</span></a>')
        if s["id"] == "financials":  # one numbered entry per company section
            subs = "".join(f'<a class="nav-sub" href="{ctx.href("financials", "fin-" + cid)}" data-jump="fin-{cid}">'
                           f'<span class="nav-num">{ctx.sec_no(cid)}</span> <span>{esc(ctx.cos[cid]["short"])}</span></a>'
                           for cid in ctx.order)
            nav.append(f'<div class="nav-subs">{subs}</div>')
    return (f'<aside class="side" aria-label="Dashboard navigation">'
            f'<a class="brand" href="{ctx.href("overview")}">{LOGO}<span class="brand-t"><strong>TIC Industry</strong>'
            f'<small>Dashboard</small></span></a>'
            f'<nav class="nav" aria-label="Screens"><p class="nav-h">Screens</p>{"".join(nav)}</nav>'
            f'<div class="side-foot"><p>As of {fdate(ctx.as_of)}</p><p>Public sources only. Not investment advice.</p></div>'
            f'</aside>')


REVIEW_LEAD = {"none": "Unverified draft.", "part": "Partly checked.", "all": "Checked by a person."}


def names(items):
    """Xavier Chen; A and B; A, B and C."""
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def review_dates(r):
    """on 24 November 2026, or between two dates when the sign-offs were given on different days."""
    if r["first"] == r["last"]:
        return f'on {fdate(r["last"], long=True)}'
    return f'between {fdate(r["first"], long=True)} and {fdate(r["last"], long=True)}'


def banner(ctx):
    """The note on every screen. Its wording follows how much a person has signed off."""
    r, b = review(ctx.d), ctx.meta["banner"]
    fill = {"{as_of}": fdate(ctx.as_of, long=True), "{checked}": f'{r["checked"]:,}', "{sourced}": f'{r["sourced"]:,}',
            "{px_done}": str(r["px_done"]), "{px_total}": str(r["px_total"]),
            "{who}": names(r["who"]) if r["who"] else "", "{when}": review_dates(r) if r["who"] else ""}
    text = " ".join((b["intro"], b[r["state"]], b["outro"]))
    for k, v in fill.items():
        text = text.replace(k, v)
    cls = "note note-ok" if r["state"] == "all" else "note"
    return (f'<div class="{cls}" role="note"><strong>{REVIEW_LEAD[r["state"]]}</strong> {esc(text)} '
            f'<a href="{ctx.href("sources")}">Sources and method</a></div>')


# ---------- overview ----------

def outlook_summary(ctx):
    groups = {s: [] for s in STATUSES}
    for cid in ctx.order:
        groups[ctx.fin[cid]["latest"]["status"]].append(cid)
    cols = []
    for st in STATUSES:
        items = "".join(f'<li>{ctx.fin_link(cid)}<span>{esc(ctx.fin[cid]["latest"]["status_text"])}</span></li>'
                        for cid in groups[st]) or '<li class="muted">None</li>'
        cols.append(f'<div class="st-col"><p class="st-h">{status_pill(st)}<span class="st-n">{len(groups[st])}</span></p>'
                    f'<ul>{items}</ul></div>')
    return f'<div class="st-grid">{"".join(cols)}</div>'


def scoreboard(ctx):
    rows = []
    for cid in ctx.order:
        co, fin = ctx.cos[cid], ctx.fin[cid]
        row, orow = latest(ctx, cid)
        g, o, m = row["v"].get("growth"), orow["v"].get("organic"), row["v"].get("margin")
        otag = ""
        if orow is not row or co["organic_label"] != "Organic growth":
            bits = ([co["organic_label"].lower()] if co["organic_label"] != "Organic growth" else []) + \
                   ([orow["label"]] if orow is not row else [])
            otag = f'<small>{esc(", ".join(bits))}</small>'
        margin = (f'{f_pct(m)}<small>{esc(co["margin_measure"])}</small>' if m is not None
                  else '<span class="muted">Revenue only</span>')
        rep = f'Reported {fdate(row["reported"])}' if row.get("reported") else ""
        rows.append(
            f'<tr><th scope="row">{ctx.fin_link(cid)}<small>{esc(co["listing"])}</small></th>'
            f'<td>{esc(row["label"])}<small>{rep}</small></td>'
            f'{_money_td(ctx, co, row)}'
            f'<td class="num">{f_change(g) if g is not None else "<span class=na>n/f</span>"}</td>'
            f'<td class="num">{f_change(o) if o is not None else "<span class=na>n/f</span>"}{otag}</td>'
            f'<td class="num">{margin}</td>'
            f'<td>{status_pill(fin["latest"]["status"])}<small>{esc(fin["latest"]["status_text"])}</small></td>'
            f'<td>{ctx.ev(ctx.label(row["src"]))}<small>{ctx.ext(row["src"])}</small></td></tr>')
    return ('<div class="table-wrap"><table class="t score"><thead><tr><th scope="col">Company</th>'
            '<th scope="col">Period</th><th scope="col" class="num">Revenue</th>'
            '<th scope="col" class="num">Reported growth</th><th scope="col" class="num">Organic growth</th>'
            '<th scope="col" class="num">Margin</th><th scope="col">Full-year outlook</th>'
            f'<th scope="col">Evidence</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _money_td(ctx, co, row):
    src = period_src(row, "revenue")
    mark = '<sup class="mk">c</sup>' if src == "computed" else ""
    return f'<td class="num">{big(co, row["v"]["revenue"])}{mark}</td>'


def chart_organic(ctx):
    rows = []
    for cid in ctx.order:
        co = ctx.cos[cid]
        _, orow = latest(ctx, cid)
        v = orow["v"].get("organic")
        if v is None:
            continue
        lfl = co["organic_label"] != "Organic growth"
        rows.append({"label": co["short"], "sub": orow["label"] + (", like-for-like" if lfl else ""), "value": v,
                     "title": f'{co["short"]}, {orow["label"]}: {f_change(v)} ({co["organic_label"].lower()})'})
    rows.sort(key=lambda r: -r["value"])
    svg = charts.hbars([(None, rows)], f_change, "Organic revenue growth in the latest reported period, ranked by company")
    return figure("Organic growth, latest reported period",
                  "Each company's own definition, ranked. Periods differ and are printed under each name.", svg,
                  "The latest-period table above carries the same figures.")


def chart_margins(ctx):
    fam = {"operating": [], "ebitda": []}
    for cid in ctx.order:
        co, fin = ctx.cos[cid], ctx.fin[cid]
        v = role_row(fin, "margin")["cells"][-1][0]
        col = fin["annual"]["columns"][-1]
        fam[co["margin_family"]].append({"label": co["short"], "sub": col, "value": v,
                                         "title": f'{co["short"]}, {col}: {f_pct(v)} ({co["margin_measure"].lower()})'})
    for rows in fam.values():
        rows.sort(key=lambda r: -r["value"])
    svg = charts.hbars([("Operating profit margins, adjusted or underlying", fam["operating"]),
                        ("Adjusted EBITDA margins", fam["ebitda"])], f_pct,
                       "Headline profit margin in the latest full year, in two groups by profit measure")
    return figure("Headline margin, latest full year",
                  "Two groups because the measures differ. EBITDA margins sit above operating margins by construction.",
                  svg, "The latest-full-year table below carries the same figures.")


def fullyear_table(ctx):
    rows = []
    for cid in ctx.order:
        co, fin = ctx.cos[cid], ctx.fin[cid]
        col = fin["annual"]["columns"][-1]

        def last(role, kind=None):
            r = role_row(fin, role)
            if r is None:
                return '<td class="num na" title="Not found in the sources used">n/f</td>'
            c = r["cells"][-1]
            return cell(ctx, co, c[0], c[1], kind or r["kind"], c[2] if len(c) > 2 else None)

        rev = role_row(fin, "revenue")["cells"][-1]
        rows.append(f'<tr><th scope="row">{ctx.fin_link(cid)}<small>{esc(co["unit"])}</small></th>'
                    f'<td>{esc(col)}<small>Year to {esc(co["fy_end"])}</small></td>'
                    f'<td class="num">{big(co, rev[0])}</td>{last("growth")}{last("organic")}'
                    f'<td>{esc(co["profit_measure"])}</td>{last("profit")}{last("margin")}{last("leverage")}</tr>')
    return ('<div class="table-wrap"><table class="t"><thead><tr><th scope="col">Company</th>'
            '<th scope="col">Fiscal year</th><th scope="col" class="num">Revenue</th>'
            '<th scope="col" class="num">Reported growth</th><th scope="col" class="num">Organic growth</th>'
            '<th scope="col">Headline profit measure</th><th scope="col" class="num">Profit</th>'
            '<th scope="col" class="num">Margin</th><th scope="col" class="num">Net debt / EBITDA</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>{LEGEND}')


def next_dates(ctx):
    cal = sorted((c for c in ctx.news["calendar"] if c["date"] >= ctx.as_of), key=lambda c: c["date"])
    items = [f'<li><span class="when">{esc(w["window"])}</span><span>{ctx.fin_link(w["company"])}: {esc(w["event"])}</span></li>'
             for w in ctx.news["calendar_windows"]]
    items += [f'<li><span class="when"><time datetime="{c["date"]}">{fdate(c["date"])}</time></span>'
              f'<span>{ctx.fin_link(c["company"])}: {esc(c["event"])}</span></li>' for c in cal[:4]]
    return f'<ul class="dates">{"".join(items)}</ul><p class="legend">{esc(ctx.news["calendar_note"])}</p>'


def open_items(ctx, n=4):
    items = "".join(f"<li>{esc(g)}</li>" for g in ctx.meta["known_gaps"][:n])
    more = len(ctx.meta["known_gaps"]) - n
    return (f'<ul class="gaps">{items}</ul><p class="more"><a href="{ctx.href("sources", "gaps")}">'
            f'{more} more gaps, and how the data was compiled</a></p>')


# ---------- news: shared by the Industry news and TIC earnings news screens ----------

def news_items(ctx, earnings):
    """Results items for the earnings screen; every other type for the industry screen."""
    return [it for it in ctx.news["news"] if (it["type"] in EARNINGS_TYPES) == earnings]


def company_chips(ctx, industry):
    """industry adds a chip for sector items that belong to no single company."""
    chips = ['<button class="chip" type="button" data-filter-company="all" aria-pressed="true">All companies</button>']
    chips += [f'<button class="chip" type="button" data-filter-company="{cid}" aria-pressed="false">'
              f'{esc(ctx.cos[cid]["short"])}</button>' for cid in ctx.order]
    if industry:
        chips.append('<button class="chip" type="button" data-filter-company="industry" aria-pressed="false">Industry</button>')
    return f'<div class="chips" role="group" aria-label="Filter by company">{"".join(chips)}</div>'


def type_chips(ctx):
    chips = ['<button class="chip" type="button" data-filter-type="all" aria-pressed="true">All types</button>']
    chips += [f'<button class="chip" type="button" data-filter-type="{k}" aria-pressed="false">{esc(v)}</button>'
              for k, v in ctx.news["types"].items() if k not in EARNINGS_TYPES]
    return f'<div class="chips" role="group" aria-label="Filter by type">{"".join(chips)}</div>'


def results_log(ctx):
    """One row per results release in the as-of year: full-year results and each interim release."""
    year = ctx.as_of[:4]
    rows = []
    for cid in ctx.order:
        co, fin = ctx.cos[cid], ctx.fin[cid]
        a = fin["annual"]
        if a.get("reported", "") >= year:
            def last(role):
                r = role_row(fin, role)
                return (r["cells"][-1][0], r["cells"][-1][1]) if r else (None, "not_found")
            rows.append({"date": a["reported"], "cid": cid, "period": a["columns"][-1] + " full year",
                         "rev": last("revenue"), "growth": last("growth")[0], "organic": last("organic")[0],
                         "margin": last("margin")[0], "src": last("revenue")[1]})
        seen = set()
        for p in fin["interim"]["periods"]:
            if not p.get("reported") or p["reported"] < year or p["reported"] in seen:
                continue
            seen.add(p["reported"])
            rows.append({"date": p["reported"], "cid": cid, "period": p["label"],
                         "rev": (p["v"]["revenue"], period_src(p, "revenue")), "growth": p["v"].get("growth"),
                         "organic": p["v"].get("organic"), "margin": p["v"].get("margin"), "src": p["src"]})
    rows.sort(key=lambda r: (r["date"], r["cid"]), reverse=True)
    out = []
    for r in rows:
        co = ctx.cos[r["cid"]]

        def pc(v, f):
            return f'<td class="num">{f(v)}</td>' if v is not None else '<td class="num na">–</td>'

        src = r["src"] if r["src"] in ctx.src else None
        evid = f'{ctx.ev(ctx.label(src))}<small>{ctx.ext(src)}</small>' if src else ctx.ev("computed")
        mark = '<sup class="mk">c</sup>' if r["rev"][1] == "computed" else ""
        out.append(f'<tr data-company="{r["cid"]}"><td><time datetime="{r["date"]}">{fdate(r["date"])}</time></td>'
                   f'<th scope="row">{ctx.fin_link(r["cid"])}</th><td>{esc(r["period"])}</td>'
                   f'<td class="num">{big(co, r["rev"][0])}{mark}</td>{pc(r["growth"], f_change)}'
                   f'{pc(r["organic"], f_change)}{pc(r["margin"], f_pct)}<td>{evid}</td></tr>')
    return ('<div class="table-wrap"><table class="t" data-filterable><thead><tr><th scope="col">Reported</th>'
            '<th scope="col">Company</th><th scope="col">Period</th><th scope="col" class="num">Revenue</th>'
            '<th scope="col" class="num">Reported growth</th><th scope="col" class="num">Organic growth</th>'
            '<th scope="col" class="num">Headline margin</th><th scope="col">Evidence and source</th></tr></thead>'
            f'<tbody>{"".join(out)}</tbody></table></div>'
            '<p class="legend">A dash means the release gave revenue only, or the figure was not captured. '
            'Intertek growth is like-for-like where the organic column is filled. Margins use each company\'s '
            'headline measure. Full detail is on the company financials screen.</p>')


def calls_block(ctx):
    cards = []
    for c in sorted(ctx.news["calls"], key=lambda c: c["date"], reverse=True):
        pts = "".join(f"<li>{esc(p)}</li>" for p in c["points"])
        links = "; ".join(ctx.ext(s, f'{ctx.src[s]["title"]} ({ctx.src[s]["publisher"]})') for s in c["links"])
        when = fdate(c["date"]) + (f', {esc(c["time"])}' if c.get("time") else "")
        cards.append(f'<article class="call" data-company="{c["company"]}"><p class="call-co">{ctx.fin_link(c["company"])}</p>'
                     f'<h3>{esc(c["event"])}</h3><p class="call-when"><time datetime="{c["date"]}">{when}</time></p>'
                     f'<ul>{pts}</ul><p class="ni-src">{ctx.ev(ctx.label(c["sources"][0]))}'
                     f'<span>Read or listen: {links}</span></p></article>')
    rows = "".join(f'<tr data-company="{c["company"]}"><td><time datetime="{c["date"]}">{fdate(c["date"])}</time></td>'
                   f'<th scope="row">{ctx.fin_link(c["company"])}</th><td>{esc(c["event"])}</td>'
                   f'<td>{ctx.ext(c["link"])}</td></tr>' for c in ctx.news["earlier_calls"])
    return (f'<div class="calls" data-filterable>{"".join(cards)}</div>'
            '<h3 class="h-sub">More call transcripts and summaries from this year</h3>'
            '<div class="table-wrap"><table class="t" data-filterable><thead><tr><th scope="col">Date</th>'
            '<th scope="col">Company</th><th scope="col">Event</th><th scope="col">Third-party record</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def calendar_items(ctx, kind):
    """Timing windows first, then confirmed dates in order, for one kind of entry."""
    return ([w for w in ctx.news["calendar_windows"] if w["kind"] == kind]
            + sorted((c for c in ctx.news["calendar"] if c["kind"] == kind), key=lambda c: c["date"]))


def _when(c):
    return f'<time datetime="{c["date"]}">{fdate(c["date"])}</time>' if c.get("date") else esc(c["window"])


def calendar_earnings(ctx):
    rows = [f'<tr data-company="{c["company"]}"><td>{_when(c)}</td><th scope="row">{ctx.fin_link(c["company"])}</th>'
            f'<td>{esc(c["event"])}</td><td>{ctx.ext(c["src"])}</td></tr>' for c in calendar_items(ctx, "earnings")]
    return ('<div class="table-wrap"><table class="t" data-filterable><thead><tr><th scope="col">Date</th>'
            '<th scope="col">Company</th><th scope="col">Event</th><th scope="col">Source</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div><p class="legend">{esc(ctx.news["calendar_note"])}</p>')


def calendar_other(ctx):
    items = [f'<li data-company="{c["company"]}"><span class="when">{_when(c)}</span>'
             f'<span>{ctx.fin_link(c["company"])}: {esc(c["event"])}<small>Source: {ctx.ext(c["src"])}</small></span></li>'
             for c in calendar_items(ctx, "other")]
    return f'<ul class="dates" data-filterable>{"".join(items)}</ul>'


def feed(ctx, earnings):
    """The month-by-month feed for one of the two news screens."""
    months, order = {}, []
    for it in news_items(ctx, earnings):
        key = it["date"][:7]
        if key not in months:
            months[key] = []
            order.append(key)
        srcs = ", ".join(ctx.ext(s) for s in it["sources"])
        kind = "" if earnings else f'<span class="tag">{esc(ctx.news["types"][it["type"]])}</span>'
        months[key].append(
            f'<article class="news-item" id="n-{it["id"]}" data-company="{it["company"]}" data-type="{it["type"]}">'
            f'<div class="ni-meta"><time datetime="{it["date"]}">{fdate(it["date"])}</time>'
            f'<span class="tag tag-co">{esc(ctx.co_name(it["company"]))}</span>{kind}</div>'
            f'<div class="ni-body"><h3>{esc(it["headline"])}</h3><p>{esc(it["summary"])}</p>'
            f'<p class="ni-src">{ctx.ev(ctx.label(it["sources"][0]))}<span>Sources: {srcs}</span></p></div></article>')
    out = [f'<section class="month" data-month><h3 class="month-h">{fdate(k, long=True)}</h3>{"".join(months[k])}</section>'
           for k in order]
    empty = ("No earnings news for this company in the period covered." if earnings
             else "No news items match these filters. Choose All companies or All types to see more.")
    return f'<div class="feed" data-feed>{"".join(out)}</div><p class="empty" data-empty hidden>{empty}</p>'


# ---------- company financials ----------

def jumpbar(ctx):
    links = "".join(f'<a href="{ctx.href("financials", "fin-" + cid)}" data-jump="fin-{cid}">'
                    f'<span class="tick">{ctx.sec_no(cid)}</span> {esc(ctx.cos[cid]["short"])} '
                    f'<span class="tick">{esc(ctx.cos[cid]["ticker"])}</span></a>' for cid in ctx.order)
    return f'<nav class="jump" aria-label="Jump to a company">{links}</nav>'


def tile(ctx, refs, label, value, sub, src):
    foot = ctx.ev("computed") if src == "computed" else f'{ctx.ev(ctx.label(src))} {refs.mark(src)}'
    return (f'<div class="tile"><p class="tile-k">{esc(label)}</p><p class="tile-v">{value}</p>'
            f'<p class="tile-s">{esc(sub)}</p><p class="tile-f">{foot}</p></div>')


def tiles(ctx, cid, refs):
    co, fin = ctx.cos[cid], ctx.fin[cid]
    col = fin["annual"]["columns"][-1]
    rev, gr = role_row(fin, "revenue"), role_row(fin, "growth")
    mar, pr = role_row(fin, "margin"), role_row(fin, "profit")
    row, orow = latest(ctx, cid)
    g = gr["cells"][-1][0] if gr else None
    out = [tile(ctx, refs, f'{rev["label"]}, {col}', big(co, rev["cells"][-1][0]),
                f'{f_change(g)} {gr.get("tile_sub", "on the year before")}' if g is not None else "",
                rev["cells"][-1][1]),
           tile(ctx, refs, f'{co["margin_measure"]}, {col}', f_pct(mar["cells"][-1][0]),
                f'{co["profit_measure"]} {big(co, pr["cells"][-1][0])}', mar["cells"][-1][1])]
    rg = row["v"].get("growth")
    rev_label = next(m["label"] for m in fin["interim"]["metrics"] if m["key"] == "revenue")
    out.append(tile(ctx, refs, f'{rev_label}, {row["label"]}', big(co, row["v"]["revenue"]),
                    f"{f_change(rg)} as reported" if rg is not None else "", period_src(row, "revenue")))
    ov = orow["v"].get("organic")
    if ov is not None:
        out.append(tile(ctx, refs, f'{co["organic_label"]}, {orow["label"]}', f_change(ov),
                        f'Full-year outlook {WORD[fin["latest"]["status"]].lower()}', period_src(orow, "organic")))
    return f'<div class="tiles">{"".join(out)}</div>'


def company_charts(ctx, cid):
    co, fin = ctx.cos[cid], ctx.fin[cid]
    figs = []
    if fin.get("auto_charts", True):
        cols = fin["annual"]["columns"]
        rev, mar = role_row(fin, "revenue"), role_row(fin, "margin")
        pts = [{"label": c, "value": x[0], "title": f"{c}: {big(co, x[0])}" if x[0] is not None else f"{c}: not found"}
               for c, x in zip(cols, rev["cells"])]
        figs.append(figure(f'{rev["label"]} by fiscal year, {co["unit"]}', None,
                           charts.columns(pts, lambda v: f_money(v, co["dp"]),
                                          f'{co["short"]} {rev["label"].lower()} by fiscal year'), cls="fig", level=4))
        pts = [{"label": c, "value": x[0], "title": f"{c}: {f_pct(x[0])}" if x[0] is not None else f"{c}: not found"}
               for c, x in zip(cols, mar["cells"])]
        figs.append(figure(f'{co["margin_measure"]} by fiscal year', None,
                           charts.line(pts, f_pct, f'{co["short"]} {co["margin_measure"].lower()} by fiscal year'),
                           "The scale is fitted to the data to show change. Read levels from the printed values.",
                           cls="fig", level=4))
    for ch in fin.get("charts", []):
        money = ch["kind"] == "money"
        f = (lambda v: f_money(v, co["dp"])) if money else f_pct
        pts = [{"label": p[0], "value": p[1], "title": f"{p[0]}: {f(p[1])}"} for p in ch["points"]]
        comp = [f"{p[0]} is computed: {p[3]}." for p in ch["points"] if p[2] == "computed" and len(p) > 3]
        note = " ".join([ch.get("note", "")] + comp).strip()
        title = ch["title"] + (f', {co["unit"]}' if money else "")
        svg = (charts.columns if money else charts.line)(pts, f, f'{co["short"]}: {ch["title"]}')
        figs.append(figure(title, None, svg, note or None, cls="fig", level=4))
    return f'<div class="figs">{"".join(figs)}</div>'


def annual_table(ctx, cid, refs):
    """Full fiscal years, then one Latest column with the newest year-to-date figure for each row."""
    co, fin = ctx.cos[cid], ctx.fin[cid]
    a = fin["annual"]
    cols = a["columns"]
    head = "".join(f'<th class="num" scope="col">{esc(c)}</th>' for c in cols)
    show_latest = bool(fin["latest"].get("ytd_order"))  # empty between a full-year release and the next interim one
    if show_latest:
        head += '<th class="num lat" scope="col">Latest<small>year to date</small></th>'
    body, notes = [], []
    for row in a["rows"]:
        tds, sids = [], []
        for col, c in zip(cols, row["cells"]):
            v, src, note = c[0], c[1], (c[2] if len(c) > 2 else None)
            tds.append(cell(ctx, co, v, src, row["kind"], note))
            if v is not None and src != "computed":
                sids.append(src)
            if v is not None and note:
                notes.append(("c" if src == "computed" else "†", row["label"], col, note))
        ytd = ytd_figure(fin, row["key"]) if show_latest else None
        if ytd:
            v, src, formula, period = ytd
            tds.append(cell(ctx, co, v, src, row["kind"], formula, cls="num lat", under=period))
            if src != "computed":
                sids.append(src)
            if formula:
                notes.append(("c", row["label"], period, formula))
        elif show_latest:
            tds.append('<td class="num lat na" title="No year-to-date figure reported for this row, or not captured">–</td>')
        key = " key" if row.get("role") in ("revenue", "profit") else ""
        body.append(f'<tr class="r{key}"><th scope="row">{esc(row["label"])}</th>{"".join(tds)}'
                    f'<td class="refs">{refs.marks(sids)}</td></tr>')
    colnotes = ""
    if a.get("column_notes"):
        colnotes = '<p class="legend">' + " ".join(f"<strong>{esc(k)}:</strong> {esc(v)}."
                                                   for k, v in a["column_notes"].items()) + "</p>"
    cellnotes = ""
    if notes:
        cellnotes = '<ul class="cell-notes">' + "".join(
            f'<li><span class="mk">{m}</span> <strong>{esc(r)}, {esc(c)}:</strong> {esc(n)}</li>' for m, r, c, n in notes) + "</ul>"
    latest_note = ('<p class="legend"><strong>Latest:</strong> the newest year-to-date figure reported in '
                   f'{ctx.as_of[:4]}, with its period under the value. It covers part of a year, so do not read it '
                   'against the full-year columns. Balance-sheet rows are at the period end.</p>') if show_latest else ""
    return (f'<div class="table-wrap"><table class="t fin"><thead><tr><th scope="col">{esc(co["unit"])}</th>{head}'
            f'<th scope="col" class="refs">Sources</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>'
            f'{latest_note}{colnotes}{cellnotes}{LEGEND}')


def interim_table(ctx, cid, refs):
    co, it = ctx.cos[cid], ctx.fin[cid]["interim"]
    metrics = it["metrics"]
    head = "".join(f'<th class="num" scope="col">{esc(m["label"])}</th>' for m in metrics)
    body = []
    for per in it["periods"]:
        tds, extra = [], []
        for m in metrics:
            if m["key"] in per["v"]:
                note = (per.get("computed") or {}).get(m["key"])
                tds.append(cell(ctx, co, per["v"][m["key"]], period_src(per, m["key"]), m["kind"], note))
                if note:
                    extra.append(f'{m["label"]} is computed: {note}.')
            else:
                tds.append('<td class="num na" title="Not reported for the period, or not captured">–</td>')
        sids = [per["src"]] + list((per.get("srcs") or {}).values())
        rep = f'Reported {fdate(per["reported"])}' if per.get("reported") else "Derived here"
        derived = all(k in (per.get("computed") or {}) for k in per["v"])
        evid = ctx.ev("computed" if derived else ctx.label(per["src"]))
        body.append(f'<tr class="r"><th scope="row">{esc(per["label"])}<small>{rep}</small></th>{"".join(tds)}'
                    f'<td class="refs">{evid} {refs.marks(sids)}</td></tr>')
        text = " ".join([per.get("note", "")] + extra).strip()
        if text:
            body.append(f'<tr class="subrow"><td colspan="{len(metrics) + 2}">{esc(text)}</td></tr>')
    return (f'<div class="table-wrap"><table class="t fin"><thead><tr><th scope="col">{esc(co["unit"])}</th>{head}'
            f'<th scope="col" class="refs">Evidence</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def segment_tables(ctx, cid, refs):
    co, fin = ctx.cos[cid], ctx.fin[cid]
    out = []
    for seg in fin.get("segments", []):
        share_key, total = seg.get("share_of"), seg.get("total")
        head = '<th scope="col">Segment</th>'
        for c in seg["columns"]:
            head += f'<th class="num" scope="col">{esc(c["label"])}</th>'
            if c["key"] == share_key:
                head += '<th scope="col">Share of total</th>'
        body = []
        for r in seg["rows"]:
            tds = f'<th scope="row">{esc(r["name"])}</th>'
            for c in seg["columns"]:
                v = r.get(c["key"])
                if v is None:
                    txt = (r.get("text") or {}).get(c["key"])
                    tds += (f'<td class="num">{esc(txt)}</td>' if txt
                            else '<td class="num na" title="Not found in the sources used">n/f</td>')
                else:
                    tds += f'<td class="num">{fmt(v, c["kind"], co["dp"])}</td>'
                if c["key"] == share_key:
                    tds += f"<td>{charts.share_bar(100 * v / total)}</td>" if v is not None else "<td></td>"
            body.append(f"<tr>{tds}</tr>")
        sids = [seg["src"]] + seg.get("srcs", [])
        note = f'<p class="legend">{esc(seg["note"])}</p>' if seg.get("note") else ""
        out.append(f'<div class="seg"><h4>{esc(seg["title"])} <span class="h-meta">{ctx.ev(ctx.label(seg["src"]))} '
                   f'{refs.marks(sids)}</span></h4><div class="table-wrap"><table class="t fin"><thead><tr>{head}</tr></thead>'
                   f'<tbody>{"".join(body)}</tbody></table></div>{note}</div>')
    if fin.get("segments_note"):
        out.append(f'<p class="legend">{esc(fin["segments_note"])}</p>')
    return "".join(out)


def outlook_block(ctx, cid, refs):
    o = ctx.fin[cid]["outlook"]
    items = []
    for it in o["items"]:
        sid = it.get("src", o["src"])
        second = ctx.ev("secondary_report") if ctx.label(sid) == "secondary_report" else ""
        pill = status_pill(it["change"]) if it.get("change") else '<span class="st st-none">Stated</span>'
        was = f'<span class="was">Before: {esc(it["was"])}</span>' if it.get("was") else ""
        items.append(f'<li>{pill}<div><span>{esc(it["text"])} {refs.mark(sid)} {second}</span>{was}</div></li>')
    html = (f'<div class="ol-col"><h4>{esc(o["title"])} <span class="h-meta">as of {fdate(o["as_of"])} '
            f'{ctx.ev("company_claim")}</span></h4><ul class="ol">{"".join(items)}</ul></div>')
    t = o.get("targets")
    if t:
        lis = "".join(f"<li>{esc(x)}</li>" for x in t["items"])
        second = ctx.ev("secondary_report") if ctx.label(t["src"]) == "secondary_report" else ctx.ev("company_claim")
        html += (f'<div class="ol-col"><h4>{esc(t["title"])} <span class="h-meta">{second} {refs.mark(t["src"])}</span></h4>'
                 f'<ul class="tg">{lis}</ul></div>')
    return f'<div class="ol-grid">{html}</div>'


def _moved(pct):
    return "unchanged" if pct == 0 else f'{"up" if pct > 0 else "down"} {abs(pct):.1f}%'


def share_price(series):
    """A share's last month-end close with its currency mark: CHF 103.60, 5,930p."""
    return f'{series["price_prefix"]}{series["last_close"]:,.{series["price_dp"]}f}{series["price_suffix"]}'


def share_line(ctx, cid, refs):
    """Last month-end share price and the total return so far that year, from data/prices.json."""
    series, ix = ctx.px["series"][cid], ctx.ix
    last = ix["months"][-1]
    year = last[:4]
    ret, full = stockindex.share_year_return(ix, cid, f"{int(year) - 1}-12", last)
    span = f"in {year} to that date" if full else f'since {ln_month(ix["first"][cid])}, when the price series starts'
    return (f'{esc(share_price(series))} at the close on {fdate(ctx.px["last_date"])}. Total return {span}: '
            f'{f_change(ret * 100)}, dividends included. {ctx.ev(ctx.label(series["src"]))} '
            f'{refs.mark(series["src"])}')


def latest_summary(ctx, cid, refs):
    """What the company last reported, its outlook, its share price, the main points and the newest news.

    Every part is drawn from data already on the dashboard, so the block cannot disagree with the tables.
    """
    co, fin = ctx.cos[cid], ctx.fin[cid]
    row, orow = latest(ctx, cid)
    v, used = row["v"], [(row, "revenue")]
    rev_label = next(m["label"] for m in fin["interim"]["metrics"] if m["key"] == "revenue")
    lead = f'{esc(rev_label)} {big(co, v["revenue"])}'
    if v.get("growth") is not None:
        lead += f', {_moved(v["growth"])} as reported'
        used.append((row, "growth"))
    lead += "."
    if orow["v"].get("organic") is not None:
        where = "" if orow is row else f' in {esc(orow["label"])}'
        lead += f' {esc(co["organic_label"])} was {f_pct(orow["v"]["organic"])}{where}.'
        used.append((orow, "organic"))
    if "profit" in v and "margin" in v:
        lead += f' {esc(co["profit_measure"])} {big(co, v["profit"])}, a margin of {f_pct(v["margin"])}.'
        used += [(row, "profit"), (row, "margin")]
    else:
        lead += " The update gave no profit figure."
    srcs = []
    for per, key in used:
        sid = period_src(per, key)
        if sid not in srcs:
            srcs.append(sid)
    labels = []
    for sid in srcs:
        if ctx.label(sid) not in labels:
            labels.append(ctx.label(sid))
    when = f', reported {fdate(row["reported"])}' if row.get("reported") else ""
    head = (f'<h3 id="ls-{cid}">Latest summary <span class="h-meta">{esc(row["label"])}{when} '
            f'{" ".join(ctx.ev(x) for x in labels)} {refs.marks(x for x in srcs if x != "computed")}</span></h3>')
    lat, o = fin["latest"], fin["outlook"]
    osrcs = [o["src"]] + [it["src"] for it in o["items"] if it.get("src")]
    olabel = ctx.ev("company_claim")  # an outlook is the company's own claim, whoever reports it
    if any(ctx.label(sid) == "secondary_report" for sid in osrcs):
        olabel += " " + ctx.ev("secondary_report")
    facts = (f'<dl class="ls-facts"><div><dt>Full-year outlook</dt><dd>{status_pill(lat["status"])} '
             f'{esc(lat["status_text"])} {olabel} {refs.marks(osrcs)}</dd></div>'
             f'<div><dt><a href="{ctx.href("stock")}">Month-end share price</a></dt>'
             f'<dd>{share_line(ctx, cid, refs)}</dd></div></dl>')
    news = [it for it in ctx.news["news"] if it["company"] == cid][:3]
    recent = ""
    if news:
        items = "".join(
            f'<li><time datetime="{it["date"]}">{fdate(it["date"])}</time>'
            f'<a href="{ctx.href("earnings" if it["type"] in EARNINGS_TYPES else "industry-news", "n-" + it["id"])}">'
            f'{esc(it["headline"])}</a></li>' for it in news)
        recent = f'<h4>Recent news</h4><ul class="ls-news">{items}</ul>'
    calls = [c for c in ctx.news["calls"] if c["company"] == cid]
    points = ""
    if calls:
        call = max(calls, key=lambda c: c["date"])
        pts = "".join(f"<li>{esc(p)}</li>" for p in call["points"])
        points = (f'<div class="ls-side"><h4>Main points: {esc(call["event"])}, {fdate(call["date"])} '
                  f'<span class="h-meta">{ctx.ev(ctx.label(call["sources"][0]))} {refs.marks(call["sources"])}</span></h4>'
                  f'<ul class="ls-points">{pts}</ul></div>')
    return (f'<section class="latest" aria-labelledby="ls-{cid}">{head}'
            f'<div class="ls-grid"><div class="ls-main"><p class="ls-lead">{lead}</p>{facts}{recent}</div>{points}</div>'
            f'</section>')


def company_section(ctx, cid):
    co, fin = ctx.cos[cid], ctx.fin[cid]
    refs = Refs(ctx, f"src-{cid}")
    facts = [("Head office", co["hq"]), ("Chief executive", co["ceo"]),
             ("Chief financial officer", co["cfo"]), ("People", co["people"]), ("Fiscal year end", co["fy_end"]),
             ("Reports in", co["unit"])]
    dl = "".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in facts if v)
    profile_refs = refs.marks(co["profile_sources"])
    summary = latest_summary(ctx, cid, refs)
    status = ""
    if co.get("status"):
        st = co["status"]
        status = (f'<div class="note" role="note"><strong>{esc(st["label"])}.</strong> {esc(st["text"])} '
                  f'{refs.marks(st["sources"])}</div>')
    t = tiles(ctx, cid, refs)
    annual = annual_table(ctx, cid, refs)
    interim = interim_table(ctx, cid, refs)
    segs = segment_tables(ctx, cid, refs)
    outlook = outlook_block(ctx, cid, refs)
    notes = "".join(f"<li>{esc(n)}</li>" for n in fin.get("notes", []))
    annual_h = "Annual figures and the latest year to date" if fin["latest"].get("ytd_order") else "Annual figures"
    return (
        f'<section class="card co" id="fin-{cid}" aria-labelledby="h-{cid}">'
        f'<header class="co-head"><div><h2 id="h-{cid}"><span class="sec-no">{ctx.sec_no(cid)}</span> {esc(co["name"])}</h2>'
        f'<p class="co-desc">{esc(co["description"])} {profile_refs}</p></div>'
        f'<p class="co-links"><span class="pill">{esc(co["listing"])}</span>'
        f'<a class="btn" href="{esc(co["ir_url"], quote=True)}" target="_blank" rel="noopener noreferrer">Investor relations site</a></p>'
        f'</header>{summary}{status}<dl class="facts">{dl}</dl>{t}{company_charts(ctx, cid)}'
        f'<h3>{annual_h}</h3>{annual}'
        f'<h3>Interim results reported in {ctx.as_of[:4]}</h3>{interim}'
        f'<h3>Segments</h3>{segs}'
        f'<h3>Outlook and targets</h3>{outlook}'
        f'<h3>Reading notes</h3><ul class="notes">{notes}</ul>'
        f'<h3>Sources for this company</h3>{refs.render()}'
        f'<p class="top"><a href="{ctx.href("financials")}">Back to the company list</a></p></section>')


def companies(ctx):
    return "".join(company_section(ctx, cid) for cid in ctx.order)


# ---------- TIC stock price ----------

EV_COMPUTED = '<span class="ev ev-computed">computed</span>'
INDEX_NAMES = {"cap": "Market-cap weighted", "eq": "Equal weighted"}


def f_level(v):
    return f"{v:,.1f}"


def stock_tiles(ctx):
    """Level of each index at the last month end, then each index's return so far that year."""
    ix = ctx.ix
    months, last = ix["months"], ix["months"][-1]
    year_start = f"{int(last[:4]) - 1}-12"
    on = fdate(ctx.px["last_date"])

    def stat(label, value, sub):
        return (f'<div class="tile"><p class="tile-k">{esc(label)}</p><p class="tile-v">{value}</p>'
                f'<p class="tile-s">{esc(sub)}</p><p class="tile-f">{EV_COMPUTED}</p></div>')

    out = [stat(f"{INDEX_NAMES[k]} index", f_level(ix[k][-1]),
                f'At {on}. {f_change((ix[k][-1] / ix[k][0] - 1) * 100)} since the end of {ln_month(months[0])}')
           for k in ("cap", "eq")]
    out += [stat(f"{INDEX_NAMES[k]}, {last[:4]} so far",
                 f_change(stockindex.change(ix[k], months, year_start, last) * 100),
                 f'To {on}. {ln_month(last)} alone: {f_change(ix[k + "_ret"][-1] * 100)}')
            for k in ("cap", "eq")]
    return f'<div class="tiles">{"".join(out)}</div>'


def stock_chart(ctx):
    ix = ctx.ix
    months = ix["months"]
    notes = [(ix["first"][cid], f'{ctx.cos[cid]["short"]} joins') for cid in ctx.order if ix["first"][cid] != months[0]]
    lines = [{"name": INDEX_NAMES["cap"], "values": ix["cap"], "dashed": False},
             {"name": INDEX_NAMES["eq"], "values": ix["eq"], "dashed": True}]
    svg = charts.timeseries(months, lines, "Market-cap-weighted and equal-weighted indexes of the "
                            f"{len(ctx.order)} TIC shares at each month end, {ln_month(months[0])} to "
                            f"{ln_month(months[-1])}", notes=sorted(notes), base=stockindex.BASE_LEVEL)
    return figure(f"Both indexes at each month end, end of {ln_month(months[0])} = 100",
                  "Total return with dividends reinvested, each share in its own currency. Solid line: weighted by "
                  "market cap. Dashed line: every share weighted equally.", svg,
                  "The scale is fitted to the data to show change. The latest level is printed at the end of each "
                  "line; point at a month to read it. Every month-end level is in the table lower down this screen.",
                  cls="card chart chart-wide")


def stock_returns(ctx, refs):
    """Calendar-year total returns: the two indexes, then each share in its own currency."""
    ix = ctx.ix
    months = ix["months"]
    spans = stockindex.year_spans(months)
    on = fdate(ctx.px["last_date"])
    head = "".join(f'<th class="num" scope="col">{y}{"" if done else f"<small>to {on[:-5]}</small>"}</th>'
                   for y, _, _, done in spans)
    rows = []
    for key in ("cap", "eq"):
        tds = "".join(f'<td class="num">{f_change(stockindex.change(ix[key], months, a, b) * 100)}</td>'
                      for _, a, b, _ in spans)
        rows.append(f'<tr class="r key"><th scope="row">{INDEX_NAMES[key]} index<small>All shares in the index, '
                    f'each in its own currency</small></th>{tds}'
                    f'<td class="num">{f_change((ix[key][-1] / ix[key][0] - 1) * 100)}</td><td>{EV_COMPUTED}</td></tr>')
    part = False
    for cid in ctx.order:
        series = ctx.px["series"][cid]
        tds = ""
        for _, a, b, _ in spans:
            r, full = stockindex.share_year_return(ix, cid, a, b)
            if r is None:
                tds += '<td class="num na" title="Not in the indexes in this year">n/a</td>'
            else:
                part = part or not full
                tds += f'<td class="num">{f_change(r * 100)}{"" if full else DAGGER}</td>'
        whole = ix["first"][cid] == months[0]
        part = part or not whole
        srcs = [series["src"]] + ([series["ret_src"]] if series.get("ret_src") else [])
        rows.append(f'<tr><th scope="row">{ctx.fin_link(cid)}<small>{esc(series["symbol"])} on '
                    f'{esc(series["market"])}, in {esc(series["currency"])}</small></th>{tds}'
                    f'<td class="num">{f_change((ix["growth"][cid][-1] - 1) * 100)}{"" if whole else DAGGER}</td>'
                    f'<td class="refs">{ctx.ev(ctx.label(series["src"]))} {refs.marks(srcs)}</td></tr>')
    note = (f'<p class="legend">{DAGGER} From the month end the share joined the indexes, so not a full period. '
            'n/a: not in the indexes that year.</p>') if part else ""
    return ('<div class="table-wrap"><table class="t fin"><thead><tr><th scope="col">Index or share</th>'
            f'{head}<th class="num" scope="col">All years<small>since {ln_month(months[0])}</small></th>'
            f'<th scope="col" class="refs">Evidence</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>{note}'
            '<p class="legend">Returns include dividends. Each share is in its own currency, so the share rows are '
            'not like-for-like with each other.</p>')


def stock_weights(ctx, refs):
    """Each share's weight going into the next month, with the market cap behind it."""
    ix = ctx.ix
    months = ix["months"]
    last = months[-1]
    equal = 100 / len(ix["last_weights"])
    rows, drifted = [], False
    for cid in ctx.order:
        co, series, mcap = ctx.cos[cid], ctx.px["series"][cid], ctx.px["market_caps"][cid]
        known = dict(mcap["values"])
        at = max((m for m in known if m <= last), default=min(known))
        how = f"Published value of {known[at]:,.2f} at the end of {ln_month(at)}"
        mark = ""
        if at != last:
            how += ", moved by the share's return since then"
            mark, drifted = '<sup class="mk">c</sup>', True
        joined = "From the start" if ix["first"][cid] == months[0] else ln_month(ix["first"][cid])
        rows.append(
            f'<tr><th scope="row">{ctx.fin_link(cid)}<small>{esc(co["listing"])}</small></th>'
            f'<td>{joined}</td><td class="num">{esc(share_price(series))}</td>'
            f'<td class="num" title="{esc(how, quote=True)}">{ix["mcap"][cid][-1]:,.1f}{mark}</td>'
            f'<td>{charts.share_bar(ix["last_weights"][cid] * 100, dp=1)}</td><td class="num">{equal:.1f}%</td>'
            f'<td class="refs">{ctx.ev(ctx.label(mcap["src"]))} {refs.mark(mcap["src"])}</td></tr>')
    rows.append(f'<tr class="r key"><th scope="row">All {len(ix["last_weights"])} shares</th><td></td><td></td>'
                f'<td class="num">{ix["last_total"]:,.1f}</td><td>{charts.share_bar(100, dp=1)}</td>'
                f'<td class="num">100.0%</td><td></td></tr>')
    notes = "".join(f'<li><strong>{esc(ctx.cos[cid]["short"])}:</strong> {esc(ctx.px["market_caps"][cid]["note"])}</li>'
                    for cid in ctx.order if ctx.px["market_caps"][cid].get("note"))
    notes = f'<ul class="cell-notes">{notes}</ul>' if notes else ""
    legend = ('<sup class="mk">c</sup> computed here: the latest published year-end value, moved by the share\'s '
              'return since then. ') if drifted else ""
    return ('<div class="table-wrap"><table class="t fin"><thead><tr><th scope="col">Share</th>'
            '<th scope="col">In the indexes</th>'
            f'<th class="num" scope="col">Share price, {fdate(ctx.px["last_date"])}</th>'
            '<th class="num" scope="col">Market cap used, USD bn</th><th scope="col">Market-cap weight</th>'
            '<th class="num" scope="col">Equal weight</th><th scope="col" class="refs">Market cap from</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>{notes}'
            f'<p class="legend">{legend}Share prices are in each share\'s own currency. US dollar market caps '
            'are used only to set the weights.</p>')


def stock_levels(ctx):
    """Every month-end level of both indexes: the numbers behind the chart."""
    ix = ctx.ix
    months = ix["months"]
    head = "".join(f'<th class="num" scope="col">{m}</th>' for m in charts.MONTH_NAMES)
    out = []
    for key in ("cap", "eq"):
        level = dict(zip(months, ix[key]))
        rows = []
        for year, start, end, done in stockindex.year_spans(months):
            tds = "".join(f'<td class="num">{f_level(level[f"{year}-{m:02d}"])}</td>' if f"{year}-{m:02d}" in level
                          else '<td class="num na"></td>' for m in range(1, 13))
            rows.append(f'<tr><th scope="row">{year}</th>{tds}'
                        f'<td class="num lat">{f_change(stockindex.change(ix[key], months, start, end) * 100)}</td></tr>')
        out.append(f'<h3 class="h-sub">{INDEX_NAMES[key]} index</h3><div class="table-wrap"><table class="t fin lv">'
                   f'<thead><tr><th scope="col">Year</th>{head}<th class="num lat" scope="col">Year\'s return</th></tr>'
                   f'</thead><tbody>{"".join(rows)}</tbody></table></div>')
    last = months[-1]
    return "".join(out) + (f'<p class="legend">Both indexes are {f_level(stockindex.BASE_LEVEL)} at the end of '
                           f'{ln_month(months[0])}. The return for {last[:4]} runs to the end of {ln_month(last)}. '
                           f'All levels are computed here by <code>tools/stockindex.py</code>.</p>')


def stock_blocks(ctx):
    """Every slot on the TIC stock price screen. The tables share one numbered source list."""
    refs = Refs(ctx, "src-stock")
    out = {
        "stock_last": fdate(ctx.px["last_date"]),
        "stock_read_on": fdate(ctx.px["read_on"], long=True),
        "stock_base": fdate(ctx.ix["months"][0], long=True),
        "stock_tiles": stock_tiles(ctx),
        "stock_chart": stock_chart(ctx),
        "stock_returns": stock_returns(ctx, refs),
        "stock_weights": stock_weights(ctx, refs),
        "stock_levels": stock_levels(ctx),
        "stock_method": bullet(ctx, "method", ctx.px),
        "stock_limits": bullet(ctx, "limits", ctx.px),
    }
    out["stock_sources"] = refs.render()
    return out


# ---------- sources and method ----------

def labels_table(ctx):
    t = tally(ctx.d)
    rows = "".join(f'<tr><th scope="row">{ctx.ev(k)}</th><td>{esc(ctx.meta["evidence_labels"][k])}</td>'
                   f'<td class="num">{t["by_label"][k]:,}</td></tr>' for k in LABELS)
    return ('<div class="table-wrap"><table class="t"><thead><tr><th scope="col">Label</th><th scope="col">Meaning</th>'
            f'<th scope="col" class="num">Figures</th></tr></thead><tbody>{rows}</tbody></table></div>')


def review_block(ctx):
    r = review(ctx.d)
    who = (f'<p class="review-by">Signed off by {esc(names(r["who"]))} {review_dates(r)}: {r["sources_done"]} of '
           f'{r["sources_total"]} sources in the register below.</p>') if r["who"] else ""
    return (f'<p class="review"><span class="review-n">{r["checked"]:,} of {r["sourced"]:,}</span> sourced figures have been '
            f'checked against their source by a person.</p>{who}<p class="sub">{esc(ctx.meta["review"]["how"])}</p>'
            f'<p class="sub">Share prices are counted by source, not by figure: {r["px_done"]} of {r["px_total"]} price and '
            f'market-cap sources behind <a href="{ctx.href("stock")}">TIC stock price</a> have been checked.</p>')


def bullet(ctx, key, where=None):
    items = (where or ctx.meta)[key]
    return '<ul class="notes">' + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"


def register(ctx):
    use = source_use(ctx.d)
    rows = []
    for sid, s in ctx.src.items():
        checked = (f'{esc(s["reviewed_by"])}, {fdate(s.get("reviewed_on"))}' if s.get("reviewed_by")
                   else '<span class="muted">No</span>')
        rows.append(f'<tr><td>{ctx.ext(sid, s["title"])}<small><code>{sid}</code></small></td><td>{esc(s["publisher"])}</td>'
                    f'<td>{fdate(s["date"])}</td><td>{ctx.ev(ctx.label(sid))}</td><td class="num">{use[sid]}</td>'
                    f'<td>{checked}</td></tr>')
    return ('<div class="table-wrap"><table class="t"><thead><tr><th scope="col">Source</th><th scope="col">Publisher</th>'
            '<th scope="col">Date</th><th scope="col">Evidence label</th><th scope="col" class="num">Times cited</th>'
            f'<th scope="col">Checked by a person</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


# ---------- slots ----------

def slots(ctx):
    t = tally(ctx.d)
    return {
        "banner": banner(ctx),
        "as_of": fdate(ctx.as_of),
        "as_of_long": fdate(ctx.as_of, long=True),
        "href_overview": ctx.href("overview"),
        "href_industry_news": ctx.href("industry-news"),
        "href_earnings": ctx.href("earnings"),
        "href_financials": ctx.href("financials"),
        "href_sources": ctx.href("sources"),
        "href_stock": ctx.href("stock"),
        "sec_first": ctx.sec_no(ctx.order[0]),
        "sec_last": ctx.sec_no(ctx.order[-1]),
        "n_companies": str(len(ctx.order)),
        "n_industry_news": str(len(news_items(ctx, False))),
        "n_earnings_news": str(len(news_items(ctx, True))),
        "n_sources": str(len(ctx.src)),
        "n_figures": f'{sum(t["by_label"][k] for k in LABELS[:4]):,}',
        "outlook_summary": outlook_summary(ctx),
        "scoreboard": scoreboard(ctx),
        "chart_organic": chart_organic(ctx),
        "chart_margins": chart_margins(ctx),
        "fullyear_table": fullyear_table(ctx),
        "next_dates": next_dates(ctx),
        "open_items": open_items(ctx),
        "industry_chips": company_chips(ctx, industry=True),
        "type_chips": type_chips(ctx),
        "industry_feed": feed(ctx, earnings=False),
        "calendar_other": calendar_other(ctx),
        "earnings_chips": company_chips(ctx, industry=False),
        "results_log": results_log(ctx),
        "calls": calls_block(ctx),
        "calendar_earnings": calendar_earnings(ctx),
        "earnings_feed": feed(ctx, earnings=True),
        "jumpbar": jumpbar(ctx),
        "companies": companies(ctx),
        **stock_blocks(ctx),
        "labels_table": labels_table(ctx),
        "review": review_block(ctx),
        "comparability": bullet(ctx, "comparability"),
        "gaps": bullet(ctx, "known_gaps"),
        "register": register(ctx),
    }
