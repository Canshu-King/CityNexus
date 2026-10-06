"""Build audit_closure_coordinates_r4.py from r3 by appending the coordinates cited since 05:4x."""
import ast
import hashlib
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "audit_closure_coordinates_r3.py"
DST = "audit_closure_coordinates_r4.py"
INSTR = "receipt_consistency_o0276_r1.py"


def blob_of(path):
    data = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), len(data)


instr_sha, instr_bytes = blob_of(INSTR)

NEW = (
    ("live_checks/dist_hardlink_scan.py", "ec3a3814bfb794e423e8fe27efe8b0671722de94", 9958,
     "hardlink scanner (named the white-page mechanism)"),
    ("evidence/commander-dist-hardlink-scan/scan_r1.json", "1ee0d991ff832b53734f67c5836b3c9bf28cf283", 11065,
     "real scan: 38 files / 35 hits / rc=3"),
    ("evidence/commander-dist-hardlink-scan/selftest_r1.txt", "37c2df0917c81cca4ea0f401d1b35cd33febb2b1", 497,
     "scanner selftest 5/5 (r1 was 3/5 on fixture bugs)"),
    ("live_checks/receipt_consistency_o0276_r1.py", instr_sha, instr_bytes, "ORD-0276 recomputation ruler"),
    ("evidence/ord0276-hjp3-cells/O0276-2505_readings.json", "3ec966e90bc14f20955ef3d10936a9ce5ca17f6b", 10906,
     "lane HJ-P3 ORD-0276 readings"),
    ("evidence/ord0276-hjp3-cells/RECEIPT_O0276-2505.md", "20ab8b3b231d10a9fabc6a2876343d8bf6f9ce85", 5718,
     "lane HJ-P3 ORD-0276 receipt"),
    ("evidence/ord0276-hjp3-cells/o0276_rig.py", "adadc49eda18c4bb9a3dae038daea4f0763f8b5f", 12808,
     "lane HJ-P3 ORD-0276 rig"),
    ("evidence/ord0276-hjp3-cells/o0276_face.py", "535853a65840e13ca7b544231ce25ea32a428d67", 2984,
     "lane HJ-P3 ORD-0276 face"),
    ("evidence/ord0276-hjp3-cells/shots_O0276-legacy-surface-clean-port.png", "512ff616c1256113dd7c9d4327554109d213516b", 18210,
     "lane HJ-P3 ORD-0276 shot (legacy surface)"),
    ("evidence/ord0276-hjp3-cells/shots_O0276-v8-surface-clean-port.png", "23f1ad6723b9b00ba6ceaa74cbad52e50635959f", 69332,
     "lane HJ-P3 ORD-0276 shot (v8 surface)"),
)

src = io.open(SRC, encoding="utf-8", newline="").read()
marker = '    ("evidence/ord0269-0273-gate-v7-45b0a5e/manifest-5b549be.json", "e2bca6c975a95dcf6972463851ddcc11bda31d0c", 2997, "lane D manifest"),\n'
assert src.count(marker) == 1, "anchor count %d" % src.count(marker)
add = "".join(f'    ("{p}", "{b}", {s}, "{w}"),\n' for p, b, s, w in NEW)
out = src.replace(marker, marker + add, 1)
assert out != src
io.open(DST, "w", encoding="utf-8", newline="").write(out)
ast.parse(out)
old = src.splitlines()
added = [l for l in out.splitlines() if l not in old]
removed = [l for l in old if l not in out.splitlines()]
print("checker blob", instr_sha, instr_bytes, "B")
print("wrote", DST, len(out.encode("utf-8")), "B; added", len(added), "removed", len(removed))
assert len(added) == len(NEW) and not removed
ns = {}
exec(compile(out.split("def main()")[0], "r4-head", "exec"), ns)
print("claims in r4:", len(ns["CLAIMS"]))
