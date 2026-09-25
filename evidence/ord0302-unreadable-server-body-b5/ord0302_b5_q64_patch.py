"""ORD-0302 b5: the raw-reading panel keeps whitelist fields only (Q64=①, UI_EVIDENCE_EXPOSURE_GATE_V1).

Anchored once each, asserted before writing, and every claim below is re-read out of the resulting bytes:

  * `body_head` leaves the type, the capture and the render -- the commander's gate flags the NAME anywhere in
    the file, so deleting only the render line would still be caught;
  * the spec's `expectedRaw` returns the three fields this device measured, and X1 gains two directions:
    no fragment of the forced body may appear in the panel (witnessed by a credential-shaped body, R24) and an
    empty body must still show `bytes=0` (so the absence check cannot be vacuously true);
  * the label above the panel stops claiming "原始回读" of the answer and says which fields it is.

What this does NOT do: it does not rewrite the card sentence 「原因原文在“技术详情”里」.  Q53=① ruled that the
fix is to render the block rather than soften that sentence, and Q64=① forbids putting the answer's text in it.
Those two rulings leave one case unsolved -- a 200 answer that carries no server sentence -- and that residual
is delivered as a measured cell for the arbiter, not patched by me on my own reading.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SHEET = LANE / "frontend/src/features/planning/PlanWithAiSheet.tsx"
SPEC = LANE / "frontend/e2e/qoder-ord0302-unreadable-server-body.spec.ts"

EDITS = {
    SHEET: [
        ("  bytes: number | null;\n  body_head: string;\n",
         "  bytes: number | null;\n"),
        ("        bytes: raw === null ? null : new TextEncoder().encode(raw).length,\n"
         "        body_head: raw === null ? \"\" : raw.slice(0, 240),\n",
         "        bytes: raw === null ? null : new TextEncoder().encode(raw).length,\n"),
        ("                      {`bytes=${result.rawReading.bytes ?? \"\"}\\n`}\n"
         "                      {`body=${result.rawReading.body_head}`}\n",
         "                      {`bytes=${result.rawReading.bytes ?? \"\"}\\n`}\n"),
        ('                    {/* Field, then the value exactly as it arrived: no translation, no rewriting, no\n'
         '                        "probably because". An empty body shows as `bytes=0` with nothing after `body=`. */}',
         '                    {/* Q64=① whitelist: only what this device measured -- status, content-type, byte\n'
         '                        count.  No fragment of the upstream body is forwarded into the DOM, so a\n'
         '                        screenshot or an evidence file cannot carry a credential that arrived here. */}'),
        ('                      {zh ? "这台设备读到的原始回读" : "Raw reading this device took"}',
         '                      {zh ? "这台设备自己量到的回读字段" : "Fields this device measured"}'),
        ("           points at 技术详情, and what belongs under it is the answer's own bytes, not a sentence this screen\n"
         "           invented. The block still renders -- it is gated on `rawReading` below -- it just says nothing that\n"
         "           was not measured. */",
         "           points at 技术详情, and what belongs under it is only the fields THIS device measured\n"
         "           (status, content-type, byte count): Q64=① forbids forwarding upstream body text into the DOM,\n"
         "           so the block renders without any of the answer's bytes in it. */"),
    ],
    SPEC: [
        ("type X5Shape = { row: string; status: number; contentType: string; body: string };",
         "/* Q64=① witness: a body that looks like a credential.  Under b4 exactly this string was sliced into the\n"
         "   panel; under b5 nothing of it may appear, while `bytes` still has to equal its real length. */\n"
         "const FAKE_TOKEN_BODY =\n"
         '  "upstream said: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.supersecret-not-for-the-screen";\n'
         "type X5Shape = { row: string; status: number; contentType: string; body: string };"),
        ('  { row: "R23_④_200_mission_unusable_status", status: 200, contentType: "application/json",\n'
         "    body: JSON.stringify({ mission: { id: \"ord0302-mission\", status: \"FAILED_UPSTREAM\",\n"
         "                                      failure_reason: null, reasoning_summary: null } }) },\n];",
         '  { row: "R23_④_200_mission_unusable_status", status: 200, contentType: "application/json",\n'
         "    body: JSON.stringify({ mission: { id: \"ord0302-mission\", status: \"FAILED_UPSTREAM\",\n"
         "                                      failure_reason: null, reasoning_summary: null } }) },\n"
         '  { row: "R24_Q64_200_credential_shaped_text", status: 200, contentType: "text/plain; charset=utf-8",\n'
         "    body: FAKE_TOKEN_BODY },\n];"),
        ('/** What the block must show for a shape we forced: the answer\'s own fields, unedited. */\n'
         "function expectedRaw(sh: X5Shape): Record<string, string> {\n"
         "  return {\n"
         "    http_status: String(sh.status),\n"
         '    "content-type": sh.contentType,\n'
         "    bytes: String(new TextEncoder().encode(sh.body).length),\n"
         "    body: sh.body,\n"
         "  };\n}",
         "/** What the block must show for a shape we forced: only the fields this device measured (Q64=①). */\n"
         "function expectedRaw(sh: X5Shape): Record<string, string> {\n"
         "  return {\n"
         "    http_status: String(sh.status),\n"
         '    "content-type": sh.contentType,\n'
         "    bytes: String(new TextEncoder().encode(sh.body).length),\n"
         "  };\n}\n"
         "/** The other direction: nothing that was forwarded from the answer's body may be on screen. */\n"
         "function panelLeaksBody(read: { raw_text: string }, sh: X5Shape): boolean {\n"
         "  const frag = sh.body.slice(0, 24);\n"
         "  return frag.length > 0 && read.raw_text.includes(frag);\n}"),
        ('      rows.push({ claim: `${sh.row}: its block carries the raw reading, field for field, unedited`,\n'
         "        ok: Object.entries(want).every(([k, v]) => (got[k] ?? null) === v),\n"
         '        got: { expected: want, rendered: got } });',
         '      rows.push({ claim: `${sh.row}: its block carries the whitelist fields, value for value`,\n'
         "        ok: Object.entries(want).every(([k, v]) => (got[k] ?? null) === v),\n"
         '        got: { expected: want, rendered: got } });\n'
         '      rows.push({ claim: `${sh.row}: no fragment of the answer\'s body reaches the DOM (Q64=①)`,\n'
         "        ok: !panelLeaksBody(read, sh),\n"
         '        got: { fed_head: sh.body.slice(0, 24), leaked: panelLeaksBody(read, sh),\n'
         '               panel: read.raw_text } });\n'
         '      rows.push({ claim: `${sh.row}: an empty answer still shows its byte count, so the check above '
         "is not vacuous`,\\n"
         "        ok: sh.body !== \"\" || (read.raw_text ?? \"\").includes(\"bytes=0\"),\n"
         '        got: { fed_bytes: new TextEncoder().encode(sh.body).length, panel: read.raw_text } });'),
        ('    readings["X1"] = { want: "raw", force_shape: "five HTTP 200 bodies on both write legs (R19-R23)",',
         '    readings["X1"] = { want: "raw", force_shape: "HTTP 200 bodies on both write legs (R19-R23, plus the '
         'Q64=① credential-shaped witness R24)",'),
    ],
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


for path, pairs in EDITS.items():
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        hits = text.count(old)
        if hits != 1:
            raise SystemExit(f"{path.name}: anchor occurs {hits} times, expected exactly 1: {old[:78]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    print("patched", path.name, sha(path)[:16])

s = SHEET.read_text(encoding="utf-8")
p = SPEC.read_text(encoding="utf-8")
print("Q64 read-back:", {"body_head_in_sheet": s.count("body_head"), "body_render_in_sheet": s.count("{`body="),
                         "raw_slice_in_sheet": s.count("raw.slice"), "fake_token_in_spec": p.count("FAKE_TOKEN_BODY"),
                         "R24": "R24_Q64_200_credential_shaped_text" in p,
                         "leak_fn": "panelLeaksBody" in p, "expectedRaw_body_key": "body: sh.body" in p})


def run(cmd):
    r = subprocess.run(cmd, cwd=str(LANE / "frontend"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    return r.returncode, ((r.stdout or "") + (r.stderr or ""))[-600:]


for cfg in ("tsconfig.check.json", "tsconfig.typecheck.json"):
    rc, tail = run(["npx", "--no-install", "tsc", "-p", cfg, "--noEmit"])
    print("tsc", cfg, "rc=", rc, "" if rc == 0 else tail)
rc, tail = run(["node", "node_modules/@playwright/test/cli.js", "test", "-c", "playwright.config.ts",
                "e2e/qoder-ord0302-unreadable-server-body.spec.ts", "--list"])
print("collect rc=", rc, "|", [l.strip() for l in tail.splitlines() if "Total" in l][:1],
      [l.strip()[:70] for l in tail.splitlines() if "ord0302-" in l][:6])
