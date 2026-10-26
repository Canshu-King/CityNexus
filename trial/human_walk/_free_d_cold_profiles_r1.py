import pathlib
import shutil
import sys

SRC_ROOT = pathlib.Path(r"D:/moodle/_cmdr_v3_live_1022")
DST_ROOT = pathlib.Path(r"E:/_cmdr_cold_1027")
NAMES = [
    "_chrome_gozero_map49",
    "_chrome_gozero_map51",
    "_chrome_gozero_r48",
    "_chrome_gozero_r49",
    "_chrome_gozero_r50",
]


def tree_bytes(path: pathlib.Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def free_bytes(path: str) -> int:
    usage = shutil.disk_usage(path)
    return usage.free


report = []
DST_ROOT.mkdir(parents=True, exist_ok=True)
for name in NAMES:
    src = SRC_ROOT / name
    dst = DST_ROOT / name
    if not src.is_dir():
        report.append(f"{name} MISSING-SKIP")
        continue
    if dst.exists():
        report.append(f"{name} DEST-EXISTS-ABORT")
        continue
    src_bytes = tree_bytes(src)
    if free_bytes(str(DST_ROOT)) < src_bytes + 200 * 1024 * 1024:
        report.append("E-FREE-TOO-LOW-ABORT " + str(free_bytes(str(DST_ROOT))))
        break
    try:
        shutil.copytree(src, dst, symlinks=False)
    except OSError as error:
        report.append(f"{name} COPY-FAIL {type(error).__name__} {str(error)[:90]}")
        continue
    dst_bytes = tree_bytes(dst)
    if dst_bytes != src_bytes:
        report.append(f"{name} MISMATCH src={src_bytes} dst={dst_bytes} KEPT-BOTH")
        continue
    shutil.rmtree(src)
    gone = not src.exists()
    report.append(f"{name} MOVED bytes={src_bytes} src_gone={gone} dst={dst_bytes}")

report.append(f"D_FREE {free_bytes('D:')/1024/1024:.0f} MB  E_FREE {free_bytes('E:')/1024/1024:.0f} MB")
sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(report))
