"""Independent verification of the shipped 出页门 interlock (`refuse_on_red`), by lane 6a150e1e.

CMDR 19:45 asked this lane to add `ABORT_READINGS_RED` to the page emitter. Measured against the line,
the phone lane had already shipped exactly that (`review/ord0500-checkin/tools/r9_block.py:69`, called at
`r10_block.py:140`), so this lane does not add a second door -- it verifies the one on the line.

Self-contained: the two emitter files are taken from the line itself (`git show <tip>:<path>`), their
blob hashes are recomputed rather than asserted, and everything runs inside this directory. One command:

    python D:/moodle/_qoder_6a_ord0531_20261001/emitter_door_check_r1/door_check_r1.py
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

SCRATCH = pathlib.Path(__file__).resolve().parent
REPORT = SCRATCH / "emitter_door_verdict_r1.json"
OUT = SCRATCH / "run_scratch"
OUT.mkdir(exist_ok=True)
REPO = pathlib.Path(os.environ.get("DOOR_REPO", "D:/moodle/_qoder_n2b_ord0466_20260929/wt"))
TOOLS = "review/ord0500-checkin/tools"


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


TIP = os.environ.get("DOOR_TIP") or git("rev-parse", "origin/mirror/integration-frontend-apple-pass1")
blobs = {}
for name in ("r9_block.py", "r10_block.py"):
    raw = subprocess.run(["git", "-C", str(REPO), "show", f"{TIP}:{TOOLS}/{name}"],
                         capture_output=True, timeout=180)
    assert raw.returncode == 0, f"the line does not carry {name}: {raw.stderr[:120]}"
    (SCRATCH / name).write_bytes(raw.stdout)
    blobs[name] = git("hash-object", str(SCRATCH / name))
    assert blobs[name] == git("rev-parse", f"{TIP}:{TOOLS}/{name}"), f"copy of {name} is not the line's bytes"

sys.path.insert(0, str(SCRATCH))
import r9_block as B  # noqa: E402  extracted above and hash-checked against the line

checks = []


def add(name, ok, detail):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})


GREEN = [("引文闸判语", True, "GREEN"), ("引文闸反件全咬", True, "bit"), ("后端臂退出码", True, "0")]

# 1. all green: the door opens and writes nothing
before = set(OUT.iterdir())
result = B.refuse_on_red("verdr1", GREEN, dest_dir=str(OUT))
add("all_green_opens_and_writes_nothing",
    result.get("verdict") == "GREEN" and result.get("checks") == len(GREEN)
    and set(OUT.iterdir()) == before, {"result": result, "new_files": sorted(
        str(p.name) for p in set(OUT.iterdir()) - before)})

# 2. one red: the page is refused and the only artifact is the named failure sheet
try:
    B.refuse_on_red("verdr2", GREEN + [("词汇闸判语", False, "RED")], dest_dir=str(OUT))
    add("one_red_raises", False, "refuse_on_red returned instead of aborting")
except SystemExit as exit_:
    sheet = OUT / "verdr2_READINGS_RED.json"
    data = json.loads(sheet.read_text(encoding="utf-8")) if sheet.exists() else {}
    add("one_red_raises", str(exit_).startswith("ABORT_READINGS_RED"), str(exit_)[:120])
    add("red_writes_only_the_named_sheet",
        sheet.exists() and data.get("aborts") == "ABORT_READINGS_RED"
        and not (OUT / "verdr2_block_page.md").exists()
        and len(data.get("failed_checks") or []) == 1,
        {"sheet": sheet.name, "aborts": data.get("aborts"),
         "failed": [c.get("check") for c in data.get("failed_checks") or []]})
    add("sheet_says_the_page_was_not_generated", "not generated" in str(data.get("note", "")),
        str(data.get("note"))[:120])

# 3. the lane's own hook: every check true, one named -- the door still bites
env = {**os.environ, "R10_FORCE_RED": "后端臂退出码"}
try:
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys;r=sys.argv[1];o=sys.argv[2];sys.path.insert(0,r);import r9_block as B;"
         "B.refuse_on_red('verdr3',[('引文闸判语',True,'GREEN'),('后端臂退出码',True,'0')],"
         "dest_dir=o)",
         str(SCRATCH), str(OUT)],
        cwd=str(SCRATCH), capture_output=True, text=True, env=env, timeout=120,
    )
    sheet = OUT / "verdr3_READINGS_RED.json"
    data = json.loads(sheet.read_text(encoding="utf-8")) if sheet.exists() else {}
    add("forced_red_hook_bites",
        "ABORT_READINGS_RED" in (proc.stderr + proc.stdout) and sheet.exists()
        and data.get("failed_checks") and data["failed_checks"][0].get("forced") is True,
        {"stderr_tail": (proc.stderr or proc.stdout).strip()[-140:],
         "forced_row": (data.get("failed_checks") or [{}])[0].get("check")})
except BaseException as exc:  # noqa: BLE001 - a failure here is itself the finding
    add("forced_red_hook_bites", False, f"{type(exc).__name__}: {exc}")

# 4. ordering on the line: the refusal is reached long before the page can be opened
r10 = (SCRATCH / "r10_block.py").read_text(encoding="utf-8").splitlines()
refuse_at = next(i for i, l in enumerate(r10, 1) if "B.refuse_on_red(" in l)
write_at = next(i for i, l in enumerate(r10, 1) if 'open(dest, "w"' in l)
add("refusal_precedes_the_page_write", refuse_at < write_at,
    {"refuse_on_red_line": refuse_at, "page_write_line": write_at})

summary = {"verifier": "lane 6a150e1e, D:/moodle/_qoder_6a_ord0531_20261001/emitter_door_check_r1",
           "subject": f"refuse_on_red as shipped on {TIP}",
           "copies_are_the_line_bytes": blobs,
           "checks_total": len(checks), "checks_failed": [c["check"] for c in checks if not c["pass"]],
           "checks": checks}
REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                  newline="\n")
print(json.dumps({"checks_total": summary["checks_total"],
                  "checks_failed": summary["checks_failed"]}, ensure_ascii=False))
for c in checks:
    print(("PASS " if c["pass"] else "FAIL ") + c["check"])
raise SystemExit(0 if not summary["checks_failed"] else 1)
