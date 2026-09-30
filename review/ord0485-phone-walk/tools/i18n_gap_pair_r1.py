"""ORD-0485 -- measure the key gap TWICE, once per generation, into two different files.

The delivered sheet first claimed "exactly 0 keys missing" about the tip generation, because the
instrument that measured the tip and the instrument that measured the candidate both wrote to
one fixed path and the later run ate the earlier one.  This runner keeps the two readings apart
by name, and asserts they actually differ.

Nothing here rebuilds a bundle: the tree is swapped for the measurement and swapped back to the
candidate bytes, and the swap-back is proved by sha256 against the worktree copy that was built
into the candidate bundle.
"""
import hashlib
import json
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
SRC_FILE = LANE + "/export/frontend/src/i18n/LocaleContext.tsx"
WT_FILE = LANE + "/wt/frontend/src/i18n/LocaleContext.tsx"
BASE = "dcb90cccc68b81f2317b28db19051dedb9f06c80"
CAND = "80608938c52e92a23dcbed79f74e25a08f5736ff"
REPO = r"D:/moodle/CityNexus"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TOOL = LANE + "/tools/i18n_key_gap_r2.py"
EV = LANE + "/evidence"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def git_show(rev, rel):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, rel)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit("ABORT_GIT_SHOW %s:%s" % (rev, rel))
    return p.stdout


def run_gap(label, out):
    env = dict(os.environ, CNX_GAP_LABEL=label, CNX_GAP_OUT=out, HTTP_PROXY="", HTTPS_PROXY="")
    p = subprocess.run([PY, "-X", "utf8", TOOL], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise SystemExit("ABORT_GAP %s %s" % (label, p.stdout.decode("utf-8", "replace")[:400]))
    return json.load(open(out, encoding="utf-8"))


def main():
    cand_bytes = open(WT_FILE, "rb").read()
    base_bytes = git_show(BASE, "frontend/src/i18n/LocaleContext.tsx")
    before_sha = sha(SRC_FILE)

    open(SRC_FILE, "wb").write(base_bytes)
    gap_base = run_gap("BASE_" + BASE[:8], EV + "/i18n_gap_base_gen_r1.json")

    open(SRC_FILE, "wb").write(cand_bytes)
    gap_cand = run_gap("CANDIDATE_" + CAND[:8], EV + "/i18n_gap_candidate_gen_r1.json")

    restored_sha = sha(SRC_FILE)
    pair = {
        "tool": "i18n_gap_pair_r1",
        "base_generation": {k: gap_base[k] for k in
                            ("dictionary_sha256_over_bytes", "keys_in_en", "keys_in_zhCN",
                             "referenced_key_count", "referenced_keys_missing_from_both")},
        "base_missing_from_both": gap_base["missing_from_both"],
        "candidate_generation": {k: gap_cand[k] for k in
                                 ("dictionary_sha256_over_bytes", "keys_in_en", "keys_in_zhCN",
                                  "referenced_key_count", "referenced_keys_missing_from_both")},
        "candidate_missing_from_both": gap_cand["missing_from_both"],
        "the_two_dictionaries_are_different_bytes":
            gap_base["dictionary_sha256_over_bytes"] != gap_cand["dictionary_sha256_over_bytes"],
        "export_restored_to_the_built_candidate_bytes": restored_sha == sha(WT_FILE),
        "export_sha_before_and_after_this_tool": {"before": before_sha, "after": restored_sha},
    }
    with open(EV + "/i18n_gap_pair_r1.json", "w", encoding="utf-8") as f:
        json.dump(pair, f, indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(pair, indent=2, ensure_ascii=False))
    ok = (pair["the_two_dictionaries_are_different_bytes"]
          and pair["export_restored_to_the_built_candidate_bytes"]
          and gap_base["referenced_keys_missing_from_both"] >= 1
          and gap_cand["referenced_keys_missing_from_both"] == 0)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
