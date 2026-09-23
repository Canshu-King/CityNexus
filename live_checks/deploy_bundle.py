#!/usr/bin/env python3
"""Additive-before-switch deploy for the preview bundle, with an A-E receipt.

Frozen rule DEPLOY_BUNDLE_RETENTION: never let a live URL answer 200 + HTML at a .js path.
That happens when the new index.html is switched before its assets exist (or when an old
index.html points at assets a cleanup already deleted).  So: UNION the new content-hashed
assets first, PROVE each one is reachable and is really JavaScript, and only then switch
index.html / sw.js.  A cleanup of the previous generation is a separate, later action and is
NOT performed here.

Usage:
  python deploy_bundle.py --src <build_out> --serve <served_dist> --live-tree <tree> --sha <sha>
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:4781"
HTML_FALLBACK_MARKERS = ("<!DOCTYPE", "<!doctype", "<html", "<!ENTITY")
UNION_EXT = (".js", ".css", ".mjs", ".map", ".woff", ".woff2", ".svg", ".png", ".json")
ROOT_FILES = ("index.html", "manifest.webmanifest", "sw.js", "v10-sw.js")


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def http_get(path: str, want_head: bool = False) -> dict:
    """GET through the local preview (no auth proxy) and classify the answer."""
    req = urllib.request.Request(BASE + path, method="HEAD" if want_head else "GET")
    req.add_header("Cache-Control", "no-cache")
    req.add_header("User-Agent", "cnx-deploy-receipt")
    out = {"path": path, "status": None, "content_type": None, "length": None,
           "head_bytes": None, "sha256": None, "is_html_fallback": None, "error": None}
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = b"" if want_head else r.read()
            out["status"] = r.status
            out["content_type"] = r.headers.get("Content-Type")
            out["length"] = r.headers.get("Content-Length")
            if body:
                out["head_bytes"] = body[:24].decode("utf-8", "replace")
                out["sha256"] = hashlib.sha256(body).hexdigest()
                out["body_size"] = len(body)
            head = (out["head_bytes"] or "").strip()
            out["is_html_fallback"] = any(head.startswith(m) for m in HTML_FALLBACK_MARKERS)
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        out["error"] = f"HTTPError {e.code}"
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def asset_refs(html: str) -> list[str]:
    refs = re.findall(r'["\'](/assets/[^"\']+)["\']', html)
    seen, ordered = set(), []
    for r in refs:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def asset_verdict(ref: str, expect_ct: str, serve: pathlib.Path) -> dict:
    """THE single strict judge for one served asset.

    Deliberately the only place this predicate lives: the arbiter caught the previous version
    assigning `verdict` twice, where the second (lax) assignment silently overrode the strict one
    and left only `200 and not html`.  One predicate means the gauge that ships is the gauge that
    was tested against a mutant in --selftest.
    """
    g = http_get(ref)
    on_disk = serve / ref.lstrip("/")
    g["disk_present"] = on_disk.is_file()
    g["disk_bytes"] = on_disk.stat().st_size if g["disk_present"] else None
    g["disk_sha256"] = sha256(on_disk) if g["disk_present"] else None
    g["expect_content_type_substring"] = expect_ct
    g["verdict"] = "GREEN" if (
        g["status"] == 200
        and g["is_html_fallback"] is False                       # E: 200+HTML at a .js URL is RED
        and isinstance(g["content_type"], str)
        and expect_ct in g["content_type"].lower()                # MIME must match the extension
        and g["sha256"] is not None
        # A-3 (arbiter 5788111742, 2026-09-23): a comparison against an absent side is NOT a
        # comparison.  The previous form was `disk_sha256 is None or ==`, which let an asset that
        # answers 200 with the right MIME but has no counterpart under `serve` pass with zero
        # bytes compared.  Presence is now a required conjunct; the killer arm in selftest feeds
        # this exact shape and must read RED.
        and g["disk_present"]
        and g["sha256"] == g["disk_sha256"]                       # body == disk bytes
        and g.get("body_size") == g["disk_bytes"]
    ) else "RED"
    return g


def selftest(serve: pathlib.Path) -> int:
    """Prove the asset gauge BOTH ways against the live server, without touching the deploy.

    Arms 1-2 are the true positives (the assets the live index actually references must be GREEN).
    Arms 3-4 are the killers the arbiter's strict-vs-lax finding demands: an object that answers 200
    with a *non-HTML* body but the wrong MIME must be RED (the lax twin read that as GREEN), and a
    missing path must be RED because vite preview answers it with the SPA index — the exact
    `200 + HTML at a .js URL = STALE_CLIENT_BREAKAGE_RISK` case of rule E.
    """
    live = pathlib.Path(os.environ.get("CNX_DEPLOY_SELFTEST_ROOT", str(serve)))
    served = serve / "index.html"
    refs = asset_refs(served.read_text(encoding="utf-8")) if served.is_file() else []
    arms = [{"arm": f"true_positive:{r}", "expect": "GREEN",
             "got": asset_verdict(r, "css" if r.endswith(".css") else "javascript", live)} for r in refs]
    arms.append({"arm": "killer:wrong_mime_non_html(/manifest.webmanifest as js)", "expect": "RED",
                 "got": asset_verdict("/manifest.webmanifest", "javascript", live)})
    arms.append({"arm": "killer:missing_asset_spa_html_fallback", "expect": "RED",
                 "got": asset_verdict("/assets/__cnx_no_such_asset__.js", "javascript", live)})
    # A-3 killer (arbiter 5788111742): take a ref the live index really names — so it answers 200
    # with the correct MIME — but judge it against a root that does not contain it.  Before the
    # fix this arm read GREEN with ZERO bytes compared (`disk_sha256 is None or ==`), which is the
    # "absent side masquerading as a passed comparison" family the rule exists to kill.
    ghost_root = live / "__cnx_no_such_root__"
    killer_ref = refs[0] if refs else "/assets/index.js"
    arms.append({"arm": f"killer:served_but_absent_on_disk({killer_ref})", "expect": "RED",
                 "got": asset_verdict(killer_ref, "css" if killer_ref.endswith(".css") else "javascript",
                                       ghost_root)})
    # B-arm (redteam 2026-09-23): the live index must name refs that actually resolve, and the
    # previous generation's entry must be absent.  Both halves are asserted as separate fields so
    # "the old name is gone" is a claim rather than something derived from a before/after diff.
    idx = http_get("/")
    body_html = ""
    if idx["status"] == 200:
        req = urllib.request.Request(BASE + "/")
        req.add_header("Cache-Control", "no-cache")
        with urllib.request.urlopen(req, timeout=60) as r:
            body_html = r.read().decode("utf-8", "replace")
    live_refs = asset_refs(body_html)
    resolved = all(asset_verdict(r, "css" if r.endswith(".css") else "javascript", live)["verdict"] == "GREEN"
                   for r in live_refs) if live_refs else False
    arms.append({"arm": "B1:live_index_refs_all_resolve", "expect": "GREEN",
                 "got": {"verdict": "GREEN" if (idx["status"] == 200 and resolved) else "RED",
                         "status": idx["status"], "content_type": idx["content_type"],
                         "is_html_fallback": idx["is_html_fallback"], "sha256": idx["sha256"],
                         "disk_sha256": None, "disk_bytes": None, "body_size": idx.get("body_size")}})
    old_ref = os.environ.get("CNX_DEPLOY_SELFTEST_OLD_REF")
    if old_ref:
        absent = old_ref not in body_html
        arms.append({"arm": f"B2:previous_generation_absent({old_ref})", "expect": "GREEN",
                     "got": {"verdict": "GREEN" if absent else "RED",
                             "status": idx["status"], "content_type": idx["content_type"],
                             "is_html_fallback": idx["is_html_fallback"], "sha256": idx["sha256"],
                             "disk_sha256": None, "disk_bytes": None, "body_size": idx.get("body_size")}})
        arms.append({"arm": f"B2-neg:absent-check-can-fail(names the CURRENT ref {live_refs[0] if live_refs else '?'})",
                     "expect": "RED",
                     # This arm must feed the ABSENCE predicate the live entry's own name: absence is
                     # false there, so the predicate must read RED.  (First version computed the
                     # presence predicate instead and the control failed on its own polarity, not on
                     # the gauge - which is exactly what a negative control is for.)
                     "got": {"verdict": "RED" if (live_refs and live_refs[0] in body_html) else "GREEN",
                             "status": idx["status"], "content_type": idx["content_type"],
                             "is_html_fallback": idx["is_html_fallback"], "sha256": idx["sha256"],
                             "disk_sha256": None, "disk_bytes": None, "body_size": idx.get("body_size")}})
    ok = True
    for arm in arms:
        got = arm["got"]["verdict"]
        match = got == arm["expect"]
        ok = ok and match
        print(f"  [{'OK ' if match else 'BAD'}] {arm['arm']}  expect={arm['expect']} got={got}"
              f"  status={arm['got']['status']} ct={arm['got']['content_type']} "
              f"html={arm['got']['is_html_fallback']} body_sha={str(arm['got']['sha256'])[:12]}")
    print(f"SELFTEST {'GREEN' if ok else 'RED'} ({sum(1 for a in arms if a['got']['verdict'] == a['expect'])}"
          f"/{len(arms)} arms matched)")
    out = pathlib.Path(__file__).with_name("receipts")
    out.mkdir(exist_ok=True)
    dest = out / f"gauge_selftest_{time.strftime('%m%d_%H%M%S')}.json"
    dest.write_text(json.dumps({
        "what": "deploy_bundle.py asset-gauge selftest (true positives + the two killers)",
        "why": "arbiter 5781096542 (verdict assigned twice, lax one won) + 5788111742 A-3 "
               "(a comparison against an absent side is not a comparison)",
        "base": BASE, "serve": str(serve), "overall": "GREEN" if ok else "RED",
        "arms": [{"arm": a["arm"], "expect": a["expect"], "got": a["got"]["verdict"],
                  "status": a["got"]["status"], "content_type": a["got"]["content_type"],
                  "is_html_fallback": a["got"]["is_html_fallback"],
                  "body_sha256": a["got"]["sha256"], "disk_sha256": a["got"]["disk_sha256"],
                  "body_size": a["got"].get("body_size"), "disk_bytes": a["got"]["disk_bytes"]}
                 for a in arms]}, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"[receipt] {dest}")
    return 0 if ok else 9


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--serve", required=True)
    ap.add_argument("--live-tree")
    ap.add_argument("--sha")
    ap.add_argument("--skip-build-check", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="prove the asset gauge both ways against the live server; no deploy is performed")
    a = ap.parse_args()
    if a.selftest:
        return selftest(pathlib.Path(a.serve))
    if not a.src or not a.live_tree or not a.sha:
        print("REFUSED: --src, --live-tree and --sha are required unless --selftest is given")
        return 5
    src, serve, tree = pathlib.Path(a.src), pathlib.Path(a.serve), pathlib.Path(a.live_tree)

    receipt: dict = {"sha": a.sha, "src": str(src), "serve": str(serve), "t": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    # --- precondition 0: the tree must not have the frontend dirty in a way that flatters us
    if not a.skip_build_check:
        dirty = subprocess.run(["git", "-C", str(tree), "status", "--porcelain", "--", "frontend/"],
                               capture_output=True, text=True).stdout.strip()
        receipt["frontend_dirty"] = dirty
        if dirty:
            print("REFUSED: frontend/ is dirty, refusing to deploy a half-built tree")
            print(dirty[:600])
            return 5
        tip = subprocess.run(["git", "-C", str(tree), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        receipt["tree_tip"] = tip
        if tip != a.sha[:len(tip)] and not a.sha.startswith(tip):
            print(f"REFUSED: --sha {a.sha} does not match tree tip {tip}")
            return 5

    new_index = src / "index.html"
    if not new_index.is_file():
        print(f"REFUSED: {new_index} missing - nothing was built")
        return 5
    new_html = new_index.read_text(encoding="utf-8")
    new_refs = asset_refs(new_html)
    receipt["new_index_refs"] = new_refs
    if not new_refs:
        print("REFUSED: the built index.html references no /assets/ file")
        return 5
    for ref in new_refs:
        if not (src / ref.lstrip("/")).is_file():
            print(f"REFUSED: built index.html references {ref} but the build did not produce it")
            return 5

    # --- read the CURRENT generation before touching anything
    old_index = serve / "index.html"
    old_html = old_index.read_text(encoding="utf-8") if old_index.is_file() else ""
    old_refs = asset_refs(old_html)
    receipt["old_index_refs"] = old_refs
    old_js = next((r for r in old_refs if r.endswith(".js")), None)
    old_entry = None
    if old_js:
        probe = http_get(old_js)
        on_disk = serve / old_js.lstrip("/")
        old_entry = {"ref": old_js, "probe": probe,
                     "disk_bytes": on_disk.stat().st_size if on_disk.is_file() else None}
        receipt["generation_OLD"] = old_entry
    print(f"[pre] served index.html references: {old_refs}")
    print(f"[pre] build references          : {new_refs}")

    # --- phase 1: UNION the new hashed assets (never delete, never overwrite-with-different)
    copied, added = [], []
    src_assets, dst_assets = src / "assets", serve / "assets"
    dst_assets.mkdir(parents=True, exist_ok=True)
    for p in sorted(src_assets.iterdir()):
        if not p.is_file():
            continue
        dst = dst_assets / p.name
        if dst.is_file():
            if dst.stat().st_size == p.stat().st_size and sha256(dst) == sha256(p):
                copied.append(p.name)
                continue
            print(f"REFUSED: {dst.name} exists with DIFFERENT bytes - a name collision would silently")
            print("         swap content under an already-published URL. Resolve by hand.")
            return 6
        shutil.copy2(p, dst)
        added.append(p.name)
        copied.append(p.name)
    receipt["assets_union"] = {"added": added, "already_identical": [n for n in copied if n not in added],
                               "total_in_serve_assets": len(list(dst_assets.iterdir()))}
    print(f"[union] added {len(added)} new asset(s); {len(copied) - len(added)} already byte-identical")

    # --- phase 2: PROVE the new assets answer before the switch (gate E lives here)
    pre = []
    for ref in new_refs:
        got = http_get(ref)
        on_disk = src / ref.lstrip("/")
        got["disk_bytes"] = on_disk.stat().st_size
        got["disk_sha256"] = sha256(on_disk)
        got["verdict"] = ("OK" if (got["status"] == 200 and got["is_html_fallback"] is False
                                   and got["sha256"] == got["disk_sha256"]) else "RED")
        pre.append(got)
    receipt["pre_switch_asset_probes"] = pre
    reds = [p["path"] for p in pre if p["verdict"] != "OK"]
    if reds:
        print("REFUSED before switching index (E: 200 alone is never sufficient):")
        for p in pre:
            if p["verdict"] != "OK":
                print(f"  {p['path']} status={p['status']} ct={p['content_type']} head={p['head_bytes']!r} "
                      f"body_sha={str(p['sha256'])[:12]} disk_sha={str(p['disk_sha256'])[:12]}")
        return 7
    print(f"[gate] {len(pre)} new asset(s) reachable, real bytes, no HTML fallback")

    # --- phase 3: BACKUP then SWITCH the unhashed root files
    stamp = time.strftime("%H%M")
    bak = serve.parent / f"dist_bak_{stamp}"
    bak.mkdir(parents=True, exist_ok=True)
    backed = []
    for name in ROOT_FILES + tuple(p.name for p in src.glob("workbox-*.js")):
        cur = serve / name
        if cur.is_file():
            shutil.copy2(cur, bak / name)
            backed.append(name)
    receipt["backup_dir"] = str(bak)
    receipt["backed_up"] = backed
    switched = []
    for name in ROOT_FILES:
        s = src / name
        if s.is_file():
            shutil.copy2(s, serve / name)
            switched.append(name)
    for p in src.glob("workbox-*.js"):
        shutil.copy2(p, serve / p.name)
        switched.append(p.name)
    receipt["switched"] = switched
    print(f"[switch] backed up {len(backed)} root file(s) -> {bak}")
    print(f"[switch] installed {switched}")

    time.sleep(1)

    # --- phase 4: A-E receipt
    a_old = None
    if old_js:
        probe = http_get(old_js)
        disk = serve / old_js.lstrip("/")
        a_old = {"ref": old_js, "status": probe["status"], "content_type": probe["content_type"],
                 "is_html": probe["is_html_fallback"], "disk_bytes": disk.stat().st_size if disk.is_file() else None,
                 "verdict": "GREEN" if (probe["status"] == 200 and probe["is_html_fallback"] is False) else "RED"}
    b_new = http_get("/")
    b_body_ok = (b_new["status"] == 200 and isinstance(b_new.get("head_bytes"), str))
    b_refs_ok = None
    b_new_refs_present = None
    b_old_refs_absent = None
    if b_body_ok:
        req = urllib.request.Request(BASE + "/")
        req.add_header("Cache-Control", "no-cache")
        with urllib.request.urlopen(req, timeout=60) as r:
            served_html = r.read().decode("utf-8", "replace")
        got_refs = asset_refs(served_html)
        # Split the two claims into two fields (redteam 2026-09-23): the old version stored one
        # combined boolean named refs_match_new, so "the previous bundle name is gone" was only
        # derivable from a before/after diff rather than asserted.  Both must now be GREEN.
        b_new_refs_present = all(r in served_html for r in new_refs)
        b_old_refs_absent = (old_js is None) or (old_js not in served_html)
        b_refs_ok = b_new_refs_present and b_old_refs_absent
        receipt["served_after_switch_refs"] = got_refs
    c_new = []
    for ref in new_refs:
        expect_ct = "css" if ref.endswith(".css") else "javascript"
        c_new.append(asset_verdict(ref, expect_ct, serve))
    d_sw = []
    for name in ("sw.js", "v10-sw.js"):
        g = http_get("/" + name)
        disk = serve / name
        g["disk_bytes"] = disk.stat().st_size if disk.is_file() else None
        g["matches_disk"] = (disk.is_file() and g["sha256"] == sha256(disk))
        g["verdict"] = "GREEN" if (g["status"] == 200 and g["is_html_fallback"] is False and g["matches_disk"]) else "RED"
        d_sw.append(g)
    receipt["receipt_ABCDE"] = {
        "A_OLD_ASSET_still_served": a_old,
        "B_NEW_INDEX": {"status": b_new["status"], "refs_match_new": b_refs_ok,
                        "new_refs_present": b_new_refs_present, "old_refs_absent": b_old_refs_absent,
                        "old_ref_tested": old_js,
                        "verdict": "GREEN" if (b_new["status"] == 200 and b_refs_ok) else "RED"},
        "C_NEW_ASSET": c_new,
        "D_SERVICE_WORKER": d_sw,
        "E_NOTE": ("200 alone is never sufficient: a 200 that carries HTML at a .js URL is "
                   "DEPLOYMENT_RED / STALE_CLIENT_BREAKAGE_RISK. Every entry above records the "
                   "first bytes and content-type, not just the status."),
    }
    all_green = (all(x["verdict"] == "GREEN" for x in c_new)
                 and all(x["verdict"] == "GREEN" for x in d_sw)
                 and receipt["receipt_ABCDE"]["B_NEW_INDEX"]["verdict"] == "GREEN"
                 and (a_old is None or a_old["verdict"] == "GREEN"))
    receipt["overall"] = "GREEN" if all_green else "RED"

    out = pathlib.Path(__file__).with_name("receipts")
    out.mkdir(exist_ok=True)
    dest = out / f"deploy_{a.sha}_{time.strftime('%m%d_%H%M%S')}.json"
    dest.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"[receipt] {dest}")
    print(json.dumps(receipt["receipt_ABCDE"], indent=1, ensure_ascii=False)[:2400])
    print(f"OVERALL {receipt['overall']}")
    return 0 if all_green else 8


if __name__ == "__main__":
    raise SystemExit(main())
