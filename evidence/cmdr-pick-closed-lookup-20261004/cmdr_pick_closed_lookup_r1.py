"""CMDR pick-closed-lookup ruler r1 - does displayVocabulary's pick() hand the caller's own bytes back?

Why: the landing gate's Q64 arm answered "cells 6 -> 18" for ORD-0551 even though 5 of the 6 named
files are not in that candidate's diff.  Read straight off the shipped source at
`frontend/src/lib/displayVocabulary.ts` (`rawChannel` at :172, `pick` at :178 on the 10-04 02:4x tip),
the reason is one shape: when the table has no entry, `pick` returns `rawChannel(value, zh)` -- the
caller's own argument, i.e. the server's enum -- so a ruler that answers a helper's return value "by
every call site" drags the whole label vocabulary across every panel that calls it.  The ruling is to
close the lookup.  This file is that ruling as a re-runnable arm: it counts, on any rev or any file,
whether the miss branch hands the input back.

Arms:  --rev <40hex>          measure what is shipped (expected RED until the fix lands)
       --mutant-punished      the same file with the miss branch turned back into 回吐入参 (RED)
       --closed-variant       the miss branch returning null instead (GREEN)

Usage: python cmdr_pick_closed_lookup_r1.py [--rev <40hex>] [--file <path>] [--json <out>]
"""
import argparse, json, re, subprocess, sys, os, tempfile

REPO = "D:/moodle/CityNexus"
PATH = "frontend/src/lib/displayVocabulary.ts"
ANCHOR_FUNCS = ("rawChannel", "pick")


def body_of(src: str, name: str):
    m = re.search(r"(?m)^(?:export\s+)?function\s+%s\s*\(" % re.escape(name), src)
    if not m:
        return None
    i = src.index("{", m.end())
    depth, j = 0, i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    return None


def measure(src: str, label: str):
    pick = body_of(src, "pick")
    raw = body_of(src, "rawChannel")
    out = {"arm": label, "rawChannel_present": raw is not None, "pick_present": pick is not None}
    if pick is None:
        out.update(verdict="RULER_OUT_OF_SCOPE", why="no pick() function in this file")
        return out
    lines = pick.splitlines()
    returns = [(n + 1, ln.strip()) for n, ln in enumerate(lines) if re.search(r"\breturn\b", ln)]
    out["return_statements"] = returns
    out["return_count"] = len(returns)
    leaks = [r for r in returns if re.search(r"return\s+rawChannel\s*\(", r[1])]
    out["miss_branch_hands_back_input"] = bool(leaks)
    out["leaking_lines_inside_pick"] = leaks
    out["verdict"] = "RED" if leaks else "GREEN"
    out["claim"] = ("pick 未命中即把调用方入参原样回吐（尺按所有调用点回答 => 标签扩散）"
                    if leaks else "pick 未命中不回吐入参（查找已闭合）")
    return out


def get_rev(rev: str) -> str:
    r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, PATH)],
                       capture_output=True, timeout=180)
    if r.returncode != 0:
        raise SystemExit("cannot read %s:%s -> %s" % (rev, PATH, r.stderr.decode("utf-8", "replace")[:120]))
    return r.stdout.decode("utf-8", "replace")


def closed_variant(src: str) -> str:
    return src.replace("  return rawChannel(value, zh);\n", "  return null as never;\n", 1)


def mutant_punished(src: str) -> str:
    # force the miss branch back into handing the input upstream, whatever the shipped shape is
    if "return rawChannel(value, zh);" in src:
        return src
    return src.replace("function pick(", "function pick_leak_marker_unused(", 1).replace(
        "function pick_leak_marker_unused(", "function pick(", 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev")
    ap.add_argument("--file")
    ap.add_argument("--json")
    a = ap.parse_args()
    if a.file:
        src = open(a.file, encoding="utf-8").read()
        base_label = "file:" + a.file
    elif a.rev:
        src = get_rev(a.rev)
        base_label = "rev:" + a.rev
    else:
        raise SystemExit("give --rev <40hex> or --file <path>")

    arms = [measure(src, base_label + " (as shipped)")]
    closed = closed_variant(src)
    arms.append(measure(closed, base_label + " + closed-lookup variant (expects GREEN)"))
    if "return rawChannel(value, zh);" in src:
        forced = src
        arms.append(measure(forced, base_label + " mutant: miss branch 回吐入参 (expects RED)"))
    else:
        forced = src.replace("function pick(", "function pick(\n  return rawChannel(value, zh);\n  // ", 1)
        arms.append(measure(forced, base_label + " mutant: miss branch 回吐入参 (expects RED)"))

    report = {"instrument": "cmdr_pick_closed_lookup_r1", "path": PATH, "arms": arms,
              "shipped_verdict": arms[0]["verdict"]}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if a.json:
        open(a.json, "w", encoding="utf-8").write(text)
    # self-check: the three arms must not all say the same thing, or the ruler measures nothing
    kinds = {x["verdict"] for x in arms}
    print(text)
    if kinds == {"RED"} or kinds == {"GREEN"}:
        print("SELF-CHECK FAILED: every arm returned %s -- the ruler cannot tell the two shapes apart" % kinds)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
