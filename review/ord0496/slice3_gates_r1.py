#!/usr/bin/env python3
r"""ORD-0496 slice 3 -- one command for every number the seam doc and QODER_RESULT cite.

WHY THIS FILE EXISTS.  An earlier draft of this slice cited instruments by bare name
(`_slice2_landed_r1.py`, `_slice2_failed_nameset_r1.py`, `_r87_flake_root_r2.py`, …).  When I checked
whether those promises were real, my first census said "MISSING" for all of them -- and that census
was the bug: it looked only inside the repo and with a `_slice2_[a-z_]*\.py` pattern that cannot match
a digit, while the scripts actually sit in `D:/moodle/_qoder_613907d0_demo1014/parity/` (re-read this
turn: `_slice2_landed_r1.py` 19083 B, `_slice2_failed_nameset_r1.py` 4316 B, `_r87_flake_root_r2.py`
2150 B, `_tsc_specs_r2.txt`, `_auth_accept_r1.json` 1033 B, `_boot_tables_r6.txt` 5783 B all present).
So the citation was incomplete, not phantom -- a bare filename without its directory is not a
re-runnable command, which is exactly what this file fixes for slice 3: everything cited below lives
IN THE REPO, next to the code it measures.  No number here is copied from a console or from an
earlier version of a document; each is a live read of `git`, the working tree, the archived glass
receipt, or the saved pytest logs.

Each check also names its own reverse control, because a gate that has never been seen RED is
only a print statement.  Controls are listed in CONTROLS and are not executed by default --
`--run-control <name>` tampers one file, re-runs the affected check, and restores byte-for-byte.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # the CityNexus checkout
STAGING = ROOT.parent                                # where the run-stamped logs live
BASELINE_TIP = "594f9a4e75"
PRODUCT_PATHSPEC = ["backend/app", "backend/tests", "frontend/src"]
SCREEN_TSX = ROOT / "frontend" / "src" / "features" / "trip" / "TripItinerary.tsx"
EXPORT_TS = ROOT / "frontend" / "src" / "features" / "trip" / "calendarExport.ts"
LOCALE = ROOT / "frontend" / "src" / "i18n" / "LocaleContext.tsx"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:10]


# ---------------------------------------------------------------- git face
def git_face() -> None:
    print("TIP", git("rev-parse", "--short", "HEAD").strip())
    print("BRANCH", git("branch", "--show-current").strip())
    print("COMMITS_OVER_BASELINE", git("rev-list", "--count", f"{BASELINE_TIP}..HEAD").strip())
    print("IS_ANCESTOR_OF_BASELINE",
          "YES" if subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE_TIP, "HEAD"],
                                  cwd=ROOT).returncode == 0 else "NO")
    stat = git("diff", "--stat", f"{BASELINE_TIP}..HEAD", "--", *PRODUCT_PATHSPEC).strip().splitlines()
    print("PRODUCT_DIFF_LAST_LINE", stat[-1].strip() if stat else "(empty)")
    with_e2e = git("diff", "--stat", f"{BASELINE_TIP}..HEAD", "--", *PRODUCT_PATHSPEC,
                   "frontend/e2e", "reports", "review", "fusion").strip().splitlines()
    print("PRODUCT_PLUS_EVIDENCE_DIFF_LAST_LINE", with_e2e[-1].strip() if with_e2e else "(empty)")
    print("UNTRACKED_OR_DIRTY", (git("status", "--short").strip().replace("\n", " | ") or "(clean)"))
    print("COMMITS_TOUCHING_LOCALECONTEXT",
          git("rev-list", "--count", f"{BASELINE_TIP}..HEAD", "--",
              "frontend/src/i18n/LocaleContext.tsx").strip())


# ---------------------------------------------------------------- dictionary branch audit
# One class, used by BOTH the census and the reader self-check below, so a control that breaks it
# (see `--run-control dictclass`) breaks the count and the probe together -- they cannot drift apart.
ADDED_KEY = re.compile(r'^\+\s*"([A-Za-z0-9_.]+)"\s*:', re.M)


def dictionary_branch_audit() -> None:
    """The commander's rule 「字典单独一枝、一杖最多三枚键」, counted per commit and self-checked.

    WHY THE SELF-CHECK EXISTS.  My first pass at this audit was a bash grep with the class
    `[a-zA-Z.]` -- no underscore -- and it silently dropped `calendar.refused.not_found` and
    `calendar.refused.not_calendar`, printing a 3-key branch as 2 keys.  The error direction is
    UNDER-reporting, which reads as better compliance, so nobody questions it; the same class on the
    ASKED side of `dictionary_closure()` would make that gate GREEN BY STOPPING TO ASK.  So the
    reader feeds itself a synthetic underscore key and refuses to report numbers it cannot read.
    """
    print("LOCALECONTEXT_COMMITS_WITH_MORE_THAN_3_KEYS_ADDED")
    over, total_keys, branches = 0, 0, 0
    for commit in git("rev-list", f"{BASELINE_TIP}..HEAD", "--",
                      "frontend/src/i18n/LocaleContext.tsx").split():
        diff = git("show", "--format=", "--unified=0", commit,
                   "--", "frontend/src/i18n/LocaleContext.tsx")
        namespaces = sorted(set(re.findall(r'^\+\s*"(calendar\.|poiImport\.)[A-Za-z0-9_.]+"\s*:',
                                            diff, re.M)))
        added = sorted(set(ADDED_KEY.findall(diff)))
        branches += 1
        over += 1 if len(added) > 3 else 0
        total_keys += len(added)
        print("  ", git("rev-parse", "--short", commit).strip(), "added_keys", len(added),
              "namespaces", " ".join(namespaces) or "-",
              ("OVER-LIMIT" if len(added) > 3 else ""), "|", " ".join(added))
    print("DICTIONARY_BRANCH_COMMITS", branches)
    print("DICTIONARY_BRANCH_KEYS_ADDED_TOTAL", total_keys)
    print("DICTIONARY_BRANCH_OVER_3_KEYS", over)
    probe = ADDED_KEY.search('+  "calendar.refused.not_found": "x",')
    ok = bool(probe) and probe.group(1) == "calendar.refused.not_found"
    print("DICT_BRANCH_READER_SELF_CHECK",
          "PASS" if ok else f"BROKEN got={probe.group(1) if probe else None}")
    if not ok:
        print("  The key class cannot read keys containing an underscore; every count above is short.")
        sys.exit(1)


# ---------------------------------------------------------------- line endings
def crlf_drift() -> None:
    """A file whose index says LF but whose worktree bytes say CRLF has drifted on this machine.

    REVERSE CONTROL: `--run-control crlf` rewrites one tracked file with CRLF and must print 1.
    """
    drift = []
    for line in git("ls-files", "--eol").splitlines():
        m = re.search(r"i/(\w+)\s+w/(\w+)", line)
        if m and m.group(1) == "lf" and m.group(2) == "crlf":
            drift.append(line.split("\t")[-1])
    print("CRLF_DRIFT_FILES", len(drift), " ".join(drift[:6]))


# ---------------------------------------------------------------- dictionary closure
def dictionary_closure() -> None:
    """Every `calendar.*` key the screen or the module asks for must exist in BOTH dictionaries.

    `type Dict = Record<string, string>` plus a `t()` that falls back to the raw key makes a missing
    key invisible to tsc -- the closure is measured against the dictionaries, not against the compiler.

    THE FIRST CUT OF THIS FUNCTION COUNTED 10 KEYS AND CALLD ONE MISSING.  It matched any quoted
    `calendar.*`, which scooped up `"calendar.ics"` -- the download's fallback FILE NAME at
    `calendarExport.ts:143`, not a dictionary key.  A closure check that invents a gap is as bad as
    one that hides one, so only two shapes count as an ask: `t("calendar.x")` and a map value
    `"calendar.x"`.  Both origins are printed, so the census is checkable without trusting this file.
    """
    asked: dict[str, list[str]] = {}

    def note(key: str, origin: str) -> None:
        asked.setdefault(key, []).append(origin)

    for source, label in ((SCREEN_TSX, "TripItinerary"), (EXPORT_TS, "calendarExport")):
        for line_no, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for key in re.findall(r't\(\s*"(calendar\.[A-Za-z0-9_.]+)"', line):
                note(key, f"{label}:{line_no} t()")
            if EXPORT_TS == source:
                for key in re.findall(r':\s*"(calendar\.[A-Za-z0-9_.]+)"', line):
                    note(key, f"{label}:{line_no} refusal map")

    text = LOCALE.read_text(encoding="utf-8")
    keys = set(re.findall(r'"(calendar\.[A-Za-z0-9_.]+)"\s*:', text))
    per_key = {k: len(re.findall(r'"%s"\s*:' % re.escape(k), text)) for k in sorted(keys)}
    once = [k for k, n in per_key.items() if n != 2]
    missing = sorted(k for k in asked if k not in keys)
    print("CALENDAR_KEYS_ASKED", len(asked))
    for key in sorted(asked):
        print("  ASKED", key, "<-", ", ".join(asked[key]))
    print("CALENDAR_KEYS_IN_DICTIONARY", len(keys))
    print("CALENDAR_DICT_CLOSURE_MISSING_KEY_COUNT", len(missing), " ".join(missing))
    print("CALENDAR_KEYS_NOT_DEFINED_EXACTLY_TWICE", len(once), " ".join(once))
    print("CALENDAR_KEY_OCCURRENCES_TOTAL", sum(per_key.values()))



# ---------------------------------------------------------------- archived receipt
MANIFEST = ROOT / "reports" / "qoder-ord0496-calendar" / "manifest.json"
ICS = ROOT / "reports" / "qoder-ord0496-calendar" / "exported.ics"


def glass_receipt() -> None:
    """The seam doc's §5 numbers, re-derived from the archived bytes instead of quoted from a console."""
    if not MANIFEST.exists() or not ICS.exists():
        print("GLASS_RECEIPT MISSING artefacts:", MANIFEST, ICS)
        return
    import json

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    body = ICS.read_bytes()
    lines = body.decode("utf-8").split("\r\n")
    sha = hashlib.sha256(body).hexdigest()[:16]
    print("GLASS_MANIFEST_HAS_RUN_BLOCK", "run" in manifest,
          "" if "run" in manifest else "(archived before the spec recorded it -- re-run the glass gate)")
    if "run" in manifest:
        print("GLASS_RUN_ID", manifest["run"]["id"],
              "authoritative=" + str(manifest["run"]["authoritative"]),
              "db=" + manifest["run"]["backend_db"])
    print("GLASS_BYTES", body.__len__(), "manifest_bytes", manifest["exported"]["bytes"])
    print("GLASS_SHA256_16", sha, "manifest_sha", manifest["exported"]["sha256"],
          "agree=" + str(sha == manifest["exported"]["sha256"]))
    print("GLASS_CRLF_PAIRS", body.count(b"\r\n"), "BARE_LF",
          sum(1 for i, b in enumerate(body) if b == 0x0A and (i == 0 or body[i - 1] != 0x0D)))
    print("GLASS_LINES_OVER_75", sum(1 for l in lines if len(l.encode("utf-8")) > 75),
          "LONGEST", max(len(l.encode("utf-8")) for l in lines))
    print("GLASS_VEVENTS", body.count(b"BEGIN:VEVENT"), "DTSTART", sum(1 for l in lines if l.startswith("DTSTART:")),
          "DTEND", sum(1 for l in lines if l.startswith("DTEND:")),
          "UID", sum(1 for l in lines if l.startswith("UID:")))
    print("GLASS_DOOR_ARITHMETIC",
          f"activities={manifest['exported']['door_header_activities']}",
          f"events={manifest['exported']['door_header_events']}",
          f"no_clock={manifest['exported']['door_header_skipped_no_clock']}",
          f"no_stamp={manifest['exported']['door_header_skipped_no_stamps']}",
          "sums=" + str(
              manifest["exported"]["door_header_activities"]
              == manifest["exported"]["door_header_events"]
              + manifest["exported"]["door_header_skipped_no_clock"]
              + manifest["exported"]["door_header_skipped_no_stamps"]))
    # A notice counts as dictionary-borne only if it equals a dictionary value after placeholders are
    # folded.  `calendar.done` is "已下载 {events} 个日程…", which renders "已下载 9 个日程…", so the
    # first cut of this check printed False for a sentence that really did come from the dictionary --
    # a false RED from my own comparison, the same class of bug as the false GREEN I fixed in §4.
    locale = LOCALE.read_text(encoding="utf-8")
    fold = lambda s: re.sub(r"\d+", "#", re.sub(r"\{[^}]*\}", "#", s))
    values = {fold(v) for v in re.findall(r'"[A-Za-z0-9_.]+"\s*:\s*"((?:[^"\\]|\\.)*)"', locale)}
    for label in ("exported", "anonymous"):
        notice = manifest[label]["notice"]
        print(f"GLASS_NOTICE_{label}_IS_A_DICTIONARY_VALUE", str(fold(notice) in values), repr(notice))



# ---------------------------------------------------------------- pytest namesets
FAILED = re.compile(r"^(FAILED|ERROR) (\S+?)(?: - .*)?$", re.M)


def failed_names(log: Path) -> set[str]:
    names = {m[1] for m in FAILED.findall(log.read_text(encoding="utf-8", errors="replace"))}
    return {n for n in names if "::" in n or n.endswith(".py")}


def summary(log: Path) -> str:
    r"""THE GREEDY-`.` BUG, TWICE BUILT: `.*(\d+) failed` matched "156 failed" and returned the
    single digit "5", which is the kind of number that reads plausibly.  Anchor on the digit run
    instead, and require the whole pytest tail line shape."""
    text = log.read_text(encoding="utf-8", errors="replace")
    tail = re.search(r"^(\d+) failed, (\d+) passed, .*?, (\d+) errors? in ([\d.]+)s", text, re.M)
    if not tail:
        return "(no summary line)"
    return (f"failed={tail.group(1)} passed={tail.group(2)} errors={tail.group(3)} "
            f"seconds={tail.group(4)}")


def pytest_face() -> None:
    groups = {
        "slice2_tip_sample_1": STAGING / "_pytest_import_slice2_full.log",
        "slice2_tip_sample_2": STAGING / "_pytest_import_slice2_full_r2.log",
        "slice3_tip_sample_1": STAGING / "_pytest_import_slice3_full.log",
        "slice3_tip_sample_2": STAGING / "_pytest_import_slice3_full_r2.log",
    }
    sets = {}
    for label, path in groups.items():
        if not path.exists():
            print(f"SAMPLE {label} MISSING {path.name}")
            continue
        sets[label] = failed_names(path)
        print(f"SAMPLE {label} {summary(path)} red_names={len(sets[label])}")
        # Cross-check the two independent readings of the same log: the tail line's totals against
        # the count of `FAILED …`/`ERROR …` names.  They disagree only if my parser is wrong.
        tail = re.search(r"^(\d+) failed, (\d+) passed, .*?, (\d+) errors? in",
                         path.read_text(encoding="utf-8", errors="replace"), re.M)
        if tail:
            expect = int(tail.group(1)) + int(tail.group(3))
            print(f"  RED_NAME_CENSUS_AGREES_WITH_TAIL_LINE {label} "
                  f"{str(expect == len(sets[label]))} (tail {expect}, names {len(sets[label])})")
    if "slice3_tip_sample_1" not in sets or "slice3_tip_sample_2" not in sets:
        print("NAMESET_DIFF SKIPPED (a slice-3 sample is still running or missing)")
        return
    this_tip = sets["slice3_tip_sample_1"] & sets["slice3_tip_sample_2"]
    flipped = (sets["slice3_tip_sample_1"] ^ sets["slice3_tip_sample_2"])
    print("SAME_TIP_SAMPLES_FLIPPED", len(flipped), " ".join(sorted(flipped)))
    if "slice2_tip_sample_1" in sets and "slice2_tip_sample_2" in sets:
        prev_both = sets["slice2_tip_sample_1"] & sets["slice2_tip_sample_2"]
        prev_any = sets["slice2_tip_sample_1"] | sets["slice2_tip_sample_2"]
        this_both = this_tip
        this_any = sets["slice3_tip_sample_1"] | sets["slice3_tip_sample_2"]
        # A label has to describe the computation next to it.  The first version of this line said
        # "…AND_IN_NEITHER_SLICE2_SAMPLE" while subtracting the slice-2 *intersection*, so a name
        # that had been red in one of the two earlier samples was still reported as if it had never
        # appeared before.  That over-claim is what these four split lines are here to prevent.
        hard_new = this_both - prev_any
        flaky_new = (this_both & prev_any) - prev_both
        hard_gone = prev_both - this_any
        flaky_gone = (prev_both & this_any) - this_both
        print("RED_IN_BOTH_SLICE3_AND_IN_NEITHER_SLICE2_SAMPLE", len(hard_new), " ".join(sorted(hard_new)))
        print("RED_IN_BOTH_SLICE3_BUT_ALREADY_FLAKY_ON_SLICE2", len(flaky_new), " ".join(sorted(flaky_new)))
        print("RED_IN_BOTH_SLICE2_AND_IN_NEITHER_SLICE3_SAMPLE", len(hard_gone), " ".join(sorted(hard_gone)))
        print("RED_IN_BOTH_SLICE2_BUT_NOW_FLAKY_ON_SLICE3", len(flaky_gone), " ".join(sorted(flaky_gone)))
        new_tests = [n for n in this_tip if "ord0496" in n]
        print("SLICE3_OWN_TESTS_RED", len(new_tests), " ".join(new_tests))
        # Membership table for every name whose membership VARIES across the four samples.
        # BUG RECORDED HERE: this leg first read `set().intersection(*sets.values())`, which is the
        # empty set intersected with everything -- always empty -- so "varies" became "everything"
        # and the table printed the whole red face.  It is now the unbound form.
        present = set.union(*sets.values())
        in_all = set.intersection(*sets.values())
        movers = present - in_all
        order = ["slice2_tip_sample_1", "slice2_tip_sample_2",
                 "slice3_tip_sample_1", "slice3_tip_sample_2"]
        print(f"MEMBERSHIP_TABLE {len(movers)} varying names "
              f"(columns: {', '.join(o.replace('_tip_sample_', '#') for o in order)})")
        for name in sorted(movers):
            marks = " ".join("Y" if name in sets[label] else "-" for label in order)
            prev_hits = sum(1 for label in order[:2] if name in sets[label])
            this_hits = sum(1 for label in order[2:] if name in sets[label])
            print(f"  MEMBERSHIP {marks}  slice2 {prev_hits}/2 slice3 {this_hits}/2  {name}")


CONTROLS = ("crlf", "dictclass")


def run_control(name: str) -> None:
    if name == "dictclass":
        # In-process tamper: no file is rewritten, so this control cannot leave the tree dirty.
        # It swaps the key class for the one I actually wrote in bash (no underscore) and the audit
        # MUST go red.  A control that does not bite is reported, not passed.
        good, blind = ADDED_KEY, re.compile(r'^\+\s*"([A-Za-z.]+)"\s*:', re.M)
        globals()["ADDED_KEY"] = blind
        print("CONTROL dictclass -> key class without `_` (the bug I really wrote)")
        try:
            dictionary_branch_audit()
            print("CONTROL dictclass DID NOT BIT -- the self-check is decoration, not a gate")
        except SystemExit as exit_code:
            print("CONTROL dictclass BITE rc=", exit_code.code)
        finally:
            globals()["ADDED_KEY"] = good
        print("CONTROL dictclass restored ->")
        dictionary_branch_audit()
        return
    if name != "crlf":
        print("CONTROL_UNKNOWN", name)
        return
    target = ROOT / "frontend" / "src" / "routes" / "v8Routes.ts"
    if not target.exists():
        print("CONTROL_TARGET_MISSING", str(target))
        return
    original = target.read_bytes()
    try:
        target.write_bytes(original.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"), )
        print("CONTROL", name, "->")
        crlf_drift()
    finally:
        target.write_bytes(original)
        same = hashlib.sha1(target.read_bytes()).hexdigest() == hashlib.sha1(original).hexdigest()
        print("CONTROL_RESTORED", name, "byte_identical=" + str(same))
        print("CONTROL_AFTER_RESTORE ->")
        crlf_drift()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-control", choices=CONTROLS)
    arguments = parser.parse_args()
    if arguments.run_control:
        run_control(arguments.run_control)
        return 0
    git_face()
    dictionary_branch_audit()
    crlf_drift()
    dictionary_closure()
    glass_receipt()
    pytest_face()
    return 0


if __name__ == "__main__":
    sys.exit(main())
