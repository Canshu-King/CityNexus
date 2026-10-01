"""ORD-0545 acceptance item two: read the same screen on BOTH sides of the move, same store.

The acceptance line asks for 搬前后两代产物对读.  My earlier evidence was an assertion about one
string on each side; this is the page itself, taken twice, from two checkouts that differ only by this
order's three files (dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5 is the direct parent of
8d259c1f75daae0ace81ebe2b32d3f5508fd83b6, and no other lane sits between them).

Everything that could drift is pinned: the same copy of the scheduled store (re-copied per
generation), the same backend port, the same vite dev server, the same viewport, the same stored
journey reference, the same locale.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
GENERATIONS = [
    ("pre_move", "dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5"),
    ("post_move", "8d259c1f75daae0ace81ebe2b32d3f5508fd83b6"),
]
JOURNEY = "22222222-2222-4222-8222-222222222222"
BACKEND_PORT, FRONT_PORT = 4911, 4912


def ports_listening(port):
    finished = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    return sorted({line.split()[-1] for line in finished.stdout.splitlines()
                   if len(line.split()) >= 5 and f":{port} " in line
                   and line.split()[3] == "LISTENING"})


def run(cmd, cwd, env=None, timeout=300):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def wait_port(port, seconds=90):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if ports_listening(port):
            return True
        time.sleep(2)
    return False


def main():
    readings = {}
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    for label, rev in GENERATIONS:
        checkout = run(["git", "checkout", "--detach", rev], str(ROOT))
        assert checkout.returncode == 0, checkout.stderr[-300:]
        head = run(["git", "rev-parse", "HEAD"], str(ROOT)).stdout.strip()
        assert head == rev, (head, rev)

        stack = run([PY, "review/ord0533/lane_stack_r1.py", "--start"], str(ROOT),
                    env={**env, "CITYNEXUS_ORD0533_TAG": f"0545_{label}"}, timeout=600)
        assert stack.returncode == 0, stack.stdout[-400:] + stack.stderr[-400:]

        vite = subprocess.Popen(
            ["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(FRONT_PORT)],
            cwd=str(ROOT / "frontend"),
            # vite.config.ts proxies /api to CITYNEXUS_BACKEND_PORT and defaults to 8000, which on this
            # box belongs to somebody else's backend.  Without this the "read" would be taken against
            # another lane's store and still look like a page.
            env={**env, "CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT)},
            stdout=open(DATA / f"vite_{label}.log", "w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        try:
            if not wait_port(FRONT_PORT):
                raise RuntimeError(f"vite never listened on {FRONT_PORT} for {label}")
            out_path = DATA / f"screen_{label}.txt"
            dump = run(["node", str(DATA / "dump_screen.cjs"),
                        f"http://127.0.0.1:{FRONT_PORT}", str(out_path), JOURNEY],
                       str(ROOT / "frontend"), env=env, timeout=300)
            assert dump.returncode == 0, dump.stdout[-400:] + dump.stderr[-400:]
            text = out_path.read_text(encoding="utf-8")
            label_text = out_path.with_name(f"screen_{label}.label.txt").read_text(encoding="utf-8")
            readings[label] = {
                "generation": rev,
                "characters": len(text),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "badge_cell": label_text,
                "key_names_visible": text.count("poiImport."),
                "machine_words": len([m for m in __import__("re").findall(
                    r"[A-Z][A-Z0-9]*_[A-Z0-9_]+", text)]),
            }
        finally:
            run(["taskkill", "/T", "/F", "/PID", str(vite.pid)], str(ROOT), timeout=120)
            run([PY, "review/ord0533/lane_stack_r1.py", "--stop"], str(ROOT), env=env, timeout=180)
            # A stale server under a new checkout fakes a product state, so the ports must be empty
            # before the next generation is read -- proved, not assumed from the kill's exit code.
            time.sleep(2)
            assert not ports_listening(FRONT_PORT), f"vite still on {FRONT_PORT} after {label}"
            assert not ports_listening(BACKEND_PORT), f"backend still on {BACKEND_PORT} after {label}"

    restore = run(["git", "checkout", "review/newlane-ord0545-badge-copy-table-r2"], str(ROOT))
    assert restore.returncode == 0, restore.stderr[-300:]

    same = readings["pre_move"]["sha256"] == readings["post_move"]["sha256"]
    result = {
        "controlled_pair": {"pre": readings["pre_move"]["generation"],
                            "post": readings["post_move"]["generation"],
                            "relationship": "direct parent and child; only ORD-0545's three files differ"},
        "readings": readings,
        "page_text_identical": same,
        "badge_cell_equal": readings["pre_move"]["badge_cell"] == readings["post_move"]["badge_cell"],
        "differences": None if same else {
            k: [readings["pre_move"], readings["post_move"]] for k in ("characters", "sha256")},
        "backend_stack": "same runner, per-generation copy of the canary store (mode=ro + online backup)",
        "viewport": "390x844", "locale": "zh-CN", "stored_journey_reference": JOURNEY,
    }
    if not same:
        a = (DATA / "screen_pre_move.txt").read_text(encoding="utf-8").splitlines()
        b = (DATA / "screen_post_move.txt").read_text(encoding="utf-8").splitlines()
        result["line_diff_sample"] = [{"pre": x, "post": y} for x, y in zip(a, b) if x != y][:10]
        result["line_count"] = {"pre": len(a), "post": len(b)}
    (DATA / "two_gen_read.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                            encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=1, ensure_ascii=True))
    return 0 if same and result["badge_cell_equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
