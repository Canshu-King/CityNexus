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
import ast
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

BASE_DEFAULT = "http://127.0.0.1:4781"      # the commander's live preview chain (vite static)
BASE = os.environ.get("CNX_DEPLOY_BASE", BASE_DEFAULT).rstrip("/")
BASE_WAS_DEFAULTED = "CNX_DEPLOY_BASE" not in os.environ


def base_url() -> str:
    """The HTTP side of every comparison, resolved at CALL time so `--selftest` (and any other lane)
    can retarget it without editing this file.  Recorded in every probe as `base`."""
    return os.environ.get("CNX_DEPLOY_BASE", BASE_DEFAULT).rstrip("/")
# Why this is now env-declared instead of hardcoded: A-E read `--serve` from DISK but every status/MIME/
# digest comes from HTTP against BASE.  Another lane pointing --serve at its own dist while BASE stays here
# gets a mixed reading - its files judged against MY server's bytes - which is the A-3 wrong-side family
# wearing a green badge.  main() now refuses that combination instead of reporting it.
# Redteam round 3 (bus 5789163700): a single probe was only forbidden on F, so a URL that exactly one
# arm probes (the dynamically-imported maplibre chunk - in the SW precache, not in index.html) could still
# serve #1 fine and 404 forever after while the gauge read ALL_GREEN.  Repeat is now the default for every
PROBE_TIMES = int(os.environ.get("CNX_DEPLOY_PROBE_TIMES", "2"))
HTML_FALLBACK_MARKERS = ("<!DOCTYPE", "<!doctype", "<html", "<!ENTITY")
UNION_EXT = (".js", ".css", ".mjs", ".map", ".woff", ".woff2", ".svg", ".png", ".json")
ROOT_FILES = ("index.html", "manifest.webmanifest", "sw.js", "v10-sw.js")


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


CMDR_DIST = "D:/moodle/_qoder_preview_20260920"      # the deployment this chain's --serve normally points at


def git_blob_sha1(data: bytes) -> str:
    """A real git blob id, computed without needing a repository (same formula git uses)."""
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def gauge_self_binding() -> dict:
    """D1-5 (arbiter `5789539216`): a selftest/receipt must name the exact bytes of the gauge that ran.

    Without this, `33/31+... GREEN` says only "some version of this file passed", and an external auditor
    cannot tell which blob it may rely on - the same defect that made me post a stale D-1 coordinate twice.
    """
    p = pathlib.Path(__file__)
    data = p.read_bytes()
    return {"gauge_path": str(p), "gauge_bytes": len(data),
            "gauge_content_digest_sha256": hashlib.sha256(data).hexdigest(),
            "gauge_git_blob_sha1": git_blob_sha1(data),
            "gauge_git_blob_len": len(git_blob_sha1(data)),
            "rule": "a receipt may only endorse the exact gauge bytes it names (arbiter D1-5)"}


def surface_sides_check(serve: pathlib.Path) -> dict:
    """The HTTP side (`base_url()`) and the disk side (`--serve`) must belong to one deployment.

    Redteam hole 2 (`5790009042`): the first version compared a SUBSTRING, so
    `--serve <CMDR_DIST>/../someone_else/dist` contained the marker and slipped past the refusal.
    Comparing resolved paths closes `..`, backslash, and casing tricks in one go.
    """
    info = {"http_base": base_url(), "declared_via_env": "CNX_DEPLOY_BASE" in os.environ,
            "disk_serve": str(serve), "rule": "the HTTP side and the disk side must belong to the same deployment",
            "declares_cmdr_live_explicitly": os.environ.get("CNX_DEPLOY_BASE_IS_CMDR_LIVE", "").strip() == "1"}
    try:
        rs, rc = pathlib.Path(serve).resolve(), pathlib.Path(CMDR_DIST).resolve()
        info["resolved_serve"], info["resolved_cmdr_dist"] = str(rs), str(rc)
        inside = rs == rc or rs.is_relative_to(rc)
    except (OSError, ValueError) as exc:                                  # noqa: BLE001
        rs, inside = None, False
        info["resolve_error"] = f"{type(exc).__name__}: {exc}"
    info["inside_cmdr_dist_resolved"] = inside
    # Redteam's hole-1 construction did NOT leave the base defaulted: it pointed CNX_DEPLOY_BASE at its own
    # ephemeral server while --serve stayed on my dist.  So the rule has to run in BOTH directions:
    # the base is classified, and a disagreement in either direction is a mixed pair.
    try:
        import urllib.parse as _up
        _p = _up.urlsplit(base_url())
        _port = _p.port
        base_is_cmdr_like = (_port in (4781, 4782)) or (_p.hostname or "").endswith("trycloudflare.com")
    except ValueError:
        _port, base_is_cmdr_like = None, False
    info["base_port"] = _port
    info["base_is_cmdr_like"] = base_is_cmdr_like
    defaulted = "CNX_DEPLOY_BASE" not in os.environ
    ok = True
    if info["declares_cmdr_live_explicitly"]:
        info["pairing"] = "DECLARED_CMDR_LIVE_BY_OPERATOR"
    elif inside and not base_is_cmdr_like:
        ok = False
        info["pairing"] = "MIXED: disk side is the commander dist, HTTP side is a foreign base"
        info["refuse_reason"] = (
            "--serve resolves INSIDE the commander's live dist but CNX_DEPLOY_BASE points at a foreign server "
            f"({info['http_base']}). A pre-flight that reads my files and someone else's bytes is still a "
            "mixed-sides claim (redteam 5790009042 hole 1). Point --serve at your own dist, or set "
            "CNX_DEPLOY_BASE_IS_CMDR_LIVE=1 if you really do mean to judge my chain.")
    elif (not inside) and (defaulted or base_is_cmdr_like):
        ok = False
        info["pairing"] = "MIXED: disk side is foreign, HTTP side is the commander chain"
        info["refuse_reason"] = (
            "--serve resolves outside the commander's live dist while the HTTP side is my chain "
            f"(base {'defaulted to' if defaulted else 'set to'} {info['http_base']}): bytes would be read from "
            f"{info['http_base']} and compared against files under {info.get('resolved_serve')}. "
            "Set CNX_DEPLOY_BASE=http://127.0.0.1:<your static port>, or CNX_DEPLOY_BASE_IS_CMDR_LIVE=1 to say")
    return {"ok": ok, "info": info}


def manifest_binding_row(ref: str, served_status, served_sha, disk_sha, entry: dict | None) -> dict:
    """D1-3 (arbiter `5789539216`) pure judge: a content-hashed filename claims a content; nothing in the
    old receipt compared that claim to anything.  Redteam had already produced a bundle whose name said one
    digest while its bytes were another, and six arms stayed GREEN.

    Three sides now: served bytes, file on disk, and the digest recorded **when the tool published it**.
    A hand edit after publication changes two of the three, which is exactly what this catches.
    """
    row = {"ref": ref, "bound_in_manifest": entry is not None,
           "served_status": served_status, "served_sha256": served_sha, "disk_sha256": disk_sha,
           "manifest_sha256": (entry or {}).get("sha256"), "manifest_bytes": (entry or {}).get("bytes")}
    if entry is None:
        row["verdict"] = "RED"
        row["why"] = "asset is claimed/served but has no binding in assets_manifest.json (absent != passed)"
        return row
    row["served_matches_manifest"] = served_sha == entry["sha256"]
    row["disk_matches_manifest"] = disk_sha == entry["sha256"]
    row["verdict"] = "GREEN" if (served_status == 200 and row["served_matches_manifest"]
                                 and row["disk_matches_manifest"]) else "RED"
    if row["verdict"] == "RED":
        row["why"] = ("name/content binding broken: "
                      + ", ".join(k for k, v in (("served", row["served_matches_manifest"]),
                                                 ("disk", row["disk_matches_manifest"]),
                                                 ("status-200", served_status == 200)) if not v))
    return row


def asset_manifest_write(serve: pathlib.Path) -> dict:
    """Record, at the moment of publication, the digest of every asset that now sits in the served tree."""
    assets = serve / "assets"
    entries = {}
    if assets.is_dir():
        for p in sorted(assets.iterdir()):
            if p.is_file():
                entries["/assets/" + p.name] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    doc = {"written_by": "live_checks/deploy_bundle.py", "gauge": gauge_self_binding(),
           "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "rule": "name -> digest at publication time (D1-3)",
           "assets": entries}
    (serve / "assets_manifest.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False),
                                                 encoding="utf-8", newline="\n")
    return doc


def asset_manifest_verdict(serve: pathlib.Path, refs: list[str]) -> dict:
    mf = serve / "assets_manifest.json"
    out = {"manifest": str(mf), "rule": "served bytes == disk bytes == digest recorded at publication",
           "checked": []}
    if not mf.is_file():
        if os.environ.get("CNX_DEPLOY_ALLOW_NO_MANIFEST", "").strip() == "1":
            out["verdict"] = "DECLARED_NO_ASSET_MANIFEST"
            out["why"] = ("declared gap: the tree carries no binding, so no name/content claim was verified; "
                          "this is NOT a pass and never counts toward all_green")
        else:
            out["verdict"] = "RED"
            out["reason"] = ("no assets_manifest.json next to the served tree - a deployment that cannot name "
                             "what each hashed filename was supposed to contain has not been checked")
        return out
    doc = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
    assets = doc.get("assets", {})
    out["manifest_gauge"] = doc.get("gauge")
    bad = []
    for ref in refs:
        if not ref.startswith("/assets/"):
            continue
        g = http_get(ref)
        disk = serve / ref.lstrip("/")
        row = manifest_binding_row(ref, g["status"], g["sha256"],
                                   sha256(disk) if disk.is_file() else None, assets.get(ref))
        out["checked"].append(row)
        if row["verdict"] != "GREEN":
            bad.append(row)
    out["refs_checked"] = len(out["checked"])
    if not out["checked"]:
        out["verdict"] = "RED"
        out["reason"] = "manifest present but no /assets/ ref claimed by this receipt - nothing was bound (A-3)"
    else:
        out["verdict"] = "RED" if bad else "GREEN"
        if bad:
            out["reason"] = "; ".join(f"{r['ref']}: {r.get('why')}" for r in bad)[:300]
    return out


def http_get(path: str, want_head: bool = False, base: str | None = None, auth_file: str | None = None) -> dict:
    """GET one surface and classify the answer.

    `base` defaults to the unauthenticated vite port; F passes the cnx proxy / the public tunnel,
    because the surface the user actually reaches is not 127.0.0.1:4781.  `auth_file` is the
    TAB-separated `user<TAB>password` preview credential - it is only ever turned into a header and
    never appears in the returned dict or any print.
    """
    url = (base or base_url()) + path
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
    out = {"path": path, "status": None, "content_type": None, "length": None, "cache_control": None,
           "head_bytes": None, "sha256": None, "is_html_fallback": None, "error": None,
           "base": base or base_url(), "auth_applied": bool(auth_file)}
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = b"" if want_head else r.read()
            out["status"] = r.status
            out["content_type"] = r.headers.get("Content-Type")
            out["length"] = r.headers.get("Content-Length")
            # round 4 (redteam bus 5789252266): every previous conjunct looked at status, MIME, first
            # bytes and digests - **never at response headers**.  A shell document served with
            # `max-age=31536000, immutable` therefore passed the whole receipt while guaranteeing that
            # the next generation is never fetched (white screen once old assets are pruned).
            out["cache_control"] = r.headers.get("Cache-Control")
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


def shell_cache_policy() -> tuple[int, str]:
    """(allowed max-age, declared basis).  Read live so --selftest can drive BOTH directions.

    Round-5 finding (redteam `5789355832` ①): the old default of 600 was a *widening*, not a tightening.
    The length a client can be locked to a stale shell equals the shell's own max-age - `updateViaCache`
    only covers the SW **script**, and an SW update never replaces the shell document - so any window is
    a real white-screen window.  The production chain already serves `no-cache` (measured), so 0 is the
    value that matches reality.  A non-zero window is still allowed, but only with a written basis.
    """
    raw = os.environ.get("CNX_DEPLOY_SHELL_MAX_AGE")
    basis = os.environ.get("CNX_DEPLOY_SHELL_MAX_AGE_BASIS", "").strip()
    return (0 if raw is None or not raw.strip() else int(raw)), basis


def cache_semantics_verdict(ref: str, probe: dict) -> dict:
    """A-9: the *shell* document must never be cached immutably or for a long time.

    Hashed /assets/* keep `immutable` legitimately (content-addressed, safe forever).  The shell is the
    opposite: it is the only thing that tells the browser which bundle exists next, so an
    `immutable`/long `max-age` on it makes the next generation unfetchable - the exact white screen
    DEPLOY_BUNDLE_RETENTION exists to prevent, produced by headers rather than by deleting files.
    """
    is_shell = ref.endswith((".html", ".htm")) or ref.endswith("/") or ref == ""
    limit, basis = shell_cache_policy()
    cc = (probe.get("cache_control") or "").lower()
    out = {"ref": ref, "is_shell": is_shell, "cache_control": probe.get("cache_control"),
           "allowed_max_age": limit, "declared_basis": basis or None,
           "rule": (f"shell must not carry immutable; max-age <= {limit}"
                    + ("" if limit == 0 else f" (declared basis: {basis})"))}
    if not is_shell:
        # hashed assets are allowed (and encouraged) to be immutable - but that must be a *seen* header,
        # not an absence of evidence, so we still record what was served.
        out["verdict"] = "NOT_SHELL_RECORDED"
        return out
    if "immutable" in cc:
        out["verdict"] = "RED"
        out["reason"] = "shell document served with Cache-Control: immutable"
        return out
    if "no-store" in cc or "no-cache" in cc or "must-revalidate" in cc:
        out["verdict"] = "GREEN"
        return out
    found = re.search(r"max-age\s*=\s*(\d+)", cc)
    if found is None:
        out["verdict"] = "RED"
        out["reason"] = "shell document carries no Cache-Control at all - revalidation policy is undefined"
        return out
    age = int(found.group(1))
    out["measured_max_age"] = age
    if age > limit:
        out["verdict"] = "RED"
        out["reason"] = f"shell max-age={age} exceeds {limit}"
        return out
    if limit > 0 and not basis:
        # A window without a written reason is the same family as a check that never ran: the number
        # looks configured, but nobody has to defend it.  Refuse the widening, do not inherit it.
        out["verdict"] = "RED"
        out["reason"] = (f"UNDECLARED_CACHE_WINDOW: max-age={age} allowed only because "
                         f"CNX_DEPLOY_SHELL_MAX_AGE={limit} was set without CNX_DEPLOY_SHELL_MAX_AGE_BASIS")
        return out
    out["verdict"] = "GREEN"
    return out


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
        and cache_semantics_verdict(ref, g)["verdict"] != "RED"   # A-9 (redteam round 4)
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


def repeated_verdict(ref: str, expect_ct: str, serve: pathlib.Path, base: str | None = None,
                     auth_file: str | None = None, times: int = 2) -> dict:
    """Probe the SAME url `times` times and require every answer to be GREEN.

    Why this exists (redteam bus `5788977359`, second attack): the old F arm hit each target once,
    and that single probe *was* the first request.  A stateful edge/proxy that serves request #1 fine
    and answers 501 from request #2 onward therefore produced gauge `ALL_GREEN` while the user's
    second visit was broken - deterministic, not the probabilistic `UNEXPLAINED_EDGE_501`.
    """
    rows = [asset_verdict(ref, expect_ct, serve, base=base, auth_file=auth_file) for _ in range(max(1, times))]
    ok = bool(rows) and all(r["verdict"] == "GREEN" for r in rows)
    return {"verdict": "GREEN" if ok else "RED", "times": len(rows),
            "statuses": [r["status"] for r in rows], "probes": rows,
            "red_refs": [f"{r['status']}/{r['content_type']}" for r in rows if r["verdict"] != "GREEN"]}


def http_text(path: str, base: str | None = None, auth_file: str | None = None) -> dict:
    """Fetch one URL and keep the BODY, for predicates that must read bytes rather than headers.

    It records `sha256` of exactly what it read, so arm I can prove the text it parsed is the same
    bytes arm C hashed - parsing a different side would be the A-3 family again.
    """
    out = {"path": path, "base": base or base_url(), "status": None, "text": None, "sha256": None,
           "body_size": None, "error": None}
    try:
        req = urllib.request.Request((base or base_url()) + path)
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
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            out["status"] = r.status
            out["sha256"] = hashlib.sha256(body).hexdigest()
            out["body_size"] = len(body)
            out["text"] = body.decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


SW_REGISTER_RULE = ('every navigator.serviceWorker.register() in the SERVED bundle must declare '
                    'scope "/" and updateViaCache "none"')

# Module level because BOTH the pre-flight helper and main() need it (the 15:33 deploy crashed with
# NameError: preflight referenced the copy that only existed inside main()).
DECLARED_NO_PRECACHE = {"sw.js": "hand-written service worker, no workbox precacheAndRoute array"}


def strip_js_comments(text: str) -> str:
    """Redteam `5789637279`: a good-looking `register("/v10-sw.js", {...updateViaCache:"none"})` left in a
    COMMENT was matched by the parser while the real, broken call used a variable URL and escaped it.
    Judging executable code means removing the prose first."""
    no_block = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    no_line = re.sub(r"(?m)^\s*//.*$", "", no_block)
    return re.sub(r"(?<![:'\"])//[^'\"\n]*$", "", no_line, flags=re.M)


def sw_register_verdict(text: str | None, source: str) -> dict:
    """Arm I (redteam `5789355832` ②): the registration parameters live only inside the bundle bytes.

    Their construction: change `updateViaCache:"none"` to `"all"` in the built bundle and all six arms
    stayed GREEN, while "all" lets the HTTP cache hold the old SW script - so the user can keep running
    the previous generation's precache forever.  `scope` decides which pages the SW controls at all.
    Absence of a parseable call is RED, not "nothing to check".
    """
    out = {"source": source, "rule": SW_REGISTER_RULE, "calls": [], "verdict": None}
    if text is None:
        out["verdict"] = "RED"
        out["reason"] = f"bundle bytes could not be read from {source}: nothing was parsed"
        return out
    code = strip_js_comments(text)
    # Every textual registration attempt, then what the parser could actually read parameters from.
    mentions = len(re.findall(r"serviceWorker\.register\s*\(", code))
    for m in re.finditer(r"serviceWorker\.register\(\s*(?P<url>[\"'`][^\"'`]*[\"'`])\s*(?:,\s*(?P<opts>\{[^{}]*\}))?\s*\)",
                         code):
        url = m.group("url").strip("\"'`")
        opts = m.group("opts") or ""
        scope = re.search(r"scope\s*:\s*[\"'`]([^\"'`]*)[\"'`]", opts)
        uvc = re.search(r"updateViaCache\s*:\s*[\"'`]([^\"'`]*)[\"'`]", opts)
        entry = {"sw_url": url,
                 "scope": scope.group(1) if scope else None,
                 "updateViaCache": uvc.group(1) if uvc else None,
                 "opts_present": bool(opts)}
        # An SW's default scope is the DIRECTORY of its script URL, so "/v10-sw.js" is implicitly root
        # scope; "/sub/v10-sw.js" would not be, and anything we cannot resolve as a root-relative
        # filename must carry an explicit scope="/".
        if entry["scope"] is not None:
            entry["scope_ok"] = entry["scope"] == "/"
        else:
            entry["scope_ok"] = url.startswith("/") and "/" not in url.lstrip("/")
        entry["update_via_cache_ok"] = entry["updateViaCache"] == "none"
        out["calls"].append(entry)
    out["register_mentions_in_code"] = mentions
    out["register_calls_parsed"] = len(out["calls"])
    out["unresolved_registrations"] = mentions - len(out["calls"])
    if not out["calls"]:
        out["verdict"] = "RED"
        out["reason"] = ("no serviceWorker.register() call found in the comment-stripped bundle - either the SW is "
                         "never installed or the minified shape moved out of this parser's range; neither "
                         "may be read as a pass (A-3)")
        return out
    # The hole redteam actually drove: one parseable GOOD call plus one real call the parser cannot see
    # (variable URL, nested options object, template literal).  A partial read is not a read.
    if out["unresolved_registrations"] > 0:
        out["verdict"] = "RED"
        out["reason"] = (f"{out['unresolved_registrations']} serviceWorker.register() mention(s) in the code could "
                         "not be parsed to arguments - an unreadable registration is an unjudged one "
                         "(redteam 5789637279: good call in a comment + variable-URL call outside range)")
        return out
    bad = [c for c in out["calls"] if not (c["scope_ok"] and c["update_via_cache_ok"])]
    if bad:
        out["verdict"] = "RED"
        out["reason"] = "; ".join(
            f"{c['sw_url']} scope={c['scope']!r} updateViaCache={c['updateViaCache']!r}" for c in bad)[:300]
    else:
        out["verdict"] = "GREEN"
    return out


class _FirstOkThenFailServer:
    """Local one-shot-then-501 server, used ONLY by --selftest to make the repeat witness load-bearing.

    Binds an ephemeral port on 127.0.0.1, serves 200+javascript for the first hit of a URL and
    501 for every later hit - the exact shape of the redteam construction.  Serves a fixed tiny body
    so the byte checks are exercised too.
    """

    def __enter__(self):
        import http.server
        import threading

        seen = {}

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                n = seen.get(self.path, 0) + 1
                seen[self.path] = n
                if n == 1:
                    body = b"first-ok-probe-body"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/javascript")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    body = b"edge refuses now"
                    self.send_response(501)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

            def log_message(self, *a):  # silence
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        self.th = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.th.start()
        return self

    def __exit__(self, *exc):
        self.srv.shutdown()
        self.srv.server_close()
        return False


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
    def g_detail(urls, base=None, times=2):
        """verdict + the offending refs: a boolean-only red is not diagnosable (A-5 discipline)."""
        if not urls:                                   # A-3: an empty manifest proves nothing
            return {"verdict": "RED", "bad_refs": ["<empty manifest>"]}
        bad = []
        for u in urls:
            ref = u if u.startswith("/") else "/" + u
            v = repeated_verdict(ref, expect_ct_for(ref), live, base=base, times=times)
            if v["verdict"] != "GREEN":
                bad.append(f"{ref} statuses={v['statuses']} first_ct={v['probes'][0]['content_type']} "
                           f"disk={v['probes'][0]['disk_present']}")
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
    # Round-3 witness (redteam bus 5789163700): a dynamically-imported chunk that only the precache arm
    # probes, served 200 once and 501 afterwards.  With C/G/H repeating, G must see it.
    with _FirstOkThenFailServer() as edge3:
        g3 = g_detail(["/assets/maplibre-gl-CLqlEDxz.js"], base=f"http://127.0.0.1:{edge3.port}", times=2)
    arms.append({"arm": "G-killer:precache_url_breaks_on_second_probe", "expect": "RED",
                 "got": {"verdict": g3["verdict"], "error": "; ".join(g3["bad_refs"])[:160]}})
    g3b = g_detail(["/assets/maplibre-gl-CLqlEDxz.js"], base=None, times=2)
    arms.append({"arm": "G-true_positive:same_url_twice_on_real_server", "expect": "GREEN",
                 "got": {"verdict": g3b["verdict"], "error": "; ".join(g3b["bad_refs"])[:160]}})
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
    # A-9 witness (round 4): a shell answered with immutable/1-year must read RED through the SAME
    # predicate, while the real preview shell (no such header) must read GREEN-or-declared, never RED.
    fake = {"cache_control": "public, max-age=31536000, immutable"}
    v_imm = cache_semantics_verdict("/index.html", fake)
    v_real = cache_semantics_verdict("/", http_get("/"))
    v_asset = cache_semantics_verdict("/assets/index-DtQ86lsQ.js", fake)
    arms.append({"arm": "A9-killer:shell_immutable_is_red", "expect": "RED",
                 "got": {"verdict": v_imm["verdict"], "error": v_imm.get("reason")}})
    arms.append({"arm": "A9-true_positive:real_shell_revalidable", "expect": "GREEN",
                 "got": {"verdict": v_real["verdict"], "error": v_real.get("reason")}})
    arms.append({"arm": "A9-scope:hashed_asset_may_stay_immutable", "expect": "NOT_SHELL_RECORDED",
                 "got": {"verdict": v_asset["verdict"], "error": None}})
    # Round-5 witnesses (redteam `5789355832` ①): the old 600 default was a WIDENING, so the granted
    # window is now 0 unless it is asked for AND justified.  All four directions are asserted so
    # "declared" cannot become a blanket exemption and "0" cannot become a permanent red.
    A9_ENV = ("CNX_DEPLOY_SHELL_MAX_AGE", "CNX_DEPLOY_SHELL_MAX_AGE_BASIS")
    for a9_name, a9_cc, a9_expect, a9_env in (
        ("A9-killer:undeclared_max_age_300_is_red", "public, max-age=300", "RED", {}),
        ("A9-threshold_zero:max_age_0_revalidates", "max-age=0", "GREEN", {}),
        ("A9-killer:granted_window_without_basis_is_red", "public, max-age=600", "RED",
         {"CNX_DEPLOY_SHELL_MAX_AGE": "600"}),
        ("A9-declared:granted_window_with_basis_is_green", "public, max-age=600", "GREEN",
         {"CNX_DEPLOY_SHELL_MAX_AGE": "600",
          "CNX_DEPLOY_SHELL_MAX_AGE_BASIS": "selftest witness, not a production grant"}),
    ):
        saved = {k: os.environ.get(k) for k in A9_ENV}
        for k in A9_ENV:
            os.environ.pop(k, None)
        os.environ.update(a9_env)
        try:
            a9v = cache_semantics_verdict("/index.html", {"cache_control": a9_cc})
        finally:
            for k, prev in saved.items():
                if prev is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = prev
        arms.append({"arm": a9_name, "expect": a9_expect,
                     "got": {"verdict": a9v["verdict"], "error": a9v.get("reason"),
                             "allowed_max_age": a9v.get("allowed_max_age"),
                             "declared_basis": a9v.get("declared_basis")}})
    # Arm I witnesses (redteam `5789355832` ②): the real bundle must actually parse and pass - a killer
    # that only fires on synthetic text proves nothing if the production text never reaches the judge.
    entry_js = next((r for r in refs if r.endswith(".js")), None)
    i_fetch = http_text(entry_js) if entry_js else {"text": None, "sha256": None, "error": "no entry .js"}
    i_real = sw_register_verdict(i_fetch["text"], f"served {entry_js}")
    arms.append({"arm": "I-true_positive:served_bundle_registers({} calls)".format(
                     i_real.get("register_calls_parsed")),
                 "expect": "GREEN",
                 "got": {"verdict": i_real["verdict"], "error": i_real.get("reason"),
                         "served_sha256": str(i_fetch.get("sha256"))[:16],
                         "calls": i_real.get("calls"),
                         "mentions": i_real.get("register_mentions_in_code"),
                         "unresolved": i_real.get("unresolved_registrations")}})
    for i_name, i_text, i_expect in (
        ("I-killer:updateViaCache_all_is_red",
         'navigator.serviceWorker.register("/v10-sw.js",{scope:"/",updateViaCache:"all"})', "RED"),
        ("I-killer:non_root_scope_is_red",
         'navigator.serviceWorker.register("/v10-sw.js",{scope:"/app/",updateViaCache:"none"})', "RED"),
        ("I-killer:no_register_call_is_not_a_pass", "const a=1;export default a;", "RED"),
        ("I-killer:unreadable_bundle_bytes_are_red", None, "RED"),
        ("I-true_positive:synthetic_correct_call",
         'navigator.serviceWorker.register("/v10-sw.js",{scope:"/",updateViaCache:"none"})', "GREEN"),
        # redteam `5789637279`: the good call is prose, the broken one is the code that actually runs.
        ("I-killer:good_call_in_comment_variable_url_is_real",
         '// navigator.serviceWorker.register("/v10-sw.js",{scope:"/",updateViaCache:"none"})\n'
         'navigator.serviceWorker.register(window.__SW_PATH||"/v10-sw.js",{scope:"/",updateViaCache:"all"})',
         "RED"),
        ("I-killer:unresolved_registration_is_not_a_read",
         'navigator.serviceWorker.register(e,"{scope:\'/\',updateViaCache:\'all\'}")', "RED"),
        ("I-killer:nested_options_escape_the_parser",
         'navigator.serviceWorker.register("/v10-sw.js",{scope:"/",installUrl:{a:1},updateViaCache:"all"})',
         "RED"),
        ("I-killer:one_readable_one_unreadable_is_partial_read",
         'navigator.serviceWorker.register("/v10-sw.js",{scope:"/",updateViaCache:"none"});\n'
         'navigator.serviceWorker.register(SW_URL,{scope:"/",updateViaCache:"all"})', "RED"),
    ):
        iv = sw_register_verdict(i_text, "synthetic")
        arms.append({"arm": i_name, "expect": i_expect,
                     "got": {"verdict": iv["verdict"], "error": iv.get("reason")}})
    # Base-retargeting witnesses: the HTTP side must follow CNX_DEPLOY_BASE **at call time**.  Otherwise a
    # lane that runs this gauge against its own dist silently compares its files to MY :4781 bytes, which
    # is the A-3 "absent/foreign second side" family wearing a green badge.
    with _FirstOkThenFailServer() as edgeB:
        os.environ["CNX_DEPLOY_BASE"] = "http://127.0.0.1:%d" % edgeB.port
        try:
            b_env = repeated_verdict("/anything.js", "javascript", live, times=2)
        finally:
            del os.environ["CNX_DEPLOY_BASE"]
        b_back = repeated_verdict(killer_ref, "javascript", live, times=2)
    arms.append({"arm": "BASE-env:cnx_deploy_base_is_honoured_at_call_time", "expect": "RED",
                 "got": {"verdict": b_env["verdict"],
                         "error": "probe_base=%s statuses=%s" % (b_env["probes"][0]["base"], b_env["statuses"])}})
    arms.append({"arm": "BASE-restore:unset_again_reads_the_commander_chain", "expect": "GREEN",
                 "got": {"verdict": b_back["verdict"],
                         "error": "probe_base=%s statuses=%s" % (b_back["probes"][0]["base"], b_back["statuses"])}})
    # ---- D1-3 (arbiter) + redteam hole 2 witnesses.  Every one of these has BOTH directions: a binding that
    # never went red would be decoration.
    j_disk = live / killer_ref.lstrip("/")
    j_served = http_get(killer_ref)
    j_real_sha = sha256(j_disk) if j_disk.is_file() else "MISSING"
    j_cases = (
        ("J-true_positive:served_and_disk_match_binding",
         manifest_binding_row(killer_ref, j_served["status"], j_served["sha256"], j_real_sha,
                              {"sha256": j_real_sha, "bytes": j_disk.stat().st_size if j_disk.is_file() else 0})),
        ("J-killer:name_kept_content_changed",                    # the redteam construction, as a judge case
         manifest_binding_row(killer_ref, j_served["status"], "0" * 64, j_real_sha,
                              {"sha256": j_real_sha, "bytes": 1})),
        ("J-killer:unbound_asset_is_not_a_pass",
         manifest_binding_row(killer_ref, j_served["status"], j_served["sha256"], j_real_sha, None)),
    )
    for j_name, j_row in j_cases:
        arms.append({"arm": j_name, "expect": {"J-true_positive:served_and_disk_match_binding": "GREEN"}.get(j_name, "RED"),
                     "got": {"verdict": j_row["verdict"], "error": j_row.get("why")}})
    j_missing = asset_manifest_verdict(live / "__cnx_no_manifest_dir__", [killer_ref])
    arms.append({"arm": "J-killer:missing_manifest_is_not_a_pass", "expect": "RED",
                 "got": {"verdict": j_missing["verdict"], "error": j_missing.get("reason")}})
    # ---- surface-sides (my own hole + redteam `5790009042` hole 2)
    sides_cmdr = surface_sides_check(live)
    sides_foreign = surface_sides_check(pathlib.Path("D:/moodle/_qoder_cmdr_canary_0923/foreign_dist"))
    sides_traversal = surface_sides_check(pathlib.Path(CMDR_DIST + "/../_qoder_cmdr_canary_0923/trav"))
    arms.append({"arm": "SIDES-true_positive:cmdr_dist_and_default_base_agree", "expect": "OK",
                 "got": {"verdict": "OK" if sides_cmdr["ok"] else "REFUSED",
                         "error": "resolved=%s" % sides_cmdr["info"].get("resolved_serve")}})
    arms.append({"arm": "SIDES-killer:foreign_dist_without_base_is_refused", "expect": "REFUSED",
                 "got": {"verdict": "OK" if sides_foreign["ok"] else "REFUSED",
                         "error": sides_foreign["info"].get("refuse_reason")}})
    arms.append({"arm": "SIDES-killer:dotdot_traversal_resolves_outside_and_is_refused", "expect": "REFUSED",
                 "got": {"verdict": "OK" if sides_traversal["ok"] else "REFUSED",
                         "error": "resolved=%s" % sides_traversal["info"].get("resolved_serve")}})
    # redteam `5790009042` hole 1 exactly: foreign base + MY dist as --serve.  Refusing only the "base was
    # left defaulted" direction would have let this through, so both directions are asserted here.
    os.environ["CNX_DEPLOY_BASE"] = "http://127.0.0.1:5899"
    try:
        sides_reversed = surface_sides_check(live)
    finally:
        del os.environ["CNX_DEPLOY_BASE"]
    sides_reversed_ok = surface_sides_check(live)
    arms.append({"arm": "SIDES-killer:foreign_base_with_cmdr_serve_is_refused", "expect": "REFUSED",
                 "got": {"verdict": "OK" if sides_reversed["ok"] else "REFUSED",
                         "error": "%s | base=%s" % (sides_reversed["info"].get("pairing"),
                                                     sides_reversed["info"].get("http_base"))}})
    arms.append({"arm": "SIDES-true_positive:same_pair_after_unset_passes", "expect": "OK",
                 "got": {"verdict": "OK" if sides_reversed_ok["ok"] else "REFUSED",
                         "error": "base=%s" % sides_reversed_ok["info"].get("http_base")}})
    # ---- D1-CLOSE-1: persistence of refusals is proved STRUCTURALLY, not by one happy artifact.
    rp = refusal_persistence_proof()
    arms.append({"arm": "REFUSE-proof:no_undocumented_refusal_exit_in_this_file", "expect": "GREEN",
                 "got": {"verdict": rp["verdict"],
                         "error": "naked=%s routed=%s min=%s" % (rp["naked_refusal_returns"],
                                                                  rp["routed_refusals"],
                                                                  rp["min_routed_required"])}})
    # The scanner itself must be falsifiable, or it is decoration (redteam `5792183031` holes A + B).
    for s_name, s_src, s_expect, s_min in (
        ("REFUSE-killer:bare_refusal_return_is_caught", "def f():\n    return 5\n", "RED", 0),
        ("REFUSE-killer:ifexp_refusal_is_caught", "def f(ok):\n    return 0 if ok else 9\n", "RED", 0),
        ("REFUSE-killer:function_other_than_main_is_not_exempt",
         "def main():\n    return 0\ndef side():\n    return 7\n", "RED", 0),
        ("REFUSE-true_positive:refuse_call_is_compliant",
         "def f(c):\n    return refuse(c, 'tag', 5, 'reason')\n", "GREEN", 1),
    ):
        sc = refusal_scan(s_src, min_routed=s_min)
        arms.append({"arm": s_name, "expect": s_expect,
                     "got": {"verdict": sc["verdict"], "error": str(sc["naked_refusal_returns"])[:120]}})
    # redteam `5792183031` ②: the predicate used to lstrip every leading slash.
    for n_name, n_ref, n_expect in (
        ("TEMPORAL-true_positive:canonical_root_ref_is_owned", "/index.html", "OK"),
        ("TEMPORAL-killer:no_leading_slash_is_not_owned", "index.html", "REFUSED"),
        ("TEMPORAL-killer:double_leading_slash_is_not_owned", "//index.html", "REFUSED"),
        ("TEMPORAL-killer:hashed_asset_may_not_be_waived", "/assets/index-CrAwWm5f.js", "REFUSED"),
    ):
        arms.append({"arm": n_name, "expect": n_expect,
                     "got": {"verdict": "OK" if temporal_declaration_ok(n_ref) else "REFUSED", "error": None}})
    # ---- D1-CLOSE-2 (PRE_ACTION_TEMPORAL_OBLIGATION_V1), both directions each.
    ob = [{"ref": "/index.html", "src_sha256": "AA", "discharged_by": "G arm"}]
    led_ok = obligation_ledger_verdict(ob, {"/index.html": {"verdict": "GREEN", "probes": [{"sha256": "AA"}]}})
    led_gone = obligation_ledger_verdict(ob, {})          # the post-switch witness removed/broken
    led_wrong = obligation_ledger_verdict(ob, {"/index.html": {"verdict": "GREEN", "probes": [{"sha256": "BB"}]}})
    led_none = obligation_ledger_verdict([], {})
    for t_name, t_led, t_expect in (
        ("TEMPORAL-true_positive:digest_match_discharges", led_ok, "DISCHARGED"),
        ("TEMPORAL-killer:missing_post_witness_blocks_final_green", led_gone, "UNDISCHARGED"),
        ("TEMPORAL-killer:digest_mismatch_is_not_discharge", led_wrong, "UNDISCHARGED"),
        ("TEMPORAL-true_positive:no_obligations_is_none_pending", led_none, "NONE_PENDING"),
    ):
        arms.append({"arm": t_name, "expect": t_expect,
                     "got": {"verdict": t_led["verdict"], "error": str(t_led["undischarged"])[:160]}})
    dead = asset_verdict("/v10-sw.js", "javascript", live, base="http://127.0.0.1:59999")
    arms.append({"arm": "F-killer:unreachable_surface_is_red_not_absent", "expect": "RED",
                 "got": dead})
    # Second-attack witness (redteam bus 5788977359): a single probe cannot see
    # "first request fine, later requests broken".  Both directions are asserted.
    tp = repeated_verdict(killer_ref, "javascript", live, times=2)
    arms.append({"arm": "F-true_positive:two_live_probes_agree", "expect": "GREEN",
                 "got": {"verdict": tp["verdict"], "error": None, "status": tp["statuses"]}})
    with _FirstOkThenFailServer() as edge:
        st = repeated_verdict("/assets/edge-stateful.js", "javascript", live,
                              base=f"http://127.0.0.1:{edge.port}", times=2)
    arms.append({"arm": "F-killer:edge_serves_first_then_refuses_later", "expect": "RED",
                 "got": {"verdict": st["verdict"], "error": None, "status": st["statuses"]}})
    # B-arm (redteam 2026-09-23): the live index must name refs that actually resolve, and the
    # previous generation's entry must be absent.  Both halves are asserted as separate fields so
    # "the old name is gone" is a claim rather than something derived from a before/after diff.
    idx = http_get("/")
    body_html = ""
    if idx["status"] == 200:
        req = urllib.request.Request(base_url() + "/")
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
        "base": base_url(), "serve": str(serve), "overall": "GREEN" if ok else "RED",
        "gauge": gauge_self_binding(),
        "arms": [{"arm": a["arm"], "expect": a["expect"], "got": a["got"]["verdict"],
                  "status": a["got"].get("status"), "content_type": a["got"].get("content_type"),
                  "is_html_fallback": a["got"].get("is_html_fallback"),
                  "body_sha256": a["got"].get("sha256"), "disk_sha256": a["got"].get("disk_sha256"),
                  "disk_present": a["got"].get("disk_present"), "error": a["got"].get("error"),
                  "body_size": a["got"].get("body_size"), "disk_bytes": a["got"].get("disk_bytes")}
                 for a in arms]}, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"[receipt] {dest}")
    if not ok:
        return refuse({"argv": sys.argv[1:], "selftest_receipt": str(dest),
                       "mismatched_arms": [a["arm"] for a in arms if a["got"]["verdict"] != a["expect"]][:12]},
                      "refused_selftest_failed", 9,
                      f"selftest arms did not all match: {sum(1 for a in arms if a['got']['verdict'] != a['expect'])}"
                      f"/{len(arms)} mismatched", quiet=True)
    return 0


def f_surface_probes(refs: list[str], serve: pathlib.Path, times: int | None = None) -> list[dict]:
    """Probe every configured user-facing surface for `refs`.  Shared by the pre-flight and the
    post-switch receipt so the two can never disagree by using two different judges."""
    probes = []
    for label, base in (("proxy_4782", os.environ.get("CNX_DEPLOY_PROXY_BASE")),
                        ("tunnel", os.environ.get("CNX_DEPLOY_TUNNEL_BASE"))):
        if not base:
            probes.append({"surface": label, "verdict": "NOT_CONFIGURED", "base": None})
            continue
        for ref in refs:
            probes.append({"surface": label, "base": base,
                           "got": repeated_verdict(ref, expect_ct_for(ref), serve, base=base,
                                                   auth_file=os.environ.get("CNX_DEPLOY_AUTH_FILE"),
                                                   times=times or int(os.environ.get("CNX_DEPLOY_PROBE_TIMES", "2")))})
    return probes


def f_verdict_of(probes: list[dict], declared_unprobed: bool) -> str:
    # a configured surface stores its verdict under "got"; only the unconfigured placeholder has a top-level
    # "verdict".  Reading one shape from both made a *configured* run crash AFTER the index was switched.
    unconfigured = any(p.get("verdict") == "NOT_CONFIGURED" for p in probes)
    if unconfigured and declared_unprobed:
        return "F_UNPROBED_DECLARED"          # declared gap, kept OUT of all_green by name
    if unconfigured:
        return "RED"                          # fail closed: absent comparison != passed comparison
    return "GREEN" if all(p.get("got", {}).get("verdict") == "GREEN" for p in probes) else "RED"


def persist_receipt(receipt: dict, tag: str) -> pathlib.Path:
    """A refusal is the artifact most worth keeping.  Until 15:29 the early-return paths wrote nothing at
    all, so "the gauge refused to switch" left no readable reason behind - the same family as not measuring."""
    out = pathlib.Path(__file__).with_name("receipts")
    out.mkdir(exist_ok=True)
    dest = out / f"deploy_{tag}_{time.strftime('%m%d_%H%M%S')}.json"
    receipt["refusal_tag"] = tag
    dest.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"[receipt] {dest}")
    return dest


REFUSAL_RC = (4, 5, 6, 7, 9)          # every non-success early exit main() can take
MIN_ROUTED_REFUSALS = 12              # main() had 13 refusal sites before this change; keep it honest


def refuse(ctx: dict, tag: str, rc: int, reason: str, quiet: bool = False) -> int:
    """ONE way out of main() when we say no (arbiter D1-CLOSE-1, bus `5791893215`).

    A refusal that leaves no artifact is the same family as not measuring: "I refused" is exactly the
    claim a later reader cannot check.  `ctx` may be a partial receipt - a minimal one (argv + known
    paths + reason + timestamp + gauge binding) is still auditable.
    """
    rec = dict(ctx) if isinstance(ctx, dict) else {}
    rec.setdefault("gauge", gauge_self_binding())
    rec.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    rec["refusal_tag"] = tag
    rec["refusal_rc"] = rc
    rec["reason"] = reason
    if not quiet:
        print("REFUSED:", reason)
    persist_receipt(rec, tag)
    return rc


def refusal_scan(source: str, min_routed: int = 1) -> dict:
    """Pure scanner: any `return` carrying a REFUSAL_RC constant anywhere in its expression
    (bare constant, `IfExp` branch, `BoolOp`, tuple...) is a refusal that leaves no artifact
    unless the return IS a `refuse(...)` call.  Kept pure so --selftest can drive it both ways."""
    tree = ast.parse(source)

    def carries_refusal_code(node: ast.AST) -> bool:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value in REFUSAL_RC:
                return True
        return False

    naked, routed, per_fn = [], 0, {}
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for n in ast.walk(fn):
            if not isinstance(n, ast.Return) or n.value is None:
                continue
            is_refuse_call = isinstance(n.value, ast.Call) and \
                getattr(n.value.func, "id", getattr(n.value.func, "attr", "")) == "refuse"
            if is_refuse_call:
                routed += 1
                continue
            if carries_refusal_code(n.value):
                naked.append(f"{fn.name}:{n.lineno}")
                per_fn[fn.name] = per_fn.get(fn.name, 0) + 1
    return {"verdict": "GREEN" if (not naked and routed >= min_routed) else "RED",
            "naked_refusal_returns": naked,
            "functions_with_violations": per_fn,
            "routed_refusals": routed,
            "scope": "every FunctionDef in the scanned source; IfExp/BoolOp/Tuple bodies included",
            "rule": "no return may carry a REFUSAL_RC constant unless it is a refuse() call"}


def refusal_persistence_proof() -> dict:
    """Structural regression: one real refusal artifact proves ONE path, not universal persistence.

    Redteam `5792183031` drove two holes in the first version of this check:
      A) it scanned only `main()`, so `selftest()`'s own failure exit left nothing on disk;
      B) `return 0 if ok else 9` is an `ast.IfExp`, not a bare constant, so a refusal could hide in it.
    Both are closed in `refusal_scan`, and the scanner itself is exercised by synthetic arms.
    """
    out = refusal_scan(pathlib.Path(__file__).read_text(encoding="utf-8"), MIN_ROUTED_REFUSALS)
    out["min_routed_required"] = MIN_ROUTED_REFUSALS
    return out


ACTION_OWNED_ROOT_REFS = ("index.html", "manifest.webmanifest", "sw.js", "v10-sw.js")


def temporal_declaration_ok(ref: str, owned: tuple = ACTION_OWNED_ROOT_REFS) -> bool:
    """PRE_ACTION_TEMPORAL_OBLIGATION_V1, half 1: only a ref the action itself replaces may be declared
    'not yet published'.  Anything else using that state is hiding a real gap behind a waiver.

    Redteam `5792183031` ②: the first version `lstrip(\"/\")`-ed the ref, so `index.html` (no slash) and
    `//index.html` / `///index.html` all passed the predicate.  None of those is how the switch addresses
    a root file, so they are now rejected: a ref that is not exactly `/name` gets judged strictly like
    any other asset (a stricter尺, not a loophole).
    """
    if not ref.startswith("/") or ref.count("/") != 1:
        return False
    return ref[1:] in owned


def obligation_ledger_verdict(obligations: list[dict], post_rows: dict) -> dict:
    """PRE_ACTION_TEMPORAL_OBLIGATION_V1, half 2: a temporal declaration is a DEBT, and it is discharged
    only by the named strict post-action arm proving the shipped bytes are what is now served."""
    discharged, undischarged = [], []
    for ob in obligations:
        got = post_rows.get(ob["ref"], {}) or {}
        served_sha = (got.get("probes") or [{}])[0].get("sha256")
        if got.get("verdict") == "GREEN" and served_sha and served_sha == ob.get("src_sha256"):
            discharged.append({"ref": ob["ref"], "served_sha256": served_sha, "matches_src": True,
                               "discharged_by": ob.get("discharged_by")})
        else:
            undischarged.append({"ref": ob["ref"], "post_switch_verdict": got.get("verdict"),
                                 "served_sha256": served_sha, "expected_src_sha256": ob.get("src_sha256"),
                                 "why": "post-switch strict arm did not prove this ref equals the shipped bytes"})
    verdict = ("NONE_PENDING" if not obligations
               else ("DISCHARGED" if not undischarged else "UNDISCHARGED"))
    return {"rule": "PRE_ACTION_TEMPORAL_OBLIGATION_V1 - DECLARED_NOT_YET_PUBLISHED_PRE_<ACTION> is a debt; "
                    "final overall may not go GREEN while anything is UNDISCHARGED",
            "pending_at_pre_flight": len(obligations), "discharged": discharged,
            "undischarged": undischarged, "verdict": verdict}


def preflight_before_switch(src: pathlib.Path, serve: pathlib.Path, new_refs: list[str],
                            old_js: str | None, allow_unprobed: bool) -> dict:
    """The rule this tool owed since 13:02: **every read-only judgement runs BEFORE the switch**.

    The 13:0x deploy switched `index.html` and only then reached the code that crashed, so for ~6 minutes
    the phone was on a generation with no receipt.  Union-before-switch is what kept the user off a white
    screen, not luck - but a *sequence* fix is available too: nothing below writes anything, so any red
    here stops the deploy while the old generation is still the one being served.

    Which arms can legitimately run pre-switch: the new assets are already unioned into `serve/`, so they
    resolve; the NEW service worker and the NEW bundle are read from the build export (`src`), because they
    are only served after the switch.  B-after/H/D are inherently post-switch (they ask "what does the
    server hand out now that we switched") and stay in the post-switch receipt.
    """
    out: dict = {}
    html = (src / "index.html").read_text(encoding="utf-8", errors="replace")
    out["B_pre_index_names_new_refs"] = {
        "refs": new_refs, "all_present": all(r in html for r in new_refs),
        "verdict": "GREEN" if all(r in html for r in new_refs) else "RED"}
    out["C_pre_new_assets_reach_the_live_server"] = [
        repeated_verdict(r, expect_ct_for(r), src, times=PROBE_TIMES) for r in new_refs]
    # G_pre: parse the NEW sw's precache manifest out of the build export and resolve each url live.
    # Self-referential flaw found on the FIRST live use (15:25, deploy refused at exit 4): a precache entry
    # naming an UNHASHED root file (`/index.html`) can never be green before the switch, because the server
    # still answers the previous generation for exactly that path - so a strict pre-switch judge on those
    # refs is a permanent red, which is as useless as a permanent green.  Root docs are therefore NAMED
    # gaps pre-switch, with both digests recorded; the post-switch G arm keeps full strictness.
    ROOT_DOC_REFS = ("index.html", "manifest.webmanifest", "sw.js", "v10-sw.js")
    obligations = []
    g_pre = []
    for name in ("sw.js", "v10-sw.js"):
        swf = src / name
        if not swf.is_file():
            continue
        urls = precache_urls(swf.read_text(encoding="utf-8", errors="replace"))
        entry = {"sw": name, "sw_sha256_src": sha256(swf), "urls_found": len(urls), "probes": []}
        asset_rows, declared_rows = [], []
        for u in urls:
            ref = u if u.startswith("/") else "/" + u
            if temporal_declaration_ok(ref):
                served = http_get(ref)
                srcp = src / ref.lstrip("/")
                ob = {"ref": ref,
                      "verdict": "DECLARED_NOT_YET_PUBLISHED_PRE_SWITCH",
                      "src_sha256": sha256(srcp) if srcp.is_file() else None,
                      "src_present": srcp.is_file(),
                      "served_status": served["status"], "served_sha256": served["sha256"],
                      "must_discharge_post_action": True,
                      "discharged_by": "post-switch arms G_PRECACHE_INTEGRITY + D_SERVICE_WORKER "
                                       "(strict, same predicate, after the root file is replaced)"}
                entry["probes"].append(ob)
                declared_rows.append(ref)
                obligations.append(ob)
                continue
            v = repeated_verdict(ref, expect_ct_for(ref), src, times=PROBE_TIMES)
            asset_rows.append(v)
            entry["probes"].append({"ref": ref, "got": v})
        # PRE_ACTION_TEMPORAL_OBLIGATION_V1: the declaration is only legal for the fixed action-owned set.
        illegal = [o for o in declared_rows if o.lstrip("/") not in ROOT_DOC_REFS]
        assets_ok = bool(asset_rows) and all(v["verdict"] == "GREEN" for v in asset_rows)
        entry["hashed_assets_checked"] = len(asset_rows)
        entry["root_docs_declared_pending"] = declared_rows
        entry["illegal_temporal_declarations"] = illegal
        if illegal:
            entry["verdict"] = "RED"
            entry["reason"] = f"non-root ref(s) used a temporal declaration: {illegal}"
        elif not assets_ok and asset_rows:
            entry["verdict"] = "RED"
            entry["reason"] = "; ".join(str(v.get("red_refs")) for v in asset_rows if v["verdict"] != "GREEN")[:300]
        elif asset_rows:
            entry["verdict"] = "GREEN"
        else:
            entry["verdict"] = ("DECLARED_NO_PRECACHE_ARRAY" if name in DECLARED_NO_PRECACHE else "RED")
        g_pre.append(entry)
    out["G_pre_precache_of_the_new_sw_resolves"] = g_pre
    # I_pre: the registration parameters of the bundle about to go live, read from the build export.
    i_pre = []
    for ref in [r for r in new_refs if r.endswith(".js")]:
        p = src / ref.lstrip("/")
        text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None
        v = sw_register_verdict(text, f"src {ref}")
        v["src_sha256"] = sha256(p) if p.is_file() else None
        i_pre.append(v)
    out["I_pre_sw_register_params_of_new_bundle"] = i_pre
    f_pre = f_surface_probes([r for r in new_refs if r.endswith(".js")] + ["/"], serve)
    out["F_pre_user_surfaces"] = {"probes": f_pre, "verdict": f_verdict_of(f_pre, allow_unprobed)}
    if old_js:
        g = asset_verdict(old_js, expect_ct_for(old_js), serve)
        out["A_pre_current_generation_still_served"] = {"ref": old_js, "got": g}

    def _reds(node) -> list[str]:
        hits = []
        if isinstance(node, dict):
            if node.get("verdict") == "RED":
                who = node.get("ref") or node.get("sw") or node.get("path") or node.get("source") or "?"
                detail = (node.get("reason") or node.get("why") or node.get("red_refs")
                          or (node.get("probes") and [p.get("status") for p in node["probes"][:1]] or None)
                          or node.get("statuses") or "")
                hits.append(f"{who} :: {str(detail)[:200]}")
            for v in node.values():
                hits += _reds(v)
        elif isinstance(node, list):
            for v in node:
                hits += _reds(v)
        return hits
    reds = _reds(out)
    # F_UNPROBED_DECLARED is a named gap, not a red: it stays out of all_green by name (A-3), exactly as
    # in the post-switch receipt, so the pre-flight cannot be greener than the thing it gates.
    #
    # D1-CLOSE-2 (arbiter `5791893215`): a temporal DECLARED_* obligation may NOT live inside an aggregate
    # called GREEN - that is one refactor away from a permanent waiver.  The pre-flight therefore reports
    # two separate states and never uses the word GREEN while something is still owed to the post-switch arms.
    out["temporal_obligations"] = obligations
    out["switch_readiness"] = "BLOCKED" if reds else "READY_TO_SWITCH"
    out["promotion_state"] = ("PENDING_POST_SWITCH" if obligations
                              else ("NOT_READY" if reds else "NO_TEMPORAL_OBLIGATIONS"))
    out["verdict"] = out["switch_readiness"] if not reds else "RED"
    out["reds"] = reds[:12]
    out["rule"] = ("read-only arms judged against the live server + build export BEFORE index.html moves; "
                   "BLOCKED means the old generation stays served and nothing is written; "
                   "PENDING_POST_SWITCH means final overall may not go GREEN until every obligation is "
                   "discharged by the named strict post-switch arm")
    return out


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
    ap.add_argument("--preflight-check", action="store_true",
                    help="read-only: run the PRE-SWITCH arms against --src and the live server, print the "
                         "receipt and stop.  Nothing is unioned, copied or switched.")
    a = ap.parse_args()
    if a.selftest:
        return selftest(pathlib.Path(a.serve))
    if a.preflight_check:
        if not a.src:
            return refuse({"argv": sys.argv[1:], "serve": a.serve}, "refused_preflight_no_src", 5,
                          "--preflight-check needs --src (a build export, or the live dist to self-check)")
        s, sv = pathlib.Path(a.src), pathlib.Path(a.serve)
        # Redteam `5790009042` hole 1: this read-only branch used to return BEFORE the mixed-sides check, so it
        # printed PREFLIGHT GREEN while HTTP came from one deployment and files from another.  Same judge now.
        pf_sides = surface_sides_check(sv)
        if not pf_sides["ok"]:
            return refuse({"what": "PREFLIGHT REFUSED before any judgement (mixed sides)",
                           "src": str(s), "serve": str(sv), "surface_base": pf_sides["info"],
                           "hint": "set CNX_DEPLOY_BASE=<your static server>, or "
                                   "CNX_DEPLOY_BASE_IS_CMDR_LIVE=1 to say you really mean my chain"},
                          "refused_preflight_mixed_sides", 5, pf_sides["info"].get("refuse_reason") or "")
        srefs = asset_refs((s / "index.html").read_text(encoding="utf-8", errors="replace"))
        oidx = sv / "index.html"
        orefs = asset_refs(oidx.read_text(encoding="utf-8", errors="replace")) if oidx.is_file() else []
        pf = preflight_before_switch(s, sv, srefs, next((r for r in orefs if r.endswith(".js")), None),
                                     bool(a.allow_proxy_unprobed))
        print(json.dumps(pf, indent=1, ensure_ascii=False)[:3000])
        out = pathlib.Path(__file__).with_name("receipts")
        out.mkdir(exist_ok=True)
        dest = out / f"preflight_{time.strftime('%m%d_%H%M%S')}.json"
        dest.write_text(json.dumps({"what": "PREFLIGHT ONLY - no union, no copy, no switch",
                                    "src": str(s), "serve": str(sv), "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                    "surface_base": pf_sides["info"], "gauge": gauge_self_binding(),
                                    "src_index_refs": srefs, "served_index_refs": orefs, "preflight": pf},
                                   indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        print(f"[receipt] {dest}\nPREFLIGHT {pf['switch_readiness']} promotion={pf['promotion_state']}")
        if pf["switch_readiness"] != "READY_TO_SWITCH":
            return refuse({"what": "PREFLIGHT BLOCKED", "src": str(s), "serve": str(sv),
                           "preflight": pf, "surface_base": pf_sides["info"]},
                          "refused_preflight_blocked", 4,
                          "read-only pre-flight is BLOCKED: " + "; ".join(str(x)[:120] for x in pf["reds"][:4]),
                          quiet=True)
        return 0
    if not a.src or not a.live_tree or not a.sha:
        return refuse({"argv": sys.argv[1:], "serve": a.serve}, "refused_missing_arguments", 5,
                      "--src, --live-tree and --sha are required unless --selftest is given")
    src, serve, tree = pathlib.Path(a.src), pathlib.Path(a.serve), pathlib.Path(a.live_tree)

    receipt: dict = {"sha": a.sha, "src": str(src), "serve": str(serve), "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                     "gauge": gauge_self_binding()}

    # A-3 applied to the gauge itself: disk side = --serve, HTTP side = base_url().  One implementation,
    # used by both the deploy path and the read-only --preflight-check branch (redteam hole 1).
    sides = surface_sides_check(serve)
    receipt["surface_base"] = sides["info"]
    if not sides["ok"]:
        return refuse(receipt, "refused_mixed_sides", 5,
                      (sides["info"].get("refuse_reason") or "") +
                      " | fix: CNX_DEPLOY_BASE=http://127.0.0.1:<your static port>, or "
                      "CNX_DEPLOY_BASE_IS_CMDR_LIVE=1 when you really do mean to probe my chain")

    # --- precondition 0: the tree must not have the **build inputs** dirty in a way that flatters us
    if not a.skip_build_check:
        dirty = subprocess.run(["git", "-C", str(tree), "status", "--porcelain", "--", "frontend/"],
                               capture_output=True, text=True).stdout.strip()
        receipt["frontend_dirty"] = dirty
        # `vite build` reads the working tree, so a dirty INPUT would ship code nobody accepted.  Dirt that
        # cannot reach the bundle (e2e specs, review tooling) is a different claim - still named, but it must
        # not silently block a deploy nor silently approve one.
        BUILD_INPUTS = ("frontend/src/", "frontend/index.html", "frontend/public/", "frontend/vite.config",
                        "frontend/tsconfig", "frontend/package.json", "frontend/package-lock.json")
        input_lines = [l for l in dirty.splitlines() if any(b in l for b in BUILD_INPUTS)]
        non_input = [l for l in dirty.splitlines() if l not in input_lines]
        receipt["build_input_dirty"] = input_lines
        if input_lines:
            receipt["refused_because"] = input_lines
            return refuse(receipt, "refused_dirty_build_inputs", 5,
                          "frontend/ build inputs are dirty, refusing to deploy a half-built tree: "
                          + " | ".join(l[:120] for l in input_lines[:6]))
        if non_input:
            receipt["declared_non_input_dirt"] = {
                "verdict": "DECLARED_NON_INPUT_DIRT",
                "files": non_input,
                "why": "these paths do not feed vite build (frontend/e2e, review tooling, ...), so they cannot"
                       " change the bundle bytes - but this is a NAMED gap, not a pass: the receipt says which"
                       " files were dirty and that they were excluded from the build-input set"}
            print(f"[declared] {len(non_input)} dirty frontend path(s) outside the build inputs (named, not silenced):")
            for l in non_input[:8]:
                print("   ", l[:150])
        tip = subprocess.run(["git", "-C", str(tree), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        receipt["tree_tip"] = tip
        if tip != a.sha[:len(tip)] and not a.sha.startswith(tip):
            return refuse(receipt, "refused_sha_not_tree_tip", 5,
                          f"--sha {a.sha} does not match tree tip {tip}")

    new_index = src / "index.html"
    if not new_index.is_file():
        return refuse(receipt, "refused_no_built_index", 5, f"{new_index} missing - nothing was built")
    new_html = new_index.read_text(encoding="utf-8")
    new_refs = asset_refs(new_html)
    receipt["new_index_refs"] = new_refs
    if not new_refs:
        return refuse(receipt, "refused_index_names_nothing", 5,
                      "the built index.html references no /assets/ file")
    for ref in new_refs:
        if not (src / ref.lstrip("/")).is_file():
            return refuse(receipt, "refused_unproduced_asset", 5,
                          f"built index.html references {ref} but the build did not produce it")

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
            return refuse(receipt, "refused_union_name_collision", 6,
                          f"{dst.name} exists with DIFFERENT bytes - a name collision would silently swap "
                          "content under an already-published URL; resolve by hand")
        shutil.copy2(p, dst)
        added.append(p.name)
        copied.append(p.name)
    receipt["assets_union"] = {"added": added, "already_identical": [n for n in copied if n not in added],
                               "total_in_serve_assets": len(list(dst_assets.iterdir()))}
    # D1-3: bind every published hashed filename to the bytes we actually have at this moment, BEFORE any arm
    # is judged, so "the name claims digest X" becomes checkable instead of assumed.
    mf_doc = asset_manifest_write(serve)
    receipt["asset_manifest"] = {"path": str(serve / "assets_manifest.json"),
                                 "assets_bound": len(mf_doc["assets"]), "gauge": mf_doc["gauge"]}
    print(f"[union] added {len(added)} new asset(s); {len(copied) - len(added)} already byte-identical; "
          f"{len(mf_doc['assets'])} name->digest bindings written")

    # --- phase 2: PROVE the new assets answer before the switch (gate E lives here).
    # D1-4 (arbiter `5789539216`): this used to be ONE `http_get` with its own inline verdict, i.e. the gate
    # that decides whether to switch was the least-observed arm in the tool.  Same judge as everywhere else.
    pre = [repeated_verdict(ref, expect_ct_for(ref), src, times=PROBE_TIMES) for ref in new_refs]
    receipt["pre_switch_asset_probes"] = pre
    reds = [v for v in pre if v["verdict"] != "GREEN"]
    if reds:
        for v in reds:
            for r in v["probes"]:
                if r["verdict"] != "GREEN":
                    print(f"  {r['path']} status={r['status']} ct={r['content_type']} head={r['head_bytes']!r} "
                          f"body_sha={str(r['sha256'])[:12]} disk_sha={str(r['disk_sha256'])[:12]} "
                          f"disk_present={r['disk_present']}")
        return refuse(receipt, "refused_pre_switch_gate", 7,
                      "E: 200 alone is never sufficient - " +
                      ", ".join(str(v.get("red_refs"))[:120] for v in reds[:4]))
    print(f"[gate] {len(pre)} new asset(s) reachable x{PROBE_TIMES}, real bytes vs the build export, no HTML fallback")

    # --- phase 2b: PRE-FLIGHT (the 13:02 lesson).  Every read-only arm is judged here, so a red stops
    # the deploy while the CURRENT generation is still what the user gets - never "switch, then find out".
    pf = preflight_before_switch(src, serve, new_refs, old_js, bool(getattr(a, "allow_proxy_unprobed", False)))
    receipt["preflight_before_switch"] = pf
    print(f"[preflight] {pf['switch_readiness']} / promotion={pf['promotion_state']}  "
          f"(B_pre/C_pre/G_pre/I_pre/F_pre/A_pre; reds={len(pf['reds'])})")
    for line in pf["reds"]:
        print("  RED:", str(line)[:180])
    if pf["switch_readiness"] != "READY_TO_SWITCH":
        return refuse(receipt, "refused_preflight", 4,
                      "pre-flight is BLOCKED, so the old generation stays live and nothing is switched: "
                      + "; ".join(str(x)[:120] for x in pf["reds"][:4]))

    # --- phase 3: BACKUP then SWITCH the unhashed root files
    stamp = time.strftime("%H%M%S")
    # D1-6 (arbiter `5789539216`): seconds alone still collide (`mkdir(exist_ok=True)` silently reused a
    # directory), which would let arm H measure "some generation inside this second".  Unique id, fail closed.
    gen_id = f"{stamp}_{time.time_ns()}"
    bak = serve.parent / f"dist_bak_{gen_id}"
    try:
        bak.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return refuse(receipt, "refused_backup_collision", 9,
                      f"backup dir {bak} already exists - refusing to mix two generations into one anchor")
    receipt["backup_generation_id"] = gen_id
    receipt["previous_index_sha256"] = sha256(old_index) if old_index.is_file() else None
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
    if not old_js:
        # boundary (i) named by the redteam: previously this arm just vanished with no explanation.
        a_old = {"ref": None, "verdict": "DECLARED_NO_OLD_JS",
                 "reason": "previous index.html named no .js asset - A cannot compare anything; "
                           "this is a declared gap, not a pass"}
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
        req = urllib.request.Request(base_url() + "/")
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
        # C now repeats too (redteam round 3): one arm, one probe, is blind to "first fine, later broken"
        c_new.append(repeated_verdict(ref, expect_ct_for(ref), serve, times=PROBE_TIMES))
    d_sw = []
    for name in ("sw.js", "v10-sw.js"):
        # D1-4 (arbiter): these were single `http_get` calls with a hand-rolled verdict while C/G/H repeated.
        # The service worker is the file that decides whether a stale client survives - it is not a minor ref.
        d_sw.append(repeated_verdict("/" + name, expect_ct_for(name), serve, times=PROBE_TIMES))

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
            entry["probes"].append({"ref": ref,
                                    "got": repeated_verdict(ref, expect_ct_for(ref), serve, times=PROBE_TIMES)})
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
            h_prev.append({"ref": r, "got": repeated_verdict(r, expect_ct_for(r), serve, times=PROBE_TIMES)})
    h_same_as_current = bool(prev_index and prev_index.is_file() and sha256(prev_index) == sha256(serve / "index.html")
                             if (serve / "index.html").is_file() else False)
    h_prev_verdict = ("GREEN" if h_prev and all(x["got"]["verdict"] == "GREEN" for x in h_prev)
                      else ("NOT_CONFIGURED" if not h_prev else "RED"))
    if h_prev_verdict == "GREEN" and h_same_as_current:
        # boundary (ii) named by the redteam: with an unchanged index, "previous generation" IS this
        # generation, so H proves nothing beyond C.  Say so instead of reporting a stronger claim.
        h_prev_verdict = "GREEN_H_EQ_C_NO_CHANGE_DEPLOY"

    # F: the surface the user actually reaches - auth proxy and public tunnel - probed for the NEW
    # bundle, not just for `/`.  Bases come from the environment; unset means UNPROBED, which is
    # never GREEN (fail closed) unless the operator declares the gap out loud.
    f_probes = f_surface_probes([r for r in new_refs if r.endswith(".js")] + ["/"], serve)
    f_verdict = f_verdict_of(f_probes, bool(getattr(a, "allow_proxy_unprobed", False)))

    # I: the registration parameters are not in any header or filename - they exist only inside the
    # bundle bytes, which is exactly why A-H could all stay GREEN while `updateViaCache` was broken
    # (redteam `5789355832` ②).  Parsed from the SERVED body, and the served digest is recorded so the
    # text parsed is provably the bytes arm C compared.
    i_arms = []
    for ref in [r for r in new_refs if r.endswith(".js")]:
        t = http_text(ref)
        v = sw_register_verdict(t["text"], f"served {ref}")
        v["served_sha256"] = t["sha256"]
        v["served_body_size"] = t["body_size"]
        v["fetch_status"] = t["status"]
        if t["error"]:
            v["fetch_error"] = t["error"]
        i_arms.append(v)
    i_green = bool(i_arms) and all(x["verdict"] == "GREEN" for x in i_arms)

    # J: name -> content binding (arbiter D1-3).  Checked over every asset this receipt claims for either
    # generation, against the digest written at publication time.
    j_verdict = asset_manifest_verdict(serve, [r for r in new_refs] + [r for r in old_refs])
    j_green = j_verdict["verdict"] == "GREEN"

    receipt["receipt_FGH_blindspot_arms"] = {
        "G_PRECACHE_INTEGRITY": g_precache,
        "H_PREVIOUS_GENERATION": {"refs_probed": len(h_prev), "probes": h_prev, "verdict": h_prev_verdict},
        "I_SW_REGISTER_PARAMS": {"arms": i_arms,
                                 "verdict": "GREEN" if i_green else ("NOT_CONFIGURED" if not i_arms else "RED")},
        "J_ASSET_NAME_CONTENT_BINDING": j_verdict,
        "F_PROXY_AND_TUNNEL": {"probes": f_probes, "verdict": f_verdict,
                               "why": "BASE is 127.0.0.1:4781 (no auth proxy); the proxy and the tunnel "
                                      "were never probed by A-E - redteam bus 5788606895"},
    }
    # A declared entry is not a pass either: at least one sw must actually be checked (GREEN), and no
    # entry may be RED.  Two-way killer in --selftest: an UNDECLARED empty manifest must read RED.
    g_green = (bool(g_precache)
               and any(e["verdict"] == "GREEN" for e in g_precache)
               and not any(e["verdict"] == "RED" for e in g_precache))

    # D1-CLOSE-2: the pre-flight's temporal declarations are DEBTS, not passes.  Each one is discharged
    # only by the strict post-switch arm measuring the same ref against the same digest we shipped.
    post_rows = {}
    for e in g_precache:
        for p in e.get("probes", []):
            if p.get("ref"):
                post_rows[p["ref"]] = p.get("got") or {}
    obligations = (receipt.get("preflight_before_switch") or {}).get("temporal_obligations") or []
    ledger = obligation_ledger_verdict(obligations, post_rows)
    receipt["temporal_obligation_ledger"] = ledger
    obligations_ok = ledger["verdict"] != "UNDISCHARGED"
    receipt["arms"] = {"A": (a_old or {}).get("verdict"), "B": "see receipt_ABCDE",
                       "G_precache": [e["verdict"] for e in g_precache],
                       "H_prevgen": h_prev_verdict, "I_sw_register": "GREEN" if i_green else "RED",
                       "J_name_content_binding": j_verdict["verdict"],
                       "temporal_obligations": receipt["temporal_obligation_ledger"]["verdict"],
                       "F_proxy_tunnel": f_verdict,
                       "all_green_requires": "A,B,C,D,E + G + I + J + F + discharged temporal obligations"}
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
                 and g_green and i_green and j_green and obligations_ok and f_verdict == "GREEN")
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
