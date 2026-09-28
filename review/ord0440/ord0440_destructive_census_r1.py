#!/usr/bin/env python3
"""ORD-0440 - which destructive actions does this product actually put on a traveller's screen?

The order says to hang a churn-survey sheet in front of **an action that already exists** and is
actually used ("落点选我们已经存在的高频破坏动作，不新建注销流"), so the landing spot has to be chosen
from a census, not from a preference. This script measures three things per candidate:

  1. does a product handler destroy state (DELETE verb, or an endpoint whose own code deletes rows)?
  2. is there a rendered control a traveller can tap (a `data-testid` on a button in `frontend/src`)?
  3. how many e2e gates click that control today - because a sheet that becomes a step in front of
     the action turns those gates red, and a lane may not re-earn green by editing another lane's
     test (`不许改断言凑绿` + the standing rule that another lane's red is not mine to relax).

Usage: python ord0440_destructive_census_r1.py <worktree-root> <out-json>
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else None
SRC = ROOT / "frontend" / "src"
E2E = ROOT / "frontend" / "e2e"

# Handlers that destroy state: an HTTP DELETE, or a named endpoint whose own product code deletes rows.
DESTROYING_ENDPOINTS = {
    "demo/reset": "backend/app/services.py reset_all - the whole library",
    "traveler-twin/learned": "DELETE clears learned soft evidence",
    "/abandon": "cancels an in-flight job and discards its provider work",
    "undelete": "not destroying: brings a binned trip back",
}

# A control is a candidate when its testid or its visible label names a destructive act.
DESTROY_WORDS = re.compile(
    r"reset|abandon|clear|delete|discard|purge|drop|移除|删除|清空|放弃|重置|丢弃|注销", re.IGNORECASE
)


def read(path: Path) -> str:
    return io.open(path, encoding="utf-8", errors="replace").read() if path.exists() else ""


def ts_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in (".ts", ".tsx") and "node_modules" not in path.parts:
            yield path


def main() -> int:
    # contracts/testIds.ts maps a constant name to the literal the DOM carries; resolve it, or a
    # control whose testid comes from that file looks absent to a literal-only scan (measured blind spot).
    name_to_value: dict[str, str] = {}
    for path in ts_files(SRC):
        for line in read(path).splitlines():
            m = re.match(r"\s*([A-Za-z][A-Za-z0-9]*):\s*[\"']([^\"']+)[\"'],", line)
            if m:
                name_to_value[m.group(1)] = m.group(2)

    # 1. rendered controls carrying a destructive testid
    controls: dict[str, dict] = {}
    for path in ts_files(SRC):
        text = read(path)
        for i, line in enumerate(text.splitlines(), 1):
            candidates: list[str] = []
            m = re.search(r'data-testid=[{"\']([^"\'{}$]+)[\'"]', line)
            if m:
                candidates.append(m.group(1))
            # data-testid={TEST_IDS.someName} / data-testid={someName}
            m = re.search(r"data-testid=\{(?:[A-Za-z0-9_]+\.)*([A-Za-z][A-Za-z0-9]*)\}", line)
            if m and m.group(1) in name_to_value:
                candidates.append(name_to_value[m.group(1)])
            # data-testid={`prefix-${suffix}`} - enumerate the suffix literals used in this file
            m = re.search(r"data-testid=\{`([A-Za-z0-9_-]*)\\\$\{", line)
            if m:
                prefix = m.group(1)
                for lit in re.findall(r'\bid:\s*"([a-z0-9-]+)"', text):
                    candidates.append(f"{prefix}{lit}")
            for testid in candidates:
                if not DESTROY_WORDS.search(testid):
                    continue
                entry = controls.setdefault(testid, {"testid": testid, "sites": [], "labels": []})
                site = f"{path.relative_to(ROOT).as_posix()}:{i}"
                if site not in entry["sites"]:
                    entry["sites"].append(site)
                # the same element's label is usually a few lines away; collect nearby copy
                window = text.splitlines()[max(0, i - 12): i + 12]
                for w in window:
                    for label in re.findall(r'["\']([^"\']{2,30})["\']', w):
                        if DESTROY_WORDS.search(label) and label not in entry["labels"]:
                            entry["labels"].append(label)

    # 2. which of those are clicked by e2e today
    e2e_files = sorted(E2E.rglob("*.ts")) if E2E.exists() else []
    e2e_text = {p: read(p) for p in e2e_files}
    for testid, entry in controls.items():
        clicking = []
        for p, text in e2e_text.items():
            for i, line in enumerate(text.splitlines(), 1):
                if testid in line and re.search(r"click|tap|press|getByTestId|locator", line):
                    clicking.append(f"{p.relative_to(ROOT).as_posix()}:{i}")
        entry["e2e_click_sites"] = clicking
        entry["e2e_click_count"] = len(clicking)

    # 3. destructive endpoints the front end calls at all (with or without a button)
    calls = []
    for path in ts_files(SRC):
        text = read(path)
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r'method:\s*"DELETE"', line) or any(k in line for k in DESTROYING_ENDPOINTS):
                calls.append({"site": f"{path.relative_to(ROOT).as_posix()}:{i}", "line": line.strip()[:150]})

    verdicts = []
    for testid, entry in sorted(controls.items(), key=lambda kv: (kv[1]["e2e_click_count"], kv[0])):
        verdicts.append({
            "testid": testid,
            "rendered_sites": entry["sites"],
            "nearby_copy": entry["labels"][:6],
            "e2e_click_count": entry["e2e_click_count"],
            "e2e_click_sites": entry["e2e_click_sites"][:6],
            "usable_as_a_step_without_making_another_lane_red": entry["e2e_click_count"] == 0,
        })

    result = {
        "worktree_root": str(ROOT).replace("\\", "/"),
        "destructive_controls_found": len(controls),
        "controls": controls,
        "verdicts": verdicts,
        "destroying_endpoint_call_sites": calls,
        "e2e_spec_files_scanned": len(e2e_files),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if OUT is not None:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
