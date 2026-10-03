"""Counter-arms for ORD-0545 slice 5: the two device-decided refusals have to be watched individually.

Slice 5 reads two sentences no backend ever emits -- `errUnnamed` (the door refused without naming a
reason) and `errNoResponse` (nothing answered at all).  A green run of those arms proves nothing until a
mutation shows each arm is watching ITS OWN sentence.  Every mutation keeps the build green on purpose:
it repoints one dictionary entry at another key that really exists, so a compile error cannot be passed
off as evidence.

  M1  FAILURE_SENTENCE's UNNAMED_REFUSAL line -> "errNoResponse".  The U arms must go red; the N arms must
      stay green -- so the U arms are comparing that one sentence, not merely "a refusal appeared".
  M2  FAILURE_SENTENCE's NO_RESPONSE_FROM_ORIGIN line -> "errUnnamed".  The mirror image: N red, U green.
  M3  the technical cell stops printing this device's measured status and prints the component's own code
      name instead.  Nothing moves in the dictionary; this one tests the exposure rule, and only the U
      arms (which really do have a status) can go red -- the offline walk has no status to replace.

Controls bracket the batch: the shipped spec must be green before the first mutation and after the last,
and the panel has to come back byte-identical after every step or the receipt says so and the run stops
claiming anything.  Mutant-generation readouts are deleted; only this receipt is published, and the
filename carries the run stamp so an earlier generation can never be overwritten.

    D:/moodle/CityNexus/.venv/Scripts/python.exe -X utf8 review/ord0545/refusal_glass2_counterarm_r1.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PANEL = FRONTEND / "src/features/poiimport/PoiImportPanel.tsx"
SPEC = FRONTEND / "e2e/qoder-ord0545s5-refusal-glass-2-r1.spec.ts"
CONFIG = "playwright.ord0545s5-refusal-glass2.config.ts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
READOUTS = ROOT / "review/ord0545/readouts"
BASE_TIP = "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
FRONTEND_PORT = 4926
BACKEND_PORT = 4921
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RECEIPT = READOUTS / ("refusal_glass2_counterarms_" + RUN_STAMP + ".json")
LOCK = DATA / "refusal_glass2_counterarm.lock"
PY = sys.executable

U_GREP = "Uzh|Wen"
N_GREP = "Nzh|Ren"

MUTATIONS = [
    ("M1_unnamed_pointed_at_another_real_key",
     '  UNNAMED_REFUSAL: "errUnnamed",',
     '  UNNAMED_REFUSAL: "errNoResponse",', U_GREP, N_GREP),
    ("M2_no_response_pointed_at_another_real_key",
     '  NO_RESPONSE_FROM_ORIGIN: "errNoResponse",',
     '  NO_RESPONSE_FROM_ORIGIN: "errUnnamed",', N_GREP, U_GREP),
    ("M3_technical_cell_paints_the_code_name",
     '<small data-testid="poi-import-error-detail">HTTP {failure.status}</small>',
     '<small data-testid="poi-import-error-detail">{failure.code}</small>', U_GREP, N_GREP),
]


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def listeners(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP"
                   and ln.split()[3].upper() == "LISTENING" and ln.split()[1].endswith(f":{port}")})


def reap_my_orphan_vite() -> dict:
    """Kill only a vite whose own command line names THIS lane's frontend port."""
    probe = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine "
             "-match 'vite\\.js.*--port " + str(FRONTEND_PORT) + "' } | ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", probe],
                         capture_output=True, text=True, errors="replace").stdout
    killed = []
    for pid in [x for x in out.split() if x.isdigit()]:
        subprocess.run(["powershell.exe", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"],
                       capture_output=True)
        killed.append(int(pid))
    return {"killed": killed, "still_listening": listeners(FRONTEND_PORT)}


def gate(label: str, grep: str, tag: str) -> dict:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_ORD0545_TAG": tag,
        "CITYNEXUS_ORD0545_BASE_TIP": BASE_TIP,
        "CITYNEXUS_ORD0545S5_PORT": str(FRONTEND_PORT),
        "CITYNEXUS_ORD0545_BACKEND_PORT": str(BACKEND_PORT),
        "DEEPSEEK_API_KEY": "",
    })
    cmd = ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG, "-g", grep]
    started = time.time()
    proc = subprocess.run(cmd, cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=420, env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    (DATA / f"counterarm_{tag}.txt").write_text(out, encoding="utf-8", newline="\n")
    num = lambda pat: (int(re.search(pat, out).group(1)) if re.search(pat, out) else 0)
    return {
        "label": label, "grep": grep, "rc": proc.returncode,
        "wall_seconds": round(time.time() - started, 1),
        "collected": num(r"Running (\d+) tests?"), "passed": num(r"(\d+) passed"), "failed": num(r"(\d+) failed"),
        "failed_test_names": sorted(set(re.findall(r"spec\.ts:\d+:\d+ › [^\n]*?› ([^\n]{4,90})", out)))[:4],
    }


def main() -> int:
    if LOCK.exists():
        holder = "".join(ch for ch in LOCK.read_text(encoding="utf-8") if ch.isdigit())
        alive = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Get-Process -Id {holder} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Id }}"],
                               capture_output=True, text=True).stdout.strip() if holder.isdigit() else ""
        if alive:
            raise SystemExit("ABORT: another instance holds the lock (live pid " + alive + ")")
        print("lock left behind by a dead pid; taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    if listeners(FRONTEND_PORT):
        print("reaping my own orphan vite:", json.dumps(reap_my_orphan_vite()), flush=True)

    original = PANEL.read_bytes()
    pristine = sha(PANEL)
    spec_sha = sha(SPEC)
    rows: dict[str, object] = {"generation": {"base_tip": BASE_TIP, "recorded_at": RUN_STAMP,
                                              "panel_sha_before": pristine, "spec_sha": spec_sha,
                                              "this_lane_ports": [FRONTEND_PORT, BACKEND_PORT]},
                               "rows": []}
    bits: list[bool] = []
    aborted = ""

    def emit() -> None:
        RECEIPT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    try:
        head = gate("control_shipped_all_four", "Uzh|Wen|Nzh|Ren", "s5cahead")
        rows["rows"].append({"row": "control_shipped_all_four", "expect": "4 collected, 4 passed", **head})
        bits.append(head["rc"] == 0 and head["collected"] == 4 and head["passed"] == 4)
        emit()
        if not bits[-1]:
            aborted = "control red before any mutation -- the batch cannot claim anything"
        for name, needle, replacement, red_grep, green_grep in MUTATIONS:
            if aborted:
                break
            text = original.decode("utf-8")
            if text.count(needle) != 1:
                rows["rows"].append({"row": name, "skipped": f"anchor appears {text.count(needle)} times"})
                bits.append(False)
                aborted = name + ": anchor moved"
                emit()
                break
            PANEL.write_text(text.replace(needle, replacement, 1), encoding="utf-8", newline="\n")
            mutated = text != PANEL.read_text(encoding="utf-8")
            red = gate(name, red_grep, "s5ca_" + name.split("_")[0].lower())
            PANEL.write_bytes(original)
            restored = sha(PANEL) == pristine
            sib = gate(name + "_sibling", green_grep, "s5ca_" + name.split("_")[0].lower() + "b")
            PANEL.write_bytes(original)
            restored = restored and sha(PANEL) == pristine
            bites = (red["rc"] != 0 and red["failed"] >= 1 and red["collected"] >= 1
                     and sib["rc"] == 0 and sib["failed"] == 0 and restored and mutated)
            bits.append(bites)
            rows["rows"].append({
                "row": name, "mutation_landed": mutated,
                "mutated_arms": {"grep": red_grep, **red},
                "sibling_arms": {"grep": green_grep, **sib},
                "panel_restored_byte_identical": restored,
                "bites": bites,
            })
            emit()
            print(name, "red rc", red["rc"], "failed", red["failed"], "| sibling rc", sib["rc"],
                  "restored", restored, flush=True)
        if not aborted:
            tail = gate("control_after_everything", "Uzh|Wen|Nzh|Ren", "s5catail")
            rows["rows"].append({"row": "control_after_everything", "expect": "4 collected, 4 passed", **tail})
            bits.append(tail["rc"] == 0 and tail["collected"] == 4 and tail["passed"] == 4)
    finally:
        PANEL.write_bytes(original)
        rows["panel_sha_after"] = sha(PANEL)
        rows["panel_untouched"] = sha(PANEL) == pristine
        rows["spec_untouched"] = sha(SPEC) == spec_sha
        for junk in list(READOUTS.glob("refusal_glass2_s5ca_*.json")) + list(READOUTS.glob("report_ord0545s5_s5ca_*.json")):
            junk.unlink()
        LOCK.unlink(missing_ok=True)
        emit()

    rows["verdict"] = ("KILL_OK three mutations bite with green siblings, controls green both ends"
                       if all(bits) and rows["panel_untouched"] and rows["spec_untouched"] and not aborted
                       else "NOT_OK " + (aborted or "a row did not bite"))
    emit()
    print(rows["verdict"], "->", RECEIPT.name, RECEIPT.stat().st_size, "B")
    return 0 if rows["verdict"].startswith("KILL_OK") else 1


if __name__ == "__main__":
    raise SystemExit(main())
