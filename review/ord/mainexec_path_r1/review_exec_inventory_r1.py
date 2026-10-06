# -*- coding: utf-8 -*-
"""Inventory every agent/copilot-initiated execution entry that writes domain truth, and whether each
goes through the main path (AgentToolGateway.dispatch).

"Execution entry" here = a place where the agent, copilot, or an autonomous run mutates a domain-truth
model (PlanVersion / Activity / Commitment / Event / JourneyMission). A product route that mutates
domain truth because the *user* asked it to is NOT an execution entry in this sense -- that is the domain
truth the main path is allowed to call. The audit question is narrower and is exactly what the building
asks: does any module execute *an agent action* on its own, or does everything funnel through the main path.

Read-only. It prints a table; it decides nothing about whether a site is a defect -- that judgment, and the
per-site reasoning, belong to the note that consumes this table.
"""

import io
import os
import re

ROOT = r"D:/moodle/_qoder_exec_r1"
BACK = os.path.join(ROOT, "backend", "app")

MODELS = ["PlanVersion", "Activity", "Commitment", "Event", "JourneyMission"]
# domain-truth writes look like session.add(Activity(...)), session.add(commitment), or
# session.add_all([...]) over the models; also catch model(...) constructed then added on the next lines.
WRITE_RE = re.compile(
    r"session\.(add|add_all|merge)\s*\(",
)
MODEL_RE = re.compile(r"\b(" + "|".join(MODELS) + r")\b")
AGENT_HINTS = re.compile(r"agent|copilot|autonom|mission|run_agent|AgentToolGateway|dispatch", re.I)
GATEWAY_RE = re.compile(r"AgentToolGateway|dispatch\(")

rows = []
for dirpath, _dirs, files in os.walk(BACK):
    for name in files:
        if not name.endswith(".py"):
            continue
        path = os.path.join(dirpath, name)
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        src = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
        # find enclosing function for each write, so the table names the entry, not just the file
        func_starts = [(i, l) for i, l in enumerate(src) if re.match(r"\s*(async\s+)?def\s+", l)]
        for i, line in enumerate(src):
            if not WRITE_RE.search(line):
                continue
            # the model may be inline in the add(...) call or on the next few lines (var = Model(...)).
            window = "\n".join(src[i:i + 6])
            m = MODEL_RE.search(window)
            if not m:
                continue
            func = None
            for fi, fl in func_starts:
                if fi <= i:
                    func = (fi, fl.strip())
                else:
                    break
            # does the enclosing function call the gateway anywhere?
            start = func[0] if func else 0
            body = "\n".join(src[start:i + 60])
            via_gateway = bool(GATEWAY_RE.search(body))
            agent_context = bool(AGENT_HINTS.search(func[1] if func else "")) or bool(AGENT_HINTS.search(body[:400]))
            rows.append({
                "file": rel, "line": i + 1, "model": m.group(1),
                "func": (func[1][:90] if func else "(module level)"),
                "via_gateway": via_gateway, "agent_context": agent_context,
                "text": line.strip()[:100],
            })

# classify
for r in rows:
    if r["via_gateway"]:
        r["bucket"] = "VIA_MAIN_PATH"
    elif r["agent_context"]:
        r["bucket"] = "AGENT_WRITE_NO_GATEWAY"   # the building's target: converges or is justified
    else:
        r["bucket"] = "PRODUCT_WRITE"            # user-driven domain truth; not an execution entry

order = {"AGENT_WRITE_NO_GATEWAY": 0, "VIA_MAIN_PATH": 1, "PRODUCT_WRITE": 2}
rows.sort(key=lambda r: (order[r["bucket"]], r["file"], r["line"]))

print("bucket counts:")
for b in order:
    print("  %-24s %d" % (b, sum(1 for r in rows if r["bucket"] == b)))
print()
print("%-24s %-58s %-30s %s" % ("file:line", "model", "enclosing function", "text"))
for r in rows:
    print("%-24s %-58s %-30s %s" % (
        (r["file"] + ":" + str(r["line"]))[-24:], r["model"], r["func"][:30], r["text"][:60]))

with io.open(os.path.join(ROOT, "review_exec_inventory_r1.tsv"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("bucket\tfile\tline\tmodel\tfunc\tvia_gateway\tagent_context\ttext\n")
    for r in rows:
        fh.write("%s\t%s\t%d\t%s\t%s\t%s\t%s\t%s\n" % (
            r["bucket"], r["file"], r["line"], r["model"], r["func"],
            int(r["via_gateway"]), int(r["agent_context"]), r["text"].replace("\t", " ")))
print()
print("wrote review_exec_inventory_r1.tsv")