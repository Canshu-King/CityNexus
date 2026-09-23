"""Cell 9 (中途退出重进) facts, computed from the lane DB + the backend access log.

Nothing here is typed in as a verdict: every claim is derived from rows/lines read at run time, so
the receipt can be re-derived by anyone with the same two files.

Sources (both named, both mine):
  DB   D:/moodle/_lane_aad2d1f2_livecopy.sqlite3        (my lane copy; backend :8424 serves it)
  LOG  D:/moodle/_hjp3_lane_backend.log                 (uvicorn access log for :8424)
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3

DB = pathlib.Path('D:/moodle/_lane_aad2d1f2_livecopy.sqlite3')
LOG = pathlib.Path('D:/moodle/_hjp3_lane_backend.log')
J = 'e5a507bd-9bca-411d-9a5d-ea4521b3eba9'
OTHER = 'cc5e67c4-047a-4f45-8336-c443d3acc076'
OUT = pathlib.Path('D:/moodle/_hjp3_fan_sweep_0923/cell9_facts.json')

out: dict = {'db': str(DB), 'log': str(LOG), 'journey': J}

# ---------- 1. access log: every write request that names this journey ----------
line_re = re.compile(r'127\.0\.0\.1:(\d+) - "([A-Z]+) ([^"]+) HTTP/1\.1" (\d{3})')
writes, twins_j, twins_other = [], 0, 0
TWIN_WINDOW_FROM = 10596  # first line after my journey was created (POST ~/journeys)
twins_j_after, twins_other_after = 0, 0
for i, ln in enumerate(LOG.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
    m = line_re.search(ln)
    if not m:
        continue
    peer, meth, path, status = m.group(1), m.group(2), m.group(3), int(m.group(4))
    short = (path.replace(J, '{{J}}').replace(OTHER, '{{O}}').replace('/api/v1', '~'))
    if meth in ('POST', 'PUT', 'PATCH') and ('{{J}}' in short or path.endswith('/journeys')):
        writes.append({'line': i, 'method': meth, 'path': short, 'status': status})
    if '/twin' in path and meth == 'GET':
        if '{{J}}' in short:
            twins_j += 1
            if i >= TWIN_WINDOW_FROM:
                twins_j_after += 1
        elif '{{O}}' in short:
            twins_other += 1
            if i >= TWIN_WINDOW_FROM:
                twins_other_after += 1
out['log_total_lines'] = i
out['write_requests_for_journey'] = writes
out['twin_poll_counts'] = {
    'whole_file_mine_%s' % J[:8]: twins_j,
    'whole_file_foreign_%s' % OTHER[:8]: twins_other,
    'window_from_line_%d_mine' % TWIN_WINDOW_FROM: twins_j_after,
    'window_from_line_%d_foreign' % TWIN_WINDOW_FROM: twins_other_after,
}

n_cmd = sum(1 for w in writes if 'agent/commands' in w['path'] and '{{J}}' in w['path'])
n_gen = sum(1 for w in writes if 'plans/generate' in w['path'] and '{{J}}' in w['path'])
out['logged_agent_commands_post_count'] = n_cmd
out['logged_plans_generate_post_count'] = n_gen
out['logged_agent_commands_post_lines'] = [w['line'] for w in writes
                                           if 'agent/commands' in w['path'] and '{{J}}' in w['path']]

# ---------- 2. DB ground truth for this journey ----------
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def rows(sql, args=()):
    return [dict(r) for r in con.execute(sql, args).fetchall()]


pv_cols = [r[1] for r in con.execute('PRAGMA table_info(plan_versions)')]
out['plan_versions_columns'] = pv_cols
mis_key = 'mission_id' if 'mission_id' in pv_cols else None

missions = rows('SELECT id,status,created_at,started_at,completed_at,user_text FROM journey_missions '
                'WHERE journey_id=? ORDER BY created_at', (J,))
runs = rows('SELECT id,mission_id,status,created_at,completed_at FROM agent_runs '
            'WHERE journey_id=? ORDER BY created_at', (J,))
plans = rows('SELECT id,status,created_at%s FROM plan_versions WHERE journey_id=? ORDER BY created_at'
             % (',mission_id' if mis_key else ''), (J,))
out['missions'] = [{k: (str(v)[:40] if v is not None else None) for k, v in m.items()} for m in missions]
out['runs'] = [{k: (str(v)[:40] if v is not None else None) for k, v in r.items()} for r in runs]
out['plan_versions'] = [{k: (str(v)[:40] if v is not None else None) for k, v in p.items()} for p in plans]
out['journey_active_plan_version_id'] = [r['active_plan_version_id'] for r in
                                         con.execute('SELECT active_plan_version_id FROM journeys WHERE id=?', (J,))]

# ---------- 3. per-mission productivity: did each run leave a plan? ----------
per = []
for m in missions:
    mid = m['id']
    mr = [r for r in runs if r['mission_id'] == mid]
    mp = [p for p in plans if (p.get('mission_id') == mid)] if mis_key else []
    per.append({
        'mission': mid[:8], 'mission_status': m['status'], 'mission_created_at': m['created_at'],
        'mission_completed_at': m['completed_at'],
        'runs': len(mr), 'run_statuses': [r['status'] for r in mr],
        'plans_by_mission_id': len(mp) if mis_key else None,
        'user_text_head': (m['user_text'] or '')[:12],
    })
out['per_mission'] = per
out['plans_total_for_journey'] = len(plans)

if not mis_key:
    # plan_versions does not carry mission_id -> attribute by timestamp instead
    for e in per:
        c = e['mission_completed_at'] or e['mission_created_at']
        e['plans_after_this_mission_started'] = sum(1 for p in plans if p['created_at'] > e['mission_created_at']
                                                    and p['created_at'] <= (missions[per.index(e) + 1]['created_at']
                                                                            if per.index(e) + 1 < len(missions) else '9999'))
    out['plan_attribution_method'] = 'created_at window between consecutive missions (no mission_id column)'
else:
    out['plan_attribution_method'] = 'plan_versions.mission_id'

# ---------- 4. per-round reconciliation (generic over however many missions exist) ----------
bounds = [m['created_at'] for m in missions] + ['9999']
rounds = []
for idx, m in enumerate(missions):
    lo, hi = bounds[idx], bounds[idx + 1]
    plans_in_window = [p for p in plans if lo <= p['created_at'] < hi]
    rounds.append({
        'round': 'ABC'[idx] if idx < 3 else str(idx),
        'mission': m['id'][:8], 'mission_status': m['status'],
        'mission_created_at': m['created_at'], 'mission_completed_at': m['completed_at'],
        'run_statuses': [r['status'] for r in runs if r['mission_id'] == m['id']],
        'plans_written_in_window': len(plans_in_window),
        'plan_statuses': sorted({p['status'] for p in plans_in_window}),
        'user_text': (m['user_text'] or '')[:40],
    })
out['rounds'] = rounds
out['rounds_summary'] = {
    'missions_in_db': len(missions),
    'agent_commands_post_lines_for_this_journey': n_cmd,
    'missions_with_no_access_log_line': len(missions) - n_cmd,
}
out['derived'] = {
    'missions_recorded': len(missions),
    'logged_agent_commands_for_this_journey': n_cmd,
    'a_mission_completed_while_its_post_has_no_log_line': any(
        r['mission_status'] == 'COMPLETED' for r in rounds) and len(missions) > n_cmd,
    'every_mission_completed': all(m['status'] == 'COMPLETED' for m in missions),
    'rounds_that_left_zero_plans': [r['round'] for r in rounds if r['plans_written_in_window'] == 0],
    'rounds_that_left_three_plans': [r['round'] for r in rounds if r['plans_written_in_window'] == 3],
}
# the aborted round is the one whose POST has no log line: it precedes the first logged line
first_logged = out['logged_agent_commands_post_lines'][0] if out['logged_agent_commands_post_lines'] else None
out['aborted_round_identification'] = {
    'method': 'the mission created before the first logged agent/commands line for this journey',
    'first_logged_post_line_number': first_logged,
    'aborted_round': rounds[0]['round'] if rounds and first_logged else None,
}

out['ui_transcriptions'] = {
    'provenance': 'transcribed verbatim from page innerText during the run; not derived values',
    'in_flight_sheet_every_round': ('发出请求，等待模型返回 · 已等待 N 秒 | 后端不会中途汇报进度，所以这里只有真实等待时间，'
                                '没有百分比，也没有猜。 | ✓读取已有方案作为基线 ●发出请求，等待模型返回 '
                                '○核对本次是否真的产出了新方案 | 取消 / 取消并关闭 / 规划中…'),
    'after_reentry_today': '今天 / 还没有安排 … 方案概览 … 以下只是其中一个候选方案的预览，你还没有采用它。',
    'settled_sheet_B': '已生成 3 个可选方案 | 去“今天”对比这几个方案，选一个再继续。',
    'trips_screen_after_B': '行程 / 还没有可看的行程 / 这个行程还没有选定的方案。先让 AI 帮你规划，选定方案后这里会显示逐日安排。',
    'copilot_screen_after_B': '随时问关于这趟行程的任何事 … 消息 …（无这几趟任务的任何条目）',
    'landing_screen_doors_with_no_journey_id': ['新建行程(三步向导)', '使用封存的演示行程', 'EN', 'sim-ball'],
    'hub_visible_buttons_after_B': ['AI 帮我规划', '试用其他城市', '打开行程工作台', '对比住宿 →',
                                    '第 1 天', '第 2 天', '第 3 天', 'nav-hub/trips/map/agent/me'],
    'client_chain_round_C_observed_via_fetch_patch': [
        'POST ~/journeys/JID/agent/commands  (issued immediately on 开始规划)',
        'GET  ~/journeys/JID/twin x3          (still waiting; ~15 s cadence)',
        'GET  ~/journeys/JID/plans            (baseline read-back)',
        'POST ~/journeys/JID/plans/generate   (SECOND LEG — sent by the browser after leg 1 resolves)',
        'GET  experience/replans/wallet/offline-snapshot/agent-policy + tiles',
    ],
    'chain_consequence': ('the handshake is client-driven: leaving the page between the two legs means nobody ever sends '
                          'plans/generate, so the mission/run can still complete server-side while 0 plans are written'),
}
out['db_totals'] = {t: con.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]
                    for t in ('journeys', 'journey_missions', 'agent_runs', 'plan_versions')}
con.close()
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps({k: out[k] for k in ('logged_agent_commands_post_count', 'logged_plans_generate_post_count',
                                      'twin_poll_counts', 'derived', 'plan_attribution_method',
                                      'journey_active_plan_version_id', 'db_totals')},
                 ensure_ascii=False, indent=1))
print('writes:', json.dumps(writes, ensure_ascii=False))
print('rounds:', json.dumps(rounds, ensure_ascii=False))
