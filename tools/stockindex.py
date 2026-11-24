"""Builds the two share-price indexes on the TIC stock price screen from data/prices.json.

Nothing here is stored: the screen, the chart and the checks all call build(), so the
numbers cannot drift apart.

How the indexes are built
  - A share's monthly return is the change in its month-end adjusted close (dividends
    reinvested), in its own currency. Where a month has no adjusted price for it and for
    the month before, a published monthly return is used instead.
  - A share joins at the first month end the source has for it. Its first return is the
    month after.
  - Equal-weighted: the plain average of the returns of the shares in the index that month.
  - Market-cap-weighted: the average weighted by market cap at the previous month end.
    Market caps come from data/prices.json (USD billion at chosen month ends, mostly year
    ends). Between those points a share's market cap moves with its own return.
  - Both start at 100 at the base month.
"""

BASE_LEVEL = 100.0
RET_TOLERANCE = 0.06  # points allowed between a published monthly return and one computed from prices


def month_range(first, last):
    """Every month from first to last, both 'YYYY-MM' and both included."""
    y, m = (int(x) for x in first.split("-"))
    out = []
    while True:
        key = f"{y}-{m:02d}"
        out.append(key)
        if key == last:
            return out
        if key > last:
            raise ValueError(f"{first} is after {last}")
        m += 1
        if m == 13:
            y, m = y + 1, 1


def next_month(month):
    y, m = (int(x) for x in month.split("-"))
    return f"{y + 1}-01" if m == 12 else f"{y}-{m + 1:02d}"


def share_returns(series, months):
    """Monthly returns for one share, aligned to months. Returns (returns, kinds).

    returns[i] is a fraction or None; kinds[i] is 'price', 'published' or None.
    """
    adj = dict(series.get("adj", []))
    pub = dict(series.get("ret", []))
    rets, kinds = [None], [None]
    for prev, month in zip(months, months[1:]):
        if month in adj and prev in adj:
            rets.append(adj[month] / adj[prev] - 1)
            kinds.append("price")
        elif month in pub:
            rets.append(pub[month] / 100)
            kinds.append("published")
        else:
            rets.append(None)
            kinds.append(None)
    return rets, kinds


def build(prices, order):
    """Compute both indexes. order is the company order from companies.json."""
    months = month_range(prices["base"], prices["last"])
    n = len(months)
    rets, kinds, growth, first = {}, {}, {}, {}
    for cid in order:
        r, k = share_returns(prices["series"][cid], months)
        rets[cid], kinds[cid] = r, k
        have = [i for i in range(1, n) if r[i] is not None]
        if not have:
            raise ValueError(f"{cid}: no monthly return between {months[0]} and {months[-1]}")
        start = have[0] - 1  # the month end the share joins at
        missing = [months[i] for i in range(start + 1, n) if r[i] is None]
        if missing:
            raise ValueError(f"{cid}: no return for {missing[0]}")
        first[cid] = months[start]
        g = [None] * n  # growth of one unit held since joining, dividends reinvested
        g[start] = 1.0
        for i in range(start + 1, n):
            g[i] = g[i - 1] * (1 + r[i])
        growth[cid] = g

    # market cap used for the weights at each month end, USD billion
    mcap = {}
    for cid in order:
        known = {months.index(m): v for m, v in prices["market_caps"][cid]["values"] if m in months}
        known = {i: v for i, v in known.items() if growth[cid][i] is not None}
        if not known:
            raise ValueError(f"{cid}: no market cap inside its time in the index")
        vals = [None] * n
        for i in range(n):
            if growth[cid][i] is None:
                continue
            earlier = [j for j in known if j <= i]
            j = max(earlier) if earlier else min(known)  # before its first known value, work back from it
            vals[i] = known[j] * growth[cid][i] / growth[cid][j]
        mcap[cid] = vals

    cap, eq = [BASE_LEVEL], [BASE_LEVEL]
    cap_ret, eq_ret, members, weights = [None], [None], [[]], [None]
    for i in range(1, n):
        mem = [cid for cid in order if rets[cid][i] is not None]
        if not mem:
            raise ValueError(f"no share has a return for {months[i]}")
        total = sum(mcap[cid][i - 1] for cid in mem)
        w = {cid: mcap[cid][i - 1] / total for cid in mem}
        rc = sum(w[cid] * rets[cid][i] for cid in mem)
        re = sum(rets[cid][i] for cid in mem) / len(mem)
        cap.append(cap[-1] * (1 + rc))
        eq.append(eq[-1] * (1 + re))
        cap_ret.append(rc)
        eq_ret.append(re)
        members.append(mem)
        weights.append(w)

    # weights as they stand at the last month end (they apply to the next month's return)
    last_mem = [cid for cid in order if growth[cid][n - 1] is not None]
    total = sum(mcap[cid][n - 1] for cid in last_mem)
    last_weights = {cid: mcap[cid][n - 1] / total for cid in last_mem}

    return {"months": months, "returns": rets, "kinds": kinds, "growth": growth, "first": first, "mcap": mcap,
            "cap": cap, "eq": eq, "cap_ret": cap_ret, "eq_ret": eq_ret, "members": members, "weights": weights,
            "last_weights": last_weights, "last_total": total}


def change(levels, months, start, end):
    """Return between two month ends as a fraction, or None when either level is missing."""
    if start not in months or end not in months:
        return None
    a, b = levels[months.index(start)], levels[months.index(end)]
    return None if a is None or b is None else b / a - 1


def year_spans(months):
    """[(label, start month, end month, complete)] for each calendar year the index covers."""
    out = []
    for year in sorted({m[:4] for m in months[1:]}):
        in_year = [m for m in months if m[:4] == year]
        start = f"{int(year) - 1}-12"
        if start not in months:
            start = months[0]
        out.append((year, start, in_year[-1], in_year[-1].endswith("-12")))
    return out


def share_year_return(result, cid, start, end):
    """A share's return over a span, and whether it was in the index for the whole span.

    Returns (fraction or None, full). When the share joined part-way through, the return runs
    from its first month end and full is False.
    """
    months, g = result["months"], result["growth"][cid]
    i0, i1 = months.index(start), months.index(end)
    if g[i1] is None:
        return None, False
    if g[i0] is None:
        j = months.index(result["first"][cid])
        return (None, False) if j >= i1 else (g[i1] / g[j] - 1, False)
    return g[i1] / g[i0] - 1, True
