"""ORD-0301 arm runner: one execution = one policy stamp + one run id, never re-used.

The table below is the whole experiment: every row's server-side outcome is DECLARED here before the
arm runs, so a reading cannot be chosen after I have seen the card.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0301_0925')
import json
RIG = 'D:/moodle/HJ-P3_evidence/o0301_rig.py'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
PLAIN = 'Internal Server Error'           # the product's own contentless 500 body, byte-for-byte
# ports are read from whatever rig is live (the first pass hardcoded them, which is how the first
# seven pass-2 executions fired at a face I had already stopped: they wrote no artefact and are disclosed)
_tag = (BASE / 'current_state_tag.txt').read_text(encoding='utf-8').strip()
_ST = json.loads((BASE / (_tag + '_state.json')).read_text(encoding='utf-8'))
FCTL = _ST['ports']['face_controlled']
FREAL = _ST['ports']['face_real']
FREF = _ST['ports']['face_upstream_absent']

ARMS = {
    'a2_ctl_500_plain_fast':      (FCTL, {'write': {'mode': 'answer', 'status': 500, 'content_type': 'text/plain; charset=utf-8',
                                                    'body': PLAIN, 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a3_ctl_500_plain_slow35':    (FCTL, {'write': {'mode': 'answer', 'status': 500, 'content_type': 'text/plain; charset=utf-8',
                                                    'body': PLAIN, 'delay_ms': 35000}, 'read': {'mode': 'proxy'}}, 75000, 0),
    'a4_ctl_500_product_env_fast': (FCTL, {'write': {'mode': 'answer', 'status': 500, 'content_type': 'application/json',
                                                     'body': {'file': 'envelope_real.json'}, 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a5_ctl_503_product_env_fast': (FCTL, {'write': {'mode': 'answer', 'status': 503, 'content_type': 'application/json',
                                                     'body': {'file': 'envelope_real.json'}, 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a6_ctl_502_product_env_fast': (FCTL, {'write': {'mode': 'answer', 'status': 502, 'content_type': 'application/json',
                                                     'body': {'file': 'envelope_real.json'}, 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a7_ctl_504_product_env_fast': (FCTL, {'write': {'mode': 'answer', 'status': 504, 'content_type': 'application/json',
                                                     'body': {'file': 'envelope_real.json'}, 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a8_ctl_500_short_body':      (FCTL, {'write': {'mode': 'answer', 'status': 500, 'content_type': 'text/plain; charset=utf-8',
                                                    'body': PLAIN, 'declared_content_length': 21, 'truncate_to': 5,
                                                    'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    # The three rows that decide whether the discriminator is the STATUS CODE or the BODY SHAPE:
    # same 500, body = JSON `null` / a JSON object with no error / a gateway's plain-text 503.
    'a15_ctl_500_json_null_body': (FCTL, {'write': {'mode': 'answer', 'status': 500, 'content_type': 'application/json',
                                                    'body': 'null', 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a16_ctl_500_empty_json_object': (FCTL, {'write': {'mode': 'answer', 'status': 500, 'content_type': 'application/json',
                                                       'body': '{}', 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a17_ctl_503_plain_gateway':  (FCTL, {'write': {'mode': 'answer', 'status': 503, 'content_type': 'text/plain; charset=utf-8',
                                                    'body': 'Service Unavailable', 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a9_ctl_reset_no_response':   (FCTL, {'write': {'mode': 'reset'}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a11_ctl_silent_write':       (FCTL, {'write': {'mode': 'silent', 'hold_seconds': 200}, 'read': {'mode': 'proxy'}}, 62000, 0),
    'a12_ctl_silent_read':        (FCTL, {'read': {'mode': 'silent', 'hold_seconds': 120},
                                          'write': {'mode': 'answer', 'status': 500, 'content_type': 'application/json',
                                                    'body': {'file': 'envelope_real.json'}}}, 40000, 0),
    'a14_no_instrument_fast500':  (FCTL, {'write': {'mode': 'answer', 'status': 500, 'content_type': 'text/plain; charset=utf-8',
                                                    'body': PLAIN, 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a1_real_lock_500_plain':     (FREAL, None, 80000, 1),
    'a13_real_422_control':       (FREAL, None, 45000, 0),
    'a10_upstream_absent':        (FREF, None, 45000, 0),
    # ---- pass 2: the classes the dispatch names and my first pass did not measure ----
    'a18_route_abort_transport':  (FCTL, {'write': {'mode': 'answer', 'status': 500,
                                                    'content_type': 'text/plain; charset=utf-8',
                                                    'body': PLAIN, 'delay_ms': 250},
                                          'read': {'mode': 'proxy'}}, 45000, 0),
    'a19_200_empty_body':         (FCTL, {'write': {'mode': 'answer', 'status': 200,
                                                   'content_type': 'application/json', 'body': '',
                                                   'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a20_200_json_empty_object':  (FCTL, {'write': {'mode': 'answer', 'status': 200, 'content_type': 'application/json',
                                                   'body': '{}', 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a21_200_json_array':         (FCTL, {'write': {'mode': 'answer', 'status': 200, 'content_type': 'application/json',
                                                   'body': '[]', 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a22_200_text_plain_payload': (FCTL, {'write': {'mode': 'answer', 'status': 200,
                                                   'content_type': 'text/plain; charset=utf-8',
                                                   'body': PLAIN, 'delay_ms': 250}, 'read': {'mode': 'proxy'}}, 45000, 0),
    'a23_200_mission_bad_status': (FCTL, {'write': {'mode': 'answer', 'status': 200, 'content_type': 'application/json',
                                                   'body': {'file': 'mission_bad_status.json'}, 'delay_ms': 250},
                                          'read': {'mode': 'proxy'}}, 45000, 0),
    'a24_read_answered_after_deadline': (FCTL, {'read': {'mode': 'proxy', 'delay_ms': 20000},
                                               'write': {'mode': 'answer', 'status': 200,
                                                         'content_type': 'application/json', 'body': '{}'}}, 40000, 0),
}


def run(arm):
    if arm not in ARMS:
        raise SystemExit('unknown arm %s (inventory: %s)' % (arm, sorted(ARMS)))
    port, spec, cap, need_lock = ARMS[arm]
    stamp = arm.upper()
    if spec is not None:
        spec_file = BASE / ('spec_%s.json' % arm)
        spec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding='utf-8')
        r = subprocess.run([PY, RIG, 'policy', stamp, str(spec_file)], capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
        print('policy:', r.stdout.strip()[:400])
        if r.returncode != 0:
            raise SystemExit('policy writer failed: ' + r.stderr[-400:])
    run_id = time.strftime('O0301-%H%M%S')
    env = dict(__import__('os').environ)
    env.update({'ARM': arm, 'FACE_PORT': str(port), 'POLICY_STAMP': stamp if spec is not None else 'FACE-%d' % port,
                'RUN_ID': run_id, 'CAP_MS': str(cap)})
    if need_lock:
        env['NEED_LOCK'] = '1'
    if arm == 'a14_no_instrument_fast500':
        env['INSTRUMENTED'] = '0'
    if arm == 'a18_route_abort_transport':
        env['ROUTE_ABORT'] = '1'
    lock_proc = None
    if need_lock:
        for stale in ('sheet_ready.flag', 'lock_armed.flag'):
            p_stale = BASE / stale
            if p_stale.exists():
                p_stale.unlink()
        lock_proc = subprocess.Popen([PY, RIG, 'lock', '40'], cwd=str(BASE),
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding='utf-8', errors='replace')
    p = subprocess.run(['node', str(BASE / 'o0301_cells.cjs')], cwd=str(BASE), env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=(cap / 1000) + 180)
    pr = subprocess.run([PY, 'D:/moodle/HJ-P3_evidence/o0301_answerer.py', str(port), stamp,
                        'probe_%s_%s.json' % (arm, run_id), '8'], capture_output=True, text=True,
                        encoding='utf-8', errors='replace')
    print('answerer:', pr.stdout.strip()[:600], pr.stderr.strip()[-200:] if pr.returncode else '')
    src_log = BASE / ('origin_%d_log.jsonl' % json.loads(
        (BASE / ((BASE / 'current_state_tag.txt').read_text(encoding='utf-8').strip() + '_state.json')
         ).read_text(encoding='utf-8'))['ports']['outcome_origin'])
    if src_log.exists():
        (BASE / ('originlog_%s_%s.jsonl' % (arm, run_id))).write_text(src_log.read_text(encoding='utf-8'),
                                                                      encoding='utf-8')
    pr = subprocess.run([PY, 'D:/moodle/HJ-P3_evidence/o0301_answerer.py', str(port), stamp,
                        'probe_%s_%s.json' % (arm, run_id), '8'], capture_output=True, text=True,
                        encoding='utf-8', errors='replace')
    print('answerer:', pr.stdout.strip()[:600], pr.stderr.strip()[-200:] if pr.returncode else '')
    src_log = BASE / ('origin_%d_log.jsonl' % json.loads(
        (BASE / ((BASE / 'current_state_tag.txt').read_text(encoding='utf-8').strip() + '_state.json')
         ).read_text(encoding='utf-8'))['ports']['outcome_origin'])
    if src_log.exists():
        (BASE / ('originlog_%s_%s.jsonl' % (arm, run_id))).write_text(src_log.read_text(encoding='utf-8'),
                                                                     encoding='utf-8')
    print(p.stdout.strip()[:1600])
    if p.stderr.strip():
        print('stderr:', p.stderr.strip()[:400])
    if lock_proc:
        out, _ = lock_proc.communicate(timeout=180)
        (BASE / ('locklog_%s.txt' % run_id)).write_text(out, encoding='utf-8')
        print('locklog:', out.replace('\n', ' | ')[:400])
    return {'arm': arm, 'run_id': run_id, 'port': port, 'stamp': stamp, 'cell_file':
            str(BASE / ('cell_%s_%s.json' % (arm, run_id)))}


if __name__ == '__main__':
    res = run(sys.argv[1])
    print('RUNRESULT ' + json.dumps(res, ensure_ascii=False))
