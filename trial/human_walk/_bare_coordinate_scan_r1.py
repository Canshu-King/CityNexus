"""List every coordinate-like filename reference in the walkthrough that carries no line number, with its line.

The commander's rule accepts four coordinate shapes; a bare filename is not one of them.  Early chapters used
several.  This scanner prints what is actually in the file -- per line, so a correction can cite where each
one sits -- and counts them, because a count quoted without a denominator is the thing we keep getting caught for.
"""
import io
import inspect
import os
import re
import subprocess

DOC = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md"
# The erratum must not count itself: the doc is read at the commit that was tip when it was written, not from the
# working tree, which by now carries the correction chapter.
DOC_REF = "a499ed2e2f7e3433fd1e9e1355ca48cde8c1f5cf:trial/results/20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md"
SELF_PATH = "trial/human_walk/_bare_coordinate_scan_r1.py"
SELF = io.open(os.path.join(r"D:/moodle/_cmdr_rescue_v3_1022", SELF_PATH), encoding="utf-8").read().splitlines()


def self_line(fragment):
    """Where one of this scanner's own rules sits -- read now, because a remembered line number is how citations rot.

    The fragment has to start the line: these very assignment lines quote the fragments and would otherwise match
    themselves, which is exactly how this helper first reported line 27 for a rule that lives at line 43.
    """
    for n, r in enumerate(SELF, 1):
        if r.strip().startswith(fragment):
            return "%s:%d" % (SELF_PATH, n)
    raise AssertionError("rule not found at line start: " + fragment)


LINE_TOKEN = self_line("TOKEN = re.compile")
LINE_WIDE = self_line("for match in TOKEN.finditer(row):")
LINE_VERB = self_line("VERB = re.compile")
LINE_SCOPED = self_line("scoped = [(number, token)")
# Out-file for the scoped pass; the console on this box is GBK, so a report with Chinese verbs in it must go to a file.
OUT = os.environ.get("SCAN_OUT", "")
BACKTICK = chr(96)
# A path-ish token ending in a known suffix, optionally followed by :digits -- we report only the ones without.
TOKEN = re.compile(r"[A-Za-z0-9_./\-\u4e00-\u9fff]+\.(?:py|tsx|ts|mjs|yaml|json|md|css|txt|log|db|png)(?::\d+)?")
# Only these count as a coordinate: the sentence is citing a reading, not naming a file in prose.
CODE_TOKEN = re.compile("[" + BACKTICK + "]([A-Za-z0-9_./\\-]+\\.(?:py|tsx|ts|mjs|yaml|json|md|css|txt|log))[" + BACKTICK + "]")
VERB = re.compile("(读数|实测|量到|记录在|落在|存于|见|量自)")

rows = subprocess.run(["git", "show", DOC_REF], cwd=r"D:/moodle/_cmdr_rescue_v3_1022",
                      capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
bare = []
for number, row in enumerate(rows, 1):
    for match in TOKEN.finditer(row):
        token = match.group(0)
        if ":" in token:
            continue
        if token.endswith((".png", ".db")):
            continue  # a screenshot or a database file is named as an artefact, not as a coordinate
        bare.append((number, token))

print("doc_lines=%d bare_tokens=%d distinct_files=%d" % (len(rows), len(bare), len(set(t for _n, t in bare))))
for number, token in bare:
    print("%d\t%s" % (number, token))

# The scoped question #304 actually asked: filenames used *as* a coordinate, i.e. cited next to a reading verb.
scoped = [(number, token) for number, row in enumerate(rows, 1)
          for match in CODE_TOKEN.finditer(row)
          for token in [match.group(1)]
          if VERB.search(row[max(0, match.start() - 40):match.start()] + row[match.end():match.end() + 40])]
early = [(number, token) for number, token in scoped if number < 600]
print("scoped_bare=%d distinct=%d early_before_line_600=%d" % (len(scoped), len(set(t for _n, t in scoped)), len(early)))

EVID = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome"
io.open(os.path.join(EVID, "bare-scan-wide-1.txt"), "w", encoding="utf-8", newline="\n").write(
    "doc=trial/results/20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md\n"
    "rule=every filename token with no :line after it (scanner %s)\n" % LINE_WIDE +
    "doc_lines=%d bare_tokens=%d distinct_files=%d\n" % (len(rows), len(bare), len(set(t for _n, t in bare)))
    + "".join("%d\t%s\n" % pair for pair in bare))


TRACKED = subprocess.run(["git", "ls-files"], cwd=r"D:/moodle/_cmdr_rescue_v3_1022",
                         capture_output=True, text=True).stdout.splitlines()


def locate(token):
    """Resolve a citation written as either a full repo path or a bare basename, preferring tracked files."""
    if "/" in token:
        return token if os.path.isfile(os.path.join(r"D:/moodle/_cmdr_rescue_v3_1022", token)) else None
    hits = [t for t in TRACKED if t == token or t.endswith("/" + token)]
    if hits:
        return hits[0]
    for base in ("trial", "backend", "frontend/src"):
        for dirpath, _d, files in os.walk(os.path.join(r"D:/moodle/_cmdr_rescue_v3_1022", base)):
            if token in files:
                return os.path.relpath(os.path.join(dirpath, token),
                                       r"D:/moodle/_cmdr_rescue_v3_1022").replace(os.sep, "/")
    return None


def grep_lines(path, needle):
    full = os.path.join(r"D:/moodle/_cmdr_rescue_v3_1022", path)
    try:
        lines = io.open(full, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return []
    return [(n, r) for n, r in enumerate(lines, 1) if needle.lower() in r.lower()]


# For each citation, the fragment the walkthrough attributes to it -- what has to be on the line I name.
CASE_KEYS = {
    (51, "trial/results/20261022_V3_AGENT_HALFDAY_PRESS.md"): ["直连", "7892", "10061", "0 处地点", "0 处"],
    (67, "20261022_V3_RETURNING_TRAVELER_AND_RECEIPT_SHAPE.md"): ["## 四", "debug Chrome", "WorkBuddy"],
    (73, "20261022_V3_RETURNING_TRAVELER_AND_RECEIPT_SHAPE.md"): ["## 七", "第七节"],
    (90, "walk-47-log.txt"): ["PHOTO_STRIP", "STEP_09", "STEP_01"],
    (175, "backend/tests/test_goal_place_media.py"): ["evil.invalid"],
    (177, "walk-39-log.txt"): ["STEP", "WALK", "相册"],
    (229, "collective_screen_r1.mjs"): ["rev-departure-execution", "consent-strip", "hit:"],
    (237, "walk-44-log.txt"): ["STRIP_SHAPE", "390", "414", "430"],
    (249, "identity_pointer_r1.mjs"): ["wanted_present"],
    (289, "media-binding-before-1.txt"): ["TIMEOUT", "UNAVAILABLE"],
    (319, "departure-price-evidence-probe-1.txt"): ["blocks_departure", "price_required"],
    (327, "region-status-by-provider-1.txt"): ["amap", "photon", "MATCHED"],
    (382, "opening-reader-ab-1.txt"): ["周四", "old", "Thu"],
}


def emit_scoped(name, subset, note):
    out = ["doc=trial/results/20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md",
           "doc_scanned_at_commit=" + DOC_REF.split(":")[0],
           "rule=" + note,
           "rules=wide %s | token shape %s | verb table %s | scoped %s" % (LINE_WIDE, LINE_TOKEN, LINE_VERB, LINE_SCOPED),
           "scanner=trial/human_walk/_bare_coordinate_scan_r1.py:%d" % inspect.getsourcelines(emit_scoped)[1],
           "count=%d" % len(subset)]
    for number, token in subset:
        path = locate(token)
        if path is None:
            out.append("DOC:%d TOKEN %s -> FILE NOT FOUND IN THIS TREE" % (number, token))
            continue
        keys = CASE_KEYS.get((number, token), [token])
        hits = []
        for key in keys:
            for n, r in grep_lines(path, key):
                if (n, r) not in hits:
                    hits.append((n, r))
        if hits:
            out.append("DOC:%d TOKEN %s -> %s  (%d 行命中，逐行列出)" % (number, token, path, len(hits)))
            out.extend("   line %d | %s" % (n, r.strip()[:150]) for n, r in hits[:12])
        else:
            out.append("DOC:%d TOKEN %s -> %s  (0 行命中；下列其最后三行供判读)" % (number, token, path))
            tail = grep_lines(path, "\n") or []
            full = io.open(os.path.join(r"D:/moodle/_cmdr_rescue_v3_1022", path),
                           encoding="utf-8", errors="replace").read().splitlines()
            out.extend("   line %d | %s" % (n, r.strip()[:150]) for n, r in list(enumerate(full, 1))[-3:])
    io.open(os.path.join(EVID, name), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")


emit_scoped("bare-scan-early-1.txt", early, "文件名紧跟在实数读数之后，且引注所在行 < 600")
emit_scoped("bare-scan-all-1.txt", scoped, "文件名紧跟在实数读数之后（全部章节）")
if OUT:
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        "".join("%d\t%s%s\n" % (number, token, "\tEARLY" if number < 600 else "") for number, token in scoped))


