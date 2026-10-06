# -*- coding: utf-8 -*-
"""Caller replica for ORD-0574 r2 testing: import check_sync from an isolated tree and PROPAGATE its exit code.

Why this file exists: the shipped CLI exposes --local/--reads but not --ref/--path, so the both-empty fixture
cannot be reached through `python tools/...r2.py` alone. This runner is MY OWN file (not a published tool);
it does what the docstring tells a caller to do, so the number measured here is a real process exit code
rather than a field I read out of a dict.

usage: python ord0574_r2_caller_r3.py <module-root> <module-name> <local-path> <ref> <path>
"""
import importlib
import json
import os
import sys

root, module_name, local, ref, path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
sys.path.insert(0, root)
m = importlib.import_module("tools." + module_name)
token_file = os.environ.get("CITYNEXUS_API_TOKEN_FILE") or ""
try:
    st = m.check_sync(local_path=local, ref=ref, path=path,
                      repo_dir=r"D:\moodle\CityNexus", token_file=token_file, reads=1)
except m.IncompleteRemoteRead as e:
    sys.stderr.write("incomplete remote read leg=%s\n" % e.leg)
    raise SystemExit(9)
print(json.dumps({"verdict": st["verdict"], "exit_code": st["exit_code"],
                  "local_blob": st["local_blob"], "remote_blob": st["remote_blob"],
                  "local_bytes": st["local_bytes"], "remote_bytes": st["remote_bytes"],
                  "points": [st["points_matched"], st["points_compared"]],
                  "emptiness_floor": st.get("emptiness_floor", "field_absent")}, ensure_ascii=False))
raise SystemExit(st["exit_code"])
