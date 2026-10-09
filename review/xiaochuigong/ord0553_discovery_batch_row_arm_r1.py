"""ORD-0553 (lane xiaochuigong) -- the batch-receipt row of RealCityDiscoveryPanel, judged twice.

The order's 甲 says: take the inline `new Date(...).toLocale*` / ISO slicing and route the value
through the shared formatter, `frontend/src/lib/formatWhen.ts`, with the zone口径 stated.  The order
also says the screen's text must not change *unless* the lane can show the previous version was
itself wrong -- and names that case: 「例如原始 ISO 直接上过屏」.  This row is that case: the bytes at
the authoritative tip printed `start_at.slice(0, 16).replace("T", " ")`, i.e. the stored ISO instant
with its `T` swapped for a space, and they printed the same fragment in zh and in en alike.

So this arm does not argue about intent.  It reads the product bytes at a given sha and the screen
readings that sha produced (`frontend/e2e/qoder-xiaochuigong-0553-batch-row-clock-r1.spec.ts`, which
records the row's innerText per locale), and it requires:

  --expect parent     surgery present, formatter absent, an ISO-shaped value on screen, and the two
                      locales reading the SAME string (the screen was language-blind).
  --expect candidate  formatter present, surgery gone, no ISO fragment on screen, the two locales
                      reading two different strings, the hour:minute unchanged from the stored
                      instant, and the device offset equal to the instant's own offset -- which is
                      what makes "the numbers did not move" a measurement rather than a claim.

Shared predicates judged in both modes: the row is still on the screen path, the formatter still
carries no `timeZone` option (so device clock really is its口径), the borrowed "no time" value exists
in both dictionary arms, every key this file calls resolves in both arms (ORD-0533's B1 predicate
moved onto this file), the day label's `slice(0, 10)` was left alone, no other file on ORD-0553's
list was touched, and the evidence's recorded render line matches the bytes being judged.

The compose door's own refusal is read from the evidence too, because it is why the live route
(ORD-0435's Q4) cannot reach this row at all: 422 on `place_ids`.  Recording it here keeps that red
attached to a number instead of to a sentence.

rc: 0 green, 1 red, 2 the instrument could not start (missing bytes, missing or empty readings).
"""

import argparse
import datetime as dt
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
OTHER_ORDER_FILES = [
    "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx",
    "frontend/src/features/execution/V10LiveExecutionPanel.tsx",
    "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
    "frontend/src/features/agent/AgentComposer.tsx",
    "frontend/src/app/V8Experience.tsx",
]
ISO_WALL_CLOCK = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}")

results = []


def check(name, ok, detail):
    results.append((name, bool(ok), detail))


def git(root, *args):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.stdout.strip(), proc.returncode


def show(root, sha, path):
    out, rc = git(root, "show", f"{sha}:{path}")
    if rc != 0:
        raise SystemExit(f"ARM_ABORT: git show {sha}:{path} rc={rc} -- the instrument did not start")
    return out


def numbered(text):
    return list(enumerate(text.splitlines(), start=1))


def dictionary_values(text):
    return [(n, m.group(1)) for n, line in numbered(text)
            for m in [re.match(r'\s*"' + re.escape(PENDING_KEY) + r'":\s*"(.*?)",\s*$', line)] if m]


def keys_called(text):
    return sorted({m.group(1) for m in re.finditer(r'\bt\(\s*"([A-Za-z0-9_.\-]+)"', text)})


def arm_definitions(text, key):
    return len(re.findall(r'^\s*"' + re.escape(key) + r'":', text, re.M))


def load_readings(evidence_dir, run_id):
    files = sorted(glob.glob(os.path.join(evidence_dir, f"{run_id}__R0553*.json")))
    if not files:
        raise SystemExit(f"ARM_ABORT: no {run_id}__R0553*.json under {evidence_dir} -- the screen was "
                         "never read, so there is nothing to judge")
    read = {}
    for path in files:
        with open(path, encoding="utf-8") as handle:
            body = json.load(handle)
        for field in ("row_head", "product_render_line", "instant_used", "hour_minute_required",
                      "device_zone", "locale", "test_status"):
            if field not in body:
                raise SystemExit(f"ARM_ABORT: {path} carries no {field} -- empty reading, not a pass")
        read[body["locale"]] = body
    if sorted(read) != ["en", "zh-CN"]:
        raise SystemExit(f"ARM_ABORT: locales read = {sorted(read)}; both zh-CN and en are required")
    return read


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--expect", required=True, choices=["parent", "candidate"])
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run", required=True)
    a = ap.parse_args()

    tree = os.path.abspath(a.tree)
    sha = a.sha
    panel = show(tree, sha, PANEL)
    formatter = show(tree, sha, FORMATTER)
    dictionary = show(tree, sha, DICTIONARY)
    readings = load_readings(a.evidence, a.run)

    lis = [n for n, l in numbered(panel) if 'data-testid="v13-discovery-batch-row"' in l]
    check("the row this order names is still on the screen path", len(lis) == 1,
          f'li data-testid="v13-discovery-batch-row" hits={len(lis)} at {lis} in {PANEL}')

    spans = [(n, l) for n, l in numbered(panel) if re.search(r"<span>\{(?:formatWhen\()?row\.start_at", l)]
    check("the batch row still renders row.start_at", len(spans) == 1, f"span hits={len(spans)} at {[n for n, _ in spans]}")
    span_n, span_line = spans[0] if spans else (0, "")

    surgery = "start_at.slice(" in span_line
    calls_formatter = "formatWhen(row.start_at" in span_line
    imports_formatter = bool(re.search(r'^import \{ formatWhen \} from "\.\./\.\./lib/formatWhen";$', panel, re.M))

    zone_opts = len(re.findall(r"timeZone", formatter))
    check("the shared formatter carries no timeZone option, so device clock is its whole口径",
          zone_opts == 0, f"timeZone occurrences in {FORMATTER}={zone_opts}")

    values = dictionary_values(dictionary)
    check(f"the borrowed pending value {PENDING_KEY} exists in both dictionary arms", len(values) == 2,
          f"arms={values} in {DICTIONARY}")

    called = keys_called(panel)
    missing = [k for k in called if arm_definitions(dictionary, k) < 2]
    check("every key this file calls resolves in both arms (ORD-0533 B1, on this file)", not missing,
          f"keys called={len(called)} missing={missing}")

    day_slices = len(re.findall(r"start_at\.slice\(0, 10\)", panel))
    check("the day label was left alone (this lane did not reach past the named row)", day_slices == 1,
          f"start_at.slice(0, 10) in {PANEL}={day_slices}")

    touched, rc = git(tree, "diff", "--name-only", f"{sha}...HEAD")
    if rc != 0:
        raise SystemExit(f"ARM_ABORT: git diff --name-only rc={rc}")
    touched = [t for t in touched.splitlines() if t]
    others = [f for f in OTHER_ORDER_FILES if f in touched]
    check("no other file on the ORD-0553 list is touched by this branch", not others,
          f"branch touched={touched}")

    for locale, body in sorted(readings.items()):
        check(f"{locale}: the recorded render line equals the bytes being judged",
              body["product_render_line"].strip() in span_line or span_line.strip() in body["product_render_line"],
              f"evidence says {body['product_render_line']!r} at {PANEL}")
        check(f"{locale}: the screen node passed", body["test_status"] == "reached_end_of_arm",
              f"test_status={body['test_status']}")
        check(f"{locale}: the compose door's refusal is on the record, not routed around",
              body["real_compose_probe"]["status"] == 422,
              f"POST .../plans/authoritative-compose -> {body['real_compose_probe']['status']}, "
              f"head={body['real_compose_probe']['body_head'][:110]}")

    instants = {loc: body["instant_used"] for loc, body in readings.items()}
    device_zones = {loc: body["device_zone"] for loc, body in readings.items()}
    same_instant = len(set(instants.values())) == 1
    check("both locales read the same stored instant (so the two renderings are comparable)",
          same_instant, f"instant_used={instants}")

    def offsets_match(instant_iso, zone_name):
        try:
            when = dt.datetime.fromisoformat(instant_iso)
        except ValueError:
            return False, "unparseable instant"
        if when.tzinfo is None:
            return False, "the stored value carries no offset"
        local = when.astimezone()
        return local.utcoffset() == when.utcoffset(), f"{zone_name} offset {local.utcoffset()} vs stored {when.utcoffset()}"

    if same_instant:
        ok, why = offsets_match(list(instants.values())[0], list(device_zones.values())[0])
        check("the device zone equals the stored offset, so converging cannot move a number", ok,
              f"{why}; stored={instants}")

    heads = {loc: body["row_head"] for loc, body in readings.items()}
    tokens = {loc: ISO_WALL_CLOCK.match(h).group(0) if ISO_WALL_CLOCK.match(h) else None
              for loc, h in heads.items()}

    if a.expect == "parent":
        check("parent: the row still does string surgery", surgery, f"{PANEL}:{span_n} reads {span_line.strip()!r}")
        check("parent: the shared formatter is neither imported nor called",
              not imports_formatter and not calls_formatter, f"{PANEL}:{span_n}")
        check("parent: both locales show a raw ISO wall-clock fragment",
              all(tokens.values()), f"row heads={heads}")
        check("parent: the two locales show the SAME string (the row was language-blind)",
              len({t for t in tokens.values()}) == 1, f"time tokens={tokens}")
    else:
        check("candidate: the row calls the shared formatter", calls_formatter, f"{PANEL}:{span_n} reads {span_line.strip()!r}")
        check("candidate: no slice/replace surgery is left on that line", not surgery, f"{PANEL}:{span_n}")
        check("candidate: the formatter is imported", imports_formatter, f"{PANEL}:3-5")
        check("candidate: no ISO fragment and no T survives on the row in either locale",
              not any(tokens.values()) and not any("T" in h.split(" ")[0] for h in heads.values()),
              f"row heads={heads}")
        check("candidate: the two locales now read two different strings",
              len(set(heads.values())) == 2, f"row heads={heads}")
        preserved = all(body["hour_minute_required"] in body["row_head"] for body in readings.values())
        check("candidate: the hour:minute the store holds is the hour:minute on screen",
              preserved, f"required={ {l: b['hour_minute_required'] for l, b in readings.items()} } heads={heads}")

    red = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}\n      {detail}")
    print(f"MODE={a.expect} sha={sha[:9]} run={a.run} checks={len(results)} red={len(red)}")
    if red:
        print(f"ORD0553_ARM_RED mode={a.expect} red={len(red)}")
        return 1
    print(f"ORD0553_ARM_GREEN mode={a.expect} checks={len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
