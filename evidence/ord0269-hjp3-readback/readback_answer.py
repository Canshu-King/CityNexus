"""Final computed receipt for: can the aborted round be read back TODAY? (feeds ORD-0269 §①(i))

Everything below is derived at run time from the running backend's own routes and payloads, plus my
lane DB rows. No verdict is a literal.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.request

ROOT = 'http://127.0.0.1:8424'
J = 'e5a507bd-9bca-411d-9a5d-ea4521b3eba9'
DB = 'D:/moodle/_lane_aad2d1f2_livecopy.sqlite3'
OUT = 'D:/moodle/_hjp3_fan_sweep_0923/readback_answer.json'


def get(p):
    with urllib.request.urlopen(ROOT + p, timeout=40) as r:
        return json.loads(r.read().decode())


spec = get('/openapi.json')
routes = sorted(spec['paths'])
jget = sorted(p for p in routes if '{journey_id}' in p and 'get' in spec['paths'][p])

con = sqlite3.connect(DB)
mis = {r[0][:8]: r[1] for r in con.execute('SELECT id, status FROM journey_missions WHERE journey_id=?', (J,))}
runs = {r[0][:8]: (r[1], r[2]) for r in con.execute('SELECT id, mission_id, status FROM agent_runs WHERE journey_id=?', (J,))}
runs_by_mission_prefix = {(v[0][:8] if v[0] else None): (rid, v[1]) for rid, v in runs.items()}
plan_times = [r[0] for r in con.execute('SELECT created_at FROM plan_versions WHERE journey_id=? ORDER BY created_at', (J,))]
con.close()

feed = get('/api/v1/journeys/%s/agent-feed?limit=200' % J)['events']
feed_default = get('/api/v1/journeys/%s/agent-feed' % J)['events']

completed = [e for e in feed if e['event_type'] == 'agent.run.completed']
plans_gen = [e for e in feed if e['event_type'] == 'plans.generated']

per_round = []
for e in completed:
    mid = next((m for m in mis if m in json.dumps(e)), None)
    ts = e['timestamp']
    # the only join available today: a plans.generated event at the same instant (to the second)
    twin = [p for p in plans_gen if p['timestamp'][:19] == ts[:19]]
    per_round.append({
        'mission': mid, 'mission_status_in_db': mis.get(mid),
        'run_id_in_db': (runs_by_mission_prefix.get(mid) or (None, None))[0],
        'run_status_in_db': (runs_by_mission_prefix.get(mid) or (None, None))[1],
        'run_completed_event_at': ts,
        'plans_generated_event_at_same_second': [p['timestamp'] for p in twin],
        'plans_rows_written_for_this_round': sum(1 for t in plan_times if t[:19] == ts[:19]),
        'event_carries_FAILED_EXTERNAL': 'FAILED_EXTERNAL' in json.dumps(e),
        'plans_generated_event_names_the_mission': any(mid and mid in json.dumps(p) for p in plans_gen),
    })

routes_exposing = {}
for tpl in jget:
    try:
        body = json.dumps(get(tpl.replace('{journey_id}', J)), ensure_ascii=False)
    except Exception as ex:
        body = ''
    routes_exposing[tpl.replace('/api/v1/journeys/{journey_id}', '~')] = {
        'bytes': len(body.encode()),
        'names_any_aborted_mission': sorted(m for m in ('13cd91f3', '17aec167') if m in body),
        'DEGRADED_count': body.count('DEGRADED'),
        'FAILED_EXTERNAL_count': body.count('FAILED_EXTERNAL'),
    }

mission_paths = {p: sorted(spec['paths'][p]) for p in routes if 'mission' in p}
ans = {
 'question': 'commander 0269 §①(i): "mission=COMPLETED + run=COMPLETED + plans=0 本来就能被读回（agent-feed/missions 那条路）" - true?',
 'journey': J,
 'journey_scoped_get_routes': len(jget),
 'routes_total_in_openapi': len(routes),
 'paths_containing_mission_and_their_methods': mission_paths,
 'no_GET_route_listing_missions': not any('get' in v for v in mission_paths.values()),
 'per_round': per_round,
 'feed_pages': {'with_limit_200_events': len(feed), 'default_no_limit_events': len(feed_default),
                'default_page_omits_newest_aborted_round': not any('17aec167' in json.dumps(e) for e in feed_default)},
 'routes_that_name_the_aborted_missions': [k for k, v in routes_exposing.items() if v['names_any_aborted_mission']],
 'routes_exposing_DEGRADED': [k for k, v in routes_exposing.items() if v['DEGRADED_count']],
 'routes_exposing_FAILED_EXTERNAL': [k for k, v in routes_exposing.items() if v['FAILED_EXTERNAL_count']],
 'verdict': {
   'partly_true': all(r['run_completed_event_at'] for r in per_round),
   'terminal_mission_status_readable': bool([k for k, v in routes_exposing.items() if v['DEGRADED_count']]),
   'plans_link_to_mission_readable': any(r['plans_generated_event_names_the_mission'] for r in per_round),
   'zero_plan_round_distinguishable_only_by_timestamp': all(
       (r['plans_rows_written_for_this_round'] > 0) == bool(r['plans_generated_event_at_same_second']) for r in per_round),
 },
}
json.dump(ans, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(ans, ensure_ascii=False, indent=1)[:3500])
print('WROTE', OUT)
