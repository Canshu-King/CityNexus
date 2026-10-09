"""Commander's mechanical derivation for ORD-0301 (HJ-P3's screen-speaks range table).

Why: I relayed this table to lane B as the basis for ORD-0302's wording criteria.  Relaying a lane's
conclusion is not evidence, so this script answers three questions from the published bytes only:

  T-A does every row carry BOTH sides - what the server actually returned, and the sentence painted on
      the screen - and is the screen side the RENDERED text (not just an attribute)?
  T-B does each row say WHO answered - the application or the vite proxy?  This is the criterion that the
      dead backend taught me today: an empty-body proxy failure and an application failure can look
      identical by status code alone.  A row that cannot say who answered cannot support a wording rule.
  T-C is the claim "duration is irrelevant" actually tested?  It must appear as a pair of rows over the
      same body bytes with different elapsed times, otherwise it is an inference.

Nothing is typed as a verdict: each judgement is computed over the fetched rows.
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"
SERVER_KEYS = re.compile(r"http_status|status_code|content_type|bytes|elapsed|body|envelope|error_code|reason_code", re.I)
SCREEN_KEYS = re.compile(r"painted|card|screen|rendered|visible|inner_?text|title|body_text|details|dom", re.I)
WHO_KEYS = re.compile(r"who_answered|answered_by|answer_source|origin|proxy|app_answered|server_answered", re.I)


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-ord0301"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            err = sys.exc_info()[1]
            time.sleep(2 * (k + 1))
    raise SystemExit("GET " + path + " failed: " + str(err))


def leaves(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += leaves(v, (prefix + "." + k) if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += leaves(v, prefix + "[" + str(i) + "]")
    else:
        out.append((prefix, obj))
    return out


def find_rows(doc):
    """Take the first list of dicts that looks like the range table, whichever key it sits under."""
    best = None
    for k, v in doc.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            if best is None or len(v) > len(best[1]):
                best = (k, v)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="evidence/ord0301-screen-speaks-range-hjp3/RECEIPT_O0301-1500.json")
    ap.add_argument("--ref", default="commander/control")
    ap.add_argument("--out", default="_ord0301_commander_derivation_r1.json")
    a = ap.parse_args()

    meta = get("/repos/" + REPO + "/contents/" + a.path + "?ref=" + urllib_ref(a.ref))
    raw = base64.b64decode(get("/repos/" + REPO + "/git/blobs/" + meta["sha"])["content"])
    recomputed = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    doc = json.loads(raw.decode("utf-8", errors="replace"))

    key, rows = find_rows(doc) or (None, [])
    per = []
    for r in rows:
        names = [p for p, _ in leaves(r)]
        tail = [p.rsplit(".", 1)[-1] for p in names]
        srv = [p for p, t in zip(names, tail) if SERVER_KEYS.search(t)]
        scr = [p for p, t in zip(names, tail) if SCREEN_KEYS.search(t)]
        who = [p for p, t in zip(names, tail) if WHO_KEYS.search(t)]
        per.append({"row_index": len(per),
                    "keys": sorted(set(t.split(".")[0] for t in names))[:12],
                    "server_field_count": len(srv), "screen_field_count": len(scr), "who_answered_fields": who,
                    "T_A_both_sides": bool(srv) and bool(scr),
                    "T_B_names_who_answered": bool(who)})

    t_a = [i for i, x in enumerate(per) if not x["T_A_both_sides"]]
    t_b = [i for i, x in enumerate(per) if not x["T_B_names_who_answered"]]
    duration_rows = [i for i, x in enumerate(rows) if "duration" in json.dumps(x, ensure_ascii=False).lower()
                     or "elapsed" in json.dumps(x, ensure_ascii=False).lower()]
    t_c = len(duration_rows) >= 2

    open("_ord0301_refetched.json", "wb").write(raw)
    rulers = {}
    for name, cmd in (("q38", ["receipt_cell_derivation_check_r2.py", "--receipt", "_ord0301_refetched.json"]),
                      ("q43", ["claim_coordinate_check_r3.py", "--text", "_ord0301_refetched.json"])):
        p = subprocess.run([sys.executable] + cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=240)
        rulers[name] = {"exit_code": p.returncode,
                        "verdict_line": next((l.strip() for l in (p.stdout or "").splitlines()
                                              if "overall" in l), None)}

    out = {"schema": "CNX_CMDR_DERIVATION_V2", "order": "ORD-0301", "lane": doc.get("lane"),
           "artifact": {"path": a.path, "contents_sha": meta["sha"], "recomputed_git_sha1": recomputed,
                        "recomputed_equals_cited": recomputed == meta["sha"], "bytes": len(raw)},
           "rows_under_key": key, "rows_total": len(per),
           "T_A_rows_missing_a_side": t_a, "T_B_rows_not_naming_who_answered": t_b,
           "T_C_duration_tested_as_a_pair": t_c,
           "per_row": per,
           "rulers": rulers,
           "decisions": {
               "artifact_exists_at_that_exact_path_and_rehashes": recomputed == meta["sha"],
               "table_rows_found": len(per) > 0,
               "T_A_every_row_judges_both_sides": len(t_a) == 0,
               "T_B_every_row_says_who_answered": len(t_b) == 0,
               "T_C_duration_claim_has_a_pair": t_c},
           "scope": "What the table proves about its own rows. It does not sign derived_result (red "
                    "team's), and it does not decide ORD-0302's wording - it only says which rows can "
                    "support a wording rule and which cannot."}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("rows under", key, "=", len(per), "| T_A missing", t_a, "| T_B missing", t_b, "| T_C pair", t_c)
    print("blob recompute ok:", recomputed == meta["sha"], "| bytes", len(raw))
    for n, v in rulers.items():
        print("  ruler", n, v["exit_code"], v["verdict_line"])
    print("wrote", a.out)
    return 0


def urllib_ref(x):
    import urllib.parse
    return urllib.parse.quote(x, safe="")


if __name__ == "__main__":
    raise SystemExit(main())
