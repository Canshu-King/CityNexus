# -*- coding: utf-8 -*-
"""Build ORD-0574 fix candidates: sync_check_r2 (empty-both-sides must not answer CURRENT) and hook_r2.

Source of truth = the two published blobs (verified byte-equal to the local copies before touching anything).
Each edit is an exact-text replacement that must be found EXACTLY ONCE; anything else is an ABORT,
so a silently-missed edit cannot produce a "fixed" file that is not fixed.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
MAIN = r"D:\moodle\CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_CHECK = os.path.join(WT, "tools", "cnx_ledger_mirror_sync_check_r1.py")
SRC_HOOK = os.path.join(WT, "tools", "cnx_ledger_mirror_sync_hook_r1.py")
OUT_CHECK = os.path.join(HERE, "cnx_ledger_mirror_sync_check_r2.py")
OUT_HOOK = os.path.join(HERE, "cnx_ledger_mirror_sync_hook_r2.py")
PUBLISHED_CHECK = "5d0ca99076de5c11e9906acadc9c03ed1a3b8e6e"
PUBLISHED_HOOK = "18f51ebc995a1a496a5b6b5d7947d73f9ba818d3"
EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def git_blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def read_source(path, expected_blob, label):
    raw = io.open(path, "rb").read()
    got = git_blob(raw)
    if got != expected_blob:
        raise SystemExit("ABORT: %s local copy is blob %s, not the published %s - refusing to fork from a "
                         "file that is not the one on the line" % (label, got, expected_blob))
    text = raw.decode("utf-8")
    if "\r\n" in text:
        raise SystemExit("ABORT: %s carries CRLF - the published blob does not, the write would flip endings"
                         % label)
    return text


def apply(text, edits, label):
    for find, repl in edits:
        n = text.count(find)
        if n != 1:
            raise SystemExit("ABORT: anchor found %d times in %s (need exactly 1): %.70s"
                             % (n, label, find))
        text = text.replace(find, repl)
    return text


def main():
    R = {}
    check_src = read_source(SRC_CHECK, PUBLISHED_CHECK, "sync_check_r1")
    hook_src = read_source(SRC_HOOK, PUBLISHED_HOOK, "sync_hook_r1")

    c_edits = [
        # 1. the vocabulary grows one state
        ('CURRENT, LAGGING, DIVERGED = "CURRENT", "LAGGING", "DIVERGED"\nVERDICT_CODES = {CURRENT: 0, LAGGING: 7, DIVERGED: 8}',
         'CURRENT, LAGGING, DIVERGED, NOT_ANSWERED = "CURRENT", "LAGGING", "DIVERGED", "NOT_ANSWERED"\n'
         'VERDICT_CODES = {CURRENT: 0, LAGGING: 7, DIVERGED: 8, NOT_ANSWERED: 9}\n'
         '# the blob every absent/empty file carries; used to refuse the "both sides have no content" case\n'
         'EMPTY_BLOB = "%s"' % EMPTY_BLOB),
        # 2. the floor itself, right after the two blob lists are built
        ('    local_blobs = [s["blob"] for s in snaps]\n'
         '    remote_blobs = [r["blob_id"] for r in remotes]\n',
         '    local_blobs = [s["blob"] for s in snaps]\n'
         '    remote_blobs = [r["blob_id"] for r in remotes]\n'
         '    # ORD-0574: two empty bodies are equal, but "equal" is not an answer to "is the mirror current" -\n'
         '    # an empty ledger, a wrong path and a truncated read all collapse to the same blob, so saying\n'
         '    # CURRENT here is a false green. Measured real: the r1 tool answered CURRENT with exit 0 on a\n'
         '    # zero-byte file on both sides (ord0574_l1_rerun_r2.json). One-sided emptiness still goes red.\n'
         '    emptiness_floor = bool(local_blobs) and bool(remote_blobs) and all(\n'
         '        b == EMPTY_BLOB for b in local_blobs + remote_blobs)\n'),
        # 3. the decision chain takes the floor first
        ('    if len(matched) == len(pairs) and len(set(local_blobs) | set(remote_blobs)) == 1:\n'
         '        verdict = CURRENT\n',
         '    if emptiness_floor:\n'
         '        verdict = NOT_ANSWERED\n'
         '    elif len(matched) == len(pairs) and len(set(local_blobs) | set(remote_blobs)) == 1:\n'
         '        verdict = CURRENT\n'),
        # 4. report it, so the caller can tell the floor from a real comparison
        ('            "arm": arm or "none", "local_changed_under_the_run": len(set(local_blobs)) > 1}',
         '            "arm": arm or "none", "local_changed_under_the_run": len(set(local_blobs)) > 1,\n'
         '            "emptiness_floor": emptiness_floor,\n'
         '            "both_sides_empty": emptiness_floor, "empty_blob": EMPTY_BLOB}'),
        # 5. the documented exit code 9 has to actually come out of the CLI
        ('if __name__ == "__main__":\n    raise SystemExit(main())',
         'if __name__ == "__main__":\n'
         '    try:\n'
         '        raise SystemExit(main())\n'
         '    except IncompleteRemoteRead as e:\n'
         '        # promised in this file\'s own docstring ("9 the reader refused"): measured rc was 1 in r1,\n'
         '        # because the exception escaped main() instead of being turned into the documented code.\n'
         '        sys.stderr.write("incomplete remote read leg=%s detail=%s\\n" % (e.leg, str(e)[:200]))\n'
         '        raise SystemExit(9)'),
        # 6. the docstring promises what the code now does
        ('Exit codes, so a caller does not have to parse prose: 0 CURRENT, 7 LAGGING, 8 DIVERGED, 9 the reader refused\n'
         '(it raises with the leg that failed rather than returning partial bytes).',
         'Exit codes, so a caller does not have to parse prose: 0 CURRENT, 7 LAGGING, 8 DIVERGED,\n'
         '9 the reader refused (it raises with the leg that failed rather than returning partial bytes) and\n'
         '9 NOT_ANSWERED (ORD-0574: both sides carry no content - emptiness is equality, not currency).\n'
         'NOT_ANSWERED is also returned as a verdict string, so an importer that only checks\n'
         'verdict != "CURRENT" keeps working.'),
    ]
    check_new = apply(check_src, c_edits, "sync_check_r2")

    h_edits = [
        ('from tools.cnx_ledger_mirror_sync_check_r1 import check_sync  # noqa: E402',
         'from tools.cnx_ledger_mirror_sync_check_r2 import check_sync  # noqa: E402'),
        ('HOOK = "cnx_ledger_mirror_sync_hook_r1"', 'HOOK = "cnx_ledger_mirror_sync_hook_r2"'),
        ('TOOL = "cnx_ledger_mirror_sync_check_r1"', 'TOOL = "cnx_ledger_mirror_sync_check_r2"'),
        ('It delegates the measurement to the tool that already landed (`cnx_ledger_mirror_sync_check_r1`), which in turn',
         'It delegates the measurement to the empty-floor revision of the standing tool\n'
         '(`cnx_ledger_mirror_sync_check_r2`, ORD-0574: a both-sides-empty comparison is NOT_ANSWERED, not\n'
         'CURRENT), which in turn'),
        ('Exit codes: 0 CURRENT / 7 LAGGING / 8 DIVERGED / 9 the reader refused / 6 this hook\'s own guard fired.',
         'Exit codes: 0 CURRENT / 7 LAGGING / 8 DIVERGED / 9 the reader refused or the empty floor fired\n'
         '(NOT_ANSWERED) / 6 this hook\'s own guard fired.'),
        ('...alarm with st["verdict"] - CURRENT / LAGGING / DIVERGED...',
         '...alarm with st["verdict"] - CURRENT / LAGGING / DIVERGED / NOT_ANSWERED...'),
    ]
    hook_new = apply(hook_src, h_edits, "sync_hook_r2")

    cb = check_new.encode("utf-8")
    hb = hook_new.encode("utf-8")
    io.open(OUT_CHECK, "wb").write(cb)
    io.open(OUT_HOOK, "wb").write(hb)
    R["check_r2"] = {"path": OUT_CHECK.replace("\\", "/"), "bytes": len(cb), "git_blob": git_blob(cb),
                     "parent_blob": PUBLISHED_CHECK, "edits": len(c_edits)}
    R["hook_r2"] = {"path": OUT_HOOK.replace("\\", "/"), "bytes": len(hb), "git_blob": git_blob(hb),
                    "parent_blob": PUBLISHED_HOOK, "edits": len(h_edits)}

    # syntax must survive the surgery before anything runs it
    import ast
    for label, txt in (("check_r2", check_new), ("hook_r2", hook_new)):
        try:
            ast.parse(txt)
            R[label]["ast_parse"] = "ok"
        except SyntaxError as e:
            raise SystemExit("ABORT: %s does not parse: %s" % (label, e))
    # no published path is rewritten: both outputs are new names
    for p in (SRC_CHECK, SRC_HOOK):
        if not os.path.exists(p):
            raise SystemExit("ABORT: source vanished")
    R["published_files_untouched"] = {SRC_CHECK.replace("\\", "/"): PUBLISHED_CHECK,
                                      SRC_HOOK.replace("\\", "/"): PUBLISHED_HOOK}
    R["published_blobs_still_readable"] = [
        {"obj": o, "t": subprocess.run(["git", "-C", MAIN, "cat-file", "-t", o], capture_output=True)
            .stdout.decode().strip()} for o in (PUBLISHED_CHECK, PUBLISHED_HOOK)]

    io.open(os.path.join(HERE, "build_ord0574_r2.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
