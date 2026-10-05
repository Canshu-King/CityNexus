"""How much of the traveller-facing copy the LINE carries is actually in the bundle the phone chain serves?

The chain answers now, but it serves an older build, and last time I checked that only for four nav labels.
This asks it for my own order's sentences -- the refusal vocabulary ORD-0500 shipped in
`features/checkin/checkinCopy.ts` and `footprintCopy.ts`, which deliberately live OUTSIDE the shared i18n
dictionary.  The question a swap decision needs is: if the commander rebuilds tomorrow, is the text travellers
are supposed to see actually waiting in the built app, and how much of what the line already carries is missing
from the build being served today?

Method, and the parts that could lie:
  * strings are read from the live tip's own source files, not typed here;
  * a Vite build splits code, so grepping the entry bundle alone would understate coverage. Every chunk name
    referenced from the entry is fetched too, and the fetch list is reported;
  * only values that are plain sentences count toward the denominator; anything with an interpolation placeholder
    (`{n}`, `{moment}`) is counted separately as untestable, because a built bundle can hold its parts apart;
  * two controls keep the grep honest: a long-standing label must be found, a nonsense string must not be.
"""
import json
import os
import re
import urllib.request
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
BASE = "http://127.0.0.1:4783"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
SOURCES = ["frontend/src/features/checkin/checkinCopy.ts", "frontend/src/features/checkin/footprintCopy.ts"]
CONTROL_PRESENT = "足迹"          # a nav label the served build already carries
CONTROL_ABSENT = "zzcnxnothereqwerty"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
PLACEHOLDER = re.compile(r"[{\\]|\$\{")
VALUE_RE = re.compile(r'(?:zh|en)\s*:\s*"([^"\n]{7,200})"')
CHUNK_RE = re.compile(r"[\"']\./([A-Za-z0-9_.$-]+\.js)[\"']|assets/([A-Za-z0-9_.$-]+\.js)")


def git(*args):
    import subprocess
    q = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=300, env=ENV)
    return q.returncode, q.stdout.decode("utf-8", "replace")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "cnx-0afdb49b-copy-coverage/1",
                                               "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read().decode("utf-8", "replace")


def source_values(tip):
    rows = []
    for path in SOURCES:
        rc, text = git("show", "%s:%s" % (tip, path))
        if rc:
            raise SystemExit("ABORT_SOURCE_UNREADABLE " + path)
        for m in VALUE_RE.finditer(text):
            v = m.group(1).strip()
            line = text[:m.start()].count("\n") + 1
            rows.append({"path": path, "line": line, "value": v,
                         "testable": not PLACEHOLDER.search(v)})
    return rows


def main():
    tip = git("ls-remote", "--refs", "origin", TIP_REF)[1].split()[0]
    rows = source_values(tip)
    status, html = fetch(BASE + "/index.html")
    entry = re.findall(r'src="(/assets/[^"]+\.js)"', html)
    if not entry:
        raise SystemExit("ABORT_NO_ENTRY_BUNDLE status=%s" % status)
    e_status, entry_text = fetch(BASE + entry[0])
    chunks = sorted({(a or b) for a, b in CHUNK_RE.findall(entry_text)})
    fetched, failed, corpus = [entry[0]], [], []
    # the static server answers an unknown path with the SPA shell, so a "200" is not proof of a chunk:
    # anything that comes back looking like HTML is counted as a fallback and kept OUT of the corpus,
    # otherwise a missing file would be silently searched as if it were the app.
    fallback = []
    for name in chunks[:120]:
        url = "/assets/" + name.split("/")[-1]
        try:
            s, t = fetch(BASE + url)
        except Exception as e:
            failed.append({"url": url, "error": type(e).__name__})
            continue
        if t.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
            fallback.append(url)
            continue
        fetched.append(url)
        corpus.append(t)
    corpus.append(entry_text)
    blob = "\n".join(corpus)
    if CONTROL_PRESENT not in blob:
        raise SystemExit("ABORT_CONTROL_PRESENT_NOT_FOUND -- the corpus is not being read, not that the copy is absent")
    if CONTROL_ABSENT in blob:
        raise SystemExit("ABORT_CONTROL_ABSENT_FOUND -- the grep is matching nothing meaningful")
    hit = miss = skip = 0
    misses = []
    for r in rows:
        if not r["testable"]:
            skip += 1
            continue
        if r["value"] in blob:
            hit += 1
        else:
            miss += 1
            misses.append({"path": r["path"], "line": r["line"], "value": r["value"]})
    out = {"schema": "CNX_LANDED_COPY_COVERAGE_V1", "tool": "landed_copy_coverage_r1",
           "took_local": datetime.now().astimezone().isoformat(), "live_tip": tip,
           "served_index_status": status, "entry_bundle": entry[0], "entry_bytes": len(entry_text),
           "chunks_discovered": len(chunks), "files_fetched": len(fetched), "fetch_failures": failed,
           "spa_fallback_responses": len(fallback), "spa_fallback_urls": fallback[:6],
           "corpus_bytes": len(blob), "source_files": SOURCES, "values_read": len(rows),
           "values_untestable_placeholders": skip, "values_in_served_build": hit,
           "values_not_in_served_build": miss,
           "coverage_percent": round(100.0 * hit / max(1, hit + miss), 1),
           "missing_examples": misses[:12], "controls": {"present_found": True, "absent_found": False,
                                                         "present": CONTROL_PRESENT, "absent": CONTROL_ABSENT},
           "reading_rule": "词面在包里=可被渲染的必要条件；不在包里=这一代产物里没有这句话",
           "limit": "构建可能把带占位符的句子拆开，那类值另计不计入分母；同源不同代的两份产物不能互证",
           "worktree_written": False}
    dest = os.path.join(LANE, "evidence", "landed_copy_coverage_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("live_tip", "entry_bundle", "chunks_discovered", "files_fetched",
                                          "corpus_bytes", "values_read", "values_untestable_placeholders",
                                          "values_in_served_build", "values_not_in_served_build",
                                          "coverage_percent", "fetch_failures")}, ensure_ascii=False, indent=1))
    for m in out["missing_examples"]:
        print("MISSING %s:%d  %s" % (m["path"].split("/")[-1], m["line"], m["value"][:60]))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
