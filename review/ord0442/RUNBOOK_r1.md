# ORD-0442 runbook r1 - how the twelve named reds were reproduced, armed and attributed

Lane N3 (session `49fe0d7b`), 2026-09-29 04:2x-05:0x (+08). Everything below ran on **lane-private
exports** of the pinned tip and a lane-private pytest database (`backend/tests/conftest.py` puts the
suite on its own temp `suite.db` and refuses a real target). Nothing touched ports 8000/4781/4782/8693,
no shared preview database was written, and no `demo/reset` was run outside that private test file -
`/api/v1/demo/reset` was called only inside the private suite DB, which is how these doors are written.

Interpreters: only `D:/moodle/CityNexus/.venv/Scripts/python.exe` (3.12.14) runs this suite.

## 0. The tip

    git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1

Order pinned `8d038b21f09477b933cff3b1c7b09845c542373b`; the arm was also re-run at the present tip
`123fabb637fefe9e1be442b67f2da4be7e95ac74` (2 commits ahead: ORD-0383 格三, which rewrites
`backend/app/main.py` + two undelete test files) to check the attribution did not drift.

## 1. Exports (the named recipe manufactures three of the twelve reds)

    # named recipe, as pinned in the order
    git archive <tip> backend data contracts tools scripts agent-mcp frontend/src frontend/e2e | tar -xf - -C D:/moodle/_qoder_n3_ord0442_snap
    # complete tree, same tip - the extra paths are what three doors read
    git archive <tip> | tar -xf - -C D:/moodle/_qoder_n3_ord0442_full

`git ls-tree -r -l` of the tip: 7,827 tracked files, 113,258,914 B. The tip's own tree contains
`review/`, `qoder-handoff/` and `PACKAGE-MANIFEST.json`, all three of which the named recipe drops.

## 2. The twelve nodeids

Taken from the commander's published log (`git cat-file blob 2fbed5eba27abcafa9d8e91995cf1c7827fa1267`,
33,714 B) by `review/ord0442/extract_reds_r1.py`, which normalises `os.sep` to forward slashes:
`review/n3_0442_evidence_r1/twelve_r1.txt`. Collection first, per the standing rule:
`1436 tests collected in 25.49s` (`collect_r1.txt`), which adds up to the log's
`12 failed, 1408 passed, 15 skipped, 1 xfailed`.

    PYTHONPATH=<export-root> <venv>/Scripts/python.exe -X utf8 -m pytest <the twelve> --tb=short -q
    -> twelve_run_before_r1.txt      12 failed, 4 warnings in 16.96s   (named recipe)
    -> twelve_run_fulltree_r1.txt     9 failed, 3 passed in 14.60s     (complete tree, pinned tip)
    -> twelve_run_present_tip_r1.txt  9 failed, 3 passed in 17.52s     (complete tree, present tip)

## 3. Attribution arms

    # probes r1: matrix shape, hydration egress, agent-run payload, failure-reason mapping,
    #             lock-wait copies, and a socket guard over the two lines g8a flags
    cp review/ord0442/test_ord0442_attribution_probe_r1.py <tree>/backend/tests/
    ORD0442_PROBE_OUT=<lane>/review/n3_0442_evidence_r1/attribution_probe_r1.json \
    PYTHONPATH=<tree> <venv>/Scripts/python.exe -X utf8 -m pytest backend/tests/test_ord0442_attribution_probe_r1.py -q

    # probes r2: the same two doors with the opt-in provider leg authorised (CITYNEXUS_ANYWHERE_RESOLVER=photon)
    # probes r4: SQLite's own lock view during each provider call, with write/read/idle control arms
    # r3: g3_child_repro_r3.py - spawns the real uvicorn child twice (dead proxy exported / removed)

Proxy note, measured rather than assumed: this box exports `HTTP(S)_PROXY=http://127.0.0.1:7892` with
`NO_PROXY=localhost,127.0.0.1,::1`, and both g3 arms still reached the child - so g3's refused
connection is not the proxy. The provider legs were run with the proxy variables removed (`env -u`).

## 4. What was deliberately NOT touched

No test assertion, no fixture, no export script inside the tree, and no product file was edited this
round: the order forbids reaching outside production code to turn a red green, and the single door
whose complaint is real (g5) needs a cross-lane contract change named in the draft annex.
`review/ord0442/twelve_verdicts_r1.py` recomputes the table from these artifacts; if a number is not
in an artifact, it is not in the table.
