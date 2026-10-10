# -*- coding: utf-8 -*-
"""行号定位腿：判据逐字取自号令者那把对拍尺 _bilingual_count_r1.py 的 TERN 与 CJK，
本尺只补一件事——把每处命中的起始行号读出来。不改判据、不放宽、不收紧。"""
import io
import json
import subprocess
import sys

sys.path.insert(0, r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
from _bilingual_count_r1 import TERN, CJK  # noqa: E402  same predicates, verbatim

REPO = "D:/moodle/CityNexus"


def blob_text(sha, path):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (sha, path)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit("SHOW_FAIL %s:%s :: %s" % (sha[:10], path, p.stderr.decode("utf-8", "replace")[:200]))
    return p.stdout.decode("utf-8", "replace")


def main():
    sha = sys.argv[1]
    out = []
    for path in sys.argv[2:]:
        text = blob_text(sha, path)
        lines = text.splitlines()
        hits = []
        for m in TERN.finditer(text):
            a, b = m.group(1), m.group(2)
            if bool(CJK.search(a)) != bool(CJK.search(b)):
                line_no = text.count("\n", 0, m.start()) + 1
                hits.append({"line": line_no, "text": lines[line_no - 1].strip()[:120]})
        out.append({"path": path, "count": len(hits), "hits": hits})
    print(json.dumps({"sha": sha, "files": out}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
