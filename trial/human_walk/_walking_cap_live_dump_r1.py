"""Write the walking-cap live readings out of the two canary databases, one claim per line, no hand-typed numbers."""
import io
import json
import sqlite3

OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/walking_cap_live-1.txt"
LIVE = r"D:/moodle/_cmdr_v3_live_1022/"


def task_of(db):
    c = sqlite3.connect("file:" + LIVE + db + "?mode=ro", uri=True)
    # A canary database keeps every journey this tag walked, so "the mission" is a list, not a row:
    # reading only the first one silently drops the very walk that carries the newest fields.
    return c, [(row[0], json.loads(row[1])["goal_task"]) for row in
               c.execute("select journey_id, intent_json from journey_missions order by rowid").fetchall()]


def names(c):
    return {row[0]: row[1] for row in c.execute("select id, name from places")}


lines = []
for tag, db in (("换代前", "citynexus_v3_cap_1024.db"), ("换代后", "citynexus_v3_cap2_1024.db")):
    c, missions = task_of(db)
    for index, (journey_id, task) in enumerate(missions):
        attempt = ((task.get("prepared_plan") or {}).get("result") or {}).get("route_attempt")
        tag_row = "%s 趟=%d 库=%s" % (tag, index + 1, db)
        lines.append("%s journey_id_marker=%s" % (tag_row, journey_id))
        lines.append("%s stored_route_attempt=%s" % (tag_row, json.dumps(attempt, ensure_ascii=False, sort_keys=True)))
        evidence = json.loads(c.execute("select mobility_evidence_json from plan_versions where journey_id=? and mobility_evidence_json is not null",
                                        (journey_id,)).fetchone()[0])
        known = names(c)
        lines.append("%s frozen_fact_count_marker=%d" % (tag_row, len(evidence.get("facts") or [])))
        for fact in evidence.get("facts") or []:
            lines.append("%s frozen_fact %s|%s mode=%s distance_m=%s walking_distance_m=%s minutes=%s" % (
                tag_row, known.get(fact.get("origin_key"), "?"), known.get(fact.get("destination_key"), "?"),
                fact.get("mode"), fact.get("distance_m"), fact.get("walking_distance_m"), fact.get("minutes")))
        rows = task.get("research_routes") or []
        lines.append("%s research_row_marker=%d" % (tag_row, len(rows)))
        for row in rows:
            lines.append("%s research_row %s|%s mode=%s distance_m=%s walking_cap_m=%s frozen_mode=%s "
                         "frozen_distance_m=%s frozen_minutes=%s frozen_lines=%s" % (
                             tag_row, row.get("from_name"), row.get("to_name"), row.get("mode"), row.get("distance_m"),
                             row.get("walking_cap_m"), row.get("frozen_mode"), row.get("frozen_distance_m"),
                             row.get("frozen_minutes"), "|".join(row.get("frozen_lines") or [])))
        intent = c.execute("select source_text, capabilities_json from journey_intents where journey_id=?",
                          (journey_id,)).fetchone()
        if intent:
            lines.append("%s traveller_words source_text=%s capabilities_json=%s" % (tag_row, intent[0], intent[1]))

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("written_lines=%d path=%s" % (len(lines), OUT))
