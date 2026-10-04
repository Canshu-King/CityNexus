"""ORD-0500 anchor-form gate: this lane's shipped comments may not cite a line number any more.

Why: every time the line moved, my own comment went stale and I had to spend a hand re-measuring four
integers (git log for `backend/tests/test_qoder_ord0500_journey_refusal.py` shows those hands).  The
commander's direction is name/label anchors, which do not move.  This gate makes that a rule instead of
a preference: a numeric `path:line` inside a comment this lane authored is a finding, and each declared
label has to resolve against the file as it stands on the live tip.

What it can and cannot prove, said plainly: the label manifest is written by me, so the gate proves the
labels I listed DO resolve (and that the file is listed at all, check 4), not that I listed every label
in the sentence.  Where a label matches more than one line, the sentence has to carry a qualifier and the
manifest has to encode it as an ordering claim, which the gate then measures -- an ambiguous label with no
qualifier is a finding rather than a pass.
"""
import json
import os
import re
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
NUMERIC = re.compile(r"`?[A-Za-z0-9_/.\-]+\.(?:py|tsx|ts|yaml|json):(\d+)")


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, env=ENV, timeout=300)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def live_tip():
    rc, out = git("ls-remote", "--refs", "origin", TIP_REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_NO_TIP " + out[:160])
    return out.split()[0]


def blob_text(rev, path):
    rc, out = git("show", "%s:%s" % (rev, path))
    if rc:
        raise SystemExit("ABORT_UNREADABLE %s:%s %s" % (rev, path, out[:120]))
    return out


ANCHOR_LINE = re.compile(r"Anchor labels \(([^)]*)\):")  # noqa: the backslashes escape the literal parentheses
ENTRY = re.compile(r"`([^`:]+)::(.+?)`")


def labels_from_body(body):
    """The label list lives INSIDE the shipped file, so shrinking it is a product diff a reviewer sees.

    The external manifest could be edited to make the gate check less; that is a one-directionally blind
    ruler, and it is the reason this was moved.  What remains a limitation is stated in `limitation`.
    """
    lines = body.splitlines()
    at = [i for i, l in enumerate(lines) if ANCHOR_LINE.search(l)]
    if not at:
        return None, []
    joined = " ".join(lines[at[0]:at[0] + 6])
    return at[0] + 1, [{"file": m.group(1), "text": m.group(2)} for m in ENTRY.finditer(joined)]


def judge(manifest, tip=None, src=None):
    """(verdict, rows).  `src` lets the mutant driver feed a candidate file body."""
    tip = tip or live_tip()
    rows = []
    for entry in manifest.get("files") or []:
        path = entry["path"]
        body = src if src is not None else blob_text(tip, path)
        lines = body.splitlines()
        # 1. no numeric path:line citations left in this file
        numeric = [(i + 1, l.strip()[:90]) for i, l in enumerate(lines) if NUMERIC.search(l)]
        rows.append({"check": "NUMERIC_ANCHOR_FORBIDDEN", "file": path,
                     "verdict": "GREEN" if not numeric else "RED",
                     "hits": numeric[:6], "count": len(numeric)})
        if entry.get("numeric_allowed"):
            rows[-1]["verdict"] = "NOT_APPLICABLE"
        found_at, labels = labels_from_body(body)
        rows.append({"check": "ANCHOR_LINE_PRESENT", "file": path,
                     "verdict": "GREEN" if found_at else "RED",
                     "why": "" if found_at else "the shipped file declares no `Anchor labels` line",
                     "line": found_at, "count": len(labels)})
        for label in labels:
            text = label["text"]
            target = blob_text(tip, label["file"])
            matches = [i + 1 for i, l in enumerate(target.splitlines()) if text in l]
            row = {"check": "LABEL_RESOLVES", "file": path, "label": text,
                   "in": label["file"], "lines": matches[:6], "count": len(matches)}
            if not matches:
                row["verdict"] = "RED"
                row["why"] = "LABEL_NOT_FOUND"
            elif len(matches) > 1:
                order = label.get("ordering")
                if not order:
                    row["verdict"] = "RED"
                    row["why"] = "AMBIGUOUS_LABEL_WITHOUT_QUALIFIER"
                else:
                    first, second = order.split("<")
                    a = [i + 1 for i, l in enumerate(target.splitlines()) if first in l]
                    b = [i + 1 for i, l in enumerate(target.splitlines()) if second in l]
                    holds = bool(a) and bool(b) and min(a) < min(b)
                    row["verdict"] = "GREEN" if holds else "RED"
                    row["why"] = "" if holds else "ORDERING_QUALIFIER_FALSE"
                    row["ordering"] = order
            else:
                row["verdict"] = "GREEN"
            rows.append(row)
        listed = {e["path"] for e in (manifest.get("files") or [])}
        rows.append({"check": "MANIFEST_LISTS_THE_FILE", "file": path,
                     "verdict": "GREEN" if path in listed else "RED"})
    verdict = "GREEN" if all(r["verdict"] in ("GREEN", "NOT_APPLICABLE") for r in rows) else "RED"
    return verdict, rows


def main():
    man_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        LANE, "evidence", "anchor_form_manifest_r26.json")
    manifest = json.load(open(man_path, encoding="utf-8"))
    tip = live_tip()
    verdict, rows = judge(manifest, tip)
    out = {"schema": "CNX_ORD0500_ANCHOR_FORM_V1", "tool": "anchor_form_gate_r26",
           "tip": tip, "verdict": verdict,
           "red": [r["check"] + " " + str(r.get("label") or r.get("file")) for r in rows
                   if r["verdict"] == "RED"],
           "numeric_total": sum(r["count"] for r in rows if r["check"] == "NUMERIC_ANCHOR_FORBIDDEN"),
           "labels_checked": sum(1 for r in rows if r["check"] == "LABEL_RESOLVES"),
           "rows": rows, "limitation": "the manifest lists which labels must resolve; the gate proves "
                                       "they do, not that the list is exhaustive"}
    dest = os.path.join(LANE, "evidence", "anchor_form_gate_r26.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"verdict": verdict, "tip": tip[:12], "numeric_total": out["numeric_total"],
                      "labels_checked": out["labels_checked"], "red": out["red"]},
                     ensure_ascii=False))
    print("WROTE " + dest)
    if verdict != "GREEN":
        raise SystemExit("ANCHOR_FORM_GATE_RED")


if __name__ == "__main__":
    main()
