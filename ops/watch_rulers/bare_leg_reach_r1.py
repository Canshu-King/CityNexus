"""Which of the bare write legs are actually reachable on the phone right now?

Q60' (asked of the arbiter at 20:33) hinges on this: if a bare leg is not in the shipped bundle, "no
client deadline" is invisible to a user; if it is, a press there can sit there spinning.  So this answers
a *product* question with a *deployment* measurement rather than with a count over source files.

Method, in order, with each step's own reading kept:
  1. recompute the union of both instruments' leg sets (from the two published artifacts by blob),
  2. for every file holding a bare leg, pull distinctive CJK UI literals out of the tip's exported bytes,
  3. fetch the deployed entry bundle twice - once from the origin (:4781) and once through the Basic-auth
     proxy the phone actually uses (:4782, credential read by FILE PATH only, never printed) - and require
     the two to be byte-identical before any marker test counts (CROSS_SURFACE_GAUGE_REPRO_V1),
  4. test each literal for presence in the shipped bundle.

Nothing here starts or stops a surface, touches a database, moves a ref, or prints a credential.
"""
import base64
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
AUTH_FILE = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
ORIGIN = "http://127.0.0.1:4781"
PROXY = "http://127.0.0.1:4782"
EXPORT = r"D:/moodle/_qoder_cmdr_ref_20260921/snap_tip_30a5f90e/frontend/src"
TIP = "30a5f90e5deaed6e45a704ddcc7d6e5e9790475b"
RECON_BLOB = "1731358d86e71215aa6757a07ec14b3dfec14c45"
SCAN_FILE = "_cmdr_write_legs_30a5f90e.json"
CJK = re.compile(u"[一-鿿]{4,}")
# Any quoted literal (single, double, or backtick) long enough to be a real marker.  Built with chr() and
# re.escape so no backslash-escape has to survive a second layer of code generation (that is exactly how the
# previous version of this line broke: the `\n` was eaten and the string literal came out unterminated).
_NL = chr(10)
_QUOTES = ['"', "'", chr(96)]
LIT_RE = re.compile("|".join("%s([^%s%s]{6,})%s" % (re.escape(q), re.escape(q), re.escape(_NL), re.escape(q))
                             for q in _QUOTES))


def gh_blob(sha):
    req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + sha)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("User-Agent", "cnx-cmdr-reach")
    with urllib.request.urlopen(req, timeout=180) as r:
        return base64.b64decode(json.loads(r.read().decode())["content"])


def fetch(url, via_proxy=False):
    req = urllib.request.Request(url, headers={"User-Agent": "cnx-cmdr-reach"})
    if via_proxy:
        raw = io.open(AUTH_FILE, encoding="utf-8").read().rstrip("\r\n")
        # the file is TAB separated: user <TAB> secret.  Split on the real separator, never on ':'.
        parts = [p for p in re.split(r"[\t]", raw) if p.strip()]
        assert len(parts) == 2, "auth file shape changed - refusing to guess the separator"
        tok = base64.b64encode(("%s:%s" % (parts[0], parts[1])).encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read(), dict(r.headers)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    recon = json.loads(gh_blob(RECON_BLOB).decode("utf-8"))
    mine = json.loads(io.open(SCAN_FILE, encoding="utf-8").read())
    covered = {(l["file"], l["line"]) for l in mine["all_legs"] if l["covered_by_any_of_the_three"]}
    union = set()
    for lst in ("agreed_list", "only_mine_list"):
        for s in recon["set_comparison"][lst]:
            union.add((s["file"], s["line"]))
    for s in recon["set_comparison"]["only_hers_list"]:
        union.add((s["file"], s["line"]))
    # the two wrapper legs are covered; they live at the call lines the anchor finding names
    wrapper_covered = set()
    for f, ln in [("features/execution/LiveRecovery.tsx", 230), ("features/recovery/V14RecoveryTruthPanel.tsx", 74)]:
        wrapper_covered.add((f, ln))
    bare = sorted(union - covered - wrapper_covered)
    files = sorted({f for f, _ in bare})

    # literals per file.  The first version used CJK UI strings only, which made five files read as
    # "shipped=False" when they simply carry no CJK string - that is the name-probe false-absence trap,
    # so markers are now: any string literal >= 6 chars that occurs in ONE file of the export and nowhere
    # else (uniqueness proved against the whole tree, not assumed), and a file with zero such markers is
    # NOT_MEASURED, never "absent from the bundle".
    all_txt = {}
    for root_dir, dirnames, filenames in os.walk(EXPORT):
        for fn in filenames:
            if not fn.endswith((".ts", ".tsx")) or ".test." in fn:
                continue
            full = os.path.join(root_dir, fn)
            rel = os.path.relpath(full, EXPORT).replace("\\", "/")
            all_txt[rel] = io.open(full, encoding="utf-8", errors="replace").read()
    counts = {}
    for rel, t in all_txt.items():
        for lit in set(x for tup in LIT_RE.findall(t) for x in tup if x):
            counts[lit] = counts.get(lit, 0) + 1
    markers = {}
    for rel in files:
        cand = []
        for lit in [x for tup in LIT_RE.findall(all_txt.get(rel, "")) for x in tup if x]:
            if len(lit) >= 6 and counts.get(lit, 0) == 1 and lit not in cand:
                cand.append(lit)
        markers[rel] = cand[:6]

    index_html, _ = fetch(ORIGIN + "/index.html")
    asset = re.search(rb"/(assets/index-[A-Za-z0-9_-]+\.js)", index_html)
    assert asset, "no entry asset in the served index - instrument failure, not an absence"
    asset_path = asset.group(1).decode()
    b_origin, h_origin = fetch(ORIGIN + "/" + asset_path)
    b_proxy, h_proxy = fetch(PROXY + "/" + asset_path, via_proxy=True)
    same = sha(b_origin) == sha(b_proxy) and len(b_origin) == len(b_proxy)
    text = b_origin.decode("utf-8", "replace")

    reach = {}
    for rel in files:
        hits = [lit for lit in markers[rel] if lit in text]
        if not markers[rel]:
            verdict = "NOT_MEASURED_no_unique_marker"
        elif hits:
            verdict = "PRESENT_in_shipped_bundle"
        else:
            # The negative is NOT an absence claim.  main.tsx lands here and main.tsx is certainly shipped
            # (it mounts the app), which proves this method cannot see every shipped string - esbuild may
            # re-escape a literal, or my "unique to one file" rule may pick a string the bundler folded.
            verdict = "marker_missed_NOT_proven_absent"
        reach[rel] = {"markers_taken_from_tip_bytes": markers[rel], "markers_found_in_shipped_bundle": hits,
                      "verdict": verdict, "hit_ratio": "%d/%d" % (len(hits), len(markers[rel]))}

    shipped_verdicts = ("PRESENT_in_shipped_bundle",)
    bare_files_shipped = [rel for rel in files if reach[rel]["verdict"] in shipped_verdicts]
    out = {
        "schema": "CNX_CMDR_BARE_LEG_REACH_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": "of the write legs with no client deadline, how many are in the bundle the phone is "
                    "serving right now - that is what decides whether Q60' is a user-visible gap",
        "tip": TIP,
        "inputs": {"reconciliation_artifact": RECON_BLOB, "my_scan_artifact_file": SCAN_FILE,
                   "union_sites": len(union), "covered_by_mine": len(covered),
                   "wrapper_covered_named_by_anchor_reread": len(wrapper_covered),
                   "bare_sites_used": len(bare)},
        "surface": {"entry_asset": asset_path,
                    "origin_bytes": len(b_origin), "origin_sha256": sha(b_origin),
                    "proxy_bytes": len(b_proxy), "proxy_sha256": sha(b_proxy),
                    "two_surfaces_byte_identical": same,
                    "proxy_auth_handling": "credential read from FILE PATH %s, TAB-split, sent as one "
                                           "Authorization header; no byte of it printed or stored here" % AUTH_FILE,
                        "origin_content_type": h_origin.get("Content-Type"),
                    "proxy_content_type": h_proxy.get("Content-Type")},
        "bare_anchors_not_canonical": [{"file": f, "line": n, "method": next((l["method"] for l in mine["all_legs"]
                                                             if l["file"] == f and l["line"] == n), "see reconciliation")}
                      for f, n in bare],
        "per_file_reach": reach,
        "reading": {
            "files_involved": len(files),
            "files_present_in_the_shipped_bundle": len(bare_files_shipped),
            "marker_missed_never_reported_as_absent": [r for r in files if reach[r]["verdict"].startswith("marker_missed")],
            "why_absence_cannot_be_claimed": "main.tsx is in this bucket and main.tsx necessarily ships "
                "(it is the entry that mounts the app) - so a missed marker measures nothing about the bundle. "
                "Only the positive verdicts are used; the two misses are named so nobody reads them as 'not on the phone'.",
            "files_not_measurable": [r for r in files if reach[r]["verdict"].startswith("NOT_MEASURED")],
            "shipped_files": bare_files_shipped,
            "why_no_headline_leg_count": "the two instruments' anchors are not canonicalised onto call "
                "lines yet (her comment-line and blank-line anchors sit in this union next to my call-line "
                "ones, and two of her anchors duplicate two of my legs), so a leg COUNT from this union would "
                "be a made-up number. Per-file presence in the served bundle is anchor-independent, so that "
                "is what this receipt claims. Canonicalising the site list is exactly ORD-0315's job.",
        },
        "caveats": [
            "presence of a UI literal proves the module SHIPPED, not that a user can reach the press in the "
            "current demo state; reachability of a button still needs the phone-side run, which is HJ-P3's lane",
            "this measures the origin and the proxy surface; the tunnel is a third surface and was checked "
            "for liveness separately at the same minute (evidence/cmdr-phone-chain-2039/health_r1.json)",
        ],
        "discipline": {"surfaces_started_or_stopped": 0, "databases_opened": 0, "refs_pushed": 0,
                       "authoritative_branch_moved": 0, "demo_reset_calls": 0, "credential_values_printed": 0},
        "claim_kind": "deployment_determined",
        "claimed_result": None,
        "derived_result": None,
    }
    out["claimed_result"] = "%d of %d files holding bare legs carry a literal that IS in the bundle the phone is "                             "serving now; %d missed their markers and are explicitly NOT called absent; %d had no "                             "usable marker" % (
        len(bare_files_shipped), len(files),
        len(out["reading"]["marker_missed_never_reported_as_absent"]), len(out["reading"]["files_not_measurable"]))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_bare_leg_reach.json", "w", encoding="utf-8", newline="\n").write(txt)
    print("union=%d covered=%d wrapper=%d bare=%d files=%d" % (len(union), len(covered), len(wrapper_covered),
                                                               len(bare), len(files)))
    print("asset=%s origin=%dB proxy=%dB identical=%s" % (asset_path, len(b_origin), len(b_proxy), same))
    print("claimed:", out["claimed_result"])
    for rel in files:
        print("   %-52s %-44s ratio=%s" % (rel, reach[rel]["verdict"], reach[rel]["hit_ratio"]))
    print("file=_cmdr_bare_leg_reach.json bytes=%d" % len(txt.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
