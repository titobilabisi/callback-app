"""Run every attack and write a report.

  python -m attacks.run_all             runs everything
  python -m attacks.run_all B05 C12     runs only those

Each attack runs on its own fresh copy of the app and a throwaway
in-memory database, so nothing touches real data.
"""
import sys
import time
import traceback
from pathlib import Path

from . import bypass, compromise  # noqa: F401  (importing registers the attacks)
from .harness import ATTACKS, Breach, Ctx, Gap

REPORT = Path(__file__).with_name("report.md")


def run_one(a):
    ctx = Ctx(a["limited"])
    try:
        result = a["fn"](ctx)
        error = None
    except Exception as err:  # the attack script itself broke
        result, error = None, "".join(traceback.format_exception_only(type(err), err)).strip()
    logged = None
    if a["logs"] and error is None:
        event_type, outcome = a["logs"]
        logged = len(ctx.events(event_type, outcome)) > 0
    ctx.teardown()
    if error:
        return {"status": "ERROR", "note": error, "logged": logged}
    if isinstance(result, Breach):
        return {"status": "BREACH", "note": result.note, "logged": logged}
    if isinstance(result, Gap):
        return {"status": "GAP", "note": result.note, "logged": logged}
    if a["logs"] and not logged:
        return {"status": "NOT LOGGED", "note": f"stopped, but no {a['logs'][0]} event was written", "logged": False}
    return {"status": "DEFENDED", "note": "", "logged": logged}


def main(argv):
    wanted = set(argv)
    chosen = sorted((a for a in ATTACKS if not wanted or a["id"] in wanted), key=lambda a: (a["kind"], a["id"]))
    rows = []
    for a in chosen:
        started = time.time()
        out = run_one(a)
        out.update(id=a["id"], kind=a["kind"], title=a["title"])
        rows.append(out)
        print(f"{a['id']:<4} {out['status']:<11} {a['title']}" + (f"  -> {out['note']}" if out["note"] else ""))
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print()
    print("  ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    if not wanted:
        write_report(rows, counts)
        print(f"Report written to {REPORT}")
    bad = counts.get("BREACH", 0) + counts.get("ERROR", 0) + counts.get("NOT LOGGED", 0)
    return 1 if bad else 0


def write_report(rows, counts):
    lines = ["# Attack results", ""]
    lines.append("Each row is one attack run against a fresh copy of the app. DEFENDED means the attack failed and the audit log recorded it where it should.")
    lines.append("")
    lines.append("Totals: " + ", ".join(f"{v} {k.lower()}" for k, v in sorted(counts.items())))
    lines.append("")
    for kind, heading in (("bypass", "Bypass attacks"), ("compromise", "Compromise attacks")):
        group = [r for r in rows if r["kind"] == kind]
        if not group:
            continue
        lines += [f"## {heading} ({len(group)})", "", "| ID | Attack | Result | In audit log | Notes |", "|---|---|---|---|---|"]
        for r in group:
            logged = "yes" if r["logged"] else ("no" if r["logged"] is False else "n/a")
            lines.append(f"| {r['id']} | {r['title']} | {r['status']} | {logged} | {r['note']} |")
        lines.append("")
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
