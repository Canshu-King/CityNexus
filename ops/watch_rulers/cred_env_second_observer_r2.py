"""Second observer, widened: F's arm artifact names TWO live AI keys in the environment; my r1 observer
hard-checked exactly one (`cred_env_second_observer_r1.py` has a single NAME constant).  A one-name
instrument cannot confirm or refute a two-name claim, so this re-reads with F's scan shape and reports
presence / character length / sha256[:12] fingerprint for every candidate, in BOTH layers:

  layer 1  this process's environment        (what the gate's env scan sees at import time)
  layer 2  HKCU\\Environment in the registry  (the layer that survives a reboot and a new shell -
                                            only the user can change it, so the rotation scope has to
                                            be stated for this layer, not just for mine)

No value byte is printed, hashed to anything reversible, or written anywhere.  Candidates are named
by their variable name only.  Read-only: this writes one local JSON and touches no ref.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CAND_RE = re.compile(r"(?i)(api[_-]?key|token|secret|access[_-]?key)$")
AI_PREFIX = re.compile(r"(?i)^(deepseek|openai|anthropic|claude|gemini|google|groq|mistral|xai|cohere|"
                       r"qwen|dashscope|zhipu|moonshot|kimi|hf|huggingface|stability|perplexity|together)("
                       r"[_-].*)?$")
# the gate's own env list, quoted so this observer is comparable to it rather than to my memory
FS_NAMED = {"DEEPSEEK_API_KEY": (35, "4cabe6bcaff4"), "OPENAI_API_KEY": (67, "ed7e75ba651c")}


def shape(v):
    return {"present": True, "char_len": len(v), "fp12": hashlib.sha256(v.encode("utf-8")).hexdigest()[:12],
            "value_printed": False}


env = dict(os.environ)
names = sorted(k for k in env if CAND_RE.search(k) or AI_PREFIX.match(k))
# only AI-ish ones are interesting here; keep the rest as a counted, unnamed tail
ai_names = [k for k in names if AI_PREFIX.match(k) or k in FS_NAMED]
other_names = [k for k in names if k not in ai_names]

# registry layer, one query per named variable (a full `reg query` dump could echo values -> avoided)
reg_present = {}
for k in ai_names:
    try:
        p = subprocess.run(["reg", "query", r"HKCU\Environment", "/v", k],
                           capture_output=True, text=True, timeout=30)
        reg_present[k] = bool(re.search(re.escape(k) + r"\s+REG_", p.stdout or ""))
    except Exception as e:  # noqa: BLE001
        reg_present[k] = "QUERY_ERROR:" + type(e).__name__

report = {
    "schema": "CNX_CMDR_CRED_ENV_SECOND_OBSERVER_V2",
    "generated_at_local": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
    "why": "F's ORD-0307 arm artifact names two live keys; my r1 observer checked one. Widened to the "
           "same scan shape so the comparison is between two readings of one set, not two different sets.",
    "scan_shape": {"candidate_suffix_re": str(CAND_RE.pattern), "ai_prefix_re": str(AI_PREFIX.pattern)},
    "named_ai_key_env_vars": {k: shape(env[k]) for k in ai_names},
    "other_key_shaped_env_vars_count": len(other_names),
    "registry_hkcu_environment": reg_present,
    "against_f_arms_artifact": {},
    "value_printed": False,
}
for k, (ln, fp) in FS_NAMED.items():
    mine = report["named_ai_key_env_vars"].get(k)
    report["against_f_arms_artifact"][k] = {
        "f_reported": {"present": True, "char_len": ln, "fp12": fp},
        "cmdr_reads": mine if mine else {"present": False},
        "agree": bool(mine) and mine["char_len"] == ln and mine["fp12"] == fp,
    }
for k in report["named_ai_key_env_vars"]:
    if k not in FS_NAMED:
        report["against_f_arms_artifact"][k] = {"f_reported": "NOT_NAMED_IN_ARMS_ARTIFACT",
                                                "cmdr_reads": report["named_ai_key_env_vars"][k]}

io.open("_cmdr_cred_env_second_observer_v2.json", "w", encoding="utf-8").write(
    json.dumps(report, ensure_ascii=False, indent=1))

print("named AI-key-shaped env vars: %d -> %s" % (len(ai_names), ", ".join(ai_names)))
for k, v in report["named_ai_key_env_vars"].items():
    print("  %-26s len=%-4d fp12=%s registry=%s" % (k, v["char_len"], v["fp12"], reg_present.get(k)))
print("other key/token/secret-shaped env vars (unnamed here): %d" % len(other_names))
print("agreement with F's artifact:",
      json.dumps({k: v.get("agree", v.get("f_reported")) for k, v in report["against_f_arms_artifact"].items()},
                 ensure_ascii=False))
