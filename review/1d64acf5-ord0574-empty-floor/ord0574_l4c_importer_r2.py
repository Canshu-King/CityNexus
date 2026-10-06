# -*- coding: utf-8 -*-
"""L4c: what an *importer* (the hook) sees when the second channel refuses.

Run with CITYNEXUS_API_TOKEN_FILE cleared and token_file=None. Prints one line:
  REFUSED leg=<leg>        the reader refuses by name  (good)
  NO_REFUSAL               it returned bytes from one source (that would be the hole)
Exit code of THIS script is 0 in both cases; the interesting number is what the CLI does, measured in r2.
"""
import os
import sys

sys.path.insert(0, r"D:\moodle\_qoder_lane_S4_0926\wt0391")
os.environ.pop("CITYNEXUS_API_TOKEN_FILE", None)
from tools.cnx_ledger_mirror_sync_check_r1 import check_sync  # noqa: E402
from tools.cnx_ledger_mirror_reader_r1 import IncompleteRemoteRead  # noqa: E402

try:
    st = check_sync(local_path=r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md",
                    repo_dir=r"D:\moodle\CityNexus", token_file=None, reads=1)
    print("NO_REFUSAL verdict=" + st["verdict"])
except IncompleteRemoteRead as e:
    print("REFUSED leg=" + str(e.leg))
except Exception as e:  # any other escape is also a finding: the caller would not know it was a refusal
    print("ESCAPED_OTHER " + type(e).__name__)
