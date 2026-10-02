"""ORD-0500 r6: run the door's own arms on THIS tree, on a private store, and prove the shared store
was not touched.

Why this run exists at all: r6 replays r5's `backend/app/main.py` byte-for-byte, and I could have
carried r5's door readings forward.  Q24 says a reading belongs to the generation it was taken on, so
the arms are re-run here instead -- and the receipt also carries the three blob ids that show the
claim "the backend did not change" is about bytes, not about my memory: my candidate's `main.py`, the
r5 commit's `main.py`, and the tip's `main.py`.

The store is a fresh `backup()` copy of the shared preview DB over a read-only connection; the shared
file's size and mtime are read before and after and must be equal.
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
WT = os.path.join(LANE, "wt22")
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
DB = os.path.join(LANE, "run", "r6_pytest.db")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
R5 = "ba1c5d82b878c97d2a1e78adf8e7ad75edc2ec3b"
TIP = os.environ.get("R6_BASE_TIP") or "dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5"
FILES = ["tests/test_qoder_ord0500_journey_refusal.py", "tests/test_qoder_ord0476_checkins.py"]


def blob(cwd, rev, path):
    p = subprocess.run(["git", "-C", cwd, "rev-parse", "%s:%s" % (rev, path)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return p.stdout.decode("utf-8", "replace").strip() if p.returncode == 0 else "UNRESOLVABLE"


def stat_shared():
    st = os.stat(SHARED)
    return {"bytes": st.st_size, "mtime_ns": st.st_mtime_ns}


def main():
    for suffix in ("", "-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            os.remove(p)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)
    dst.close()
    src.close()
    before = stat_shared()

    env = {k: v for k, v in os.environ.items()
           if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    env.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
                "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false",
                "PYTHONPATH": WT, "PYTHONUTF8": "1"})
    p = subprocess.run([PY, "-X", "utf8", "-m", "pytest", "-q", "--no-header",
                        "-p", "no:cacheprovider"] + FILES, cwd=os.path.join(WT, "backend"),
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
    text = p.stdout.decode("utf-8", "replace")
    open(os.path.join(LANE, "run", "r6_pytest.txt"), "w", encoding="utf-8").write(text)
    after = stat_shared()

    con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    rows = con.execute("SELECT COUNT(*) FROM journey_checkins").fetchone()[0]
    con.close()

    out = {"tool": "pytest_r6", "took_local": datetime.now().astimezone().isoformat(),
           "exit": p.returncode, "files": FILES,
           "summary_lines": [l for l in text.splitlines() if l.strip()][-3:],
           "private_db": os.path.basename(DB),
           "checkin_rows_after_the_arms": rows,
           "shared_before": before, "shared_after": after,
           "shared_untouched": before == after,
           "main_py_blobs": {"candidate_worktree": blob(WT, "HEAD", "backend/app/main.py"),
                             "r5_commit": blob(WT, R5, "backend/app/main.py"),
                             "tip_at_run": blob(REPO, TIP, "backend/app/main.py")},
           "pytest_stdout_head": text[:400]}
    path = os.path.join(LANE, "evidence", "pytest_r6.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0 if p.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
