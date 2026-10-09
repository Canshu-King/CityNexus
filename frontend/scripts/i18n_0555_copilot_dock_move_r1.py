"""ORD-0555 mover: carry inline bilingual pairs out of CopilotDock.tsx into LocaleContext.

Nothing here re-types a screen string: every zh/en value is read off the source line
itself, so a typo in this file cannot reach the dictionary.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "frontend", "src", "features", "agent", "CopilotDock.tsx")
DICT = os.path.join(ROOT, "frontend", "src", "i18n", "LocaleContext.tsx")
OUT = os.path.join(ROOT, "frontend", "scripts", "i18n_0555_copilot_dock_move_evidence_r1.json")

BASE_TIP = "8bc584613cc5fb047453f497b2152f8ab5102ca9"

# (base-tip line number, key name proposed by the commander's ORD-0555 table)
ITEMS = [
    (242, "agent.aRuntimeEventCouldNotBeRead"),
    (253, "agent.reconnectingToRuntimeEvents"),
    (256, "agent.eventStreamUnavailableReceivedEventsArePreserved"),
    (357, "agent.stopping"),
    (361, "agent.stoppedThroughCityNexus"),
    (371, "agent.approvalIsDisabledWhileOffline"),
    (375, "agent.cityNexusApprovalIdIsNotAvailableReviewInRecovery"),
    (378, "agent.recordingCityNexusApproval"),
    (381, "agent.approvalRecordedCityNexusStillOwnsExecutionAuthorization"),
    (393, "agent.workingOnYourRequest"),
    (396, "agent.ranAgainstYourJourneyFacts"),
    (397, "agent.checkingYourJourneyFacts"),
    (406, "agent.checkingYourJourneyFacts2"),
    (427, "agent.viewSafeMissionPlan"),
    (432, "agent.cityNexusAuthority"),
    (440, "agent.suggestionsProtectedPlans"),
    (443, "agent.aSuggestionIsReadyOpenAdvancedDetailToSeeHowItWasProduced"),
    (444, "agent.thereIsNothingForYouToDecideYet"),
    (448, "agent.protectedCommitment"),
    (451, "agent.protectedActivity"),
    (465, "agent.approve"),
    (466, "agent.reject"),
    (467, "agent.modifyReview"),
    (477, "agent.stopMission"),
]

PAIR = re.compile(r'zh \? "((?:[^"\\]|\\.)*)" : "((?:[^"\\]|\\.)*)"')
EN_ANCHOR = '  "agent.runtimeDetails": "Runtime details",\n'
ZH_ANCHOR = '  "agent.runtimeDetails": "\u8fd0\u884c\u8be6\u60c5",\n'


def die(reason):
    sys.stdout.write("ABORT: " + reason + "\n")
    sys.exit(3)


def main():
    src_text = open(SRC, encoding="utf-8").read()
    if "\r" in src_text:
        die("CopilotDock.tsx carries CR bytes, expected pure LF")
    lines = src_text.split("\n")

    rows = []
    for base_line, key in ITEMS:
        idx = base_line - 1
        if idx >= len(lines):
            die("line %d is past end of file" % base_line)
        before = lines[idx]
        found = list(PAIR.finditer(before))
        if len(found) != 1:
            die("line %d holds %d bilingual pairs, expected one" % (base_line, len(found)))
        m = found[0]
        zh_text, en_text = m.group(1), m.group(2)
        after = before[: m.start()] + 't("%s")' % key + before[m.end():]
        if "zh ?" in after:
            die("line %d still reads zh ? after the swap" % base_line)
        if 't("%s")' % key not in after:
            die("line %d does not read the new key" % base_line)
        lines[idx] = after
        rows.append(
            {
                "key": key,
                "base_line": base_line,
                "new_line": base_line,
                "zh": zh_text,
                "en": en_text,
                "before": before.strip(),
                "after": after.strip(),
            }
        )

    seen = {}
    for row in rows:
        if row["key"] in seen:
            die("duplicate key in the move table: " + row["key"])
        seen[row["key"]] = True

    open(SRC, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    dict_text = open(DICT, encoding="utf-8").read()
    if "\r" in dict_text:
        die("LocaleContext.tsx carries CR bytes, expected pure LF")
    if dict_text.count(EN_ANCHOR) != 1 or dict_text.count(ZH_ANCHOR) != 1:
        die("dictionary anchor not unique: en=%d zh=%d"
            % (dict_text.count(EN_ANCHOR), dict_text.count(ZH_ANCHOR)))
    en_start = dict_text.index("const en: Dict = {")
    zh_start = dict_text.index("const zhCN: Dict = {")
    if not (en_start < dict_text.index(EN_ANCHOR, en_start) < zh_start
            and dict_text.index(ZH_ANCHOR, zh_start) < dict_text.index("const dictionaries")):
        die("anchors are not inside their own dictionary block")

    def block(rows_, side):
        out = []
        for row in rows_:
            out.append('  "%s": "%s",\n' % (row["key"], row[side]))
        return "".join(out)

    dict_text = dict_text.replace(EN_ANCHOR, EN_ANCHOR + block(rows, "en"), 1)
    dict_text = dict_text.replace(ZH_ANCHOR, ZH_ANCHOR + block(rows, "zh"), 1)
    open(DICT, "w", encoding="utf-8", newline="\n").write(dict_text)

    new_dict = open(DICT, encoding="utf-8").read().split("\n")
    for row in rows:
        hits = [n + 1 for n, ln in enumerate(new_dict) if ln == '  "%s": ' % row["key"] + '"%s",' % row["en"]]
        row["dict_en_line"] = hits[0] if hits else die("en entry not found for " + row["key"])
        hits = [n + 1 for n, ln in enumerate(new_dict) if ln == '  "%s": ' % row["key"] + '"%s",' % row["zh"]]
        row["dict_zh_line"] = hits[0] if hits else die("zh entry not found for " + row["key"])

    new_src = open(SRC, encoding="utf-8").read().split("\n")
    for row in rows:
        hits = [n + 1 for n, ln in enumerate(new_src) if ('t("%s")' % row["key"]) in ln]
        if len(hits) != 1:
            die("site for %s found %d times in the rewritten source" % (row["key"], len(hits)))
        row["new_line"] = hits[0]

    json.dump(
        {"base_tip": BASE_TIP, "items": rows, "moved": len(rows)},
        open(OUT, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )
    sys.stdout.write("MOVED %d pairs, evidence at %s\n" % (len(rows), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
