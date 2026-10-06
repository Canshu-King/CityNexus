"""UI_EVIDENCE_EXPOSURE_GATE_V1 as an instrument, not a memo (arbiter Q64=1, 09-25 23:2x).

The rule: data that reaches the UI, a screenshot, or an evidence artifact must pass
`source classification -> allowed fields -> render`, never `backend returned something -> frontend displays it`.
Allowed: http_status / content_type / body_bytes / response_received / elapsed_ms / request_id.
Forbidden: raw body / raw detail / raw exception.

This script reads a file (or a candidate ref's version of it) and reports the shapes that would put upstream
text into the DOM. It is deliberately coarse: a hit is a question to answer, not a verdict on the lane - the
same discipline I ask of every other ruler here, which is why it carries three self-test directions, including
one that must go RED for a reason the first pattern would miss (dangerouslySetInnerHTML).
"""
import argparse
import io
import json
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"

ALLOWED = ["http_status", "content_type", "body_bytes", "response_received", "elapsed_ms", "request_id"]
PATTERNS = [
    ("RAW_BODY_TO_DOM", re.compile(r"body\s*=\s*\$\{|body_head|rawReading\.body|\braw\b.*\bslice\(")),
    ("UPSTREAM_EXCEPTION_TO_DOM", re.compile(r"(stack|exception|trace)\b.*\{|\{(err|error|exception)\.?(stack|message)")),
    ("RAW_TEXT_INTERPOLATION", re.compile(r"\{`body=|textContent.*raw|\{raw[A-Za-z]*\}")),
    ("DANGEROUS_HTML", re.compile(r"dangerouslySetInnerHTML")),
]


def scan_text(label, text):
    hits = []
    for name, pat in PATTERNS:
        for m in pat.finditer(text):
            line = text[:m.start()].count("\n") + 1
            hits.append({"rule": name, "file": label, "line": line,
                         "snippet": text.splitlines()[line - 1].strip()[:120]})
    return hits


def selftest():
    good = ("<pre>{`http_status=${r.http_status}\\n`}"
            "{`content-type=${r.content_type}\\n`}{`bytes=${r.bytes}`}</pre>")
    bad_body = "<pre>{`body=${r.body_head}`}</pre>"
    bad_html = "<div dangerouslySetInnerHTML={{__html: serverText}} />"
    h_good = scan_text("good.tsx", good)
    h_bad1 = scan_text("bad_body.tsx", bad_body)
    h_bad2 = scan_text("bad_html.tsx", bad_html)
    ok = (h_good == [] and any(x["rule"] == "RAW_BODY_TO_DOM" for x in h_bad1)
          and any(x["rule"] == "DANGEROUS_HTML" for x in h_bad2))
    print(json.dumps({"verdict": "SELFTEST_PASS" if ok else "SELFTEST_FAIL",
                      "whitelist_only_render_hits": len(h_good),
                      "raw_body_hits": [x["rule"] for x in h_bad1],
                      "dangerous_html_hits": [x["rule"] for x in h_bad2],
                      "why_three": "a gate that only catches `body=` would let an exception stack or an "
                                   "innerHTML sink through; the clean render must stay clean or the gate is "
                                   "just theatre"}, ensure_ascii=False, indent=1))
    return 0 if ok else 7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="local path to scan")
    ap.add_argument("--ref", help="commit/ref holding the file, to scan the candidate's own bytes")
    ap.add_argument("--path", help="path inside the ref")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    targets = []
    if args.file:
        targets.append((args.file, io.open(args.file, encoding="utf-8", errors="replace").read()))
    if args.ref and args.path:
        p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (args.ref, args.path)], capture_output=True)
        if p.returncode:
            print("REFUSED: %s:%s did not resolve (%s)" % (args.ref, args.path,
                                                           p.stderr.decode("utf-8", "replace")[:120]))
            return 4
        targets.append(("%s:%s" % (args.ref[:12], args.path), p.stdout.decode("utf-8", "replace")))
    if not targets:
        print("usage: --file <path>  or  --ref <sha> --path <path-in-tree>  (or --selftest)")
        return 2
    hits = []
    for label, text in targets:
        hits.extend(scan_text(label, text))
    out = {
        "schema": "CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "standing_rule": "Q64=1 (arbiter): data reaching UI / screenshot / evidence artifacts must pass source "
                         "classification -> allowed fields -> render. mask is a helper, never the first gate.",
        "allowed_fields": ALLOWED,
        "forbidden": ["raw body", "raw detail", "raw exception"],
        "targets_scanned": [label for label, _ in targets],
        "hits": hits,
        "verdict": "EXPOSURE_SHAPE_FOUND" if hits else "NO_EXPOSURE_SHAPE_FOUND",
        "interpretation_limit": "a hit names a shape to justify, not a defect verdict; the lane answers either "
                                "by removing it or by showing why that specific text is inside the allowed set. "
                                "NO_EXPOSURE_SHAPE_FOUND only means this coarse net caught nothing.",
        "discipline": {"files_written": 0, "product_bytes_changed": 0, "refs_pushed": 0,
                       "credential_values_printed": 0},
        "claim_kind": "pattern_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("%s across %d scanned file(s): %d hit(s) %s" % (
        out["verdict"], len(targets), len(hits),
        sorted(set("%s@%s:%d" % (h["rule"], h["file"].split("/")[-1], h["line"]) for h in hits))[:6]))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if args.out:
        io.open(args.out, "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for h in hits[:12]:
        print("   %-26s %s:%d  %s" % (h["rule"], h["file"].split("/")[-1], h["line"], h["snippet"][:70]))
    print("file=%s bytes=%d" % (args.out, len(txt.encode("utf-8"))))
    return 0 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
