"""K8 targeted-observation setup: export F's candidate read-only, then build a mutant that removes
exactly the carrier line (the `response_json IS NULL` predicate in the Phase-B backfill seam).

Nothing here touches the authoritative line or any shared tree: the candidate comes from codeload by its
40-char sha, and the mutant is a private copy under my own directory.  Every identity claim printed here
is a recomputed git blob sha1.

  stage export : fetch + verify tree/blobs + print the seam with line numbers
  stage mutant : copy the tree, remove the guard predicate, print before/after blobs and the diff
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys
import tarfile
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_k8_0925')
SHA = '7c806fab58e872060cb5811ff96c770b40dad165'
TREE = 'CityNexus-' + SHA
EXPECTED_TREE = '04a8b56e494f53a20debfa139e8ab37c25c63352'
EXPECTED_BLOBS = {'backend/app/main.py': 'ad13f4395e', 'backend/tests/test_qoder_ord0272_continuation.py': '799fbd2fe9'}
TOKEN = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920')
GUARD = 'IdempotencyKey.response_json.is_(None)'
STAGE = sys.argv[1] if len(sys.argv) > 1 else 'export'


def blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b'blob %d\0' % len(data))
    h.update(data)
    return h.hexdigest()


def api(path):
    req = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus' + path)
    req.add_header('Authorization', 'Bearer ' + TOKEN.read_text(encoding='utf-8').strip())
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'hjp3-k8-obs')
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def do_export():
    BASE.mkdir(exist_ok=True)
    tgz = BASE / ('k8f_%s.tgz' % SHA[:7])
    if not tgz.exists():
        req = urllib.request.Request('https://codeload.github.com/Canshu-King/CityNexus/tar.gz/' + SHA)
        req.add_header('Authorization', 'Bearer ' + TOKEN.read_text(encoding='utf-8').strip())
        with urllib.request.urlopen(req, timeout=900) as r, open(tgz, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    top = BASE / 'snap'
    cand = top / TREE
    if not cand.exists():
        top.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tgz) as t:
            t.extractall(top)
    c = api('/commits/' + SHA)
    out = {'sha': SHA, 'commit_tree': c['commit']['tree']['sha'], 'tree_matches_what_f_quoted':
           c['commit']['tree']['sha'] == EXPECTED_TREE,
           'parents': [p['sha'] for p in c['parents']], 'files': sum(1 for p in cand.rglob('*') if p.is_file()),
           'cited': {}}
    for rel, want in EXPECTED_BLOBS.items():
        b = (cand / rel).read_bytes()
        got = blob_sha(b)
        out['cited'][rel] = {'blob': got, 'bytes': len(b), 'starts_like_f_quote': got.startswith(want)}
    main = (cand / 'backend/app/main.py').read_text(encoding='utf-8').splitlines()
    i = next(n for n, l in enumerate(main, 1) if l.startswith('def _fill_plan_generation_receipts'))
    out['seam'] = {'first_line': i, 'body': '\n'.join('%4d| %s' % (n, main[n - 1])
                                                     for n in range(i, i + 26))}
    (BASE / 'k8_export_proof.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


def do_mutant():
    src = BASE / 'snap' / TREE
    dst = BASE / 'snap' / (TREE + '__mutant')
    target = dst / 'backend/app/main.py'
    if not dst.exists():
        shutil.copytree(src, dst)
    before = target.read_bytes()
    text = before.decode('utf-8')
    lines = text.splitlines(keepends=True)
    hits = [n for n, l in enumerate(lines, 1) if GUARD in l]
    removed = []
    for n in hits:
        l = lines[n - 1]
        # the predicate sits inside a .where(...) call; drop only that argument, keep valid syntax
        new = l.replace(',\n' + ' ' * (len(l) - len(l.lstrip()) - 1) + GUARD, '')
        new = new.replace(GUARD + ', ', '').replace(', ' + GUARD, '').replace(GUARD, 'True')
        if new != l:
            removed.append({'line': n, 'was': l.rstrip(), 'now': new.rstrip()})
            lines[n - 1] = new
    after = ''.join(lines).encode('utf-8')
    target.write_bytes(after)
    print(json.dumps({'tree': str(dst), 'guard_occurrences': len(hits), 'removed': removed,
                      'main_py_before': blob_sha(before), 'main_py_after': blob_sha(after),
                      'bytes': [len(before), len(after)],
                      'guard_still_present_in_file': GUARD in after.decode('utf-8'),
                      'compiles': __import__('py_compile').compile(str(target), doraise=True) is not None},
                     ensure_ascii=False, indent=1))


{'export': do_export, 'mutant': do_mutant}[STAGE]()
