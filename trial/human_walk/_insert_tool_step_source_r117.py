"""Byte-preserving insertion of the per-step source disclosure into WorkspaceActions.tsx.

The file is CRLF, so the Edit-style LF anchors never match; this script keeps every existing byte and
writes only the two new blocks with \\r\\n terminators.  It refuses unless each anchor is found exactly
once, and re-reads the file afterwards to prove both landed.
"""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/frontend/src/trial/mobile/WorkspaceActions.tsx"

text = io.open(PATH, encoding="utf-8", newline="").read()
crlf = "\r\n" in text
print("LINE_ENDINGS", "crlf" if crlf else "lf", "BYTES", len(text.encode("utf-8")))

nl = "\r\n" if crlf else "\n"
anchor_one = '  return [clock, elapsed].filter(Boolean).join(" \u00b7 ");' + nl + "}" + nl
helper = "\n".join([
    "",
    "// Who actually answered for a step, read off the row the server wrote when it called the tool",
    "// (backend/app/agent/goal_amap.py:153 and goal_artifacts.py:262 carry these two keys).  A",
    "// traveller weighing \u201c\u8fdc\u592a\u5750\u5730\u94c1\u201d needs to know whether a walk came from the real map vendor or an",
    "// unverified public list.  When the row records neither, the panel prints \u672a\u8bb0\u5f55 instead of going",
    "// quiet -- a missing disclosure must read as missing, not as if it had already been checked.",
    'const PROVIDER_NAME: Record<string, string> = {',
    '  amap: "\u9ad8\u5fb7\u5730\u56fe", overpass: "OpenStreetMap \u516c\u5f00\u6570\u636e", photon: "\u516c\u5f00\u5730\u70b9\u6e05\u5355",',
    '  nominatim: "\u516c\u5f00\u5730\u70b9\u6e05\u5355", official_web: "\u5b98\u65b9\u7f51\u7ad9", valhalla: "\u8def\u7ebf\u8ba1\u7b97\u670d\u52a1",',
    '  deepseek: "\u516c\u5f00\u68c0\u7d22", searxng: "\u516c\u5f00\u68c0\u7d22",',
    "};",
    'const PROVENANCE_NAME: Record<string, string> = {',
    '  LIVE_PROVIDER: "\u771f\u4f9b\u5e94\u5546\u5df2\u6838\u5b9e", LIVE_OPENSTREETMAP_OVERPASS: "\u516c\u5f00\u5730\u56fe\u5df2\u6838\u5b9e",',
    '  UNVERIFIED: "\u8fd8\u6ca1\u6838\u5b9e",',
    "};",
    'function toolStepSourceText(result: Record<string, unknown>): string {',
    '  const provider = typeof result.provider === "string" ? result.provider : "";',
    '  const provenance = typeof result.provider_provenance === "string" ? result.provider_provenance : "";',
    "  if (!provider && !provenance) return \"\";",
    '  const who = provider ? (PROVIDER_NAME[provider] ?? "\u672a\u8bb0\u5f55\u7684\u6765\u6e90") : "\u672a\u8bb0\u5f55\u7684\u6765\u6e90";',
    '  const how = provenance ? (PROVENANCE_NAME[provenance] ?? "\u6838\u5b9e\u72b6\u6001\u672a\u8bb0\u5f55") : "\u6838\u5b9e\u72b6\u6001\u672a\u8bb0\u5f55";',
    '  return `\u6765\u6e90\uff1a${who} \u00b7 ${how}`;',
    "}",
]) + nl
if text.count(anchor_one) != 1:
    sys.exit("ABORT anchor_one hits=%d" % text.count(anchor_one))
text = text.replace(anchor_one, anchor_one + helper, 1)

anchor_two = '              <small>{toolStepClock(step)}</small>' + nl
source_row = (
    '              {(() => {' + nl
    + "                const source = toolStepSourceText(step.result);" + nl
    + '                return source ? <span className="rev-agent-tool-source" data-testid="rev-agent-tool-source">{source}</span> : null;' + nl
    + '              })()}' + nl
)
if text.count(anchor_two) != 1:
    sys.exit("ABORT anchor_two hits=%d" % text.count(anchor_two))
text = text.replace(anchor_two, source_row + anchor_two, 1)

io.open(PATH, "w", encoding="utf-8", newline="").write(text)
again = io.open(PATH, encoding="utf-8", newline="").read()
print("HELPER_LANDED", "function toolStepSourceText" in again)
print("RENDER_LANDED", 'data-testid="rev-agent-tool-source"' in again)
print("BYTES_AFTER", len(again.encode("utf-8")))
