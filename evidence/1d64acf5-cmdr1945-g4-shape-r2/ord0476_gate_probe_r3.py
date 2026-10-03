# -*- coding: utf-8 -*-
"""CMDR 01:24 裁① on one gate, re-measured on the day25 tip: the read door's response set becomes 包含式 + 具名扩容白名单, five states measured.

Only `backend/tests/test_qoder_ord0476_checkins.py:500` changes. The other five drift-prone sites named by
the census keep their equality form, and this script checks that rather than assuming it.

States, each reverted and re-hashed:
  K0 control            - contract as shipped, whitelist empty. Green.
  K1 unnamed add        - a legitimate `429` documented on the door, not named. Red, and by the unnamed-add
                          line, not by a set-size complaint.
  K2 named add          - the same `429` plus its name in the whitelist. Green: the mechanism admits growth.
  K3 promise dropped    - the documented `409` removed. Red on the promised-gone line.
  K4 stale whitelist    - a code named in the whitelist that the contract does not document. Red - so the
                          whitelist cannot quietly rot into a list of intentions.
  K5 whole file         - the rest of this test file runs green, so nothing else in the arm moved.
"""
import hashlib
import io
import json
import os
import re
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
BACKEND = os.path.join(WT, "backend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
TEST = "backend/tests/test_qoder_ord0476_checkins.py"
YAML = "contracts/openapi.yaml"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", NO_PROXY="*")
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(_k, None)

OLD = ('    assert sorted(listed["responses"]) == ["200", "409"], sorted(listed["responses"])')
NEW = '''    # CMDR 01:24 裁①, applied to this one gate: the read door owes `200` and `409` by name, and any other
    # code documented here must be named in `named_expansion_get` by the very order that documents it. An
    # unnamed add is still red, a promised code that disappeared is red on its own line, and a code that is
    # named but never documented is red too, so the whitelist cannot rot into a list of intentions.
    promised_get = {"200", "409"}
    named_expansion_get: set[str] = set()  # empty as shipped: nothing else is promised on this door
    seen_get = set(listed["responses"])
    assert promised_get <= seen_get, ("a response ORD-0476 promised is gone from the read door",
                                      sorted(promised_get - seen_get), listed["responses"])
    assert seen_get - promised_get <= named_expansion_get, (
        "the read door documents a code this arm was never told about - name it in "
        "named_expansion_get in the same order that documents it",
        sorted(seen_get - promised_get - named_expansion_get))
    assert named_expansion_get <= seen_get, ("a code is whitelisted but not documented",
                                             sorted(named_expansion_get - seen_get))'''
EMPTY_SET = '    named_expansion_get: set[str] = set()  # empty as shipped: nothing else is promised on this door'
NAMED_429 = '    named_expansion_get = {"429"}'
OTHER_FIVE = [("backend/tests/test_qoder_ord0402_recycle_bin.py", 305),
              ("backend/tests/test_qoder_ord0434_share_grants.py", 413),
              ("backend/tests/test_qoder_ord0444_collections.py", 481),
              ("backend/tests/test_qoder_ord0476_checkins.py", 499),
              ("backend/tests/test_qoder_ord0496_calendar_export.py", 944)]


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return r.returncode, (r.stdout or "").strip()


def blob_of(rev, path):
    return git("rev-parse", "%s:%s" % (rev, path))[1]


def local_blob(rel):
    return git("hash-object", os.path.join(WT, rel.replace("/", os.sep)))[1]


def write(rel, text):
    io.open(os.path.join(WT, rel.replace("/", os.sep)), "w", encoding="utf-8", newline="\n").write(text)


def read(rel):
    return io.open(os.path.join(WT, rel.replace("/", os.sep)), encoding="utf-8").read()


def run(args):
    r = subprocess.run([PY, "-m", "pytest"] + args + ["-p", "no:cacheprovider", "-q", "--tb=long"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    fired = [l.strip() for l in out.splitlines() if re.search(r"test_qoder_ord0476\S*:\d+: AssertionError", l)]
    return {"rc": r.returncode, "verdict": "green" if r.returncode == 0 else "red",
            "summary": (tail[-1] if tail else "")[:150], "bitting_line": (fired[0][:170] if fired else None)}


def mutate_yaml(add_429=False, drop_409=False):
    lines = read(YAML).split("\n")
    path_at = next(i for i, l in enumerate(lines) if l.strip() == "/journeys/{journey_id}/checkins:")
    post_at = next(i for i in range(path_at, len(lines)) if lines[i] == "    post:")
    if drop_409:
        start = next(i for i in range(path_at, post_at) if lines[i] == "        '409':")
        return "\n".join(lines[:start] + lines[post_at:])
    if add_429:
        add = ["        '429':", "          description: >-",
               "            Too many stamp reads from one traveller in a minute: a service limit on this "
               "door,", "            not a refusal of the trip", "          content:",
               "            application/json:",
               "              schema: {$ref: '#/components/schemas/ErrorEnvelope'}"]
        return "\n".join(lines[:post_at] + add + lines[post_at:])
    return None


def main():
    git("checkout", "--detach", TIP)
    tip_test = blob_of(TIP, TEST)
    tip_yaml = blob_of(TIP, YAML)
    src = read(TEST)  # the detached checkout put this file back at the tip's bytes; git() would strip them
    assert local_blob(TEST) == tip_test, "the checkout is not the tip's bytes for this file"
    assert src.count(OLD) == 1, "the arm line is not unique on this tip"
    final = src.replace(OLD, NEW)
    import ast
    ast.parse(final)
    write(TEST, final)
    final_blob = local_blob(TEST)

    yaml_orig = read(YAML)
    rows = []

    def case(pid, expect, why, yaml_change=None, test_variant=None):
        if test_variant:
            write(TEST, final.replace(EMPTY_SET, test_variant))
        if yaml_change:
            write(YAML, mutate_yaml(**yaml_change))
        res = run(["tests/test_qoder_ord0476_checkins.py::"
                   "test_the_contract_declares_both_doors_and_no_control_they_lack"])
        rows.append({"id": pid, "expect": expect, "got": res["verdict"], "met": res["verdict"] == expect,
                     "why": why, "pytest": res})
        print(json.dumps({"id": pid, "got": res["verdict"], "met": rows[-1]["met"],
                          "bitting_line": res["bitting_line"], "summary": res["summary"]},
                         ensure_ascii=False))
        write(TEST, final)
        write(YAML, yaml_orig)
        rows[-1]["test_restored_equal"] = local_blob(TEST) == final_blob
        rows[-1]["yaml_restored_equal"] = local_blob(YAML) == tip_yaml

    case("K0_control", "green", "contract as shipped, whitelist empty")
    case("K1_unnamed_add", "red", "a legitimate 429 documented but not named",
         yaml_change={"add_429": True})
    case("K2_named_add", "green", "the same 429 plus its name in the whitelist",
         yaml_change={"add_429": True}, test_variant=NAMED_429)
    case("K3_promise_dropped", "red", "the documented 409 removed from the door",
         yaml_change={"drop_409": True})
    case("K4_stale_whitelist", "red", "a code named in the whitelist but not documented",
         test_variant=NAMED_429)
    whole = run(["tests/test_qoder_ord0476_checkins.py"])
    rows.append({"id": "K5_whole_file", "expect": "green", "got": whole["verdict"],
                 "met": whole["verdict"] == "green", "why": "the rest of this file", "pytest": whole})
    print(json.dumps({"id": "K5_whole_file", "got": whole["verdict"], "summary": whole["summary"]},
                     ensure_ascii=False))

    untouched = []
    for f, n in OTHER_FIVE:
        local_line = read(f).split("\n")[n - 1]
        tip_line = (git("show", "%s:%s" % (TIP, f))[1].split("\n") + [""] * 10 ** 4)[n - 1]
        untouched.append({"site": "%s:%s" % (f, n),
                          "still_equality_form": "== [" in local_line,
                          "line": local_line.strip()[:120],
                          "line_identical_to_tip": local_line.strip() == tip_line.strip(),
                          "file_untouched": local_blob(f) == blob_of(TIP, f)})
    doc = {"tip": TIP, "arm": TEST, "tip_test_blob": tip_test, "final_test_blob": final_blob,
           "yaml_tip_blob": tip_yaml, "yaml_untouched": local_blob(YAML) == tip_yaml,
           "states": len(rows), "all_met": all(r["met"] for r in rows),
           "all_reverted": all(r.get("test_restored_equal", True) and r.get("yaml_restored_equal", True)
                               for r in rows),
           "runs": rows, "other_five_sites_untouched": untouched,
           "replacement_text": NEW}
    io.open(os.path.join(HERE, "ord0476_gate_probe_r3.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"all_met": doc["all_met"], "all_reverted": doc["all_reverted"],
                      "yaml_untouched": doc["yaml_untouched"], "final_blob": final_blob,
                      "other_five_lines_still_equality_and_identical": all(
                          u["still_equality_form"] and u["line_identical_to_tip"] for u in untouched),
                      "other_files_byte_untouched": sum(1 for u in untouched if u["file_untouched"])},
                     ensure_ascii=False))
    return 0 if (doc["all_met"] and doc["all_reverted"] and doc["yaml_untouched"]) else 7


raise SystemExit(main())
