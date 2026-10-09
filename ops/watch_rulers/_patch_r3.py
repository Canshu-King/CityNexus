"""One-shot patch: build r3 out of the r2 copy. Written as a file (not a heredoc) because the escaped `\\n`
inside generated Python literals is exactly the trap that bit me twice tonight."""
import ast
import io

P = "ui_exposure_field_check_r3.py"
s = io.open(P, encoding="utf-8", newline="").read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:56], s.count(a))
    s = s.replace(a, b, n)


rep('TEXTISH = {"text", "message", "detail", "sentence", "stack", "trace", "body", "body_head", "raw"}',
    'TEXTISH = {"text", "message", "detail", "sentence", "stack", "trace", "body", "body_head", "raw",\n'
    '           "value", "content", "reason", "output", "head"}')

rep('''    for m in INTERP_BLOCK.finditer(text):
        block = m.group(0)
        at_text_sink = bool(AFTER_TAG.search(text[max(0, m.start() - 40):m.start()])
                            or TEXT_SINK.match(text[m.end():m.end() + 24]))
        if not at_text_sink:
            continue
        for p in DOTTED_PATH.finditer(block):''',
    '''    for m in INTERP_BLOCK.finditer(text):
        block = m.group(0)
        at_text_sink = bool(AFTER_TAG.search(text[max(0, m.start() - 40):m.start()])
                            or TEXT_SINK.match(text[m.end():m.end() + 24]))
        if not at_text_sink:
            continue
        inner = block[1:-1].strip()
        if inner in tainted:                      # `<code>{sentence}</code>`: a bare local, no dots at all
            hname, hline, aline = tainted[inner]
            ln = _lineno(text, m.start())
            out.append({"rule": "UPSTREAM_TEXT_VIA_HELPER_TO_DOM", "line": ln,
                        "snippet": lines[ln - 1].strip()[:120],
                        "taint_chain": "poisoned helper %s (def :%d) -> bare local %s (assigned :%d) "
                                       "-> rendered as text at :%d" % (hname, hline, inner, aline, ln)})
            continue
        # `(out.failureReason || {}).text` breaks a naive dotted-path scan; parens and braces carry no name,
        # so drop them before looking for the tainted component.
        for p in DOTTED_PATH.finditer(re.sub(r"[(){}|]+", " ", block)):''')

HELPER = r'''function serverReasonSentence(body: unknown): string | null {
  const d = (body as { detail?: unknown } | null)?.detail;
  if (typeof d === "string") return d;
  return null;
}
export function X() {'''

NEW_FIX = (
    "    # the three shapes lane E's ORD-0319 round 2 paid for: each renders upstream prose, each was invisible\n"
    '    "bad_rename_last_part.tsx": ' + repr(HELPER + '\n  const out = {failureReason: failureNote(\n'
                                              '  serverReasonSentence(body), "fb")};\n'
                                              '  return <code>{out.failureReason.value}</code>; }') + ",\n"
    '    "bad_bare_local_hop.tsx": ' + repr(HELPER + '\n  const sentence = serverReasonSentence(body);\n'
                                            '  return <code>{sentence}</code>; }') + ",\n"
    '    "bad_paren_alias.tsx": ' + repr(HELPER + '\n  const out = {failureReason: failureNote(\n'
                                          '  serverReasonSentence(body), "fb")};\n'
                                          '  return <code>{(out.failureReason || {}).text}</code>; }') + ",\n"
    "    # and the clean side of each generalisation, or the widening is a wider net instead of a rule\n"
    '    "clean_bare_local_from_literal.tsx": ' + repr(
        'function localWording(code: string): string {\n  return code ? "device own wording" : "";\n}\n'
        'export function X() { const sentence = localWording(code);\n'
        '  return <code>{sentence}</code>; }') + ",\n"
    '    "clean_untainted_value_name.tsx": ' + repr(
        'export function X() { const out = {failureReason: {from: "device"}};\n'
        '  return <code>{out.failureReason.value}</code>; }') + ",\n"
)
anchor = '    "bad_helper_taint_multiline.tsx":'
i = s.index(anchor)
s = s[:i] + NEW_FIX + s[i:]

rep('          "bad_helper_taint_multiline.tsx": 1,',
    '          "bad_helper_taint_multiline.tsx": 1,\n'
    '          "bad_rename_last_part.tsx": 1, "bad_bare_local_hop.tsx": 1, "bad_paren_alias.tsx": 1,\n'
    '          "clean_bare_local_from_literal.tsx": 0, "clean_untainted_value_name.tsx": 0,')
s = s.replace('"""UI_EVIDENCE_EXPOSURE_GATE_V1 ruler, revision 2',
              '"""UI_EVIDENCE_EXPOSURE_GATE_V1 ruler, revision 3')

ast.parse(s)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("r3 PATCHED bytes", len(s.encode("utf-8")))
