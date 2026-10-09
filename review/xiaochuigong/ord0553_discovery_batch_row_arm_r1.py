"""ORD-0553 (lane xiaochuigong) -- the batch-receipt row of RealCityDiscoveryPanel.

What the order asked for is 甲: the row printed the server's ISO string after string surgery
(`start_at.slice(0, 16).replace("T", " ")`), which puts an unlabelled wall clock on a traveller's
screen; the fix routes that value through the one shared instant formatter, `lib/formatWhen.ts`,
whose zone is the device's own.

This arm does not trust a line number -- the render line is located by content, because the sibling
orders under this file move it every generation.

Two modes, and both are real readings rather than one green plus one promise:

  --expect parent    the bytes at the authoritative tip: the surgery is still there, formatWhen is
                     not imported, and the screen (from that run's Playwright evidence) shows an
                     ISO-shaped `YYYY-MM-DD HH:MM`.
  --expect candidate this branch: the row calls formatWhen, the surgery is gone from the rendered
                     value, the key it borrows for "no time" exists in BOTH dictionary arms, and the
                     screen shows a locale-shaped rendering with no `T` and no bare ISO date.

`--evidence` points at the directory holding `<run>__Q4zh.json` / `<run>__Q4en.json` written by
frontend/e2e/qoder-ord0435-poi-batch-multiselect.spec.ts.  A missing or empty reading aborts with
rc=2 -- an instrument that did not start must not fold into a pass.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

PANEL = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
FORMATTER = "frontend/src/lib/formatWhen.ts"
DICTIONARY = "frontend/src/i18n/LocaleContext.tsx"
PENDING_KEY = "inbox.timePending"
#: the other files ORD-0553 lists; none of them belongs to this lane
OTHER_ORDER_FILES = [
    "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx",
    "frontend/src/features/execution/V10LiveExecutionPanel.tsx",
    "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
    "frontend/src/features/agent/AgentComposer.tsx",
    "frontend/src/app/V8Experience.tsx",
]

results = []


def check(name, ok, detail):
    results.append((name, bool(ok), detail))
    return bool(ok)


def git(root, *args):
    proc = subprocess.run(
        ["git", "-C", root] + list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.stdout.strip(), proc.returncode


def show(root, sha, path):
    out, rc = git(root, "show", f"{sha}:{path}")
    if rc != 0:
        raise SystemExit(f"ARM_ABORT: git show {sha}:{path} rc={rc} -- the instrument did not start")
    return out


def numbered(text):
    return [(i + 1, line) for i, line in enumerate(text.splitlines())]


def dictionary_arms(dictionary_text):
    """Both books carry the key as a quoted literal; count the definitions, do not assume one."""
    hits = []
    for n, line in numbered(dictionary_text):
        m = re.match(r'\s*"' + re.escape(PENDING_KEY) + r'":\s*"(.*?)",\s*$', line)
        if m:
            hits.append((n, m.group(1)))
    return hits


def keys_called_by(panel_text):
    """Every key this file passes to t(), computed from the file on this run -- not a copied count."""
    return sorted({m.group(1) for m in re.finditer(r'\bt\(\s*"([A-Za-z0-9_.\-]+)"', panel_text)})


def dictionary_has_key(dictionary_text, key):
    return len(re.findall(r'^\s*"' + re.escape(key) + r'":', dictionary_text, re.M))


def load_screen_readings(evidence_dir, run_glob):
    """{arm: (row_text, title, server_start_at, test_status)} straight from the spec's own evidence."""
    files = sorted(glob.glob(os.path.join(evidence_dir, run_glob + "__Q4*.json")))
    if not files:
        raise SystemExit(
            f"ARM_ABORT: no Q4 evidence under {evidence_dir}/{run_glob}__Q4*.json -- "
            "the screen was never read, so this arm has nothing to judge"
        )
    read = {}
    for path in files:
        with open(path, encoding="utf-8") as handle:
            body = json.load(handle)
        arm = os.path.basename(path).split("__")[-1].split(".")[0]
        rows = body.get("row_texts") or []
        server = (body.get("second_read") or {}).get("picked_rows") or []
        if not rows or not server:
            raise SystemExit(f"ARM_ABORT: {path} reads rows={len(rows)} server={len(server)} -- "
                             "an empty reading is not a pass")
        read[arm] = (rows[0], str(server[0].get("title")), str(server[0].get("start_at")),
                     body.get("test_status"))
    if len(read) < 2:
        raise SystemExit(f"ARM_ABORT: only {sorted(read)} of the two locales read -- need Q4zh and Q4en")
    return read


ISO_WALL_CLOCK = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}")


def time_part(row_text, title):
    """The li's innerText is `<time> <title> <uuid>`; judge only the leading token."""
    head = row_text
    if title and title in head:
        head = head.split(title)[0]
    return head.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, help="lane worktree root")
    ap.add_argument("--sha", required=True, help="which generation of the product bytes to judge")
    ap.add_argument("--expect", required=True, choices=["parent", "candidate"])
    ap.add_argument("--evidence", required=True, help="directory of Q4 evidence json")
    ap.add_argument("--run", required=True, help="run-id glob, e.g. run563529")
    args = ap.parse_args()

    tree = os.path.abspath(args.tree)
    panel = show(tree, args.sha, PANEL)
    formatter = show(tree, args.sha, FORMATTER)
    dictionary = show(tree, args.sha, DICTIONARY)

    rendered = [n for n, l in numbered(panel) if "v13-discovery-batch-row" in l]
    check("the row this order names is still on the screen path", len(rendered) == 1,
          f"li[data-testid=v13-discovery-batch-row] hits={len(rendered)} at {rendered}")
    span = [(n, l) for n, l in numbered(panel)
            if re.search(r"<span>\{(?:formatWhen\()?row\.start_at", l)]
    check("the batch row still renders row.start_at", len(span) == 1,
          f"span hits={len(span)} at {[n for n, _ in span]}")
    span_n, span_line = span[0] if span else (0, "")

    surgery = re.search(r"start_at\.slice\(", span_line)
    uses_formatter = "formatWhen(row.start_at" in span_line
    imports_formatter = bool(re.search(r'^import \{ formatWhen \} from "\.\./\.\./lib/formatWhen";$',
                                       panel, re.M))
    day_key_slice = len(re.findall(r"start_at\.slice\(0, 10\)", panel))

    check("formatWhen declares no timeZone option, so device clock is its whole口径",
          not re.search(r"timeZone", formatter),
          f"timeZone occurrences in {FORMATTER}={len(re.findall('timeZone', formatter))}")
    check("this lane did not reach past the row: the day label's slice(0, 10) is untouched",
          day_key_slice == 1, f"start_at.slice(0, 10) occurrences={day_key_slice}")

    arms = dictionary_arms(dictionary)
    check(f"{PENDING_KEY} has exactly two arms in the dictionary", len(arms) == 2,
          f"arms={arms} at {DICTIONARY}")

    called = keys_called_by(panel)
    missing = [k for k in called if dictionary_has_key(dictionary, k) < 2]
    check("every key this file calls exists in both dictionary arms (ORD-0533 B1 on this file)",
          not missing, f"keys called={len(called)}, missing={missing}")

    changed, rc = git(tree, "diff", "--name-only", f"{args.sha}...HEAD")
    if rc != 0:
        raise SystemExit(f"ARM_ABORT: git diff --name-only rc={rc} -- the arm cannot answer")
    touched = changed.splitlines()
    others = [f for f in OTHER_ORDER_FILES if f in touched]
    check("no other file on the ORD-0553 list is touched by this branch", not others,
          f"branch touched={touched}")

    screen = load_screen_readings(args.evidence, args.run)
    per_locale = {}
    for arm_name, (row_text, title, server_at, status) in sorted(screen.items()):
        head = time_part(row_text, title)
        per_locale[arm_name] = {
            "time_on_screen": head,
            "iso_shaped": bool(ISO_WALL_CLOCK.match(head)),
            "carries_T": "T" in head,
            "server_start_at": server_at,
            "test_status": status,
        }
        check(f"{arm_name}: the node passed", status == "passed", f"test_status={status}")
    summary = json.dumps(per_locale, ensure_ascii=False)

    if args.expect == "parent":
        check("parent: the row still does string surgery", surgery is not None,
              f"{PANEL}:{span_n} reads: {span_line.strip()}")
        check("parent: formatWhen is not called", not uses_formatter, f"{PANEL}:{span_n}")
        check("parent: formatWhen is not imported", not imports_formatter, "no import line")
        check("parent: the screen shows an ISO wall clock in both locales",
              all(v["iso_shaped"] for v in per_locale.values()), summary)
    else:
        check("candidate: the row calls the shared formatter", uses_formatter,
              f"{PANEL}:{span_n} reads: {span_line.strip()}")
        check("candidate: no slice/replace surgery left on that line", surgery is None,
              f"{PANEL}:{span_n}")
        check("candidate: the formatter is imported", imports_formatter, f"{PANEL}:3-4")
        check("candidate: the screen shows no ISO date and no T in either locale",
              all(not v["iso_shaped"] and not v["carries_T"] for v in per_locale.values()), summary)
        check("candidate: the two locales rendered two different, non-empty values",
              len({v["time_on_screen"] for v in per_locale.values()}) == len(per_locale)
              and all(v["time_on_screen"] for v in per_locale.values()), summary)

    red = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}\n      {detail}")
    print(f"MODE={args.expect} checks={len(results)} red={len(red)}")
    if red:
        print(f"ORD0553_ARM_RED mode={args.expect} red={len(red)}")
        return 1
    print(f"ORD0553_ARM_GREEN mode={args.expect} checks={len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
