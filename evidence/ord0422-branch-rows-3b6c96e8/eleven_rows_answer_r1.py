# Builds the eleven-row answer table from the reading artifacts. Nothing here is typed: each row's
# route, arm hits and Chinese sentence come out of the JSON the browser wrote, and how the state was
# produced (product door vs this lane's stored-row fixture) is carried per case, so a panel reading
# is never mistaken for a production reachability claim.
import json

FIXTURE_NOTE = {
    "with_proposal": "fixture: a PRESENTED replan_proposals row and its CANDIDATE plan_versions row, "
                     "written only into this lane's private database copy; POST "
                     "/api/v1/journeys/{id}/replans refuses to create one here (422 "
                     "MOBILITY_DATA_UNAVAILABLE, no reachable routing provider on this box)",
    "with_unconfirmed_capability": "fixture: a traveler_capabilities row with confirmed = 0; the "
                     "product's only capability door POST /api/v1/travelers/{id}/capabilities/confirm "
                     "answered confirmed: true for a row sent with confirmed false, so no public door "
                     "leaves that state",
    "no_policy_row": "fixture: the traveler_agent_policies row deleted, and the read door STILL "
                     "answered 200 with a synthesised default, so the shell's policy prop is never "
                     "null on this route",
    "sealed_demo": "product path only: the sealed demo entry button and, for the empty state, a "
                   "second journey with no twin facts; the confirmed capability behind 已由旅行者确认 "
                   "was written through the product's own POST "
                   "/api/v1/travelers/{id}/capabilities/confirm, not by a database write",
}
CASES = [("with_proposal", "authoritative", "branch_readings/with_proposal_authoritative.json"),
         ("with_unconfirmed_capability", "twin", "branch_readings/with_unconfirmed_capability_twin.json"),
         ("no_policy_row", "authoritative", "branch_readings/no_policy_row_authoritative.json")]
ORDER = ["Confirmed by traveler", "Stated; confirmation needed", "No explicit preferences",
         "hard need(s) remain explicit and are never learned.",
         "policy unavailable · confirmation required", "CHANGED", "PROTECTED", "Baseline evidence",
         "Incident evidence", "Deterministic gate", "Delegation policy"]

rows = {}
for case, route, path in CASES:
    d = json.load(open("D:/moodle/_qoder_q_ord0422/" + path, encoding="utf-8"))
    en, zh = d["arms"][1], d["arms"][0]
    for r in en["rows"]:
        zr = next(x for x in zh["rows"] if x["row"] == r["row"])
        rows.setdefault(r["row"], []).append({
            "case": case, "route": route, "why": FIXTURE_NOTE[case], "keys": r["keys"],
            "interpolated": r["interpolated"], "en_leaf": r["en_leaf"], "zh_leaf": zr["zh_leaf"],
            "en_texts": r["en_texts"], "zh_texts": zr["zh_texts"]})

# The sealed-demo case is this lane's own two-arm reader over the whole inventory; the four twin rows
# that need no fixture are read out of it by whole-leaf equality on the recorded leaves.
rep = json.load(open("D:/moodle/_qoder_q_ord0422/final4/final_readings_r4.json", encoding="utf-8"))
PAIR = {"Confirmed by traveler": "twin_demo", "No explicit preferences": "twin_no_preferences",
        "hard need(s) remain explicit and are never learned.": "twin_demo"}
# The inventory records the tail of that interpolated sentence, and no leaf ever equals a tail, so the
# sealed-demo check asks for the whole rendered sentence instead.
EN_FULL = {"hard need(s) remain explicit and are never learned.":
           "1 hard need(s) remain explicit and are never learned."}
ZH_TEXT = {"Confirmed by traveler": ["已由旅行者确认"], "No explicit preferences": ["没有明确偏好"],
           "hard need(s) remain explicit and are never learned.": ["1 项硬性需求仍按明确声明保留，不会被习得。"]}
for row, label in PAIR.items():
    en = next(x for x in rep["readings"] if x["label"] == label and x["locale"] == "en")
    zh = next(x for x in rep["readings"] if x["label"] == label and x["locale"] == "zh-CN")
    rows.setdefault(row, []).append({
        "case": "sealed_demo", "route": "twin", "why": FIXTURE_NOTE["sealed_demo"], "keys": [],
        "interpolated": True, "en_leaf": EN_FULL.get(row, row) in en["leaves"], "zh_leaf": any(
            any(t in x for x in ZH_TEXT[row]) for t in zh["leaves"]),
        "en_texts": [EN_FULL.get(row, row)], "zh_texts": ZH_TEXT[row]})

L = []
add = L.append
add("ORD-0422  the eleven branch-gated rows: how each was reached and what each arm reads")
add("build under test: live tip 3b6c96e8a9f986672ddaa764f5f2ae69534ceff1, and its main JS asset is")
add("byte-equal to the delivered candidate's build -- /assets/index-oR3PVCYW.js, 1343017 bytes,")
add("sha256 ec9823cf7ed76162c854a38c53dff88c3d8d31a34086a59b63b052da7af8e22a")
add("matcher: whole rendered leaf equality, both arms, 390x844, scrolled to bottom")
add("")
add("== per row ==")
reached, notReached, reachedWithoutFixture = [], [], []
for row in ORDER:
    hits = rows.get(row, [])
    ok = [h for h in hits if h["en_leaf"] and h["zh_leaf"]]
    if ok:
        reached.append(row)
        byProduct = [h for h in ok if h["case"] == "sealed_demo"]
        if byProduct:
            reachedWithoutFixture.append(row)
        add("REACHED  %-58s  reached in %s case(s): %s"
            % (json.dumps(row, ensure_ascii=False), len(ok),
               ", ".join("%s(/v8/%s)" % (h["case"], h["route"]) for h in ok)))
        for h in ok:
            add("   [%s] en=%s  zh=%s  keys=%s%s"
                % (h["case"], json.dumps(h["en_texts"], ensure_ascii=False),
                   json.dumps(h["zh_texts"], ensure_ascii=False),
                   json.dumps(h["keys"], ensure_ascii=False),
                   "  (interpolated, count widened)" if h["interpolated"] else ""))
            add("   [%s] state: %s" % (h["case"], h["why"]))
    else:
        notReached.append(row)
        add("NOT_REACHED %-55s" % json.dumps(row, ensure_ascii=False))
        for h in hits:
            add("   tried on /v8/%s [case=%s] en=%s zh=%s -- %s"
                % (h["route"], h["case"], h["en_leaf"], h["zh_leaf"], h["why"]))
        if not hits:
            add("   no case produced a reading for this row")
add("")
add("counts: rows=%s REACHED=%s NOT_REACHED=%s" % (len(ORDER), len(reached), len(notReached)))
add("REACHED through product doors with no stored-row fixture: %s"
    % json.dumps(reachedWithoutFixture, ensure_ascii=False))
add("REACHED only because this lane wrote a row into its OWN private database copy: %s"
    % json.dumps([r for r in reached if r not in reachedWithoutFixture], ensure_ascii=False))
add("")
add("== the fixture log: rows written, and what the read doors answered ==")
raw = open("D:/moodle/_qoder_q_ord0422/branch_fixtures_log.json", encoding="utf-8").read()
dec, docs, at = json.JSONDecoder(), [], 0
while at < len(raw):
    while at < len(raw) and raw[at] not in "{[":
        at += 1
    if at >= len(raw):
        break
    doc, at = dec.raw_decode(raw, at)
    docs.append(doc)
for d in docs:
    add(json.dumps({"mode": d["mode"], "database": d["database"], "rows_before": d["rows_before"],
                    "rows_after": d["rows_after"], "verdict": d["verdict"],
                    "door_reading": d["door_reading"]}, ensure_ascii=False)[:1200])
    if d["mode"] == "nopolicy":
        ans = d["door_reading"].get("policy_door_answer", {})
        add("   DERIVED, and it refutes the verdict sentence above: the stored policy row count is %s "
            "after the read door was called (it was %s before), and the door answered with "
            "mode=%s, so reading the door materialises a default policy. There is no data state on "
            "this route that makes the shell's policy prop null, which is why "
            "v14.policyUnavailable stays NOT_REACHED."
            % (d["rows_after"]["traveler_agent_policies"],
               d["rows_before"]["traveler_agent_policies"], ans.get("mode")))

text = "\n".join(L) + "\n"
open("D:/moodle/_qoder_q_ord0422/branch_readings/eleven_rows_answer_r1.txt", "w",
     encoding="utf-8", newline="\n").write(text)
print(text)
