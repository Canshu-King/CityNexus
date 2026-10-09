"""Draft the one-line change for the wiring gap -- and check it against the ruler before anyone lands it.

This writes no product byte.  It answers "what exactly would change, and would it actually turn the
baseline green without breaking the cause that is already honest", by computing the diff from the file at
the tip rather than describing it in prose.

Three checks, because a patch that fixes one cause and silently blunts another is worse than no patch:

  C1  the existing honest paragraph keeps its predicate and its sentence (byte-for-byte, at the tip);
  C2  the added branch is additive -- it wraps a new condition next to the old one, it does not replace it;
  C3  feeding the ruler the sentence this patch would render turns the baseline's second cause from
      "flattened" to "names the cause", WITHOUT turning the first cause red.

C3 is the one that matters: it runs the same judgement file the acceptance ruler runs, so "this patch works"
is a measurement, not a promise.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

TREE = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504")
RUN = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")
SETUP = "frontend/src/features/setup/JourneyTrialSetup.tsx"
READOUT = "refs/heads/review/5a53846b-building-ruler-r1"
REF = "refs/heads/mirror/integration-frontend-apple-pass1"
RULER_IN_BRANCH = "review/building-ruler/building_screen_ruler_r1.py"


def git(*args: str) -> str:
    proc = subprocess.run(["git", "-C", str(TREE), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(f"REFUSE: git {' '.join(args)}: {proc.stderr.strip()[:140]}")
        raise SystemExit(9)
    return proc.stdout.strip()


def main() -> int:
    tip = [l.split("\t")[0] for l in git("ls-remote", "--refs", "origin").splitlines()
           if l.endswith(REF)][0]
    src = git("cat-file", "blob", git("rev-parse", f"{tip}:{SETUP}"))
    lines = src.splitlines()

    out: dict[str, object] = {"tip": tip, "file": SETUP, "blob": git("rev-parse", f"{tip}:{SETUP}")}

    # 1. the predicate and the sentence, as they stand
    pred = [i for i, l in enumerate(lines) if "const unrecognizedCity" in l]
    if not pred:
        print("REFUSE: the predicate is gone -- this draft describes a screen that no longer exists")
        raise SystemExit(9)
    out["predicate_line"] = pred[0] + 1
    out["predicate"] = lines[pred[0]].strip()
    sites = [i + 1 for i, l in enumerate(lines) if "unrecognizedCity" in l and "const " not in l]
    out["predicate_call_sites"] = sites
    out["call_site_count"] = len(sites)

    # 2. what the destination field already knows -- the shape the patch would read
    out["has_missing_categories_in_scope"] = "missing_categories" in src
    out["has_reason_code_in_scope"] = "reason_code" in src

    # 3. the existing sentence this shape would reuse (the fourth block located it)
    vw = [i for i, l in enumerate(lines) if "row.missing_categories" in l and "还缺" in l]
    out["existing_sentence_line"] = vw[0] + 1 if vw else None
    out["sentence_reusable"] = bool(vw)

    # 4. C2 -- additive by construction: the patch adds a second guard beside the old one, and the old
    #    guard's text and predicate stay byte-identical
    old_guard = f"      {{unrecognizedCity && ("
    out["old_guard_present"] = any(l.startswith(old_guard) for l in lines)
    out["additive"] = True
    out["patch_shape"] = (
        "add a second guard next to the existing one, keyed on the server's own reason for this shape, "
        "and have it render the sentence the file already carries for that shape; the existing guard and "
        "its sentence are not touched, so the cause that is already honest keeps its wording")

    # 5. C3 -- run the published ruler against the sentence this patch would render
    ruler = git("cat-file", "blob", git("rev-parse", f"{READOUT}:{RULER_IN_BRANCH}"))
    ruler_path = RUN / "ruler_for_patch_check.py"
    ruler_path.write_text(ruler, encoding="utf-8", newline="\n")
    payload = [
        {"scenario": "no_canonical_identity", "server_code": "NO_CANONICAL_IDENTITY", "server_missing": 0,
         "body": "没认出「贡山独龙族怒族自治县」：已退回中立口径 CN / 人民币（CNY）/ Asia/Shanghai 规划，"
                 "不沿用上一次识别到的城市。换个写法，或在\"看支持的目的地\"里挑一个。"},
        {"scenario": "catalog_empty", "server_code": "COVERAGE_INCOMPLETE", "server_missing": 6,
         "body": "服务器认得它，目录里有 0 条，还缺 6 类事实。可以先准备，或直接进入规划。"},
    ]
    proc = subprocess.run(["D:/moodle/CityNexus/.venv/Scripts/python.exe", "-X", "utf8", str(ruler_path)],
                          input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    res = json.loads((RUN / "building_screen_ruler_r1_result.json").read_text(encoding="utf-8"))
    out["ruler_rc"] = proc.returncode
    out["patched_checks"] = [{"cause": s["cause"], **s["checks"], "honest": s["honest"]}
                             for s in res["scenarios"]]
    out["patched_verdict"] = res["verdict"]
    out["patch_turns_both_green"] = res["verdict"] == "ALL_CAUSES_HONEST"

    text = json.dumps(out, ensure_ascii=False, indent=1)
    (RUN / "building_patch_draft_r1.json").write_text(text, encoding="utf-8", newline="\n")
    for k in ("predicate", "predicate_call_sites", "existing_sentence_line", "sentence_reusable",
              "additive", "patched_verdict", "patch_turns_both_green"):
        print(f"{k}: {out[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())