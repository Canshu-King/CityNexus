# -*- coding: utf-8 -*-
"""Cell 6 sweep: for every gateway handler, is its refusal reachable?

Cell 5 found a fake gate in my own tool -- a DENY branch that could never fire because the action it guarded
resolves ALLOW_AUTO in every mode. This asks the same question of every handler, and answers it by running the
policy, not by reading it: for each handler, which AgentAction it evaluates, and the decision that action gets
in each product mode with the tightest envelope. A handler whose only refusal is an unreachable policy DENY is
the same shape. Read-only; it decides nothing, it prints a table and writes a receipt.
"""

import io
import os
import re
import subprocess

REPO = r"D:/moodle/_qoder_exec_r1"
GATEWAY = os.path.join(REPO, "backend", "app", "agent", "gateway.py")
OUT = os.path.join(REPO, "review", "ord", "mainexec_path_r2", "handler_refusal_reachability_r2.txt")
PYEXE = "D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"

src = io.open(GATEWAY, encoding="utf-8").read()
lines = src.split("\n")

# handler name -> the AgentAction it evaluates (first evaluate_action call in its body)
handlers = ["inspect_journey", "inspect_twin", "list_replans", "search_city_services", "request_replan",
            "accept_replan", "replace_activity", "reschedule_activity", "create_booking",
            "cancel_refundable_booking", "request_commitment_change", "report_disruption"]

def body_of(name):
    start = None
    for i, l in enumerate(lines):
        if re.match(r"\s*def %s\(" % name, l):
            start = i
            break
    if start is None:
        return ""
    out = []
    for l in lines[start + 1:]:
        # stop only at the next METHOD-level def (4-space indent); nested defs (e.g. `def execute()` inside
        # a handler) are part of the handler body and must not end the scan.
        if re.match(r"    def ", l):
            break
        out.append(l)
    return "\n".join(out)

rows = []
for h in handlers:
    b = body_of(h)
    # two forms: evaluate_action(..., AgentAction.X) directly, or the typed path passing
    # `action=AgentAction.X` to the shared _run_typed_mutation (which evaluates it at line 972).
    acts = re.findall(r"evaluate_action\([^,]+,\s*AgentAction\.([A-Z_]+)", b)
    if not acts:
        acts = re.findall(r"action=AgentAction\.([A-Z_]+)", b)
    denys = len(re.findall(r"AuthorizationDecision\.DENY", b))
    raises = re.findall(r"raise HTTPException\((\d+)", b)
    rows.append({
        "handler": h,
        "action": acts[0] if acts else "(none)",
        "deny_branches": denys,
        "raise_codes": sorted(set(raises)),
    })

# ask the policy what each action resolves to in every mode, with the tightest envelope
code = (
    "import sys;sys.path.insert(0,'.');"
    "from app.agent.delegation_policy import evaluate_action, DelegationPolicy;"
    "from app.agent.contracts import AgentAction, AuthoritativeActionFacts, AgentMode;"
    "acts=['INSPECT_JOURNEY','INSPECT_TWIN','LIST_REPLANS','SEARCH_CITY_SERVICES','REQUEST_REPLAN',"
    "'ACCEPT_REPLAN','REPLACE_ACTIVITY','RESCHEDULE_ACTIVITY','CREATE_BOOKING','CANCEL_REFUNDABLE_BOOKING',"
    "'REQUEST_COMMITMENT_CHANGE','REPORT_DISRUPTION'];"
    "pol=[DelegationPolicy(mode=m,auto_accept_replan=False,max_auto_replan_cost_delta_minor=0,"
    "max_auto_loss_minor=0,max_auto_schedule_drift_min=0,allowed_activity_types=(),allowed_booking_types=(),"
    "protected_commitment_levels=('C3_Guaranteed','C4_Anchored'),version=1) for m in AgentMode];"
    "facts=AuthoritativeActionFacts();"
    "print('action|'+'|'.join(m.value for m in AgentMode));"
    "[print(a+'|'+'|'.join(evaluate_action(p,AgentAction(a),facts).decision.value for p in pol)) for a in acts]"
)
env = dict(os.environ)
for gone in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY"):
    env.pop(gone, None)
proc = subprocess.run([PYEXE, "-c", code], cwd=os.path.join(REPO, "backend"),
                      capture_output=True, env=env)
policy_out = proc.stdout.decode("utf-8", "replace").strip()
policy = {}
for line in policy_out.split("\n")[1:]:
    parts = line.split("|")
    if len(parts) == 4:
        policy[parts[0]] = parts[1:]

L = ["Cell 6: for each gateway handler, can its refusal fire? Policy decisions read by running the policy",
     "with the tightest envelope (auto-accept off, zero cost/loss/drift, no allowed types), plus the refusal",
     "branches found in the handler body.", "",
     "action -> decision in each mode:"]
for line in policy_out.split("\n"):
    L.append("   " + line)
L.append("")
L.append("%-28s %-26s %-14s %s" % ("handler", "policy action", "deny-branches", "other refusals (http codes)"))
for r in rows:
    L.append("%-28s %-26s %-14d %s" % (r["handler"], r["action"], r["deny_branches"], r["raise_codes"] or "none"))
L.append("")
L.append("Read: a handler is the fake-gate shape only if its refusal is an unreachable policy DENY. Handlers")
L.append("whose action resolves ALLOW_AUTO in every mode (REQUEST_REPLAN, REPORT_DISRUPTION) cannot be refused")
L.append("by policy; if such a handler also has no other refusal, its only 'gate' is the allowlist. The typed")
L.append("mutation actions (ACCEPT_REPLAN onward) resolve REQUIRE_* / DENY under the tight envelope, so their")
L.append("refusals are reachable.")
text = "\n".join(L) + "\n"
io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
print(text)