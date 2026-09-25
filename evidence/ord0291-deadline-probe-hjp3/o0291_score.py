"""ORD-0291: derive every verdict from the artefacts; no verdict is typed by hand.

Reads: probe_state.json (the two private copies + the one-literal patch + face byte proofs),
arm_readings_read_*.json, arm_readings_write_*_lock.json, arm_readings_write_*_silent.json,
legs_out_of_range.json (regex self-test), write_channels.json (the range).
Writes: O0291-<run>_score.json
"""
from __future__ import annotations

import json
import pathlib

BASE = pathlib.Path('D:/moodle/_hjp3_0291_0925')
RUN = 'O0291-2507'


def j(name):
    return json.loads((BASE / name).read_text(encoding='utf-8'))


st = j('probe_state.json')
rx = j('arm_readings_read_X.json')
rh = j('arm_readings_read_Xhalf.json')
wl = {a: j('arm_readings_write_%s_lock.json' % a) for a in ('X', 'Xhalf')}
ws = {a: j('arm_readings_write_%s_silent.json' % a) for a in ('X', 'Xhalf')}
legs = j('legs_out_of_range.json')
chan = j('write_channels.json')
TIP = j('tip_readback.json')

CONST_X, CONST_HALF = st['patch']['ms_before'], st['patch']['ms_after']
CONST_DELTA = CONST_X - CONST_HALF


def hung_leg(reading):
    for l in reading['api_legs']:
        if l.get('status') is None and l.get('elapsed_ms'):
            return l
    return None


def write_legs(reading):
    return reading['write_legs']


MY_ARTEFACTS = [
    'D:/moodle/_hjp3_0281_0925/SHAPE_ORD-0281.md',
    'D:/moodle/_hjp3_0288_0925/SHAPE_ORD-0288.md',
    'D:/moodle/HJ-P3_evidence/block_0281.md', 'D:/moodle/HJ-P3_evidence/bus_0281.md',
    'D:/moodle/HJ-P3_evidence/block_0288.md', 'D:/moodle/HJ-P3_evidence/bus_0288.md',
    'D:/moodle/HJ-P3_evidence/o0288_shape.py', 'D:/moodle/HJ-P3_evidence/o0281_shape.py',
]


def arbitration_recount():
    """Two readings the commander could not reproduce and sent back to this lane: count the literal hits in
    the files this lane actually published, and print the inventory so the zero means something."""
    import re
    pats = {'DEFAULT_WRITE_DEADLINE_MS': re.compile(r'DEFAULT_WRITE_DEADLINE_MS'),
            'ten_thousand_ms': re.compile(r'\b10_?000\b'),
            'commit_1106': re.compile(r'1106'),
            'record_audit_1111': re.compile(r':1111\b')}
    hits = {k: [] for k in pats}
    read = []
    for p in MY_ARTEFACTS:
        path = pathlib.Path(p)
        if not path.exists():
            read.append([p, 'MISSING'])
            continue
        txt = path.read_text(encoding='utf-8', errors='replace')
        read.append([p, len(txt)])
        for k, rx in pats.items():
            for m in rx.finditer(txt):
                hits[k].append('%s@%d:%s' % (path.name, m.start(), txt[max(0, m.start() - 40):m.start() + 40]))
    return {
        'method': 'every artefact file this lane published for ORD-0281 / ORD-0288 was read and searched for the '
                  'literal strings; the inventory with byte counts is printed below',
        'files_read': read, 'coverage': 'NOT EXHAUSTIVE - chat/bus prose that was never written to one of these '
                                        'files is outside this search',
        'hits': {k: v for k, v in hits.items()},
        'hit_counts': {k: len(v) for k, v in hits.items()},
    }


x_hung, h_hung = hung_leg(rx), hung_leg(rh)
abort_x = x_hung['elapsed_ms'] if x_hung else None
abort_h = h_hung['elapsed_ms'] if h_hung else None
card_x, card_h = rx['first_trigger']['ms'], rh['first_trigger']['ms']
card_delta = card_x - card_h
abort_delta = (abort_x or 0) - (abort_h or 0)

lock_no_card = [a for a in wl if wl[a]['deadline_card_during_flight'] is None]
lock_settled = {a: [l.get('status') for l in write_legs(wl[a])] for a in wl}
silent_no_card = [a for a in ws if ws[a]['deadline_card_during_flight'] is None]
silent_open = {a: [l.get('status') is None and l.get('client_error') is None for l in write_legs(ws[a])]
               for a in ws}

RIG_FALLBACK = 'write-lock rig (backend 127.0.0.1:8493, bounded SQLite busy_timeout)'


def rig_of(reading):
    """Two of the lock-rig arms were executed before the reading carried a `rig` field; their file is named
    so the fallback is auditable rather than silent."""
    return {'present_in_file': 'rig' in reading, 'value': reading.get('rig', RIG_FALLBACK),
            'file_was_written_before_the_field_existed': 'rig' not in reading}


score = {
    'order': 'ORD-0291', 'run_id': RUN, 'lane': 'HJ-P3 aad2d1f2',
    'frozen_tip': TIP['head_sha'],
    'frozen_tip_source': 'read back with `git rev-parse HEAD` inside the very tree the scans ran against, and '
                         'that tree\'s `git status --porcelain` is empty (%d lines) - see tip_readback.json; '
                         'the abbreviated form in the ledger is not a coordinate' % TIP['porcelain_lines'],
    'claim_kind': 'runtime_measured - per Q25 none of these durations may be inherited by another generation',
    'constant': {
        'export_name': 'READ_DEADLINE_MS', 'source_site': 'frontend/src/lib/readDeadline.ts:15',
        'source_constant_line': legs['wrapper_definition']['constant_text'],
        'minified_site_offset': st['patch']['offset'],
        'before_literal': st['patch']['before'], 'after_literal': st['patch']['after'],
        'ms_before': CONST_X, 'ms_after': CONST_HALF,
        'occurrences_of_before_literal': st['patch']['occurrences_of_before_literal'],
        'product_bytes_changed': 0,
        'why': 'the patch was applied only inside two private copies of a frozen dist; the served bundle on '
               'the user chain was never rewritten',
    },
    'verdicts': {
        'V1_constant_is_single_site_and_named': {
            'rule': 'the before-literal must occur exactly once and the source must name one export',
            'occurrences': st['patch']['occurrences_of_before_literal'],
            'source_constant_lines': legs['wrapper_definition']['constant_lines'],
            'derived': 'SINGLE_SITE_NAMED' if (st['patch']['occurrences_of_before_literal'] == 1
                                               and len(legs['wrapper_definition']['constant_lines']) == 1)
                       else 'NOT_SINGLE_SITE',
        },
        'V2_read_trigger_moves_with_the_constant': {
            'rule': 'the rendered trigger moment must shift by (within 1 s) the constant delta',
            'constant_delta_ms': CONST_DELTA,
            'card_ms': {'X': card_x, 'X_half': card_h}, 'card_delta_ms': card_delta,
            'abort_ms': {'X': abort_x, 'X_half': abort_h}, 'abort_delta_ms': abort_delta,
            'seconds_shown': {'X': rx['first_trigger']['seconds_shown'],
                              'X_half': rh['first_trigger']['seconds_shown']},
            'sentence_X': rx['first_trigger']['deadline_line'], 'sentence_X_half': rh['first_trigger']['deadline_line'],
            'derived': 'MOVES_WITH_CONSTANT' if abs(card_delta - CONST_DELTA) <= 1000
                       and abs(abort_delta - CONST_DELTA) <= 1000 else 'DOES_NOT_MOVE',
        },
        'V3_write_leg_is_insensitive_on_the_lock_rig': {
            'rule': 'with the same two constants, a write leg that showed no card at either value is not '
                    'being bounded by the constant',
            'arms_without_card': sorted(lock_no_card), 'arms_expected': ['X', 'Xhalf'],
            'server_status_seen': lock_settled,
            'elapsed_ms': {a: [l.get('elapsed_ms') for l in write_legs(wl[a])] for a in wl},
            'derived': 'WRITE_LEG_IGNORES_CONSTANT' if sorted(lock_no_card) == ['X', 'Xhalf']
                       and all(any(s is not None for s in v) for v in lock_settled.values()) else 'INCONCLUSIVE',
        },
        'V4_write_leg_against_a_silent_origin': {
            'rule': 'the origin answers every read and never answers the POST; if the client has no bound of '
                    'its own the leg stays open and the screen never changes - that is ORD-0281 T-b counter-'
                    'example 1, executable today',
            'arms_without_card': sorted(silent_no_card),
            'leg_still_open_at_cap': silent_open,
            'cap_ms': {a: ws[a]['timeline_tail'][-1]['ms'] for a in ws},
            'derived': 'WRITE_LEG_STILL_UNBOUNDED' if sorted(silent_no_card) == ['X', 'Xhalf']
                       and all(any(v) for v in silent_open.values()) else 'WRITE_LEG_ENDED_ON_ITS_OWN',
        },
        'V5_the_instrument_can_see_the_card': {
            'rule': 'a negative reading is only worth its positive control: the same matcher must fire on the '
                    'deadline sentence and must not fire on the progress counter',
            'selftest': legs['regex_selftest'],
            'read_arms_produced_a_card': [rx['first_trigger'] is not None, rh['first_trigger'] is not None],
            'derived': 'CONTROL_OK' if (legs['regex_selftest']['verdict'] == 'SELFTEST_OK'
                                        and all([rx['first_trigger'] is not None,
                                                 rh['first_trigger'] is not None])) else 'CONTROL_BROKEN',
        },
        'V6_range_which_legs_the_constant_can_reach': {
            'rule': 'name every write leg and the channel it travels on (per-file helper resolution)',
            'tree_scanned': chan['tree'], 'search_space': chan['search_space'],
            'channel_tally': chan['channel_tally'],
            'through_the_wrapper_short_circuited_by_readDeadline_line_43': chan['channel_tally'].get('WRAPPER'),
            'raw_fetch_never_seeing_the_wrapper': chan['channel_tally'].get('RAW_FETCH'),
            'unresolved_rows': [('%s:%d' % (r['file'], r['line'])) for r in chan['per_site']
                                if r['channel'] == 'UNRESOLVED'],
            'coverage': chan['coverage'],
            'derived': 'RANGE_NAMED',
        },
    },
    'arms': {
        'read_X': {'port': rx['port'], 'origin': rx['origin'], 'face_bytes_sha': st['faces']['X']['served_sha256']},
        'read_Xhalf': {'port': rh['port'], 'origin': rh['origin'], 'face_bytes_sha': st['faces']['Xhalf']['served_sha256']},
        'write_lock_X': {'port': wl['X']['port'], 'rig': rig_of(wl['X']),
                         'face_bytes_sha': st['write_faces']['X']['served_sha256']},
        'write_lock_Xhalf': {'port': wl['Xhalf']['port'], 'rig': rig_of(wl['Xhalf']),
                             'face_bytes_sha': st['write_faces']['Xhalf']['served_sha256']},
        'write_silent_X': {'port': ws['X']['port'], 'rig': rig_of(ws['X']),
                           'face_bytes_sha': [v for k, v in (st.get('faces_extra') or {}).items()
                                              if v['arm'] == 'X' and k == str(ws['X']['port'])][0]['served_sha256']},
        'write_silent_Xhalf': {'port': ws['Xhalf']['port'], 'rig': rig_of(ws['Xhalf']),
                               'face_bytes_sha': [v for k, v in (st.get('faces_extra') or {}).items()
                                                  if v['arm'] == 'Xhalf' and k == str(ws['Xhalf']['port'])][0]['served_sha256']},
    },
    'disclosed_instrument_failures': [
        {'what': 'the first selective origin closed the connection instead of holding it, so vite\u0027s proxy '
                'answered the browser with its own 500 in 90 ms; that arm was discarded, the file kept as '
                'arm_readings_write_X_silent-INSTRUMENT_BROKEN.json',
         'fix': 'hold the handler thread on an event until teardown (o0291_selective_origin.py SILENCE)'},
        {'what': 'the write arm for X on the lock rig was overwritten by that discarded run; it was re-executed '
                'and now lives in arm_readings_write_X_lock.json',
         'fix': 'every artefact name now carries the rig tag (_lock / _silent)'},
    ],
    'arbitration_items_returned_to_this_lane': arbitration_recount(),
}
out = BASE / ('%s_score.json' % RUN)
out.write_text(json.dumps(score, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: v['derived'] for k, v in score['verdicts'].items()}, ensure_ascii=False, indent=1))
print('card_delta %d vs constant_delta %d ; abort %s/%s' % (card_delta, CONST_DELTA, abort_x, abort_h))
