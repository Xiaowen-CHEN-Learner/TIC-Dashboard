"""Inline SVG charts for the dashboard.

Rules (see CLAUDE.md, "Charts"): one blue for every data mark, text in ink
colours, every value printed beside its mark, bars start at zero, and a table
with the same numbers sits on the same screen.
"""
from html import escape

BLUE = "#1D4ED8"
INK = "#101828"
MUTED = "#475467"
RULE = "#D0D5DD"


def _hbar(x, y, w, h, r=4, right=True):
    """Horizontal bar: data end rounded, baseline end square."""
    w = abs(w)
    if w <= 0:
        return ""
    r = min(r, h / 2, w)
    if right:
        return (f"M{x:.1f},{y:.1f}h{w - r:.1f}a{r:.1f},{r:.1f} 0 0 1 {r:.1f},{r:.1f}v{h - 2 * r:.1f}"
                f"a{r:.1f},{r:.1f} 0 0 1 -{r:.1f},{r:.1f}h-{w - r:.1f}z")
    return (f"M{x:.1f},{y:.1f}h-{w - r:.1f}a{r:.1f},{r:.1f} 0 0 0 -{r:.1f},{r:.1f}v{h - 2 * r:.1f}"
            f"a{r:.1f},{r:.1f} 0 0 0 {r:.1f},{r:.1f}h{w - r:.1f}z")


def _col(x, y0, w, h, r=4, up=True):
    """Column from the baseline y0: data end rounded, baseline end square."""
    if h <= 0:
        return ""
    r = min(r, w / 2, h)
    if up:
        return (f"M{x:.1f},{y0:.1f}v-{h - r:.1f}a{r:.1f},{r:.1f} 0 0 1 {r:.1f},-{r:.1f}h{w - 2 * r:.1f}"
                f"a{r:.1f},{r:.1f} 0 0 1 {r:.1f},{r:.1f}v{h - r:.1f}z")
    return (f"M{x:.1f},{y0:.1f}v{h - r:.1f}a{r:.1f},{r:.1f} 0 0 0 {r:.1f},{r:.1f}h{w - 2 * r:.1f}"
            f"a{r:.1f},{r:.1f} 0 0 0 {r:.1f},-{r:.1f}v-{h - r:.1f}z")


def _svg(width, height, label, body):
    return (f'<svg class="chart-svg" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label, quote=True)}">'
            f'{"".join(body)}</svg>')


def hbars(groups, fmt, label, width=520, label_w=176, value_w=66):
    """Ranked horizontal bars.

    groups: [(group title or None, [ {label, sub, value, title} ])]. All groups
    share one scale so bar lengths stay comparable across the figure.
    """
    values = [r["value"] for _, rows in groups for r in rows]
    vmax, vmin = max(values + [0]), min(values + [0])
    span = (vmax - vmin) or 1
    x0, x1 = label_w, width - value_w
    zero = x0 + (0 - vmin) / span * (x1 - x0)
    row_h, bar_h, head_h = 36, 16, 26
    body, y = [], 2
    for title, rows in groups:
        if title:
            body.append(f'<text x="0" y="{y + 16}" class="c-group">{escape(title)}</text>')
            y += head_h
        top = y
        for r in rows:
            w = abs(r["value"]) / span * (x1 - x0)
            by = y + (row_h - bar_h) / 2
            right = r["value"] >= 0
            end = zero + w if right else zero - w
            tx = end + 7 if right else end - 7
            anchor = "" if right else ' text-anchor="end"'
            body.append(f'<g><title>{escape(r["title"])}</title>'
                        f'<text x="0" y="{y + 15}" class="c-label">{escape(r["label"])}</text>'
                        f'<text x="0" y="{y + 29}" class="c-sub">{escape(r["sub"])}</text>'
                        f'<path d="{_hbar(zero, by, w, bar_h, right=right)}" fill="{BLUE}"/>'
                        f'<text x="{tx:.1f}" y="{by + bar_h / 2 + 4:.1f}" class="c-val"{anchor}>'
                        f'{escape(fmt(r["value"]))}</text></g>')
            y += row_h
        body.append(f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="{top + 4}" y2="{y - 4}" stroke="{RULE}" stroke-width="1"/>')
        y += 6
    return _svg(width, y, label, body)


def columns(points, fmt, label, width=500, height=196, col_w=24):
    """Columns for a short series. points: [ {label, value or None, title} ]."""
    vals = [p["value"] for p in points if p["value"] is not None]
    vmax, vmin = max(vals + [0]), min(vals + [0])
    span = (vmax - vmin) or 1
    top, bottom, side = 24, 26, 6
    plot = height - top - bottom
    if vmin < 0:
        plot -= 14
    slot = (width - 2 * side) / len(points)
    w = min(col_w, slot * 0.6)
    y0 = top + vmax / span * plot
    body = [f'<line x1="{side}" x2="{width - side}" y1="{y0:.1f}" y2="{y0:.1f}" stroke="{RULE}" stroke-width="1"/>']
    for i, p in enumerate(points):
        cx = side + slot * (i + 0.5)
        body.append(f'<g><title>{escape(p["title"])}</title>')
        if p["value"] is None:
            body.append(f'<text x="{cx:.1f}" y="{y0 - 7:.1f}" text-anchor="middle" class="c-sub">n/f</text>')
        else:
            h = abs(p["value"]) / span * plot
            up = p["value"] >= 0
            body.append(f'<path d="{_col(cx - w / 2, y0, w, h, up=up)}" fill="{BLUE}"/>')
            ty = y0 - h - 7 if up else y0 + h + 15
            body.append(f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" class="c-val">{escape(fmt(p["value"]))}</text>')
        body.append(f'<text x="{cx:.1f}" y="{height - 7}" text-anchor="middle" class="c-sub">{escape(p["label"])}</text></g>')
    return _svg(width, height, label, body)


def line(points, fmt, label, width=500, height=196):
    """Line with markers for a rate over time. The scale is fitted to the data,
    so the line shows change; read levels from the printed values."""
    vals = [p["value"] for p in points if p["value"] is not None]
    lo, hi = min(vals), max(vals)
    pad = max((hi - lo) * 0.35, 0.5)
    lo, hi = lo - pad, hi + pad
    top, bottom, side = 26, 28, 6
    plot = height - top - bottom
    slot = (width - 2 * side) / len(points)

    def xy(i, v):
        return side + slot * (i + 0.5), top + (hi - v) / (hi - lo) * plot

    body = [f'<line x1="{side}" x2="{width - side}" y1="{height - bottom + 4}" y2="{height - bottom + 4}" '
            f'stroke="{RULE}" stroke-width="1"/>']
    run = []
    for i, p in enumerate(points + [{"value": None}]):
        if p["value"] is None:
            if len(run) > 1:
                d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in run)
                body.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="2" '
                            f'stroke-linejoin="round" stroke-linecap="round"/>')
            run = []
        else:
            run.append(xy(i, p["value"]))
    for i, p in enumerate(points):
        cx = side + slot * (i + 0.5)
        body.append(f'<g><title>{escape(p["title"])}</title>')
        if p["value"] is None:
            body.append(f'<text x="{cx:.1f}" y="{height - bottom - 8}" text-anchor="middle" class="c-sub">n/f</text>')
        else:
            x, y = xy(i, p["value"])
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{BLUE}" stroke="#FFFFFF" stroke-width="2"/>'
                        f'<text x="{x:.1f}" y="{y - 13:.1f}" text-anchor="middle" class="c-val">{escape(fmt(p["value"]))}</text>')
        body.append(f'<text x="{cx:.1f}" y="{height - 7}" text-anchor="middle" class="c-sub">{escape(p["label"])}</text></g>')
    return _svg(width, height, label, body)


def share_bar(share):
    """Small inline bar for a share of total, 0 to 100."""
    w = max(0.0, min(100.0, share))
    return (f'<span class="share"><span class="share-track"><span class="share-fill" style="width:{w:.1f}%"></span></span>'
            f'<span class="share-val">{share:.0f}%</span></span>')
