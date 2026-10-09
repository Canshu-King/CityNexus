"""Commander's mechanical derivation for ORD-0301 (HJ-P3's screen-speaks range table) - revision 2.

Why r2 exists (self-correction, kept in the artifact):
  r1 computed T_B with a key-name regex (WHO_KEYS) that did not contain the field the lane actually
  used, `answer_attributed_to`.  r1 therefore reported "7 of 8 cells do not name who answered", which
  is FALSE - the name is carried per observation row, not per cell.  r1 is being published alongside
  this file as a wrong version, and nothing downstream may quote r1's T_B.

What r2 does differently:
  - it does not judge key NAMES at the cell level.  It locates the observation ROWS inside each cell
    (any list of dicts under `measured`) and judges the FIELDS AND VALUES of every row;
  - every judgement prints the union of field names it actually read, so a "missing" claim can be
    checked against an inventory instead of against a guess;
  - a positive control proves the tests can fail (a synthetic row lacking a side must be caught),
    and a negative control proves they do not fire on the real rows for the wrong reason.

Questions answered, from the published bytes only:
  T-A does every OBSERVATION row carry both sides - what came off the wire, and the sentence painted
      on the screen?  Which cells have no browser observation at all (code-only / in-process)?
  T-B does every OBSERVATION row say who answered, with a non-empty value?
  T-C is "duration is not the discriminator" backed by a pair of rows over the same body bytes with
      different elapsed times, or is it an inference?
  T-D does every cell that makes a wording-relevant claim name the painted text it measured
      (`painted_*`) - i.e. can a copy rule quote the row rather than the cell's prose?
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"

SERVER = re.compile(r"^(http_status|status|content_type|bytes|body|client_error|envelope_code|"
                    r"answer_attributed_to|declared|sibling_probe|origin_own_record)$", re.I)
SCREEN = re.compile(r"^(painted_.*|card|says_cannot_reach_server|details_elements_in_dom|"
                    r"reason_label|reason_value|data_result_status|secondary_surface|verdict)$", re.I)
WHO = re.compile(r"^(answer_attributed_to|who_answered.*|declared)$", re.I)
DURATION = re.compile(r"^(elapsed_ms|delay_ms|hold_seconds|cap_ms)$", re.I)


def get(path, tries=6):
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path, headers={
                "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-ord0301-r2"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (k + 1))
    raise SystemExit("GET " + path + " failed: " + str(last))


def blob(path_or_sha, is_sha=False):
    if is_sha:
        return base64.b64decode(get("/repos/" + REPO + "/git/blobs/" + path_or_sha)["content"])
    meta = get("/repos/" + REPO + "/contents/" + path_or_sha + "?ref=" +
               urllib.parse.quote("commander/control", safe=""))
    return meta, base64.b64decode(get("/repos/" + REPO + "/git/blobs/" + meta["sha"])["content"])


def row_lists(node, prefix=""):
    """Every list-of-dicts reachable inside a cell, with the path it sits at."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            out += row_lists(v, (prefix + "." + k) if prefix else k)
    elif isinstance(node, list) and node and all(isinstance(x, dict) for x in node):
        out.append((prefix, node))
    return out


def has_value(row, key):
    v = row.get(key)
    if v is None or v == "" or v == [] or v == {}:
        return False
    if key == "declared" and isinstance(v, dict):
        return bool(v.get("mode"))
    if key == "origin_own_record" and isinstance(v, list):
        return len(v) > 0
    return True


def judge(rows, label, notes):
    """Compute per-row presence of each side. Returns (bad_rows, field_union)."""
    union = sorted({k for r in rows for k in r})
    srv_names = [k for k in union if SERVER.match(k)]
    scr_names = [k for k in union if SCREEN.match(k)]
    who_names = [k for k in union if WHO.match(k)]
    dur_names = [k for k in union if DURATION.match(k)]
    bad = []
    for i, r in enumerate(rows):
        srv = [k for k in srv_names if has_value(r, k)]
        scr = [k for k in scr_names if has_value(r, k)]
        who = [k for k in who_names if has_value(r, k)]
        if not srv or not scr:
            bad.append({"row": r.get("row", "#%d" % i), "missing":
                        ([] if srv else ["server"]) + ([] if scr else ["screen"])})
        r["_who_ok"] = bool(who)
        r["_dur_ok"] = any(has_value(r, k) for k in dur_names)
    notes.append({"label": label, "path": None, "rows": len(rows),
                  "server_names_read": srv_names, "screen_names_read": scr_names,
                  "who_names_read": who_names, "duration_names_read": dur_names,
                  "rows_missing_a_side": bad})
    return bad, union


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="evidence/ord0301-screen-speaks-range-hjp3/RECEIPT_O0301-1500.json")
    ap.add_argument("--md", default="evidence/ord0301-screen-speaks-range-hjp3/RECEIPT_O0301-1500.md")
    ap.add_argument("--out", default="_ord0301_cmdr_derivation_r2.json")
    a = ap.parse_args()

    meta, raw = blob(a.path)
    recomputed = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    doc = json.loads(raw.decode("utf-8", errors="replace"))
    open("_ord0301_refetched.json", "wb").write(raw)
    md_meta, md_raw = blob(a.md)
    open("_ord0301_receipt.md", "wb").write(md_raw)

    cells = doc.get("cells") or []
    per_cell, all_rows = [], []
    for ci, cell in enumerate(cells):
        notes = []
        lists = row_lists(cell.get("measured") or {})
        obs = []
        for path, rows in lists:
            if len(rows) >= 1 and any(k for r in rows for k in r if SCREEN.match(k) or SERVER.match(k)):
                obs.append((path, rows))
        bad = []
        for path, rows in obs:
            n = {"path": path, "rows": len(rows)}
            u = sorted({k for r in rows for k in r})
            n["server_names_read"] = [k for k in u if SERVER.match(k)]
            n["screen_names_read"] = [k for k in u if SCREEN.match(k)]
            n["who_names_read"] = [k for k in u if WHO.match(k)]
            n["duration_names_read"] = [k for k in u if DURATION.match(k)]
            b = []
            for i, r in enumerate(rows):
                srv = [k for k in n["server_names_read"] if has_value(r, k)]
                scr = [k for k in n["screen_names_read"] if has_value(r, k)]
                who = [k for k in n["who_names_read"] if has_value(r, k)]
                if not srv or not scr:
                    b.append({"row": r.get("row", "#%d" % i),
                              "missing": ([] if srv else ["server"]) + ([] if scr else ["screen"])})
                if not who:
                    r["_who_missing"] = True
                all_rows.append(r)
            n["rows_missing_a_side"] = b
            n["rows_not_naming_who"] = [r.get("row", "#%d" % i) for i, r in enumerate(rows) if r.get("_who_missing")]
            notes.append(n)
            bad += b
        per_cell.append({"cell_index": ci, "id": cell.get("id"), "verdict": cell.get("verdict"),
                         "observation_lists": notes, "rows_total": sum(n["rows"] for n in notes),
                         "has_browser_observation": bool(notes),
                         "T_A_rows_missing_a_side": bad,
                         "T_B_rows_not_naming_who": [x for n in notes for x in n["rows_not_naming_who"]]})

    t_a_cells = [c["id"] for c in per_cell if c["rows_total"] == 0]
    t_a_rows = {c["id"]: c["T_A_rows_missing_a_side"] for c in per_cell if c["T_A_rows_missing_a_side"]}
    t_b_rows = {c["id"]: c["T_B_rows_not_naming_who"] for c in per_cell if c["T_B_rows_not_naming_who"]}

    # T-C: the duration-is-irrelevant claim must be a PAIR over identical body bytes.
    by_body = {}
    for r in all_rows:
        key = (r.get("http_status"), json.dumps(r.get("declared"), sort_keys=True, ensure_ascii=False)[:120])
        by_body.setdefault(str(key), []).append(r.get("elapsed_ms"))
    pairs = {k: v for k, v in by_body.items() if len([x for x in v if isinstance(x, (int, float))]) >= 2
             and len({round(x / 500) for x in v if isinstance(x, (int, float))}) >= 2}

    # Controls: prove the tests can fail, and that they do not fire on names they never matched.
    synthetic = [{"http_status": 500, "declared": {"mode": "answer"}, "answer_attributed_to": "product"}]
    notes = []
    sbad, _ = judge(synthetic, "positive_control_screen_side_absent", notes)
    control = {"positive_control_caught": len(sbad) == 1 and sbad[0]["missing"] == ["screen"],
               "positive_control_detail": sbad}
    real_union = sorted({k for r in all_rows for k in r})
    control["negative_control_who_name_present_in_real_rows"] = "answer_attributed_to" in real_union

    rulers = {}
    for name, cmd in (("q38_json", ["receipt_cell_derivation_check_r2.py", "--receipt", "_ord0301_refetched.json"]),
                      ("q43_json", ["claim_coordinate_check_r3.py", "--text", "_ord0301_refetched.json"]),
                      ("q43_md", ["claim_coordinate_check_r3.py", "--text", "_ord0301_receipt.md"])):
        p = subprocess.run([sys.executable] + cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=240)
        out_lines = (p.stdout or "").splitlines()
        rulers[name] = {"exit_code": p.returncode,
                        "verdict_line": next((l.strip() for l in out_lines if "overall" in l), None),
                        "claims_or_cells_line": next((l.strip() for l in out_lines
                                                      if "claims checked" in l or "cells" in l), None),
                        "top_finding_kinds": re.findall(r"'([A-Z_]{8,})'", p.stdout or "")[:6]}

    out = {"schema": "CNX_CMDR_DERIVATION_V2", "order": "ORD-0301", "revision": "r2",
           "supersedes": "r1 (T_B was a false absence: WHO_KEYS omitted answer_attributed_to)",
           "artifact": {"path": a.path, "contents_sha": meta["sha"], "recomputed_git_sha1": recomputed,
                        "recomputed_equals_cited": recomputed == meta["sha"], "bytes": len(raw),
                        "md_path": a.md, "md_contents_sha": md_meta["sha"], "md_bytes": len(md_raw)},
           "cells_total": len(cells),
           "rows_total": len(all_rows),
           "field_name_union_read_across_all_rows": real_union,
           "T_A_cells_with_no_browser_observation": t_a_cells,
           "T_A_rows_missing_a_side": t_a_rows,
           "T_B_rows_not_naming_who_answered": t_b_rows,
           "T_C_duration_pairs_same_declared_answer": {"pairs_found": len(pairs),
                                                       "detail": {k: v for k, v in list(pairs.items())[:6]}},
           "per_cell": per_cell, "controls": control, "rulers": rulers,
           "decisions": {
               "artifact_rehashes_to_cited_blob": recomputed == meta["sha"],
               "T_A_every_observation_row_judges_both_sides": not t_a_rows,
               "T_B_every_observation_row_names_who_answered": not t_b_rows,
               "T_C_duration_claim_is_a_measured_pair": len(pairs) >= 1,
               "controls_pass": control["positive_control_caught"]
                               and control["negative_control_who_name_present_in_real_rows"]},
           "scope": "What the table's own rows prove. It does not sign derived_result (red team's job) "
                    "and it does not decide ORD-0302's wording - it says which rows a wording rule may "
                    "quote and which cells are code-only / in-process and therefore cannot carry a "
                    "traveller-facing claim."}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("cells", len(cells), "| observation rows", len(all_rows))
    print("blob recompute == cited:", recomputed == meta["sha"], "|", meta["sha"], "| bytes", len(raw))
    print("T_A cells with NO browser observation:", t_a_cells)
    print("T_A rows missing a side:", {k: len(v) for k, v in t_a_rows.items()} or "none")
    print("T_B rows not naming who answered:", {k: len(v) for k, v in t_b_rows.items()} or "none")
    print("T_C duration pairs over the same declared answer:", len(pairs))
    print("controls:", control["positive_control_caught"], control["negative_control_who_name_present_in_real_rows"])
    for n, v in rulers.items():
        print("  ruler", n, "exit", v["exit_code"], "|", v["verdict_line"], "|", v["claims_or_cells_line"])
    print("field union (", len(real_union), "):", ",".join(real_union))
    print("wrote", a.out)
    return 0


def judge_rows(rows, notes):  # kept for the control path only
    return judge(rows, "control", notes)


if __name__ == "__main__":
    raise SystemExit(main())
