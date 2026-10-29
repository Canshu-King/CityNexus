"""One-line fixture repair, with its own before/after count.

The shared helper signs the plan selection as the demo traveller but posts /start with no header at all,
so every arm that reaches the journey through it fails on 401 before it can assert anything about
member-side quests.  This script changes exactly that call and reports the red count before and after so
the repair cannot be claimed without the pair of readings.
"""
import io
import re
import subprocess
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/backend/tests/test_r64_member_side_quest.py"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TARGET = '    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200'
REPLACEMENT = "\n".join([
    "    # /start is a write door like the select above it, so it has to sign as the same demo traveller.",
    "    # The 401 measured here came from the fixture dropping the header, not from the product refusing",
    "    # a member -- see the before/after counts printed by trial/human_walk/_fix_r64_start_header_r148.py.",
    '    assert client.post(',
    '        f"/api/v1/journeys/{journey_id}/start",',
    '        headers=_auth(str(reset.json()["traveler_id"])),',
    '    ).status_code == 200',
])


def run(label):
    done = subprocess.run([PY, "-m", "pytest", "-q", "tests/test_r64_member_side_quest.py",
                           "--tb=no", "-p", "no:warnings"],
                          cwd=r"D:/moodle/_cmdr_rescue_v3_1022/backend", capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    tail = [l for l in done.stdout.splitlines() if re.search(r"\d+ (failed|passed)", l)]
    print(label, tail[-1] if tail else "NO_SUMMARY rc=%d" % done.returncode)
    return tail[-1] if tail else ""


text = io.open(PATH, encoding="utf-8", newline="").read()
if text.count(TARGET) != 1:
    sys.exit("ABORT target line hits=%d" % text.count(TARGET))
before = run("BEFORE")
io.open(PATH, "w", encoding="utf-8", newline="").write(text.replace(TARGET, REPLACEMENT, 1))
after = run("AFTER")
back = io.open(PATH, encoding="utf-8").read()
print("LANDED", 'headers=_auth(str(reset.json()["traveler_id"]))' in back and TARGET not in back)
print("PAIR before=[%s] after=[%s]" % (before, after))
