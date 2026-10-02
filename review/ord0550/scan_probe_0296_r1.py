import io, json, re
from pathlib import Path
BACKEND = Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0550cut_00b5f25e/backend")
NEEDLES = ("busy_timeout=30000", "busy_timeout = 30000", '"timeout": 30')
offenders, others = {}, {}
for path in sorted((BACKEND / "app").rglob("*.py")):
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if any(n in line for n in NEEDLES):
            offenders.setdefault(str(path.relative_to(BACKEND)), []).append(i)
        elif "busy_timeout" in line:
            others.setdefault(str(path.relative_to(BACKEND)), []).append([i, line.strip()[:120]])
io.open(r"D:/moodle/_qoder_b_ord0417_20260928/run/probe_0296_r1.json","w",encoding="utf-8",newline="\n").write(
    json.dumps({"offenders": offenders, "others": others}, ensure_ascii=False, indent=1))
print("ok")
