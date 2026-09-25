"""ORD-0288 T-1: persist the round-1 teardown readings that my own re-render overwrote.

What happened: the first shipping pass closed three listeners and wrote per-pid three-way proofs into
`teardown_O0288T1.json`; a later re-render ran the same block with nothing left to close and replaced
that file with an empty round. The numbers were not lost from the session, only from disk, so this file
puts them back under a NEW name and labels exactly where they came from.

Provenance, stated plainly: these are transcriptions of command output I captured earlier in this same
session (a netstat/CIM listing taken BEFORE the first teardown, and the teardown block's own printed
summary). They are NOT the original json artefact, and the restored text cannot prove anything the
original file could not already prove.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
OUT = 'teardown_O0288T1_round1_restored_from_console.txt'

PRE_KILL_SNAPSHOT = """PID 51292 ppid=30056 created=2026-09-25T16:24:40.6891460+08:00
   cmd: "C:\\Users\\...\\uv\\python\\cpython-3.12.14-windows-x86_64-none\\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8611 --log-level info
PID 48680 ppid=44668 created=2026-09-25T16:24:35.5890130+08:00
   cmd: "C:\\Users\\...\\uv\\python\\cpython-3.12.14-windows-x86_64-none\\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8612 --log-level info
PID 6824 ppid=45616 created=2026-09-25T16:32:07.0172940+08:00
   cmd: "C:\\Users\\...\\uv\\python\\cpython-3.12.14-windows-x86_64-none\\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8613 --log-level info
PID 30056 ppid=40780 created=2026-09-25T16:24:40.6790340+08:00
   cmd: D:/moodle/CityNexus/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8611 --log-level info
PID 44668 ppid=12200 created=2026-09-25T16:24:35.5772020+08:00
   cmd: D:/moodle/CityNexus/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8612 --log-level info
8613 ancestry walk: level 0 pid 6824 ppid 45616 (uv python, -m uvicorn ... --port 8613)
                     level 1 pid 45616 ppid 46740 (D:/moodle/CityNexus/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 86..)
                     level 2 pid 46740 -> gone (that was the arms runner of this batch)
8614: no listener at the time of the snapshot (mut_sig and mut_sig_wrong share that port and had exited)
"""

ROUND1_SUMMARY = ('proven-mine verdicts: {"8611": [{"pid": 51292, "proven": true, "two_sided": true, '
                  '"killed": 0}], "8612": [{"pid": 48680, "proven": true, "two_sided": true, '
                  '"killed": 0}], "8613": [{"pid": 6824, "proven": true, "two_sided": true, '
                  '"killed": 0}]}\n'
                  'teardown all free: True | listeners now: {"8611": [], "8612": [], "8613": [], '
                  '"8614": []}\n')

later = sorted(p.name for p in B.glob('teardown_O0288T1_*.json'))
body = (
    "ORD-0288 T-1 · the round that actually closed listeners, restored from captured console output\n"
    "================================================================================================\n"
    "written at " + time.strftime('%Y-%m-%dT%H:%M:%S%z') + " by o0288_teardown_recover.py\n"
    "why this file exists: the first teardown round wrote `teardown_O0288T1.json`; a later re-render of\n"
    "the same block found nothing left to close and overwrote that name with an empty round. The empty\n"
    "round is kept, renamed, on disk as " + json.dumps(later, ensure_ascii=False) + ".\n"
    "what these lines are: transcriptions of command output captured earlier in this session - the\n"
    "netstat/CIM snapshot taken BEFORE the first teardown, and that teardown's own printed summary.\n"
    "what they are NOT: the original json artefact, and not new measurements.\n\n"
    "-- listeners and processes, snapshot before the first teardown (netstat -ano + Win32_Process) --\n"
    + PRE_KILL_SNAPSHOT + "\n"
    "-- the first teardown round's own output line (three-way proof per listener, then taskkill rc) --\n"
    + ROUND1_SUMMARY + "\n"
    "how to read `two_sided`: GET /api/v1/journeys/<my id> answered 200 and echoed the id, and\n"
    "GET /api/v1/journeys/00000000-0000-0000-0000-000000000000 answered 404 - which together tie that\n"
    "listener to my private sqlite file. `killed: 0` is the taskkill exit code, not a count.\n"
    "the ports in my named list were [8611, 8612, 8613, 8614]; 4781/4782 (the user's chain) are not on\n"
    "it and nothing in this batch touched them.\n")
(B / OUT).write_text(body, encoding='utf-8', newline='\n')
print('wrote', OUT, len(body.encode('utf-8')), 'B')
print('sha256', hashlib.sha256((B / OUT).read_bytes()).hexdigest())
print('empty rounds still on disk:', json.dumps(later, ensure_ascii=False))
