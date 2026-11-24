"""Record a person's sign-off of sources in data/sources.json.

    python tools/signoff.py --by "Your Name" --all
    python tools/signoff.py --by "Your Name" --on 2026-11-24 sgs_q3_26 uls_q3_26
    python tools/signoff.py --remove sgs_q3_26
    python tools/signoff.py --status

A sign-off says that the named person opened the source and compared every figure
that cites it. Run this yourself after checking. An AI assistant runs it only when
the owner has said in chat that the check is done, with the name and date the owner
gives; it never signs off on its own judgement and never renews a lapsed sign-off.

Each sign-off stores a short checksum of the figures that cite the source. When one
of them is later added, removed or changed, tools/check.py fails until the sign-off
is removed with --remove. The count on the dashboard then drops by itself.
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model  # noqa: E402

FIELDS = ("reviewed_by", "reviewed_on", "reviewed_sum")


def summary(d):
    r = model.review(d)
    who = f" by {', '.join(r['who'])}, latest {r['last']}" if r["who"] else ""
    return (f"Signed off: {r['sources_done']} of {r['sources_total']} sources{who}. "
            f"The dashboard will say {r['checked']} of {r['sourced']} sourced figures and "
            f"{r['px_done']} of {r['px_total']} share-price sources have been checked by a person.")


def main():
    ap = argparse.ArgumentParser(description="Record or remove a person's sign-off of sources.")
    ap.add_argument("ids", nargs="*", help="source ids, as shown under each title in the source register")
    ap.add_argument("--all", action="store_true", help="every source in the register")
    ap.add_argument("--by", help="the name of the person who checked, as it should show on the dashboard")
    ap.add_argument("--on", default=datetime.date.today().isoformat(), help="the day of the check, YYYY-MM-DD (default: today)")
    ap.add_argument("--remove", action="store_true", help="remove the sign-off instead of recording one")
    ap.add_argument("--status", action="store_true", help="print the current count and change nothing")
    args = ap.parse_args()

    d = model.load()
    sources = d["sources"]["sources"]
    if args.status:
        print(summary(d))
        return
    ids = list(sources) if args.all else args.ids
    if not ids:
        ap.error("name the source ids, or use --all")
    unknown = [i for i in ids if i not in sources]
    if unknown:
        ap.error(f"not in data/sources.json: {', '.join(unknown)}")
    if args.remove:
        for sid in ids:
            for k in FIELDS:
                sources[sid].pop(k, None)
    else:
        if not args.by or not args.by.strip():
            ap.error("--by is required: the name of the person who checked")
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.on):
                raise ValueError
            datetime.date.fromisoformat(args.on)
        except ValueError:
            ap.error("--on must be a real date, YYYY-MM-DD")
        for sid in ids:
            sources[sid].update(reviewed_by=args.by.strip(), reviewed_on=args.on, reviewed_sum=model.review_sum(d, sid))

    path = model.DATA / "sources.json"
    path.write_text(json.dumps(d["sources"], indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{'Removed the sign-off from' if args.remove else 'Signed off'} {len(ids)} source(s).")
    print(summary(model.load()))
    print("Now run: python tools/check.py")


if __name__ == "__main__":
    main()
