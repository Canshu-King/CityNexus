"""ORD-0504 A -- grade four generations of the 预订 face on one store, and prove each fix is load-bearing.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/book_face_fixA_cycle_r1.py

  tip    the file exactly as the authoritative tip holds it  -> the three arms are red (two passes)
  fix    the shipped fix                                      -> all twelve arms green (two passes)
  MA1    only the 已确认 word put back on commitment_id        -> the status arm red, the kind arms green
  MA2    only the kind word put back on the door's token      -> the two kind arms red, the status arm green

Each generation is built into its own directory, served on this lane's own front, and witnessed: the entry
JS the port answers is hashed and compared against the bytes just built, because a cycle that grades a stale
bundle proves nothing (that is how the previous hand lost a round). The product file is written back to the
committed bytes at the end and the equality is printed.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import book_screen_controls_r1 as ctl  # noqa: E402

TARGET = ctl.TARGET  # frontend/src/app/V8Experience.tsx
TIP = "701b5e3868fa9bed6e7b6a377d1c4a38a5e0d06b"
OUT = ctl.TREE / "review" / "ord0504" / "book_face_fixA_cycle_r1.txt"

STATUS_SPAN_OLD = """              <span className={`v8-booking-state${item.commitment_id ? " safe" : ""}`}>
                {item.commitment_id
                  ? zh
                    ? "已确认 · 受保护"
                    : "Confirmed · protected"
                  : zh
                    ? "已确认 · 未成承诺"
                    : "Confirmed · no commitment"}
              </span>""".encode("utf-8")

STATUS_SPAN_NEW = """              <span
                className={`v8-booking-state${serverConfirmed(item.status) && item.commitment_id ? " safe" : ""}`}
              >
                {!serverConfirmed(item.status)
                  ? zh
                    ? "待确认 · 服务器未确认"
                    : "Pending · the server has not confirmed it"
                  : item.commitment_id
                    ? zh
                      ? "已确认 · 受保护"
                      : "Confirmed · protected"
                    : zh
                      ? "已确认 · 未成承诺"
                      : "Confirmed · no commitment"}
              </span>""".encode("utf-8")

KIND_TABLE_NEW = """  TRAIN: { zh: "火车", en: "Train" },
""".encode("utf-8")

KIND_FALLBACK_NEW = """  const entry = BOOKING_TYPES[String(value ?? "").toUpperCase()];
  if (entry) return zh ? entry.zh : entry.en;
  return zh ? BOOKING_TYPE_UNKNOWN.zh : BOOKING_TYPE_UNKNOWN.en;""".encode("utf-8")

KIND_FALLBACK_OLD = """  const key = String(value ?? "").toUpperCase();
  const entry = BOOKING_TYPES[key];
  if (entry) return zh ? entry.zh : entry.en;
  return key.replaceAll("_", " ").toLowerCase();""".encode("utf-8")


def git_show(rev: str, path: str) -> bytes:
    done = subprocess.run(["git", "-C", str(ctl.TREE), "show", "%s:%s" % (rev, path)],
                          capture_output=True)
    if done.returncode:
        raise SystemExit("REFUSE: git show %s:%s failed (%s)"
                         % (rev, path, done.stderr[-200:]))
    return done.stdout


def replace_once(data: bytes, find: bytes, replace: bytes, label: str) -> bytes:
    if data.count(find) != 1:
        raise SystemExit("REFUSE: %s found %d times in the shipped file; the mutant is not single-variable"
                         % (label, data.count(find)))
    return data.replace(find, replace, 1)


def grade(label: str, data: bytes) -> dict:
    TARGET.write_bytes(data)
    dist = "dist_cycleA_%s" % label
    ctl.rebuild(dist)
    ctl.restart_front(dist)
    served = ctl.served_entry()
    on_disk = hashlib.sha1((ctl.LANE / dist / served["entry"].lstrip("/")).read_bytes()).hexdigest()
    sink = "review/ord0504/book_screen_armsA_%s.json" % label.lower()
    env = dict(os.environ, BOOK_OUT=sink)
    done = subprocess.run([ctl.NODE, "review/ord0504/book_screen_facts_r1.js"], cwd=str(ctl.TREE),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    payload = json.loads((ctl.TREE / sink).read_text(encoding="utf-8"))
    reds = sorted(x["arm"] for x in payload.get("results", []) if not x.get("pass"))
    summary = [line for line in done.stdout.splitlines() if line.startswith("ARMS=")]
    return {"label": label, "summary": summary[-1] if summary else "no-summary",
            "reds": reds, "sink": sink, "entry": served["entry"], "served_sha1": served["sha1"],
            "served_equals_built": on_disk == served["sha1"],
            "driver_error": payload.get("driver_error") or "none",
            "exit": done.returncode}


def main() -> int:
    shipped = TARGET.read_bytes()          # the committed fix
    tip_bytes = git_show(TIP, "frontend/src/app/V8Experience.tsx")
    ma1 = replace_once(shipped, STATUS_SPAN_NEW, STATUS_SPAN_OLD, "the shipped status span")
    ma2 = replace_once(shipped, KIND_TABLE_NEW, b"", "the TRAIN table entry")
    ma2 = replace_once(ma2, KIND_FALLBACK_NEW, KIND_FALLBACK_OLD, "the shipped kind fallback")

    lines = ["ORD-0504 A cycle | the tip's own file bytes sha1 %s | shipped file sha1 %s"
             % (ctl.sha1(tip_bytes), ctl.sha1(shipped)), ""]
    results = []
    results.append(("tip #1", grade("tip", tip_bytes), False))
    results.append(("tip #2", grade("tip", tip_bytes), False))
    results.append(("fix #1", grade("fix", shipped), True))
    results.append(("fix #2", grade("fix", shipped), True))
    ma1_res = grade("ma1", ma1)
    results.append(("MA1", ma1_res, False))
    ma2_res = grade("ma2", ma2)
    results.append(("MA2", ma2_res, False))

    for name, res, _green in results:
        lines.append("=== %s  (%s)" % (name, res["label"]))
        lines.append("    %s" % res["summary"])
        lines.append("    driver error: %s | exit %s" % (res["driver_error"], res["exit"]))
        lines.append("    red arms: %s" % (res["reds"] or "none"))
        lines.append("    served %s sha1 %s | equals the bundle this generation built: %s"
                     % (res["entry"], res["served_sha1"], res["served_equals_built"]))
        lines.append("    arms reading: %s" % res["sink"])
        lines.append("")

    # single-variable checks: which arm moved, and did the other fix stay in place
    status_arm = "book_screen/confirmed_words_only_where_the_server_said_confirmed"
    kind_arms = ["book_screen/no_machine_token_on_the_chinese_face",
                 "book_screen/the_ticket_kind_is_drawn_from_the_word_table"]
    lines.append("verdict MA1: the status arm is red = %s | both kind arms green = %s"
                 % (status_arm in ma1_res["reds"],
                    all(arm not in ma1_res["reds"] for arm in kind_arms)))
    lines.append("verdict MA2: both kind arms red = %s | the status arm green = %s"
                 % (all(arm in ma2_res["reds"] for arm in kind_arms),
                    status_arm not in ma2_res["reds"]))
    lines.append("verdict tip: red set = %s" % (results[0][1]["reds"] or "none"))
    lines.append("verdict fix: both passes green with zero reds = %s"
                 % all(r["summary"].endswith("FAILED=0") for n, r, _ in results if n.startswith("fix")))

    TARGET.write_bytes(shipped)
    back = TARGET.read_bytes() == shipped
    lines.append("")
    lines.append("restored: bytes_equal_to_shipped=%s sha1=%s" % (back, ctl.sha1(TARGET.read_bytes())))
    lines.append("git status --porcelain -- frontend/src/app/V8Experience.tsx = %r"
                 % ctl.run(["git", "status", "--porcelain", "--",
                            "frontend/src/app/V8Experience.tsx"], cwd=ctl.TREE).stdout)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
