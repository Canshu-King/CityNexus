"""②=发, but only when the list is non-empty -- so this tool decides whether to post at all.

The commander's ruling was one sentence: send the ownership list as a daily note, and do not spend a
slot in the inbox on an empty day.  Both branches are therefore measured, not assumed: the count comes
from the audit receipt written in this window, the post is keyed by date so a re-run cannot double-send,
and an empty list exits without touching the bus.

The note lists, per citation this lane may not judge: the file:line that cites it, the mechanical verdict
the shape rules would have given, and the 40-hex commit that authored that line -- so the owner can be
found by `git cat-file -t` / `git show` instead of by guessing from a name.
"""
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
BUS = r"D:/moodle/agent_bus/bus.py"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TO = "qoder:494abfd7"
ME = "qoder:0afdb49b"
CLOSE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"


def newest_audit():
    hits = sorted(glob.glob(os.path.join(LANE, "evidence", "citation_audit_r*.json")),
                  key=lambda p: int(re.search(r"_r(\d+)\.json$", p).group(1)))
    if not hits:
        raise SystemExit("ABORT_NO_AUDIT_RECEIPT -- ② cannot be answered without a run of the "
                         "repo-wide ruler in this window")
    return hits[-1]


def main():
    audit_path = newest_audit()
    d = json.load(open(audit_path, encoding="utf-8"))
    rows = [r for r in (d.get("rows") or []) if r.get("verdict") == "NOT_THIS_LANES_CITATION"]
    day = datetime.now().astimezone().strftime("%Y-%m-%d")
    marker = os.path.join(LANE, "run", "citation_ownership_note_%s.sent" % day)
    tally = {}
    for r in rows:
        tally[r.get("mechanical_verdict") or r.get("resolution") or "UNKNOWN"] = \
            tally.get(r.get("mechanical_verdict") or r.get("resolution") or "UNKNOWN", 0) + 1

    if not rows:
        print(json.dumps({"would_post": False, "reason": "EMPTY_DECLINED_LIST",
                          "audit": os.path.basename(audit_path),
                          "declined": d.get("citations_declined"), "day": day}, indent=2,
                         ensure_ascii=False))
        return 0
    if os.path.exists(marker):
        print(json.dumps({"would_post": False, "reason": "ALREADY_SENT_TODAY",
                          "marker": marker, "message_id": open(marker, encoding="utf-8").read().strip()},
                         indent=2, ensure_ascii=False))
        return 0

    lines = []
    for r in sorted(rows, key=lambda x: (str(x.get("cited_by")), str(x.get("owner_commit")))):
        lines.append("| %s | %s | %s |" % (r.get("cited_by"),
                                           r.get("mechanical_verdict") or r.get("resolution"),
                                           r.get("owner_commit")))
    body = "\n".join([
        "ORD-0500 全线尺的归属清单（%s 这一天的第 1 枚，也是唯一一枚）：本尺看到 %s 条引用，判 %s 条"
        "（我自己名下的），不判 %s 条，出自 %s 位作者 commit。不判的那些我一枚没改。" % (
            day, d.get("citations_found"), d.get("citations_judged"), d.get("citations_declined"),
            d.get("declined_authors")),
        "",
        "按形状算（若它们归我判会报什么）：%s。" % (
            "、".join("%s %s 条" % kv for kv in sorted(tally.items()))),
        "",
        "| 引用所在（path:line，现读） | 机械判语 | 写下那一行的 commit（完整 sha，可 cat-file） |",
        "|---|---|---|",
        "\n".join(lines),
        "",
        "读数出处：`%s`（本车道窗口内现跑的全线尺件，取数 `python tools/citation_audit_r8.py`，"
        "它扫 %s 枚文件）。空一天这一枚就不发，按 2026-10-04 那句裁语②办。" % (
            os.path.basename(audit_path), d.get("files_scanned")),
    ])
    summary = os.path.join(LANE, "run", "citation_ownership_summary_%s.txt" % day)
    with open(summary, "w", encoding="utf-8", newline="\n") as f:
        f.write("audit receipt %s\ncitations_found %s\njudged %s\ndeclined %s\nauthors %s\nfiles_scanned %s\n%s\n" % (
            os.path.basename(audit_path), d.get("citations_found"), d.get("citations_judged"),
            d.get("citations_declined"), d.get("declined_authors"), d.get("files_scanned"),
            "\n".join(lines)))
    note_path = os.path.join(LANE, "run", "citation_ownership_note_%s.md" % day)
    closing = open(CLOSE, "rb").read().rstrip(b"\r\n").decode("utf-8")
    with open(note_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body + "\n\n" + closing + "\n")

    cmd = [PY, BUS, "send", "--from", ME, "--to", TO, "--kind", "note",
           "--topic", "citation-ownership-%s-%d" % (day, int(datetime.now().timestamp() * 1000) % 100000),
           "--body-file", note_path.replace("/", "\\"),
           "--evidence", "归属清单读数|type %s" % summary.replace("/", "\\")]
    p = subprocess.run(cmd, capture_output=True, timeout=600)
    print((p.stdout or b"").decode("utf-8", "replace")[-400:] or (p.stderr or b"").decode("utf-8", "replace")[-400:])
    # read the bus log back for the id we just wrote -- the send's own stdout is not proof of an id
    mine, last = [], None
    for l in open(os.path.join(LANE, "..", "agent_bus", "bus.jsonl"), encoding="utf-8"):
        l = l.strip()
        if not l:
            continue
        try:
            e = json.loads(l)
        except Exception:
            continue
        if e.get("from") == ME and e.get("kind") == "note" and str(e.get("topic", "")).startswith(
                "citation-ownership-" + day):
            mine.append(e.get("id"))
            last = e.get("id")
    if not last:
        raise SystemExit("ABORT_NOTE_NOT_READ_BACK -- bus.py answered but the log holds nothing for "
                         "%s on %s (rc=%s)" % (ME, day, p.returncode))
    with open(marker, "w", encoding="utf-8") as f:
        f.write(last + "\n")
    print(json.dumps({"posted": True, "message_id": last, "ids_today": len(mine),
                      "declined": d.get("citations_declined"), "note_file": note_path,
                      "summary_for_evidence": summary, "marker": marker}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
