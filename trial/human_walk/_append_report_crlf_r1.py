import pathlib
import subprocess
import sys

REPORT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md")

fragment_path = pathlib.Path(sys.argv[1])
data = REPORT.read_bytes()
fragment = fragment_path.read_text(encoding="utf-8")
addition = fragment.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
if not data.endswith(b"\n"):
    data += b"\r\n"
REPORT.write_bytes(data + addition)
print("APPENDED_BYTES", len(addition), "NEW_BYTES", REPORT.stat().st_size)
numstat = subprocess.run(
    ["git", "-C", str(pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022")), "diff", "--numstat", "--",
     "trial/results/20261026_GO_FROM_BLANK_REPORT.md"],
    capture_output=True, text=True,
).stdout.strip()
print("NUMSTAT", numstat or "(none)")
