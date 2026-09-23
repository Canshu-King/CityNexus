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


def http_get(path: str, want_head: bool = False, base: str | None = None, auth_file: str | None = None) -> dict:
    """GET one surface and classify the answer.

    `base` defaults to the unauthenticated vite port; F passes the cnx proxy / the public tunnel,
    because the surface the user actually reaches is not 127.0.0.1:4781.  `auth_file` is the
    TAB-separated `user<TAB>password` preview credential - it is only ever turned into a header and
    never appears in the returned dict or any print.
    """
    url = (base or BASE) + path
    req = urllib.request.Request(url, method="HEAD" if want_head else "GET")
    req.add_header("Cache-Control", "no-cache")
    req.add_header("User-Agent", "cnx-deploy-receipt")
    if auth_file:
        try:
            raw = open(auth_file, encoding="utf-8").read().strip().split("\t")
            if len(raw) == 2:
                import base64 as _b64
                req.add_header("Authorization", "Basic " + _b64.b64encode(f"{raw[0]}:{raw[1]}".encode()).decode())
        except OSError:
            pass
    out = {"path": path, "status": None, "content_type": None, "length": None,
           "head_bytes": None, "sha256": None, "is_html_fallback": None, "error": None,
           "base": base or BASE, "auth_applied": bool(auth_file)}
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


def precache_urls(sw_text: str) -> list[str]:
    """URLs the generated service worker promises to precache.

    D proves only "the sw bytes on disk == the sw bytes served"; it never opened this list, so a
    manifest naming an unreachable asset kept the whole A-E receipt GREEN (redteam bus 5788606895).
    Parsed from the workbox `precacheAndRoute([...])` array.  Measured against the real generated
    file, entries look like `{url:"sw.js",revision:"1eebbb..."}` - the KEY IS UNQUOTED, so a `"url"`
    pattern silently returns zero urls and "zero urls" must never be readable as "nothing to check".
    """
    urls = re.findall(r'\{[^{}]*?\burl\s*:\s*"([^"]+)"[^{}]*?\}', sw_text)
    seen, ordered = set(), []
    for u in urls:
        u = "/" + u if u and not u.startswith("/") else u    # normalize BEFORE dedupe: the real
        if u and u not in seen:                              # manifest holds "index.html" and
                                                             # "/index.html" - same file, and a
                                                             # doubled count would inflate the
                                                             # non-emptiness claim A-3 rests on
            seen.add(u)
            ordered.append(u)
    return ordered


def expect_ct_for(ref: str) -> str:
    """Content-Type substring a served asset must carry, by extension (single place, so G/H/C agree).

    The precache manifest carries `favicon.svg` and pngs too; forcing those to "javascript" would
    manufacture a red that is an artifact of my judge, not of the deploy.
    """
    if ref.endswith(".css"):
        return "css"
    if ref.endswith((".json", ".webmanifest")):
        return "json"
    if ref.endswith((".html", ".htm")) or ref.endswith("/"):
        # Measured while building F: judging "/" as javascript made the index document RED on every
        # surface (status=200 ct=text/html), i.e. the new arm would have failed every deploy for the
        # wrong reason.  "/" is the shell, and HTML there is correct.
        return "html"
    if ref.endswith(".svg"):
        return "svg"
    if ref.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    if ref.endswith((".woff", ".woff2")):
        return "font"
    return "javascript"


def asset_verdict(ref: str, expect_ct: str, serve: pathlib.Path, base: str | None = None,
                  auth_file: str | None = None) -> dict:
    """THE single strict judge for one served asset.

    Deliberately the only place this predicate lives: the arbiter caught the previous version
    assigning `verdict` twice, where the second (lax) assignment silently overrode the strict one
    and left only `200 and not html`.  One predicate means the gauge that ships is the gauge that
    was tested against a mutant in --selftest.
    """
    g = http_get(ref, base=base, auth_file=auth_file)
    disk_ref = "index.html" if ref in ("/", "") else ref.lstrip("/")   # "/" is served AS index.html;
                                                           # joining it to an empty name makes the
                                                           # directory, which is never a file
    on_disk = serve / disk_ref
    g["disk_present"] = on_disk.is_file()
    g["disk_bytes"] = on_disk.stat().st_size if g["disk_present"] else None
    g["disk_sha256"] = sha256(on_disk) if g["disk_present"] else None
    g["expect_content_type_substring"] = expect_ct
    # An HTML document is only a "fallback" when HTML was NOT the answer for this URL.  "/" and
    # index.html legitimately serve HTML; a .js URL answered with HTML is the E case.
    html_ok = ref.endswith((".html", ".htm", "/"))
    g["verdict"] = "GREEN" if (
        g["status"] == 200
        # E is about HTML answering a **non-HTML** URL.  The precache manifest legitimately carries
        # /index.html, so judging its real HTML as a fallback manufactures a red (measured: G true
        # positive read `index.html status=200 ct=text/html html=True disk=True`).  HTML at a .js
        # URL stays RED, which is the case rule E was written for.
        and (g["is_html_fallback"] is False or html_ok)
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


def g_prod_shape_verdict(root: pathlib.Path) -> dict:
    """Reproduce the production shape: a declared hand-written sw (no precache array) vs the same
    bytes under an UNdeclared name.  Returns the two verdicts the selftest asserts both ways."""
    src = root / "sw.js"
    text = src.read_text(encoding="utf-8", errors="replace") if src.is_file() else ""
    declared = {"sw.js": "hand-written service worker, no workbox precacheAndRoute array"}
    urls = precache_urls(text)
    dec = ("DECLARED" if (not urls and "sw.js" in declared) else "NOT_APPLICABLE")
    und = "RED" if not urls else "GREEN"
    return {"declared": dec, "undeclared": und, "urls_found": len(urls)}


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

    # ---- G/H/F arms: the blind spots redteam d2305848 broke this gauge with (bus 5788606895).
    # Built synthetically (extra urls appended to a parsed list, a fake previous index, an unreachable
    # base) so the live dist is never mutated by a selftest.
    def g_detail(urls):
        """verdict + the offending refs: a boolean-only red is not diagnosable (A-5 discipline)."""
        if not urls:                                   # A-3: an empty manifest proves nothing
            return {"verdict": "RED", "bad_refs": ["<empty manifest>"]}
        bad = []
        for u in urls:
            ref = u if u.startswith("/") else "/" + u
            v = asset_verdict(ref, expect_ct_for(ref), live)
            if v["verdict"] != "GREEN":
                bad.append(f"{ref} status={v['status']} ct={v['content_type']} html={v['is_html_fallback']} "
                           f"disk={v['disk_present']}")
        return {"verdict": "RED" if bad else "GREEN", "bad_refs": bad}

    def g_verdict(urls):
        return g_detail(urls)["verdict"]

    swf = live / "v10-sw.js"
    g_urls = precache_urls(swf.read_text(encoding="utf-8", errors="replace")) if swf.is_file() else []
    arms.append({"arm": f"G-true_positive:precache_resolves({len(g_urls)} urls)", "expect": "GREEN",
                 "got": g_detail(g_urls)})
    arms.append({"arm": "G-killer:precache_names_unreachable_asset", "expect": "RED",
                 "got": g_detail(g_urls + ["/assets/__cnx_not_in_manifest__.js"])})
    arms.append({"arm": "G-killer:empty_manifest_is_not_a_pass", "expect": "RED",
                 "got": {"verdict": g_verdict([])}})
    # G-killer 2 (redteam bus 5788897591, measured on the production chain): a file with NO precache
    # array must not turn the gauge permanently RED if it is declared, and MUST be RED if it is not.
    # Both directions are asserted so "declared" cannot become a blanket exemption.
    prod_like = g_prod_shape_verdict(live)
    arms.append({"arm": "G-declared:handwritten_sw_without_precache_array", "expect": "DECLARED",
                 "got": {"verdict": prod_like["declared"]}})
    arms.append({"arm": "G-killer:undeclared_empty_manifest_still_red", "expect": "RED",
                 "got": {"verdict": prod_like["undeclared"]}})
    prev_ok = "\n".join(f'<script src="{r}"></script>' for r in refs)
    prev_bad = prev_ok + '\n<script src="/assets/__cnx_old_generation_gone.js"></script>'
    arms.append({"arm": f"H-true_positive:previous_generation_resolves({len(refs)} refs)", "expect": "GREEN",
                 "got": {"verdict": g_verdict(asset_refs(prev_ok))}})
    arms.append({"arm": "H-killer:previous_generation_asset_missing", "expect": "RED",
                 "got": {"verdict": g_verdict(asset_refs(prev_bad))}})
    dead = asset_verdict("/v10-sw.js", "javascript", live, base="http://127.0.0.1:59999")
    arms.append({"arm": "F-killer:unreachable_surface_is_red_not_absent", "expect": "RED",
                 "got": dead})
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
        g = arm["got"]
        print(f"  [{'OK ' if match else 'BAD'}] {arm['arm']}  expect={arm['expect']} got={got}"
              f"  status={g.get('status')} ct={g.get('content_type')} "
              f"html={g.get('is_html_fallback')} body_sha={str(g.get('sha256'))[:12]}"
              f"{' err=' + str(g.get('error'))[:60] if g.get('error') else ''}"
              f"{' bad_refs=' + '; '.join(map(str, g.get('bad_refs') or []))[:220] if g.get('bad_refs') else ''}")
    print(f"SELFTEST {'GREEN' if ok else 'RED'} ({sum(1 for a in arms if a['got']['verdict'] == a['expect'])}"
          f"/{len(arms)} arms matched)")
    out = pathlib.Path(__file__).with_name("receipts")
    out.mkdir(exist_ok=True)
    dest = out / f"gauge_selftest_{time.strftime('%m%d_%H%M%S')}.json"
    dest.write_text(json.dumps({
        "what": "deploy_bundle.py asset-gauge selftest (true positives + killers, incl. A-3 disk presence, G precache, H prev-generation, F unreachable surface)",
        "why": "arbiter 5781096542 (verdict assigned twice, lax one won) + 5788111742 A-3 "
               "(a comparison against an absent side is not a comparison)",
        "base": BASE, "serve": str(serve), "overall": "GREEN" if ok else "RED",
        "arms": [{"arm": a["arm"], "expect": a["expect"], "got": a["got"]["verdict"],
                  "status": a["got"].get("status"), "content_type": a["got"].get("content_type"),
                  "is_html_fallback": a["got"].get("is_html_fallback"),
                  "body_sha256": a["got"].get("sha256"), "disk_sha256": a["got"].get("disk_sha256"),
                  "disk_present": a["got"].get("disk_present"), "error": a["got"].get("error"),
                  "body_size": a["got"].get("body_size"), "disk_bytes": a["got"].get("disk_bytes")}
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
    ap.add_argument("--allow-proxy-unprobed", action="store_true",
                    help="declare that CNX_DEPLOY_PROXY_BASE / CNX_DEPLOY_TUNNEL_BASE were not set, so F is "
                         "recorded as F_UNPROBED_DECLARED instead of RED.  Neither is GREEN: the user-facing "
                         "surface stays unprobed either way (A-3 fail-closed, redteam bus 5788606895).")
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

    # ---- F/G/H: the three blind spots redteam d2305848 broke this gauge with (bus 5788606895).
    # D only proved "the sw file on disk equals the sw file served"; it never opened the precache
    # manifest, so a manifest naming an asset that is not reachable still produced A-E all GREEN -
    # exactly the stale-client white screen this whole rule exists to prevent.  A probed only the one
    # .js the old index named, leaving old CSS/other assets out of range.  And BASE is the unauthenticated
    # vite port, so the cnx proxy and the public tunnel were never touched at all.

    # G: precache integrity - every url the registered service workers promise must resolve as real
    # bytes, through the same asset_verdict predicate (no second, laxer judge).
    # Declared no-precache-array files (redteam bus 5788897591): the production chain still ships a
    # HAND-WRITTEN `sw.js` (measured 7,178 B) that carries no workbox `precacheAndRoute` array, so
    # parsing it yields 0 urls.  Judging that RED would make the whole gauge permanently unable to go
    # green - which is not "strict", it is broken.  A-3 is honoured the same way as F's escape hatch:
    # the gap is NAMED, carries its measured witness, and is excluded from all_green by name only.
    DECLARED_NO_PRECACHE = {"sw.js": "hand-written service worker, no workbox precacheAndRoute array"}
    g_precache = []
    for name in ("sw.js", "v10-sw.js"):
        swf = serve / name
        if not swf.is_file():
            continue
        urls = precache_urls(swf.read_text(encoding="utf-8", errors="replace"))
        entry = {"sw": name, "urls_found": len(urls), "probes": []}
        if not urls and name in DECLARED_NO_PRECACHE:
            entry["declared_no_precache_array"] = DECLARED_NO_PRECACHE[name]
            entry["measured_bytes"] = swf.stat().st_size
            entry["measured_sha256"] = sha256(swf)
            entry["verdict"] = "DECLARED_NO_PRECACHE_ARRAY"
            g_precache.append(entry)
            continue
        for u in urls:
            ref = u if u.startswith("/") else "/" + u
            entry["probes"].append({"ref": ref, "got": asset_verdict(ref, expect_ct_for(ref), serve)})
        # A-3: an empty manifest is not a passed check.  If a sw carries no precache at all, that is a
        # legitimate state only when it is declared - here we require the parse to have found entries.
        entry["verdict"] = ("GREEN" if entry["urls_found"] > 0 and all(p["got"]["verdict"] == "GREEN" for p in entry["probes"])
                            else "RED")
        g_precache.append(entry)

    # H: previous-generation completeness - every asset the PREVIOUS index named must still resolve.
    h_prev = []
    prev_index = (bak / "index.html") if bak.is_dir() else None
    if prev_index is not None and prev_index.is_file():
        for r in asset_refs(prev_index.read_text(encoding="utf-8", errors="replace")):
            h_prev.append({"ref": r, "got": asset_verdict(r, expect_ct_for(r), serve)})
    h_prev_verdict = ("GREEN" if h_prev and all(x["got"]["verdict"] == "GREEN" for x in h_prev)
                      else ("NOT_CONFIGURED" if not h_prev else "RED"))

    # F: the surface the user actually reaches - auth proxy and public tunnel - probed for the NEW
    # bundle, not just for `/`.  Bases come from the environment; unset means UNPROBED, which is
    # never GREEN (fail closed) unless the operator declares the gap out loud.
    f_probes = []
    for label, base in (("proxy_4782", os.environ.get("CNX_DEPLOY_PROXY_BASE")),
                        ("tunnel", os.environ.get("CNX_DEPLOY_TUNNEL_BASE"))):
        if not base:
            f_probes.append({"surface": label, "verdict": "NOT_CONFIGURED", "base": None})
            continue
        for ref in [r for r in new_refs if r.endswith(".js")] + ["/"]:
            f_probes.append({"surface": label, "base": base,
                             "got": asset_verdict(ref, expect_ct_for(ref), serve, base=base,
                                                   auth_file=os.environ.get("CNX_DEPLOY_AUTH_FILE"))})
    f_unconfigured = any(p["verdict"] == "NOT_CONFIGURED" for p in f_probes)
    f_green = (not f_unconfigured) and all(p.get("got", {}).get("verdict") == "GREEN" for p in f_probes)
    if f_unconfigured and getattr(a, "allow_proxy_unprobed", False):
        f_verdict = "F_UNPROBED_DECLARED"          # declared gap, kept OUT of all_green by name
    elif f_unconfigured:
        f_verdict = "RED"                          # fail closed: absent comparison != passed comparison
    else:
        f_verdict = "GREEN" if f_green else "RED"

    receipt["receipt_FGH_blindspot_arms"] = {
        "G_PRECACHE_INTEGRITY": g_precache,
        "H_PREVIOUS_GENERATION": {"refs_probed": len(h_prev), "probes": h_prev, "verdict": h_prev_verdict},
        "F_PROXY_AND_TUNNEL": {"probes": f_probes, "verdict": f_verdict,
                               "why": "BASE is 127.0.0.1:4781 (no auth proxy); the proxy and the tunnel "
                                      "were never probed by A-E - redteam bus 5788606895"},
    }
    # A declared entry is not a pass either: at least one sw must actually be checked (GREEN), and no
    # entry may be RED.  Two-way killer in --selftest: an UNDECLARED empty manifest must read RED.
    g_green = (bool(g_precache)
               and any(e["verdict"] == "GREEN" for e in g_precache)
               and not any(e["verdict"] == "RED" for e in g_precache))
    receipt["arms"] = {"A": (a_old or {}).get("verdict"), "B": "see receipt_ABCDE",
                       "G_precache": [e["verdict"] for e in g_precache],
                       "H_prevgen": h_prev_verdict, "F_proxy_tunnel": f_verdict,
                       "all_green_requires": "A,B,C,D,E + G + F (H reported; RED if it names an unreachable asset)"}
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
                 and (a_old is None or a_old["verdict"] == "GREEN")
                 and g_green and f_verdict == "GREEN")
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
