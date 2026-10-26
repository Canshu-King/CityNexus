import pathlib
import subprocess

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022")
REL = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"

head = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{REL}"], capture_output=True, check=True).stdout
frag = (ROOT / "trial/results/_s47_restore.md").read_text(encoding="utf-8")
frag_bytes = frag.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")

prefix = head
if not prefix.endswith(b"\n"):
    prefix += b"\r\n"
new = prefix + frag_bytes
(ROOT / "trial" / "results" / "20261026_GO_FROM_BLANK_REPORT.md").write_bytes(new)
(ROOT / "trial/results/_s47_restore.md").unlink()

print("HEAD_BYTES", len(head), "NEW_BYTES", len(new), "FRAG_CRLF_LINES", frag_bytes.count(b"\r\n"))
diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--numstat", "--", REL], capture_output=True, text=True).stdout.strip()
print("NUMSTAT", diff or "(none)")
body = (ROOT / "trial" / "results" / "20261026_GO_FROM_BLANK_REPORT.md").read_bytes()
print("LF_ONLY_LINES", sum(1 for line in body.split(b"\r\n") if b"\n" in line))
print("HAS_47", b"## 47." in body, "HAS_46", b"## 46." in body, "HAS_1", b"## 1." in body)
