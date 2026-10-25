"""Every evidence file the demo docs point at must exist on disk before class."""
import pathlib
import re

ROOT = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022")
EVIDENCE = ROOT / "trial/results/20261022_v3_human_chrome"
DOCS = [
    ROOT / "trial/results/20261025_CLASSROOM_DEMO_RUNBOOK.md",
    ROOT / "trial/results/20261025_HANDOFF.md",
]
WITH_PATH = re.compile(r"(trial/results/[A-Za-z0-9_./-]+\.(?:png|txt))")
BARE_NAME = re.compile(r"`([A-Za-z0-9_.-]+\.(?:png|txt))`")

missing = []
seen = set()
for doc in DOCS:
    text = doc.read_text(encoding="utf-8")
    refs = [(match.group(1), ROOT) for match in WITH_PATH.finditer(text)]
    refs += [(match.group(1), EVIDENCE) for match in BARE_NAME.finditer(text) if "/" not in match.group(1)]
    for ref, base in refs:
        if ref in seen:
            continue
        seen.add(ref)
        if not (base / ref).exists():
            missing.append((doc.name, ref))

print(f"docs={len(DOCS)} refs={len(seen)} missing={len(missing)}")
for doc_name, ref in missing:
    print(f"MISSING {doc_name} -> {ref}")
