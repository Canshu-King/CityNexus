"""Whole front-end scan: counted nouns followed by a copula (two shapes).

arm=marker  -> `{plural:stem}` inside a dictionary or copy-module literal
arm=helper  -> `englishCountNoun(...)` inside a template literal in code

Reads tracked bytes from one pinned tip, so no worktree is required.
Product bytes are never touched: this file only reads and writes its own artifacts.
"""
import io
import re
import subprocess
import sys

REPO = r"D:\moodle\CityNexus"
SCOPE = "frontend/src"
AUTH = "refs/heads/mirror/integration-frontend-apple-pass1"
MARKER = re.compile(r"\{plural:[^}]+\}")
HELPER = re.compile(r"englishCountNoun\(([^)]*)\)")
SKIP = re.compile(r"""^([}\)"'`]*\s+)(are|were|is)\b""", re.I)
SKIPWORD = re.compile(r"""^([}\)"'`]*\s+)([A-Za-z]+)""")
WORD = re.compile(r"""^[}\)"'`]*\s+([A-Za-z]+)""")
HEAD_TOKEN = re.compile(r"\{(\w+)\}|\$\{([^}]+)\}")
CMDR_ROWS = [("frontend/src/features/poiimport/poiImportCopy.ts", 159, "are"),
             ("frontend/src/features/poiimport/poiImportCopy.ts", 163, "were"),
             ("LocaleContext-dict", 0, "were")]
OUT_TSV = r"D:\moodle\_qoder_kuaijiangong_copula_r2.tsv"
OUT_EV = r"D:\moodle\_qoder_kuaijiangong_copula_r2.txt"


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def classify(tail):
    sm = SKIP.match(tail)
    if sm:
        return "COPULA_AFTER_COUNTED_NOUN", sm.group(2), sm.span(2)
    wm = SKIPWORD.match(tail)
    if wm:
        return "VERB_OR_WORD_AFTER_NOT_COPULA", wm.group(2), None
    return "NOTHING_AFTER", "", None


def scan_line(line):
    """Yield one record per counted-noun token found in the line."""
    out = []
    for arm, rx in (("marker", MARKER), ("helper", HELPER)):
        for ordinal, m in enumerate(rx.finditer(line), 1):
            tail = line[m.end():]
            verdict, word, span = classify(tail)
            fix = "drop_copula" if span else "none"
            head = line[:m.start()]
            tokens = HEAD_TOKEN.findall(head)
            count_token = ""
            for a, b in reversed(tokens):
                if a or b:
                    count_token = a or b
                    break
            copula = word if span else ""
            after = line
            if span:
                after = line[:m.end() + span[0]] + line[m.end() + span[1]:]
                after = re.sub(r"\s+", " ", after)
            out.append([arm, m.group(0), count_token, word, copula, verdict, fix,
                        line[max(0, m.start() - 14):m.end() + 30].strip()[:80],
                        (after[max(0, m.start() - 14):m.end() + 30].strip()[:80] if copula else "")])
    return out


def selftest():
    cases = [
        ('en: "{n} {plural:place} are on {day}",', "marker", "are", "COPULA_AFTER_COUNTED_NOUN"),
        ('en: "{n} {plural:place} were already on {shelf}",', "marker", "were", "COPULA_AFTER_COUNTED_NOUN"),
        ('en: "{n} {plural:place} is on {day}",', "marker", "is", "COPULA_AFTER_COUNTED_NOUN"),
        ('en: "{n} {plural:place} on {day}",', "marker", "on", "VERB_OR_WORD_AFTER_NOT_COPULA"),
        ('en: "{n} {plural:place} selected",', "marker", "selected", "VERB_OR_WORD_AFTER_NOT_COPULA"),
        ("`these ${c} ${englishCountNoun(c, \"stop\")} are walked`,", "helper", "are", "COPULA_AFTER_COUNTED_NOUN"),
        ("`${c} ${englishCountNoun(c, \"stop\")} completed`,", "helper", "completed", "VERB_OR_WORD_AFTER_NOT_COPULA"),
    ]
    bad = []
    for text, arm, word, verdict in cases:
        recs = [r for r in scan_line(text) if r[0] == arm]
        if not recs:
            bad.append("no record for " + text[:44])
            continue
        r = recs[0]
        if r[5] != verdict or (word and r[3].lower() != word.lower()):
            bad.append("want %s/%s got %s/%s for %s" % (verdict, word, r[5], r[3], text[:44]))
        if r[5] == "COPULA_AFTER_COUNTED_NOUN" and word in ("are", "were", "is") and r[8] == r[7]:
            bad.append("suggested rewrite did not change the snippet for " + text[:44])
    return ("SELFTEST OK cases=%d" % len(cases)) if not bad else ("SELFTEST BROKEN " + " | ".join(bad))


def main():
    tip = sys.argv[1] if len(sys.argv) > 1 else ""
    if not tip:
        tip = git("ls-remote", "origin", AUTH)[1].split("\t")[0].strip()
    rc, t = git("cat-file", "-t", tip)
    files = [x.rsplit(":", 1)[-1] for x in git("grep", "-l", "-e", "{plural:", "-e", "englishCountNoun(", tip, "--", SCOPE)[1].splitlines() if x.strip()]
    rows = []
    for path in sorted(files):
        body = git("show", "%s:%s" % (tip, path))[1].splitlines()
        for n, line in enumerate(body, 1):
            s = line.strip()
            if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
                continue
            for rec in scan_line(line):
                rows.append([path, str(n)] + rec)
    hdr = ["file", "line", "arm", "token", "count_token", "word_after", "copula", "verdict",
           "suggested_fix", "before_snippet", "after_snippet"]
    with io.open(OUT_TSV, "w", encoding="utf-8", newline="\n") as h:
        h.write("\t".join(hdr) + "\n")
        for r in rows:
            h.write("\t".join(r) + "\n")
    hits = [r for r in rows if r[7] == "COPULA_AFTER_COUNTED_NOUN"]
    ev = ["tip %s cat-file -t rc=%d type=%s" % (tip, rc, t.strip()),
          "files_with_a_counted_noun_surface %d" % len(files),
          "counted_noun_tokens %d" % len(rows),
          "marker_tokens %d" % sum(1 for r in rows if r[2] == "marker"),
          "helper_tokens %d" % sum(1 for r in rows if r[2] == "helper"),
          "copula_after_counted_noun %d" % len(hits)]
    for r in hits:
        ev.append("HIT %s:%s arm=%s token=%s copula=%s before=[%s] after=[%s]" % (r[0], r[1], r[2], r[3], r[6], r[9], r[10]))
    ev.append("calibration_against_the_ruling_rows poiImportCopy:159=%s poiImportCopy:163=%s dict_line_now=%s" % (
        any(r[0].endswith("poiImportCopy.ts") and r[1] == "159" for r in hits),
        any(r[0].endswith("poiImportCopy.ts") and r[1] == "163" for r in hits),
        [r[0] + ":" + r[1] for r in hits if "LocaleContext" in r[0]]))
    ev.append(selftest())
    with io.open(OUT_EV, "w", encoding="utf-8", newline="\n") as h:
        h.write("\n".join(ev) + "\n")
    print("\n".join(ev))
    print("tsv_rows %d" % len(rows))
    return 1 if "BROKEN" in ev[-1] else 0


if __name__ == "__main__":
    sys.exit(main())
