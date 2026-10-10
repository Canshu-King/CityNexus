"""Survey the tip backend for how each endpoint the 16 cells depend on answers a failure.

Read-only: the bytes come from `git show <tip>:backend/app/main.py`. For every handler I list the
`raise HTTPException(...)` sites and label the detail as prose (a sentence or an interpolated message)
or machine (an ALL_CAPS code / a variable I cannot resolve to a sentence here).
"""
import io
import json
import re
import sys

MAIN = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_sweep_scratch/backend_main.py"
HANDLERS = {
    "POST /api/v1/journeys (create)": 2713,
    "GET /api/v1/journeys/{jid}/inbox": 3632,
    "GET /api/v1/journeys/{jid}/memory": 3660,
    "POST stay-options/{oid}/select": 3145,
    "POST plans/generate": 4628,
    "POST copilot/messages": 11046,
    "POST inbox/{draft}/confirm": 3716,
    "POST inbox extract/text": 3753,
    "POST inbox extract/image": 3799,
    "POST inbox corrections": 3840,
    "POST inbox import": 4029,
}
DECOR = re.compile(r"^\s*@app\.")
RAISE = re.compile(r"raise\s+HTTPException\(([^)]*)\)", re.S)
CODEISH = re.compile(r"^\s*[A-Z][A-Z0-9_]{3,}\s*$")


def body(lines, start):
    """Handler body = from its def line to the next top-level decorator."""
    i = start
    while i < len(lines) and not lines[i].lstrip().startswith("def ") and not lines[i].lstrip().startswith("async def "):
        i += 1
    j = i + 1
    while j < len(lines) and not DECOR.match(lines[j]):
        j += 1
    return i, j


def main():
    lines = io.open(MAIN, encoding="utf-8", errors="replace").read().splitlines()
    out = {}
    for label, ln in sorted(HANDLERS.items(), key=lambda kv: kv[1]):
        a, b = body(lines, ln - 1)
        seg = "\n".join(lines[a:b])
        raises = []
        for m in RAISE.finditer(seg):
            args = " ".join(m.group(1).split())
            lineno = a + 1 + seg[:m.start()].count("\n")
            detail = ""
            dm = re.search(r"detail\s*=\s*(.+)$", args)
            if dm:
                detail = dm.group(1).strip()
            elif "," in args:
                detail = args.split(",", 1)[1].strip()
            kind = "machine_code" if CODEISH.match(detail.strip('"\'')) else (
                "prose_or_interp" if detail else "no_detail")
            raises.append({"line": lineno, "status_arg": args.split(",")[0].strip(),
                           "detail": detail[:110], "kind": kind})
        out[label] = {"handler_def_line": a + 1, "handler_span": [a + 1, b],
                      "raise_count": len(raises), "raises": raises[:12],
                      "has_untouched_500_risk": "no HTTPException in handler" if not raises else ""}
    json.dump(out, io.open(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_sweep_scratch/backend_raises.json",
                           "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    for k, v in out.items():
        kinds = {}
        for r in v["raises"]:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        print("%-34s def:%-6d raises=%-3d %s" % (k, v["handler_def_line"], v["raise_count"], json.dumps(kinds)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
