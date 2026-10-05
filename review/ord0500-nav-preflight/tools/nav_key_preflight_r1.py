"""Pre-flight on the screen-name fix the line already carries: when the phone chain swaps generation, will
those four routes print words -- or the dictionary keys?

ORD-0567 batch 2 added four route names to the shell's registry (`import / footprints / trash / access`), and
the shell labels the top bar with `t("nav." + route)`.  The bundle served today predates that addition, so the
screens still fall back to the hub label -- but the day the chain is rebuilt, whatever the dictionaries hold for
`nav.import` etc. goes straight onto the screen.  This asks the two questions that matter before that day:

  1. does each registered route have an entry in BOTH word tables (en and zh)?
  2. does any of those values equal the key itself -- the classic "t() echoed the key" defect this order exists
     to stop, which no browser at 390x844 would catch until after the swap?

The route list is read out of the landed commit's own added lines, and the file is read out of the live tip.
Two controls ride along: a route that must resolve (`hub`) and a name that must not (`zznotaroute`).  Read-only.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
I18N = "frontend/src/i18n/LocaleContext.tsx"
SHELL = "frontend/src/app/V8Experience.tsx"
LANDING_COMMIT = "d107131c6"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    q = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=300, env=ENV)
    return q.returncode, q.stdout.decode("utf-8", "replace"), q.stderr.decode("utf-8", "replace")


def registered_routes(tip):
    """The route names the landed commit ADDED to the shell registry -- derived from the diff, not typed."""
    rc, out, err = git("diff", "%s^..%s" % (LANDING_COMMIT, LANDING_COMMIT), "--", SHELL)
    if rc:
        raise SystemExit("ABORT_LANDING_DIFF_UNREADABLE " + err[:120])
    added = [m.group(1) for m in re.finditer(r"^\+\s+([a-z][a-z0-9_]{2,20}):\s*1,", out, re.M)]
    if not added:
        raise SystemExit("ABORT_NO_ADDED_ROUTES_READ")
    return sorted(set(added)), out.count("+")


def entries(tip, key):
    """Every `"key": "value"` for that dictionary key on the line, with the line number and the value."""
    rc, text, _e = git("show", "%s:%s" % (tip, I18N))
    if rc:
        raise SystemExit("ABORT_I18N_UNREADABLE")
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.search(r'[\"\']%s[\"\']\s*:\s*[\"\']([^\"\']*)[\"\']' % re.escape(key), line)
        if m:
            hits.append({"line": n, "value": m.group(1)})
    return hits


def main():
    rc, out, _e = git("ls-remote", "--refs", "origin", TIP_REF)
    tip = out.split()[0]
    routes, added_lines = registered_routes(tip)
    rows = []
    for route in routes + ["hub", "zznotaroute"]:
        key = "nav." + route
        hits = entries(tip, key)
        values = [h["value"] for h in hits]
        row = {"route": route, "dictionary_key": key, "tables_holding_it": len(hits),
               "lines": [h["line"] for h in hits], "values": values,
               "value_equals_key": any(v == key for v in values),
               "value_is_empty": any(v == "" for v in values)}
        if route == "zznotaroute":
            row["verdict"] = "CONTROL_MUST_BE_ABSENT" if not hits else "CONTROL_BROKEN"
            row["bit"] = not hits
        elif route == "hub":
            row["verdict"] = "CONTROL_MUST_BE_PRESENT" if len(hits) >= 2 else "CONTROL_BROKEN"
            row["bit"] = len(hits) >= 2
        else:
            row["verdict"] = ("LABEL_ON_LINE" if len(hits) >= 2 and not row["value_equals_key"]
                              and not row["value_is_empty"] else "LABEL_DEFECT")
        rows.append(row)
    controls = [r for r in rows if r["route"] in ("hub", "zznotaroute")]
    if not all(c.get("bit") for c in controls):
        raise SystemExit("ABORT_CONTROLS_BROKEN " + json.dumps(controls, ensure_ascii=False)[:300])
    landed = [r for r in rows if r["route"] in routes]
    defects = [r["route"] for r in landed if r["verdict"] != "LABEL_ON_LINE"]
    out = {"schema": "CNX_NAV_KEY_PREFLIGHT_V1", "tool": "nav_key_preflight_r1",
           "took_local": datetime.now().astimezone().isoformat(), "live_tip": tip,
           "landing_commit": LANDING_COMMIT, "registry_routes_added": routes,
           "diff_plus_lines": added_lines, "carrier": I18N, "rows": rows,
           "landed_routes": len(landed), "defect_routes": defects,
           "verdict": "NO_KEY_WILL_REACH_THE_SCREEN" if not defects else "KEY_LEAK_WOULD_LAND",
           "controls_ok": True, "worktree_written": False}
    dest = os.path.join(LANE, "evidence", "nav_key_preflight_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"live_tip": tip, "routes": routes, "diff_plus_lines": added_lines,
                      "landed_routes": len(landed), "defects": defects, "verdict": out["verdict"]},
                     ensure_ascii=False))
    for r in landed:
        print("%-11s %-20s tables=%d lines=%s values=%s" % (r["route"], r["verdict"], r["tables_holding_it"],
                                                             r["lines"], json.dumps(r["values"], ensure_ascii=False)))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
