"""Second-observer reading for F's ORD-0307 claim that the live credential is in the ENVIRONMENT, not the tree.

Masks before anything else and never prints a value: the only things emitted are presence, character
length and a fingerprint prefix.  F reported `present=1, un-declared=1, DEEPSEEK_API_KEY length 35,
fp 4cabe6bcaff4`; this either reproduces it or says where it differs.
"""
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NAME = "DEEPSEEK_API_KEY"
raw_val = os.environ.get(NAME)
in_process_present = raw_val is not None and raw_val != ""
in_process_len = len(raw_val) if raw_val else 0
in_process_fp = hashlib.sha256(raw_val.encode("utf-8")).hexdigest()[:12] if raw_val else None

# the Windows registry copy is another place a value can live without being in my process env
reg = os.popen("reg query HKCU\\Environment /v " + NAME + " 2>nul").read()
registry_present = bool(re.search(NAME + r"\s+REG_", reg))

out = {
    "schema": "CNX_CMDR_CRED_ENV_SECOND_OBSERVER_V1", "name": NAME,
    "process_env_present": in_process_present, "process_env_char_len": in_process_len,
    "process_env_fp12": in_process_fp,
    "registry_hkcu_environment_present": registry_present,
    "value_printed": False,
    "note": "presence, length and a 12-hex fingerprint only; no byte of the value was written to this file, "
            "to stdout, or to any evidence path",
    "against_fs_reading": {"she_reported": {"present": 1, "len": 35, "fp": "4cabe6bcaff4"},
                           "agree_on_presence": in_process_present,
                           "agree_on_length": in_process_len == 35,
                           "agree_on_fingerprint": in_process_fp == "4cabe6bcaff4"}}
io.open("_cmdr_cred_env_second_observer.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out["against_fs_reading"], ensure_ascii=False))
print("process_env_present", in_process_present, "| registry_present", registry_present,
      "| len", in_process_len, "| fp12", in_process_fp)
