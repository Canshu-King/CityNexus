"""UI_EVIDENCE_EXPOSURE_GATE_V1 ruler, revision 2 (fixes the blind spot lane E caught in ORD-0319).

r1 (blob 0ba79e00738984ee06651219530e5a9d7fa897e3) is left byte-for-byte untouched; this is a new file because
a published coordinate must never be rewritten. E's counterexample `e0319_counter_backend_detail.tsx`
(blob 58ca96d30d4aee9a974fd54686edaedf985705b6) and the live tip render path
`PlanWithAiSheet.tsx` -> serverReasonSentence (:159-165) -> failureReason -> <code>{result.failureReason.text}</code> (:1016)
both put upstream text into the DOM while r1 reported 0 hits. That verdict was mine and it was wrong, so r2 adds:

  (1) UPSTREAM_READ_DIRECT: a forbidden upstream read inside a JSX interpolation, optional chaining included
      (`{body?.detail}`, `{resp?.error?.message}`, `{err?.stack}`).
  (2) UPSTREAM_TEXT_VIA_HELPER_TO_DOM: two-pass, file-scoped taint - a helper whose body returns a forbidden
      upstream read, a state field assigned from that helper, and any interpolation of that field's path.
      This is what r1's four line-local patterns structurally cannot see: the tainted value crosses a function
      boundary and a property name, so no single line contains both the source and the sink.

A hit is still a shape to justify, not a defect verdict. The selftest is two-sided on purpose: a helper that
returns a literal, and a `.text` render whose field was never assigned from a poisoned helper, must both stay
clean - otherwise r2 would just be a `\\.text` matcher wearing a taint costume.
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
FORBIDDEN_READ = r"(?:detail|message|stack|trace|body(?:_head)?)"

PATTERNS = [
    ("RAW_BODY_TO_DOM", re.compile(r"body\s*=\s*\$\{|body_head|rawReading\.body|\braw\b.*\bslice\(")),
    ("UPSTREAM_EXCEPTION_TO_DOM", re.compile(r"(stack|exception|trace)\b.*\{|\{(err|error|exception)\.?(stack|message)")),
    ("RAW_TEXT_INTERPOLATION", re.compile(r"\{`body=|textContent.*raw|\{raw[A-Za-z]*\}")),
    ("DANGEROUS_HTML", re.compile(r"dangerouslySetInnerHTML")),
]
# (1) forbidden read used straight inside an interpolation, `?.` tolerated
DIRECT_IN_INTERP = re.compile(
    r"\{[^{}]*?\b(?:body|resp|response|res|err|error|exception|payload|json)\s*\??\.\s*"
    r"%s(?:\s*\??\.\s*%s)?[^{}]*?\}" % (FORBIDDEN_READ, FORBIDDEN_READ))
# (2a) a helper whose body returns something read off an upstream object
HELPER_DEF = re.compile(r"function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)[^{]*\{(.*?)\n\}", re.S)
RETURN_FORBIDDEN = re.compile(r"return[^;\n]*[?.]\s*%s\b" % FORBIDDEN_READ)
LOCAL_FROM_FORBIDDEN = re.compile(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=[^;\n]*[?.]\s*%s\b" % FORBIDDEN_READ)
RETURN_LOCAL = re.compile(r"return[^;\n]*\b([A-Za-z_$][\w$]*)\b")


def _helper_is_poisoned(body):
    """A helper is poisoned if a value it returns came off an upstream object, either read inline
    (`return error.message`) or parked in a local first (`const d = body?.detail; ... return d`).
    The local hop is what r1's line-local patterns could not represent."""
    if RETURN_FORBIDDEN.search(body):
        return True
    parked = set(LOCAL_FROM_FORBIDDEN.findall(body))
    return bool(parked & set(RETURN_LOCAL.findall(body)))

# (2b) a name bound to an expression that calls one of those helpers - the call may sit on a following
#      line (`failureReason: failureNote(\n  serverReasonSentence(body),`), which is exactly how the live
#      tip defeats a line-local scan, so the window here is multi-line and stops at `;`.
# (2c) an interpolation whose dotted path passes through such a bound name
INTERP_BLOCK = re.compile(r"\{[^{}]*\}")
DOTTED_PATH = re.compile(r"\b([A-Za-z_$][\w$]*(?:\s*\??\.\s*[A-Za-z_$][\w$]*)+)\b")
# A tainted name is only a finding when what reaches the screen is prose. Without this, the same rule fires on
# `data-result-status={r?.status}` and on `x.from === "server"`, and a gate that cries wolf on attributes is a
# gate people learn to ignore.
TEXTISH = {"text", "message", "detail", "sentence", "stack", "trace", "body", "body_head", "raw"}
TEXT_SINK = re.compile(r"^\s*</(code|pre|span|div|p|li|strong|em|dd|dt)>")
AFTER_TAG = re.compile(r">\s*$")



def _lineno(text, pos):
    return text[:pos].count("\n") + 1


def _direct_hits(text):
    return [{"rule": "UPSTREAM_READ_DIRECT", "line": _lineno(text, m.start()),
             "snippet": text.splitlines()[_lineno(text, m.start()) - 1].strip()[:120]}
            for m in DIRECT_IN_INTERP.finditer(text)]


def _taint_hits(text):
    lines = text.splitlines()
    helper_lines = {}
    for m in HELPER_DEF.finditer(text):
        if _helper_is_poisoned(m.group(2)):
            helper_lines[m.group(1)] = _lineno(text, m.start())
    tainted = {}
    for hname, hline in helper_lines.items():
        for m in re.finditer(r"\b([A-Za-z_$][\w$]*)\s*[:=][^;]{0,260}?" + re.escape(hname) + r"\s*\(", text):
            tainted.setdefault(m.group(1), (hname, hline, _lineno(text, m.start())))
    out = []
    if not tainted:
        return out
    for m in INTERP_BLOCK.finditer(text):
        block = m.group(0)
        at_text_sink = bool(AFTER_TAG.search(text[max(0, m.start() - 40):m.start()])
                            or TEXT_SINK.match(text[m.end():m.end() + 24]))
        if not at_text_sink:
            continue
        for p in DOTTED_PATH.finditer(block):
            parts = [x.strip() for x in re.split(r"\??\.", p.group(1))]
            if parts[-1] not in TEXTISH:
                continue
            for comp in parts:
                if comp in tainted:
                    hname, hline, aline = tainted[comp]
                    ln = _lineno(text, m.start())
                    out.append({"rule": "UPSTREAM_TEXT_VIA_HELPER_TO_DOM", "line": ln,
                                "snippet": lines[ln - 1].strip()[:120],
                                "taint_chain": "poisoned helper %s (def :%d) -> bound name %s (assigned :%d) "
                                               "-> %s rendered as text at :%d"
                                               % (hname, hline, comp, aline, ".".join(parts), ln)})
                    break
    dedup = {}
    for h in out:
        dedup[(h["line"], h["rule"])] = h
    return sorted(dedup.values(), key=lambda h: h["line"])



def scan_text(label, text):
    hits = []
    for name, pat in PATTERNS:
        for m in pat.finditer(text):
            line = _lineno(text, m.start())
            hits.append({"rule": name, "file": label, "line": line,
                         "snippet": text.splitlines()[line - 1].strip()[:120]})
    for h in _direct_hits(text) + _taint_hits(text):
        h["file"] = label
        hits.append(h)
    return hits


FIXTURES = {
    "clean_whitelist_only.tsx": ('<pre>{`http_status=${r.http_status}\\n`}{`bytes=${r.body_bytes}`}'
                                 '<code>{result.note.text}</code></pre>'),
    "clean_literal_helper.tsx": ('function localWording(code: string): string {\n  return code ? "这台设备自己的读数" : "";\n}\n'
                                 'export function X() { const note = {failureReason: localWording(code)};'
                                 'return <code>{note.failureReason.text}</code>; }'),
    "bad_direct_optional_chain.tsx": 'export function X({body}) { return <code>{body?.detail}</code>; }',
    "bad_helper_taint.tsx": ('function serverReasonSentence(body: unknown): string | null {\n'
                             '  const detail = (body as { detail?: unknown } | null)?.detail;\n'
                             '  if (typeof detail === "string") return detail;\n  return null;\n}\n'
                             'export function X() { const r = {failureReason: note(serverReasonSentence(body))};\n'
                             '  return <code data-testid="plan-ai-reason">{r.failureReason.text}</code>; }'),
    "bad_dangerous_html.tsx": '<div dangerouslySetInnerHTML={{__html: serverText}} />',
    # the other side of the TEXTISH/text-sink narrowing: the same poisoned helper and the same bound name must
    # NOT fire when only a machine label and a status code reach the screen. Without this fixture the narrowing
    # is an unproven claim about my own rule.
    "clean_tainted_but_attribute_only.tsx": ('function serverReasonSentence(body: unknown): string | null {\n'
                                             '  const detail = (body as { detail?: unknown } | null)?.detail;\n'
                                             '  if (typeof detail === "string") return detail;\n  return null;\n}\n'
                                             'export function X() { const out = {failureReason: failureNote(\n'
                                             '  serverReasonSentence(body), "x")};\n'
                                             '  return <code data-reason-origin={out.failureReason.from}>'
                                             '{out.status}</code>; }'),
    "bad_raw_body.tsx": "<pre>{`body=${r.body_head}`}</pre>",
    # the live-tip shape: the poisoned call sits on a line AFTER the field name, so a line-local scan binds
    # the wrong callee (the wrapper) and reports clean. This fixture is what keeps that regression loud.
    "bad_helper_taint_multiline.tsx": ('function serverReasonSentence(body: unknown): string | null {\n'
                                       '  const detail = (body as { detail?: unknown } | null)?.detail;\n'
                                       '  if (typeof detail === "string") return detail;\n  return null;\n}\n'
                                       'export function X() { const out = {failureReason: failureNote(\n'
                                       '  serverReasonSentence(body),\n  "fallback"\n)};\n'
                                       '  return <code data-testid="plan-ai-reason">{out.failureReason.text}</code>; }'),
}
EXPECT = {"clean_whitelist_only.tsx": 0, "clean_literal_helper.tsx": 0,
          "clean_tainted_but_attribute_only.tsx": 0,
          "bad_direct_optional_chain.tsx": 1, "bad_helper_taint.tsx": 1,
          "bad_helper_taint_multiline.tsx": 1,
          "bad_dangerous_html.tsx": 1, "bad_raw_body.tsx": 1}


def selftest():
    per = {}
    ok = True
    for name, src in FIXTURES.items():
        hits = scan_text(name, src)
        want = EXPECT[name]
        verdict = "CLEAN" if not hits else "HIT"
        good = (not hits) if want == 0 else bool(hits)
        ok = ok and good
        per[name] = {"expected": want, "hits": [h["rule"] for h in hits], "verdict": verdict,
                     "assertion_met": good}
    print(json.dumps({"verdict": "SELFTEST_PASS" if ok else "SELFTEST_FAIL",
                      "n_fixtures": len(FIXTURES),
                      "n_clean_expected": sum(1 for v in EXPECT.values() if v == 0),
                      "n_bad_expected": sum(1 for v in EXPECT.values() if v),
                      "fixtures": per,
                      "why": "the two clean fixtures are what give the taint rule teeth: a `.text` render whose "
                             "field was never assigned from a poisoned helper must stay clean, and a helper that "
                             "returns a literal must not count as upstream text - otherwise r2 is only a `\\.text` "
                             "matcher and would fire on every honest label"}, ensure_ascii=False, indent=1))
    return 0 if ok else 7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--ref")
    ap.add_argument("--path")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    targets = []
    if args.file:
        for one in args.file.split(","):
            targets.append((one, io.open(one, encoding="utf-8", errors="replace").read()))
    if args.ref and args.path:
        p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (args.ref, args.path)], capture_output=True)
        if p.returncode:
            print("REFUSED: %s:%s did not resolve (%s)" % (args.ref, args.path,
                                                           p.stderr.decode("utf-8", "replace")[:120]))
            return 4
        targets.append(("%s:%s" % (args.ref[:12], args.path), p.stdout.decode("utf-8", "replace")))
    if not targets:
        print("usage: --file <path[,path...]> | --ref <sha> --path <in-tree path> | --selftest")
        return 2
    hits = []
    for label, text in targets:
        hits.extend(scan_text(label, text))
    rules = sorted(set(h["rule"] for h in hits))
    out = {
        "schema": "CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R2",
        "revision_of": "ui_exposure_field_check_r1.py = 0ba79e00738984ee06651219530e5a9d7fa897e3 (bytes untouched)",
        "revision_reason": "lane E d2305848 ORD-0319 caught a blind spot; commander reproduced it first-hand: "
                           "r1 reports 0 hits on the tip while PlanWithAiSheet.tsx:1016 renders "
                           "result.failureReason.text, fed by serverReasonSentence (:159-165) reading "
                           "body.detail / error.message at :576/:637/:711",
        "attribution": "COMMANDER_RULER_BLIND_SPOT",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "standing_rule": "Q64=1 (arbiter): data reaching UI / screenshot / evidence artifacts must pass source "
                         "classification -> allowed fields -> render. mask is a helper, never the first gate.",
        "allowed_fields": ALLOWED,
        "forbidden": ["raw body", "raw detail", "raw exception", "upstream sentence reaching DOM via a helper"],
        "rules_fired": rules,
        "targets_scanned": [label for label, _ in targets],
        "hits": hits,
        "verdict": "EXPOSURE_SHAPE_FOUND" if hits else "NO_EXPOSURE_SHAPE_FOUND",
        "interpretation_limit": "a hit names a shape to justify, not a defect verdict; NO_EXPOSURE_SHAPE_FOUND "
                                "from r1 is additionally worthless on its own, because r1 was proven blind at "
                                "this exact file - only r2's clean verdict is a clean verdict.",
        "selftest_command": "python ui_exposure_field_check_r2.py --selftest",
        "claim_kind": "pattern_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = "%s across %d scanned file(s): %d hit(s) %s" % (
        out["verdict"], len(targets), len(hits),
        sorted(set("%s@%s:%d" % (h["rule"], h["file"].split("/")[-1], h["line"]) for h in hits))[:8])
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if args.out:
        io.open(args.out, "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for h in hits[:14]:
        print("   %-32s %s:%d  %s" % (h["rule"], h["file"].split("/")[-1], h["line"], h["snippet"][:64]))
        if h.get("taint_chain"):
            print("       chain: %s" % h["taint_chain"])
    print("file=%s bytes=%d" % (args.out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
