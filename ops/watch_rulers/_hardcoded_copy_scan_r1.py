"""Find English PROSE that the frontend renders from a source literal instead of from the i18n dictionaries.

Why: a zh user reading /v8/twin sees `Capability needs`, `No learned signals`, `Hard accessibility needs are
never inferred from behavior.`  Those are not data - `data/mock/places.json` supplies the place names, and
those do stay English by design.  These come out of the .tsx as bare literals sitting in the SAME expression
as their translated siblings, e.g. `{t("twin.kicker")}` two nodes away from `>Capability needs<`.

What counts as prose (all three must hold):
  * the literal has at least two ASCII words, one of which is a plain English word (a stop list below), OR it
    ends with `.` and has >= 2 words;
  * it is NOT the argument of a `t(...)` / `t(\`...\`)` call;
  * it is NOT a class name / test id / route / icon name / css / mime / data attribute value.

The stop-list rule is what keeps `v8-twin-card`, `place-river-cruise` and `Copilot` out: none of them contain
an English function word.  Every hit is printed with its file:line so a human can overrule the classifier
without re-running anything, and the JSON keeps `why` for each.

Read-only.  Prints an ASCII summary; the table goes to a UTF-8 file because this box's console is GBK and a
`·` in a matched literal killed an earlier run.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"D:\moodle\CityNexus\frontend\src"
OUTJSON = sys.argv[2] if len(sys.argv) > 2 else r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_hardcoded_copy_scan_r1.json"

FUNC_WORDS = {
    "is", "are", "was", "were", "be", "been", "the", "a", "an", "and", "or", "but", "not", "no",
    "never", "always", "has", "have", "had", "will", "would", "can", "cannot", "must", "should",
    "from", "of", "to", "in", "on", "for", "with", "without", "this", "that", "these", "those",
    "it", "its", "your", "you", "we", "they", "he", "she", "needs", "need", "remain", "remains",
    "recorded", "waiting", "learned", "inferred", "accessible", "unknown", "explicit", "nothing",
    "still", "yet", "already", "when", "while", "if", "then", "than", "as", "at", "by", "into",
}

# literal shapes that are plumbing, never copy
NON_COPY = re.compile(
    r"^(?:[a-z][a-z0-9]*(?:-[a-z0-9]+)+)$"          # kebab: class names, test ids, place ids
    r"|^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+$"       # dotted: dictionary keys, i18n keys
    r"|^v\d+"                                        # v8-* / v10-* class prefixes
    r"|^[A-Z][A-Za-z0-9]*$"                          # single Capitalised word: brand / component / enum
    r"|^[A-Z][A-Z0-9_]*$"                            # SCREAMING_SNAKE enum / code
    r"|^[\w/.-]+\.(?:css|js|ts|tsx|json|svg|png|webp)$"
    r"|^https?://"
    r"|^[#/]"                                        # routes, ids
    r"|^\d"                                          # numeric-ish
)

LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`')


def looks_like_prose(s):
    t = s.strip()
    if len(t) < 8 or "\n" in t:
        return False, "too short"
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", t)
    if len(words) < 2:
        return False, "fewer than two words"
    low = {w.lower() for w in words}
    hit = low & FUNC_WORDS
    if not hit and not t.endswith("."):
        return False, "no English function word and no terminal period"
    if NON_COPY.match(t):
        return False, "matches a plumbing shape"
    return True, ("function word(s): " + ",".join(sorted(hit)[:4])) if hit else "terminal period + >=2 words"


def preceded_by_t(src, start):
    """True when the literal is the argument of a t(...) call."""
    back = src[max(0, start - 6):start]
    return bool(re.search(r"\bt\($|\bt\(\s*$|\bt\(\s*$", back))


rows = []
files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in ("node_modules", "dist", ".git")]
    for fn in filenames:
        if fn.endswith((".tsx", ".ts")):
            files.append(os.path.join(dirpath, fn))
files.sort()
print("source files scanned:", len(files), "under", ROOT)

for f in files:
    src = io.open(f, encoding="utf-8", errors="replace").read()
    lines = src.split("\n")
    # map absolute offset -> 1-based line number
    offs = []
    acc = 0
    for ln in lines:
        offs.append(acc)
        acc += len(ln) + 1

    def lineno(pos):
        lo, hi = 0, len(offs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offs[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    for m in LIT.finditer(src):
        val = m.group(1) if m.group(1) is not None else (m.group(2) if m.group(2) is not None else m.group(3))
        if val is None:
            continue
        ok, why = looks_like_prose(val)
        if not ok:
            continue
        if preceded_by_t(src, m.start()):
            continue
        rel = os.path.relpath(f, ROOT).replace("\\", "/")
        rows.append({"file": rel, "line": lineno(m.start()), "literal": val, "why": why})

per_file = {}
for r in rows:
    per_file[r["file"]] = per_file.get(r["file"], 0) + 1

res = {
    "generated_by": "_hardcoded_copy_scan_r1.py",
    "root": ROOT,
    "files_scanned": len(files),
    "hardcoded_prose_literals": len(rows),
    "files_with_hits": len(per_file),
    "per_file": dict(sorted(per_file.items(), key=lambda kv: -kv[1])),
    "rows": rows,
    "verdict": ("HARDCODED_ENGLISH_PROSE_PRESENT" if rows else "NO_HARDCODED_ENGLISH_PROSE"),
}
with io.open(OUTJSON, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)
print("hardcoded prose literals:", len(rows), "in", len(per_file), "files")
for k, v in list(res["per_file"].items())[:12]:
    print("  %-56s %d" % (k, v))
print("VERDICT", res["verdict"])
print("wrote", OUTJSON, os.path.getsize(OUTJSON), "B")
