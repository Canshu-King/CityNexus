"""Measure the duplicate ledger insertion of my own block, refuse if it is not exactly two copies.

Nothing here writes to the ledger, to the product tree, or to any ref. Read-only measurement
plus two derived artifacts in this work directory (a JSON and a flat TSV with one reading per line).
"""
import hashlib
import io
import json
import os
import subprocess
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPO = r"D:\moodle\CityNexus"
PROCESSED = r"D:\moodle\_qoder_ledger_inbox\_processed"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

TITLE = ("### 自申报那格再走一步：给写腿的空输入门做了一把可达性尺"
         "（三枚正对照按真跑对号、合成夹具会区分），"
         "顺手在我刚落地的那枚自检里量出一形「两侧都没有内容也判绿」——已发布件一字未动，改法等点单")
CLOSING = "竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度"

RECEIPTS = [
    os.path.join(PROCESSED, "1d64acf5_0347.md.inserted_035112"),
    os.path.join(PROCESSED, "1d64acf5_0447.md.inserted_044731"),
]

INBOX_NOW = r"D:\moodle\_qoder_ledger_inbox"


def read_lines():
    raw = io.open(LEDGER, "rb").read()
    return raw, raw.split(b"\n")


def git(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("git failed %s :: %s" % (args[:2], proc.stderr.decode("utf-8", "replace")[:200]))
    return proc.stdout.decode("utf-8", "replace").strip()


def blob_of_text(text):
    """git blob id of a string, computed the same way git hash-object would."""
    data = text.encode("utf-8")
    header = b"blob %d\0" % len(data)
    return hashlib.sha1(header + data).hexdigest()


def main():
    measured_at = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"],
        capture_output=True).stdout.decode("utf-8", "replace").strip()

    raw, lines = read_lines()
    # line numbers of the heading, 1-based
    hits = [i + 1 for i, ln in enumerate(lines) if ln.decode("utf-8", "replace").rstrip("\r") == TITLE]
    if len(hits) != 2:
        raise SystemExit("ABORT: expected exactly 2 heading hits, got %d - the claim would be wrong" % len(hits))

    # bound each copy: heading line -> the closing-line within the next 120 lines
    copies = []
    for start in hits:
        end = None
        for j in range(start, min(start + 120, len(lines))):
            if lines[j].decode("utf-8", "replace").rstrip("\r").startswith(CLOSING):
                end = j + 1  # 1-based inclusive
                break
        if end is None:
            raise SystemExit("ABORT: no closing line found after heading at %d" % start)
        body = b"\n".join(lines[start - 1:end])
        copies.append({
            "heading_line": start,
            "closing_line": end,
            "line_span": end - start + 1,
            "bytes_in_ledger": len(body),
            "sha256_body": hashlib.sha256(body).hexdigest(),
            "blob_body": blob_of_text(body.decode("utf-8")),
        })

    if copies[0]["sha256_body"] != copies[1]["sha256_body"]:
        raise SystemExit("ABORT: the two heading matches are NOT the same bytes - this is not a duplicate insertion")

    receipts = []
    for path in RECEIPTS:
        if not os.path.exists(path):
            raise SystemExit("ABORT: missing receipt %s" % path)
        data = open(path, "rb").read()
        receipts.append({
            "path": path.replace("\\", "/"),
            "bytes": len(data),
            "blob": blob_of_text(data.decode("utf-8")),
            "mtime": subprocess.run(["powershell", "-NoProfile", "-Command",
                                     "(Get-Item -LiteralPath '%s').LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')" % path],
                                    capture_output=True).stdout.decode("utf-8", "replace").strip(),
        })
    if receipts[0]["blob"] != receipts[1]["blob"]:
        raise SystemExit("ABORT: the two receipts differ by bytes")

    # what the inbox holds right now for my lane: proves no third copy is still queued
    inbox_mine = sorted(f for f in os.listdir(INBOX_NOW)
                        if f.startswith("1d64acf5_") and f.endswith(".md"))
    gate_copy = sorted(f for f in os.listdir(INBOX_NOW) if "gatecheck" in f.lower() or "_copy" in f.lower())

    tip = git("rev-parse", "HEAD")
    tip_parent_of_tip = git("rev-parse", "HEAD^")
    ls_remote = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]

    result = {
        "measured_at_local": measured_at,
        "ledger_path": LEDGER.replace("\\", "/"),
        "ledger_bytes": len(raw),
        "ledger_lines": len(lines),
        "heading_hits": hits,
        "heading_hit_count": len(hits),
        "copies": copies,
        "byte_equal": copies[0]["sha256_body"] == copies[1]["sha256_body"],
        "receipts": receipts,
        "receipt_blob_equal": receipts[0]["blob"] == receipts[1]["blob"],
        "inbox_mine_now": inbox_mine,
        "inbox_gatecheck_copies_now": gate_copy,
        "local_head": tip,
        "local_head_parent": tip_parent_of_tip,
        "ls_remote_tip": ls_remote,
        "ref_name": "refs/heads/mirror/integration-frontend-apple-pass1",
        "discipline": {
            "product_bytes_changed": 0,
            "authoritative_line_moved_by_me": 0,
            "force_push": 0,
            "ledger_written_by_me": 0,
        },
    }
    # a negative control on my own measurement: a title that must not be duplicated
    control = [i + 1 for i, ln in enumerate(lines)
               if ln.decode("utf-8", "replace").startswith("### 6efab655 · 号令者实例 A · 两枚候选落地")]
    result["control_single_hit_title"] = {
        "hits": control,
        "count": len(control),
        "note": "control title must be a single hit; if it were 2 the counter would be blind",
    }

    json_path = os.path.join(OUT_DIR, "dup_receipt_measure_r1.json")
    io.open(json_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(result, ensure_ascii=False, indent=1))

    rows = []
    rows.append(["local_head", result["local_head"]])
    rows.append(["local_head_parent", result["local_head_parent"]])
    rows.append(["ls_remote_tip", result["ls_remote_tip"]])
    rows.append(["ledger_bytes", result["ledger_bytes"]])
    rows.append(["ledger_lines", result["ledger_lines"]])
    rows.append(["heading_hits", ",".join(str(h) for h in result["heading_hits"])])
    rows.append(["heading_hit_count", result["heading_hit_count"]])
    rows.append(["copy_1_heading_line", copies[0]["heading_line"]])
    rows.append(["copy_1_closing_line", copies[0]["closing_line"]])
    rows.append(["copy_1_line_span", copies[0]["line_span"]])
    rows.append(["copy_1_bytes_in_ledger", copies[0]["bytes_in_ledger"]])
    rows.append(["copy_1_blob_body", copies[0]["blob_body"]])
    rows.append(["copy_2_heading_line", copies[1]["heading_line"]])
    rows.append(["copy_2_closing_line", copies[1]["closing_line"]])
    rows.append(["copy_2_line_span", copies[1]["line_span"]])
    rows.append(["copy_2_bytes_in_ledger", copies[1]["bytes_in_ledger"]])
    rows.append(["copy_2_blob_body", copies[1]["blob_body"]])
    rows.append(["byte_equal", result["byte_equal"]])
    rows.append(["receipt_1_bytes", receipts[0]["bytes"]])
    rows.append(["receipt_1_mtime", receipts[0]["mtime"]])
    rows.append(["receipt_2_bytes", receipts[1]["bytes"]])
    rows.append(["receipt_2_mtime", receipts[1]["mtime"]])
    rows.append(["receipt_blob_equal", result["receipt_blob_equal"]])
    rows.append(["inbox_mine_now", "|".join(inbox_mine) if inbox_mine else "EMPTY"])
    rows.append(["inbox_gatecheck_copies_now", "|".join(gate_copy) if gate_copy else "EMPTY"])
    rows.append(["control_title_hits", result["control_single_hit_title"]["count"]])
    rows.append(["measured_at_local", result["measured_at_local"]])

    tsv_path = os.path.join(OUT_DIR, "dup_erratum_flat_r1.tsv")
    with io.open(tsv_path, "w", encoding="utf-8", newline="\n") as fh:
        for i, (k, v) in enumerate(rows, start=1):
            fh.write("%d\t%s\t%s\n" % (i, k, v))

    sys.stdout.write(json.dumps({
        "heading_hits": result["heading_hits"],
        "byte_equal": result["byte_equal"],
        "copy_line_spans": [copies[0]["line_span"], copies[1]["line_span"]],
        "copy_bytes": [copies[0]["bytes_in_ledger"], copies[1]["bytes_in_ledger"]],
        "receipt_blobs_equal": result["receipt_blob_equal"],
        "control_title_hits": result["control_single_hit_title"]["count"],
        "ls_remote_tip": result["ls_remote_tip"],
        "json": json_path,
        "tsv": tsv_path,
    }, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
