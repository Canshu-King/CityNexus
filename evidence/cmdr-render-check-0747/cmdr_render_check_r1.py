"""Commander's own eyes on a deployed bundle: render the served page at phone size and read the
TEXT that reached the document, then judge it against the Q64 allowed-field vocabulary.

Why I run this myself after every generation swap: a deploy receipt proves bytes and content-types,
not what a traveller reads.  Green gates have already shipped a screen that printed an exception's
sentence (`PlanWithAiSheet` / the sealed-demo warning / the error boundary), so the last step of a
landing is a page rendered in a browser and a scan of its own words.

Two-way by construction: `--selftest` renders a page I plant a known leak into and requires RED, so
the GREEN on the real surface means the scanner can see, not that it never fires.

  python cmdr_render_check_r1.py --url <surface> --out <png> --json <json> [--wait 6000]
  python cmdr_render_check_r1.py --selftest
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
LEAK_PATTERNS = [
    "failed to fetch", "networkerror", "typeerror", "referenceerror", "syntaxerror",
    "cannot read propert", "is not a function", "net::err", "internal server error",
    "unexpected token", "unhandled", "traceback", "requestmethodnotallowed",
    "http status", "statuscode", "econnrefused", "operation timed out",
]
# What Q64=1 DOES allow on screen: these readings are this device's own measurements.
ALLOWED_FIELD_WORDS = ["http_status", "content_type", "body_bytes", "response_received",
                       "elapsed_ms", "request_id"]
NAME = "cnx-cmdr-render-check"


def chrome(url, out_png, wait_ms, dom=True, size="390,844"):
    """One headless render. --screenshot needs an ABSOLUTE path or Chrome silently writes nothing."""
    args = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=1", "--window-size=" + size,
            "--virtual-time-budget=%d" % wait_ms,
            "--user-data-dir=" + os.path.join(tempfile.gettempdir(), NAME + "_prof"),
            "--allow-insecure-localhost", "--no-first-run"]
    if dom:
        args.append("--dump-dom")
    if out_png:
        args.append("--screenshot=" + os.path.abspath(out_png))
    args.append(url)
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=240)
    return p


def visible_text(dom):
    """Strip tags, scripts and styles so a match means a word a person could read, not a string literal
    sitting in the JS bundle -- the difference between a leak report and a grep."""
    t = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", dom)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return re.sub(r"\s+", " ", t).strip()


def attribute_values(dom):
    """Q71: `data-*` is not on screen but it is in the DOM, so it is scanned separately."""
    vals = re.findall(r'\b(?:data-[a-z0-9-]+|aria-[a-z0-9-]+)="([^"]*)"', dom, flags=re.I)
    out, seen = [], set()
    for v in vals:
        s = v.strip()
        if len(s) > 2 and s.lower() not in ("true", "false") and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def judge(text, attrs):
    low = text.lower()
    screen_hits = sorted({p for p in LEAK_PATTERNS if p in low})
    dom_hits = sorted({p for p in LEAK_PATTERNS if p in " ".join(attrs).lower()})
    return {"verdict": "GREEN" if not screen_hits and not dom_hits else "RED",
            "on_screen": screen_hits, "in_dom_attributes": dom_hits,
            "allowed_field_words_present": sorted({w for w in ALLOWED_FIELD_WORDS if w in low}),
            "chars_of_visible_text": len(text), "attr_values_scanned": len(attrs)}


def run(url, out_png, wait_ms, tag):
    p = chrome(url, out_png, wait_ms)
    dom = p.stdout or ""
    text = visible_text(dom)
    res = judge(text, attribute_values(dom))
    res.update({"url": url, "chrome_rc": p.returncode, "png": os.path.abspath(out_png),
                "png_bytes": os.path.getsize(out_png) if os.path.isfile(out_png) else None,
                "dom_bytes": len(dom.encode("utf-8")),
                "visible_text_head": text[:600], "tag": tag})
    return res


def selftest():
    """A page I write, with a known exception sentence on screen, must read RED -- otherwise my GREEN
    on the real surface means nothing."""
    tmp = tempfile.mkdtemp(prefix=NAME + "_st_")
    good = os.path.join(tmp, "clean.html")
    bad = os.path.join(tmp, "leaky.html")
    open(good, "w", encoding="utf-8").write(
        "<html><body><h1>行程暂时打不开</h1><p>服务器没有应答，先检查网络</p>"
        "<div data-cnx-field=\"http_status\">HTTP 503</div></body></html>")
    open(bad, "w", encoding="utf-8").write(
        "<html><body><h1>原因：Failed to fetch</h1>"
        "<p>TypeError: Cannot read properties of null (reading 'detail')</p></body></html>")
    leaky_attr = os.path.join(tmp, "leaky_attr.html")
    open(leaky_attr, "w", encoding="utf-8").write(
        "<html><body><h1>行程暂时打不开</h1>"
        "<div data-error-message=\"net::ERR_CONNECTION_REFUSED\">x</div></body></html>")
    arms = []
    for name, path, want in (("clean", good, "GREEN"), ("screen_prose", bad, "RED"),
                             ("dom_attribute", leaky_attr, "RED")):
        p = chrome("file:///" + path.replace("\\", "/"), os.path.join(tmp, name + ".png"), 1500)
        dom = p.stdout or ""
        got = judge(visible_text(dom), attribute_values(dom))
        arms.append({"arm": name, "want": want, "got": got["verdict"],
                     "holds": got["verdict"] == want, "detail": got})
    ok = all(a["holds"] for a in arms)
    print(json.dumps({"selftest": "GREEN" if ok else "RED", "arms": [
        {k: a[k] for k in ("arm", "want", "got", "holds")} for a in arms]}, indent=1, ensure_ascii=False))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--png-dir", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--wait", type=int, default=7000)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    os.makedirs(a.png_dir or ".", exist_ok=True)
    rows = []
    for i, u in enumerate(a.url):
        png = os.path.join(a.png_dir or ".", "render_%d_%s.png" % (i, NAME[-6:]))
        rows.append(run(u, png, a.wait, "surface_%d" % i))
    doc = {"schema": "CNX_CMDR_RENDER_CHECK_V1", "ruler_blob": None, "wait_ms": a.wait,
           "leak_patterns": len(LEAK_PATTERNS), "surfaces": rows,
           "overall": "GREEN" if all(r["verdict"] == "GREEN" for r in rows) and rows else "RED"}
    if a.json:
        open(a.json, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
        blob = hashlib.sha1(b"blob %d\0" % os.path.getsize(a.json) + open(a.json, "rb").read())
        print("json=%s bytes=%d blob_sha1=%s" % (a.json, os.path.getsize(a.json), blob.hexdigest()))
    for r in rows:
        print("%-72s %s  on_screen=%s dom_attr=%s png=%s B=%s" % (
            r["url"][:72], r["verdict"], r["on_screen"], r["in_dom_attributes"],
            os.path.basename(r["png"]), r["png_bytes"]))
        print("        text[:180]=%s" % r["visible_text_head"][:180])
    print("OVERALL", doc["overall"])
    return 0 if doc["overall"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
