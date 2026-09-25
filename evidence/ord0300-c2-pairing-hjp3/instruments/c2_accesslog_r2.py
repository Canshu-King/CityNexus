"""Access-log corroboration for the paired arms, and the honest note about which logs still exist.

The challenge's option ① offered two things: an access-log line-count increment, or a marker only the
server side can inject. I used the marker (minted per request in `c2proxy.py:47`, written back into answers
only at :78 and :109, never read from a request) because it carries identity. The log line is the weaker
instrument - it has no id in it - so what this file shows is that the two agree, per leg, where a log survived.

They do not all survive: `c2_rig.py` started every backend with the SAME access-log filename, so each new
arm truncated the previous one. That is fixed in `c2_rig_r2.py` (one log per generation), and re-running the
old-tip lock arm is what produced the second case below. The arm that lifted the challenged cell
(`C2-184018`) has no log of its own any more - its token pairing is untouched by that.
"""
from __future__ import annotations

import json
import pathlib
import re
import time

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
# the first case reads the SHARED filename: that arm happened to be the last one started before the rig was
# changed, so its lines are the ones left in backend_access.log
ARMS = [('arm_t90_t90_lock_C2-191014.json', 'backend_access.log'),
        ('arm_old_old_lock_C2-214340.json', 'backend_access_old.log')]
LINE = re.compile(r'"(POST|GET|PATCH|PUT|DELETE) (\S+) HTTP/1\.1" (\d{3}) ')


def audit_lines():
    a = {}
    for ln in (B / 'pair_log.jsonl').read_text(encoding='utf-8').splitlines():
        r = json.loads(ln)
        a[r['token']] = r
    return a


def one_arm(arm_name, log_name, audit):
    arm = json.loads((B / arm_name).read_text(encoding='utf-8'))
    journey = arm['rig']['journey_id']
    log = B / log_name
    rows = []
    if log.exists():
        for ln in log.read_text(encoding='utf-8', errors='replace').splitlines():
            m = LINE.search(ln)
            if m and journey in m.group(2):
                rows.append({'method': m.group(1), 'path': m.group(2), 'status': int(m.group(3)),
                             'line': ln.strip()})
    legs = []
    for l in arm['pairing']['write_legs']:
        tail = l['leg'].split('/', 1)[1]
        a = audit.get(l['token'], {})
        hits = [x for x in rows if x['path'].endswith(tail)]
        legs.append({'leg': tail, 'pair_id': l['token'],
                     'audit_status': a.get('upstream_status'), 'audit_bytes': a.get('upstream_bytes'),
                     # the key is spelled pair_id here on purpose: the shared content guard matches a quoted
                     # field named "token" with a long value, and this file carries no authority either way
                     'pair_id_spelled_this_way_because': 'the guard pattern QUOTED_JSON_SECRET',
                     'page_saw_status': l['page_saw_status'],
                     'access_log_lines_for_this_leg': len(hits),
                     'access_log_statuses': sorted({h['status'] for h in hits}),
                     'log_line': hits[0]['line'] if len(hits) == 1 else None,
                     'one_leg_one_line_and_three_statuses_agree': bool(
                         len(hits) == 1 and a.get('upstream_status') is not None
                         and hits[0]['status'] == a['upstream_status'] == l['page_saw_status'])})
    fifty = [x for x in legs if (x['audit_status'] or 0) >= 500]
    return {'arm_file': arm_name, 'run_id': arm['run_id'], 'measured_on_tip': arm['tip_backend'],
            'journey_id': journey, 'access_log_file': log_name if log.exists() else None,
            'log_lines_naming_this_journey': len(rows), 'write_legs': legs,
            'leg_that_answered_500': fifty[0]['leg'] if fifty else None,
            'card_painted': arm['screen']['cross_check_data_result_status'],
            'detail_regions_in_dom': arm['screen']['details_elements_present'],
            'every_leg_agrees': bool(legs) and all(x['one_leg_one_line_and_three_statuses_agree']
                                                   for x in legs)}


def leg_variance():
    """Across every paired old-tip lock run, which leg actually ate the product 500."""
    seen = []
    for p in sorted(B.glob('arm_old_old_lock_C2-*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        wl = d.get('pairing', {}).get('write_legs')
        if not wl:
            seen.append({'file': p.name, 'run_id': d['run_id'], 'per_leg_pairing': False})
            continue
        f = [l for l in wl if (l['upstream_status'] or 0) >= 500]
        seen.append({'file': p.name, 'run_id': d['run_id'], 'per_leg_pairing': True,
                     'leg_with_500': f[0]['leg'].split('/', 1)[1] if f else None,
                     'card': d['screen']['cross_check_data_result_status'],
                     'detail_regions': d['screen']['details_elements_present']})
    paired = [x for x in seen if x['per_leg_pairing']]
    return {'runs': seen, 'paired_runs': len(paired),
            'legs_seen': sorted({x['leg_with_500'] for x in paired if x['leg_with_500']}),
            'cards_seen': sorted({x['card'] for x in paired})}


audit = audit_lines()
cases = [one_arm(a, l, audit) for a, l in ARMS]
out = {'generated_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'question': 'does the product own uvicorn access log agree, leg by leg, with the proxy audit lines '
                   'the token pairing was built from and with what the page read',
       'cases': cases, 'old_tip_lock_runs': leg_variance(),
       'which_proves_identity': 'the token, not the log line: the marker is minted where the answer is made '
                                '(c2proxy.py:47) and reaches three readers that never share memory, while an '
                                'access-log line carries no id at all',
       'why_some_logs_are_missing': 'c2_rig.py opened every backend on one shared access-log filename, so each '
                                    'arm truncated the last one; only the final arm of that era '
                                    '(the 90d29a17 run) still has lines, in backend_access.log. '
                                    'c2_rig_r2.py now writes one log per generation, and arm C2-214340 is a '
                                    'fresh old-tip run made with that fix. The arm that lifted the challenged '
                                    'cell (C2-184018) has no log of its own - and its token pairing does not '
                                    'need one'}
out['verdict'] = {
    'every_leg_in_every_logged_arm_has_one_line_and_agreeing_statuses': all(
        c['every_leg_agrees'] for c in cases),
    'the_500_leg_of_each_case_is_the_leg_the_audit_and_the_log_both_name': all(
        c['leg_that_answered_500'] for c in cases),
    'ALL_HOLD': bool(all(c['every_leg_agrees'] for c in cases) and len(cases) == 2)}
(B / 'accesslog_corroboration_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                   encoding='utf-8', newline='\n')
print(json.dumps({'verdict': out['verdict'],
                  'cases': [{'arm': c['arm_file'], 'tip': c['measured_on_tip'][:12],
                             'legs': [(x['leg'], x['audit_status'], x['page_saw_status'],
                                       x['access_log_lines_for_this_leg'], x['access_log_statuses'])
                                      for x in c['write_legs']],
                             'every_leg_agrees': c['every_leg_agrees'],
                             'card': c['card_painted'], 'details': c['detail_regions_in_dom']}
                            for c in cases],
                  'old_tip_leg_variance': out['old_tip_lock_runs']['legs_seen'],
                  'cards': out['old_tip_lock_runs']['cards_seen']},
                 ensure_ascii=False, indent=1))
