"""Census the tip tree for carriers of r3's three new grammars, so the delta claim is measured.

Counts only. Matching is deliberately crude line counting over the exported tip tree, and each class
names the pattern it used, because the point is "how many lines look like this shape", not "the ruler
agrees with me".
"""
import io
import json
import os
import re
import sys

TREE = (sys.argv[1] if len(sys.argv) > 1 else
        "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_sweep_scratch/tree/frontend/src")
OUT = (sys.argv[2] if len(sys.argv) > 2 else
       "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_sweep_scratch/census_r3.json")
KILLERS = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_sweep_scratch/killers_out_ui_exposure_field_check_r3.json"

PATTERNS = {
  "shape_A_tail_name_in_interp": r"\{[^{}]{0,80}\??\.\s*(value|content|reason|output|head)\s*\}",
  "shape_B_bare_local_in_text_sink": r"<(code|pre|span|div|p|li|strong|em)[^>]*>\s*\{[A-Za-z_$][A-Za-z_$0-9]*\}\s*</",
  "shape_C_paren_alias": r"\(\s*[A-Za-z_$][A-Za-z_$0-9. ]*\s*(\|\||\?\?)\s*\{\s*\}\s*\)\s*\??\.[A-Za-z_$]+",
  "generic_signature_function_helper": r"(?:async )?function [A-Za-z_][A-Za-z_0-9]*<",
  "arrow_helper_returning_forbidden_read":
      r"(?:const|let)\s+[A-Za-z_$][A-Za-z_$0-9]*\s*=\s*\([^)]*\)\s*(?::[^=;]{0,60})?=>[^;]{0,140}[?.]\s*"
      r"(detail|message|stack|trace|body)",
  "throw_embedding_upstream_prose":
      r"throw new \w*Error\(.*(detail|error\?\.message)",
  "setstate_called_with_error_message":
      r"set[A-Z]\w*\((?:\n|[^)\n]*\b(?:error|cause)\b[^)\n]*\.message)",
}
TEXT_SINK_LINE = re.compile(r"<(code|pre|span|div|p|li|strong|em)[^>]*>\s*\{[A-Za-z_$][A-Za-z_$0-9]*\}\s*</")


def main():
    files = {}
    for root, _dirs, names in os.walk(TREE):
        for n in names:
            if n.endswith(".ts") or n.endswith(".tsx"):
                p = os.path.join(root, n)
                files[os.path.relpath(p, TREE).replace("\\", "/")] = io.open(
                    p, encoding="utf-8", errors="replace").read().splitlines()
    census = {}
    for label, pat in PATTERNS.items():
        rx = re.compile(pat)
        hits = []
        for rel, lines in sorted(files.items()):
            for i, ln in enumerate(lines, 1):
                if rx.search(ln):
                    hits.append({"file": rel, "line": i, "text": ln.strip()[:120]})
        census[label] = {"pattern": pat, "count": len(hits), "carriers": hits}
    kj = json.load(io.open(KILLERS, encoding="utf-8"))
    killer_hits = {}
    for h in kj["hits"]:
        killer_hits.setdefault(h["file"].split("/")[-1], []).append(h["rule"])
    out = {
        "schema": "CNX_Q64_SWEEP_CENSUS_V1",
        "tree": "git archive 30de4ebe409f49c5e25f4758cb2e5f4e90764a4f frontend/src",
        "files_in_tree": len(files),
        "census": census,
        "killer_harness": {
            "ruler_used_for_killers": "ui_exposure_field_check_r3.py",
            "per_file_rules": killer_hits,
            "positive_control_fired": bool(killer_hits.get("p1_positive_control.tsx")),
        },
    }
    io.open(OUT, "w",
            encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
    for k, v in census.items():
        print("%-38s %4d" % (k, v["count"]))
    print("files_in_tree=%d positive_control_fired=%s" % (len(files), out["killer_harness"]["positive_control_fired"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
