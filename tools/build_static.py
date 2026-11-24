"""Builds the click-through site from data/ and screens/.

    python tools/build_static.py            site/Main.html, News.html, Financials.html, Sources.html, index.html
    python tools/build_static.py --single   also site/tic-dashboard.html, one self-contained file to email or share

Styles and script are inlined, so every page works when opened from disk.
The output is deterministic: the same data always gives the same files.
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model   # noqa: E402
import render  # noqa: E402

SITE = model.ROOT / "site"
SLOT = re.compile(r"\{\{([a-z_0-9]+)\}\}")
SINGLE_FILE = "tic-dashboard.html"


def read(name):
    return (model.SCREENS / name).read_text(encoding="utf-8")


def fill(template, slots, where):
    def sub(m):
        if m.group(1) not in slots:
            raise SystemExit(f"{where}: unknown slot {{{{{m.group(1)}}}}}")
        return slots[m.group(1)]
    return SLOT.sub(sub, template)


def build(d, single=False):
    """Return {file name: html}. single=True gives the one-file version."""
    ctx = render.Ctx(d, single=single)
    slots = render.slots(ctx)
    shell, css, js = read("shell.html"), read("assets/app.css"), read("assets/app.js")
    bodies = {s["id"]: fill(read(s["template"]), slots, s["template"]) for s in ctx.screens}
    title = d["meta"]["title"]
    pages = {}
    if single:
        content = "".join(f'<section class="screen" id="{s["id"]}">{bodies[s["id"]]}</section>' for s in ctx.screens)
        pages[SINGLE_FILE] = fill(shell, {"title": title, "css": css, "js": js, "mode": "single",
                                          "sidebar": render.sidebar(ctx, ctx.screens[0]["id"]),
                                          "content": content}, "shell.html")
        return pages
    for s in ctx.screens:
        pages[s["file"]] = fill(shell, {"title": f'{s["label"]} | {title}', "css": css, "js": js, "mode": "pages",
                                        "sidebar": render.sidebar(ctx, s["id"]),
                                        "content": f'<section class="screen" id="{s["id"]}">{bodies[s["id"]]}</section>'},
                                "shell.html")
    first = ctx.screens[0]["file"]
    pages["index.html"] = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
                           f'<meta http-equiv="refresh" content="0; url={first}"></head>'
                           f'<body><p><a href="{first}">Open the dashboard</a></p></body></html>\n')
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--single", action="store_true", help=f"also write site/{SINGLE_FILE}")
    args = ap.parse_args()
    d = model.load()
    pages = build(d)
    if args.single:
        pages.update(build(d, single=True))
    SITE.mkdir(exist_ok=True)
    for old in SITE.glob("*.html"):
        old.unlink()
    for name, html in sorted(pages.items()):
        (SITE / name).write_text(html, encoding="utf-8", newline="\n")
        print(f"site/{name}  {len(html.encode('utf-8')) / 1024:.0f} KB")
    print(f"Built {len(pages)} files. Open site/index.html to click through.")


if __name__ == "__main__":
    main()
