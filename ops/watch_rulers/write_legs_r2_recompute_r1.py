"""r2 of the write-leg denominator: my corrected network-only counts, the erratum for what I published,
and the phone-reach measurement recomputed on the corrected file set.

Everything is recomputed at build time from files on disk plus one bundle fetch from each surface.
It supersedes nothing by overwriting: the earlier blobs are named and left in place.
"""
import base64
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
AUTH_FILE = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
ORIGIN, PROXY = "http://127.0.0.1:4781", "http://127.0.0.1:4782"
SRC = {"old_tip": ("30a5f90e5deaed6e45a704ddcc7d6e5e9790475b",
                   r"D:/moodle/_qoder_cmdr_ref_20260921/snap_tip_30a5f90e/frontend/src",
                   "_cmdr_write_legs_30a5f90e_r2.json"),
       "current_tip": ("2344145ce6342b6ac32ac4d0955c0f524d8c9320",
                       r"D:/moodle/_qoder_cmdr_ref_20260921/snap_tip_2344145/frontend/src",
                       "_cmdr_write_legs_2344145_r2.json")}
PREV_CLAIMS = {"published_20_22_and_20_45": "my legs were 16 with covered 2 and bare 14, union with lane F = 20",
               "superseded_by_this_file": True,
               "what_was_wrong": "4 of those 16 were device-state writes, not network writes: "
                                 "lib/inFlightWrites.ts:57 quietListeners.delete(fn) (a Set unsubscribe), "
                                 "lib/offlineJourney.ts:43 and :55 database.journeys.put(x) (IndexedDB), "
                                 "main.tsx:1706 caches.delete(name) (the Service Worker cache API). "
                                 "I read all four lines before accepting that - lane F's instrument disputed "
                                 "my denominator and was right."}
LIT_RE = None


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, via_proxy=False):
    req = urllib.request.Request(url, headers={"User-Agent": "cnx-cmdr-reach-r2"})
    if via_proxy:
        raw = io.open(AUTH_FILE, encoding="utf-8").read().rstrip("\r\n")
        parts = [p for p in re.split(r"[\t]", raw) if p.strip()]
        assert len(parts) == 2, "auth file shape changed - refusing to guess the separator"
        req.add_header("Authorization", "Basic " + base64.b64encode(
            ("%s:%s" % (parts[0], parts[1])).encode()).decode())
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    # the r1 numbers are read out of the r1 receipt I already published, not retyped from memory
    r1 = json.loads(io.open("_cmdr_leg_reconciliation_2022.json", encoding="utf-8").read())
    R1 = {"r1_artifact_blob": "1731358d86e71215aa6757a07ec14b3dfec14c45",
          "my_legs_total_r1": r1["instrument_mine"]["legs_total"],
          "my_covered_r1": (r1["instrument_mine"].get("legs_covered_by_any_of_the_three") or r1["instrument_mine"]["covered"]),
          "union_with_lane_F_r1": r1["set_comparison"]["union_sites"],
          "lane_F_legs_r1": r1["instrument_hers"]["legs_total"],
          "lane_F_covered_r1": r1["instrument_hers"]["legs_covered"]}
    scans = {}
    for label, (tip, export, jf) in SRC.items():
        d = json.loads(io.open(jf, encoding="utf-8").read())
        scans[label] = {"tip": tip, "files_scanned": d["files_scanned"], "legs_total": d["legs_total"],
                        "legs_by_method": d["legs_by_method"],
                        "covered": d["legs_covered_by_any_of_the_three"],
                        "bare": d["legs_total"] - d["legs_covered_by_any_of_the_three"],
                        "bare_sites": d["bare_sites"],
                        "local_state_writes_excluded": d["local_state_writes_excluded"],
                        "local_state_writes_count": d["local_state_writes_count"],
                        "instrument_r1_numbers_kept_for_the_record": R1}

    # reach, recomputed on the current tip's bare set
    _, export, _ = SRC["current_tip"]
    files = sorted({b["file"] for b in scans["current_tip"]["bare_sites"]})
    all_txt = {}
    for root_dir, dirnames, filenames in os.walk(export):
        for fn in filenames:
            if fn.endswith((".ts", ".tsx")) and ".test." not in fn:
                rel = os.path.relpath(os.path.join(root_dir, fn), export).replace("\\", "/")
                all_txt[rel] = io.open(os.path.join(root_dir, fn), encoding="utf-8", errors="replace").read()
    q = ['"', "'", chr(96)]
    nl = chr(10)
    lit_re = re.compile("|".join("%s([^%s%s]{6,})%s" % (re.escape(x), re.escape(x), re.escape(nl), re.escape(x))
                                 for x in q))
    counts = {}
    for rel, t in all_txt.items():
        for lit in {x for tup in lit_re.findall(t) for x in tup if x}:
            counts[lit] = counts.get(lit, 0) + 1
    markers = {}
    for rel in files:
        cand = []
        for lit in [x for tup in lit_re.findall(all_txt.get(rel, "")) for x in tup if x]:
            if len(lit) >= 6 and counts.get(lit, 0) == 1 and lit not in cand:
                cand.append(lit)
        markers[rel] = cand[:6]

    index_html = fetch(ORIGIN + "/index.html")
    asset = re.search(rb"/(assets/index-[A-Za-z0-9_-]+\.js)", index_html).group(1).decode()
    b_o = fetch(ORIGIN + "/" + asset)
    b_p = fetch(PROXY + "/" + asset, via_proxy=True)
    text = b_o.decode("utf-8", "replace")
    reach = {}
    for rel in files:
        hits = [l for l in markers[rel] if l in text]
        reach[rel] = {"markers": markers[rel], "hits": hits,
                      "verdict": ("PRESENT_in_shipped_bundle" if hits else
                                  ("marker_missed_NOT_proven_absent" if markers[rel] else "NOT_MEASURED_no_marker"))}
    present = [r for r in files if reach[r]["verdict"] == "PRESENT_in_shipped_bundle"]
    out = {
        "schema": "CNX_CMDR_WRITE_LEGS_R2_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "why": "lane F's ORD-0315 disputed my denominator; I read the four disputed lines and they were not "
               "network writes, so my published 16/20 numbers are superseded by this file",
        "scans": scans,
        "erratum_for_what_I_already_published": {
            "numbers_I_published": None, "superseded_by_this_file": True,
            "what_was_wrong": "4 of my 16 legs were device-state writes, not network writes: "
                "lib/inFlightWrites.ts:57 quietListeners.delete(fn) (a Set unsubscribe), "
                "lib/offlineJourney.ts:43 and :55 database.journeys.put(x) (IndexedDB), "
                "main.tsx:1706 caches.delete(name) (the Service Worker cache API). I read all four lines "
                "before accepting it - lane F disputed my denominator and was right.",
            "r1_numbers_as_recorded_in_the_r1_receipt": R1},
        "already_published_artifacts_this_supersedes": {
            "evidence/cmdr-write-legs-2022/write_leg_reconciliation_r1.json": "1731358d86e71215aa6757a07ec14b3dfec14c45",
            "evidence/cmdr-bare-leg-reach-2044/bare_leg_reach_r1.json": "30662a703940ef9dab8dce29d34437a1d4419155",
        },
        "reach_recomputed_on_the_corrected_set": {
            "entry_asset": asset, "origin_bytes": len(b_o), "proxy_bytes": len(b_p),
            "two_surfaces_byte_identical": sha(b_o) == sha(b_p) and len(b_o) == len(b_p),
            "origin_sha256": sha(b_o), "proxy_sha256": sha(b_p),
            "files_with_bare_legs": files, "per_file": reach,
            "files_present": present, "files_present_count": len(present),
            "note": "presence proves the module shipped; it does not prove a user can reach that press in the "
                    "current demo state, and a missed marker proves nothing about absence",
        },
        "agreement_with_lane_F": {
            "her_per_tip_artifact": "evidence/ord0315-write-leg-reconciliation-f/ord0315_leg_reconciliation_per_tip_r2.json",
            "her_blob": "e157a892ffc75cc048d8944d55d8201d3062dd9e",
            "her_sites_per_tip": 20, "my_network_only_legs_now": scans["current_tip"]["legs_total"],
            "why_the_two_still_differ": "her definition counts the wrapper form (fetchWithWriteDeadline) and "
                                        "request({method:<write>}); mine counts only fetch(...) with a literal "
                                        "write method plus a client verb call on a non-local receiver. Neither "
                                        "is wrong; hers is the wider one and carries an occurrence-indexed site "
                                        "key, so it is the list to quote - together with the tip it was taken on.",
        },
        "discipline": {"product_bytes_changed": 0, "refs_pushed": 0, "authoritative_branch_moved": 0,
                       "databases_opened": 0, "credential_values_printed": 0, "evidence_paths_overwritten": 0},
        "claim_kind": "code_and_deployment_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("network-only write legs: %d on %s (covered %d, bare %d) and %d on %s (covered %d, "
                             "bare %d); %d device-state writes excluded; of the bare files, %d carry a literal "
                             "in the shipped bundle" % (
                                 scans["old_tip"]["legs_total"], scans["old_tip"]["tip"][:8],
                                 scans["old_tip"]["covered"], scans["old_tip"]["bare"],
                                 scans["current_tip"]["legs_total"], scans["current_tip"]["tip"][:8],
                                 scans["current_tip"]["covered"], scans["current_tip"]["bare"],
                                 scans["current_tip"]["local_state_writes_count"], len(present)))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_write_legs_r2.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    print("excluded:", json.dumps(scans["current_tip"]["local_state_writes_excluded"], ensure_ascii=False)[:600])
    print("asset", asset, "identical", out["reach_recomputed_on_the_corrected_set"]["two_surfaces_byte_identical"])
    for r in files:
        print("   %-52s %s" % (r, reach[r]["verdict"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
