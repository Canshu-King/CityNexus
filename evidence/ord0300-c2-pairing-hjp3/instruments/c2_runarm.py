"""ORD-0300 C2 pairing batch - stage 3: the arm table and the runner.

Every arm is DECLARED before it runs (below), and each execution gets its own run id and its own slice of
the append-only pairing log. What an arm produces is one cell json holding four witnesses of the SAME leg:
proxy log line (server side) / the app's own fetch result / the app's body read / the painted card.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
RIG = 'D:/moodle/HJ-P3_evidence/c2_rig.py'
CELLS = str(BASE / 'c2_cells.cjs')
PAIR_LOG = BASE / 'pair_log.jsonl'
READY = BASE / 'sheet_ready.flag'
TIPS = {'old': 'dc964086c9d412573ac19d70b24b30e6c3ee6168',
        'new': '5aff3722d5c36c760a424f5fea5c3a771298f9ac',
        'mut': '5aff3722d5c36c760a424f5fea5c3a771298f9ac',
        't90': '90d29a172e186aab6e6cb138ab4583ccf93bfa68'}
ALT_BUNDLE = {}  # unused: t90 has its own dist_t90 inside this batch  # 90d29a17 has its own export+verified bundle copy in this batch's directory


def bundle_facts_for(which, table):
    """My own batch has three built bundles; the 90d29a17 arm reuses ORD-0300's private build, so its
    facts are recomputed here from the bytes rather than trusted from that batch's notes."""
    if which not in table:
        import re as _re
        d = BASE / ('dist_' + which)
        html = (d / 'index.html').read_text(encoding='utf-8', errors='replace')
        asset = _re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
        raw = (d / 'assets' / asset).read_bytes()
        text = raw.decode('utf-8', 'replace')
        return {'which': which, 'outdir': str(d), 'asset': asset, 'bytes': len(raw),
                'sha256_64_hex': hashlib.sha256(raw).hexdigest(),
                'markers': {'network_card_wording': '连不上服务端' in text,
                            'device_note_for_network_branch': 'no readable answer reached this device' in text,
                            'http_branch_wording': 'agent/commands -> HTTP ' in text,
                            'technical_detail_wording': '技术详情' in text},
                'recomputed_from_bytes_for_this_batch': True}
    return table[which]
# backend tree, bundle, scenario, proxy mode, what this arm is FOR - all declared before it runs.
# scenario `origin500` means: the leg is answered by my proxy with the product's own contentless 500
# (21 B text/plain, exactly the bytes the proxy recorded from the real contended write), so arrival is
# no longer something I infer from a look-alike outcome - it is the thing I control and pair by token.
ARMS = [
    ('old', 'old', 'origin500', 'answer500_plain',
     'the generation my C2 was written on, with a 500 that provably arrives: which branch paints the card'),
    ('new', 'new', 'origin500', 'answer500_plain',
     'the current authority tip, same answer: the guards exist, so the server-failure branch should paint'),
    ('new', 'mut', 'origin500', 'answer500_plain',
     'single variable: this bundle differs from the one above ONLY by the two guards; same backend, same '
     'proxy, same answer'),
    ('old', 'old', 'abort', 'pass',
     'a TRUE transport death on the same tree: if the card is identical to arm 1, the card cannot tell '
     'arrival from non-arrival and only the pairing can'),
    ('old', 'old', 'lock', 'pass',
     'the real product 500 off a real write-lock contention, paired leg by leg'),
    ('new', 'new', 'lock', 'pass',
     'the same forced write on the current tip - whatever it produces, reported as produced'),
    ('t90', 't90', 'lock', 'pass',
     'THE GENERATION THE CHALLENGED CELL WAS WRITTEN ON (90d29a17, that batch made its own export and '
     'private build): reproduce the real product 500 and pair it to the card, leg by leg'),
]


def log_offset():
    return PAIR_LOG.stat().st_size if PAIR_LOG.exists() else 0


def new_log_lines(offset):
    if not PAIR_LOG.exists():
        return []
    with PAIR_LOG.open(encoding='utf-8') as f:
        f.seek(offset)
        return [json.loads(x) for x in f.read().splitlines() if x.strip()]


def start_rig(backend_which, bundles, proxy_mode):
    r = subprocess.run([sys.executable, RIG, 'start', backend_which, proxy_mode], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    print('  rig start:', (r.stdout or r.stderr).strip()[-200:], flush=True)
    if r.returncode != 0:
        # reading a stale rig_state.json after a failed start is how I nearly paired one arm's page with
        # another arm's face - refuse here and say what the rig actually answered
        raise SystemExit('rig start for %s failed (rc=%d): %s' % (backend_which, r.returncode,
                                                                  (r.stderr or r.stdout)[-400:]))
    st = json.loads((BASE / 'rig_state.json').read_text(encoding='utf-8'))
    if st.get('which') != backend_which:
        raise SystemExit('rig_state.json says %s, not %s - stale state, refusing to measure'
                         % (st.get('which'), backend_which))
    for b in bundles:
        if b != backend_which:
            r = subprocess.run([sys.executable, RIG, 'face', b], capture_output=True, text=True,
                               encoding='utf-8', errors='replace')
            print('  face %s: %s' % (b, (r.stdout or r.stderr).strip()[-140:]), flush=True)
            st = json.loads((BASE / 'rig_state.json').read_text(encoding='utf-8'))
    return st


def face_port(st, bundle):
    if 'face' in st and st['face']['tag'] == 'face_' + bundle:
        return st['face']['port']
    return st['extra_faces'][bundle]['port']


def one_leg(w, cell, lines):
    """Pair ONE write leg by the token my proxy minted for it."""
    tok = w.get('pair_token')
    srv = [x for x in lines if x['token'] == tok]
    cons = [c for c in cell['consumed'] if c.get('pair_token') == tok]
    cdp = [c for c in cell['cdp'] if c.get('pair_token') == tok]
    return {
        'leg': w['url'].split('/api/v1/journeys/')[-1].split('?')[0],
        'paired': bool(tok and len(srv) == 1),
        'token': tok,
        'proxy_lines_with_this_token': len(srv),
        'reached_upstream': bool(srv and srv[0].get('reached_upstream')),
        'upstream_status': srv[0].get('upstream_status') if srv else None,
        'upstream_bytes': srv[0].get('upstream_bytes') if srv else None,
        'upstream_content_type': srv[0].get('upstream_content_type') if srv else None,
        'upstream_body_head': srv[0].get('body_head') if srv else None,
        'upstream_elapsed_ms': srv[0].get('upstream_elapsed_ms') if srv else None,
        'answered_by_per_proxy_record': srv[0].get('answered_by') if srv else None,
        'proxy_mode_per_proxy_record': srv[0].get('mode') if srv else None,
        'proxy_says_it_aborted': bool(srv and srv[0].get('mode') == 'abort_on_write'),
        'page_fetch_rejected': w.get('fetch_rejected'),
        'page_reject': (str(w.get('reject_name')) + ': ' + str(w.get('reject_message'))
                        if w.get('fetch_rejected') else None),
        'page_saw_status': w.get('status'),
        'page_saw_ok': w.get('ok'),
        'page_elapsed_ms': w.get('elapsed_ms'),
        'browser_stack_saw': cdp[0] if cdp else None,
        'app_read_the_body': cons[0] if cons else None,
        'app_body_parse_failed': bool(cons and cons[0].get('parsed') is False),
    }


def pair_the_leg(cell, lines):
    """Every write leg of the run, each paired with itself - not the last one, not a merged story."""
    posts = [l for l in cell['legs'] if l['method'] == 'POST' and l.get('api')]
    legs = [one_leg(w, cell, lines) for w in posts]
    hit = [l for l in legs if l['upstream_status'] and l['upstream_status'] >= 500]
    return {'write_legs': legs, 'count': len(legs),
            'any_leg_paired': bool(legs) and all(l['paired'] for l in legs),
            'leg_that_got_a_500': hit[0]['leg'] if hit else None,
            'that_500_leg_is_paired': bool(hit and hit[0]['paired']),
            'that_500_arrived_at_the_page': bool(hit and hit[0]['page_saw_status'] and
                                                not hit[0]['page_fetch_rejected']),
            'that_500_body_was_read_and_failed_to_parse': bool(hit and hit[0]['app_body_parse_failed'])}


def run_arm(backend_which, bundle, mode, proxy_mode, intent):
    run_id = 'C2-%s' % time.strftime('%H%M%S')
    out = {'arm': '%s_%s_%s' % (backend_which, bundle, mode), 'run_id': run_id, 'intent_declared_before': intent,
           'tip_backend': TIPS[backend_which], 'tip_bundle_source': TIPS[bundle],
           'mode': mode}
    st = start_rig(backend_which, [bundle], proxy_mode)
    out['rig'] = {'backend_pid': st['backend']['pid'], 'proxy_pid': st['proxy']['pid'],
                  'backend_up': st['backend']['up'], 'proxy_up': st['proxy']['up'],
                  'proxy_mode_declared': st['proxy']['mode'],
                  'proxy_mode_matches_plan': st['proxy']['mode'] == proxy_mode,
                  'identity_two_sided': st['identity']['two_sided'],
                  'journey_id': st['seed']['journey_id'],
                  'db': str(BASE / ('o0300c2_%s.s3db' % backend_which))}
    bundle_table = json.loads((BASE / 'setup_facts.json').read_text(encoding='utf-8'))['bundles']
    out['bundle'] = bundle_facts_for(bundle, bundle_table)
    out['backend_bytes_equal_to_new_export'] = (
        hashlib.sha256((BASE / ('snap_%s/backend/app/main.py' % backend_which)).read_bytes()).hexdigest()
        == hashlib.sha256((BASE / 'snap_new/backend/app/main.py').read_bytes()).hexdigest()
        ) if backend_which == 'mut' else 'n/a for this arm'
    port = face_port(st, bundle)
    assert st.get('which') == backend_which, ('the rig did not start as %s; its own state says %s'
                                               % (backend_which, st.get('which')))
    assert st.get('which') == backend_which, ('the rig did not actually start as %s; its own state says %s'
                                               % (backend_which, st.get('which')))
    off = log_offset()
    if READY.exists():
        READY.unlink()
    lk = None
    if mode == 'lock':
        lk = subprocess.Popen([sys.executable, RIG, 'lock', backend_which, '40'],
                              stdout=open(BASE / ('lock_%s.log' % run_id), 'w', encoding='utf-8'),
                              stderr=subprocess.STDOUT)
    cmd = ['node', CELLS, 'http://127.0.0.1:%d' % port, st['seed']['journey_id'],
           str(BASE / ('cell_%s_%s.json' % (out['arm'], run_id))),
           {'lock': 'lock', 'abort': 'abort_control', 'origin500': 'origin500'}[mode], str(READY)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=420, cwd=str(BASE),
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    out['node_tail'] = (r.stdout or '').strip().splitlines()[-1:] + (['STDERR:' + r.stderr[-200:]]
                                                                     if (r.stderr or '').strip() else [])
    out['node_rc'] = r.returncode
    if lk:
        lk.wait(timeout=120)
    cell = json.loads((BASE / ('cell_%s_%s.json' % (out['arm'], run_id))).read_text(encoding='utf-8'))
    lines = new_log_lines(off)
    out['pairing'] = pair_the_leg(cell, lines)
    out['screen'] = {k: cell['after_open'].get(k) for k in
                     ('cross_check_data_result_status', 'network_card_painted', 'http500_card_painted',
                      'details_elements_present', 'result_card_painted', 'reason_label_painted',
                      'reason_value_painted', 'body_has_no_readble_answer_note',
                      'cross_check_data_reason_origin')}
    out['page_errors'] = cell.get('page_errors')
    out['legs_all'] = cell.get('legs')
    out['consumed_all'] = cell.get('consumed')
    out['proxy_lines_in_this_arm'] = len(lines)
    out['waited_ms'] = cell.get('waited_ms')
    subprocess.run([sys.executable, RIG, 'stop'], capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
    (BASE / ('arm_%s_%s.json' % (out['arm'], run_id))).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                                  encoding='utf-8', newline='\n')
    print(json.dumps({'arm': out['arm'], 'run': run_id, 'screen': out['screen']['cross_check_data_result_status'],
                      'details': out['screen']['details_elements_present'],
                      'legs': out['pairing']['count'],
                      'all_paired': out['pairing']['any_leg_paired'],
                      'leg_with_500': out['pairing']['leg_that_got_a_500'],
                      '500_paired': out['pairing']['that_500_leg_is_paired'],
                      '500_arrived': out['pairing']['that_500_arrived_at_the_page'],
                      'body_parse_failed': out['pairing']['that_500_body_was_read_and_failed_to_parse'],
                      'per_leg': [{'leg': l['leg'], 'up': l['upstream_status'], 'page': l['page_saw_status'],
                                   'rej': l['page_fetch_rejected'], 'tok_ok': l['paired'],
                                   'parse_fail': l['app_body_parse_failed']}
                                  for l in out['pairing']['write_legs']]}, ensure_ascii=False),
          flush=True)
    return out


if __name__ == '__main__':
    which = sys.argv[1]
    if which == 'list':
        print(json.dumps(ARMS, ensure_ascii=False, indent=1))
        raise SystemExit(0)
    n = int(which)
    try:
        run_arm(*ARMS[n])
    finally:
        # an arm that dies half way must not leave a backend holding a database: the next arm would
        # either reuse that database (wrong) or fail on the delete (confusing), and neither is a read
        subprocess.run([sys.executable, RIG, 'stop'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
