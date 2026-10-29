"""bw327: the 63 catch bodies that hide the refusal - what do they say instead, and does it go anywhere?

#369 established that the mounted panels almost never read the server's sentence.  The next question is
what the traveller gets instead, and whether that thing is a real answer or one stock phrase reused: this
ruler reads the same 64 catch bodies bw326 counted and classifies each on three independent axes, then
lists every Chinese sentence verbatim with its coordinate so "does it name the blocker" is a readable
question rather than one I invent a proxy for.

  says_zh / says_en_only / says_nothing   whether the body carries a Chinese literal, only English, none
  bilingual_shape                         the `zh ? "…" : "…"` shape the codebase uses
  into_state / into_console / nowhere     whether the sentence is handed to a setXxx(...) call, a
                                          console call, or neither
  retry_shaped                            contains 重试/再试/刷新/try again/refresh

The two axes are cross-checked both ways (zh-without-shape and shape-without-zh are each counted and
reported, because 19 == 19 is only meaningful if the reverse set is empty too), and the catch total is
required to equal bw326's published figure so the two rulers cannot describe different sets.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_button_reachability_r318 as reach  # noqa: E402
import _cmdr_panel_ask_r322 as panel  # noqa: E402  (owns the import-and-JSX mount test)
import _cmdr_panel_habit_r326 as habit  # noqa: E402  (owns bodies())
import _cmdr_screen_text_r325 as screen  # noqa: E402  (owns SERVER_READ)

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw327-what-the-panels-say-instead.txt")
BW326_REL = "trial/results/20261026_gozero/bw326-what-the-panels-do-with-a-refusal.txt"
CJK = re.compile(r"[一-鿿]")
BILINGUAL = re.compile(r"\bzh\s*\?")
SETTER = re.compile(r"\bset[A-Z]\w*\s*\(")
CONSOLE = re.compile(r"console\.\w+\s*\(")
RETRY = re.compile(r"重试|再试|刷新|try again|refresh", re.I)
STRING = re.compile(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|`((?:[^`\\]|\\.)*)`')


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    return io.open(path, encoding="utf-8", errors="replace").read()


def published_catch_total():
    """bw326's own TALLY, so this ruler cannot describe a different set than the one above it."""
    line = next((cell for cell in read(BW326_REL).split("\n")
                 if cell.startswith("TALLY panels=")), "")
    match = re.search(r"catch=(\d+)", line)
    if not match:
        raise SystemExit("ABORT bw326 publishes no readable catch total")
    return int(match.group(1))


def literals(body):
    out = []
    for match in STRING.finditer(body):
        text = next((group for group in match.groups() if group is not None), "")
        if len(text.strip()) >= 4:
            out.append(text.strip())
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = dict(reach.source_files())
    mounted_keys, imported_modules, rendered_tags = panel.registry_panels(files[panel.REGISTRY_REL])
    expected = published_catch_total()

    rows = []
    for key in sorted(mounted_keys):
        candidates = [rel for rel in files if rel.split("src/", 1)[-1].rsplit(".", 1)[0] == key]
        if not candidates:
            raise SystemExit("ABORT a mounted module has no scanned file behind it: %s" % key)
        rel = candidates[0]
        for line, body in habit.bodies(rel):
            zh = any(CJK.search(text) for text in literals(body))
            en_only = (not zh) and bool(literals(body))
            reads = bool(screen.SERVER_READ.search(body))
            rows.append({"rel": rel, "line": line, "zh": zh, "en_only": en_only,
                         "says_nothing": not literals(body), "shape": bool(BILINGUAL.search(body)),
                         "state": bool(SETTER.search(body)), "console": bool(CONSOLE.search(body)),
                         "retry": bool(RETRY.search(body)), "reads": reads,
                         "sentences": [text for text in literals(body) if CJK.search(text)]})
    total = len(rows)
    if total != expected:
        raise SystemExit("ABORT this ruler read %d catch bodies against bw326's published %d"
                         % (total, expected))

    zh = sum(1 for item in rows if item["zh"])
    shape = sum(1 for item in rows if item["shape"])
    state = sum(1 for item in rows if item["state"])
    console = sum(1 for item in rows if item["console"])
    nowhere = sum(1 for item in rows if not item["state"] and not item["console"])
    retry = sum(1 for item in rows if item["retry"])
    en_only = sum(1 for item in rows if item["en_only"])
    says_nothing = sum(1 for item in rows if item["says_nothing"])
    zh_no_shape = sum(1 for item in rows if item["zh"] and not item["shape"])
    shape_no_zh = sum(1 for item in rows if item["shape"] and not item["zh"])
    if zh + en_only + says_nothing != total:
        raise SystemExit("ABORT the three sentence axes do not cover every body")
    if state + console - sum(1 for item in rows if item["state"] and item["console"]) + nowhere != total:
        raise SystemExit("ABORT the destination axes do not cover every body")

    sentences = {}
    for item in rows:
        for text in item["sentences"]:
            sentences.setdefault(text, []).append("%s:%d" % (item["rel"], item["line"]))
    repeated = sorted(((len(where), text, where) for text, where in sentences.items()), reverse=True)
    distinct = len(sentences)
    stocked = sum(count for count, _, _ in repeated if count > 1)

    control = next((item for item in rows
                    if item["rel"].endswith("LiveRecovery.tsx") and item["line"] == 281), None)
    if not control or not (control["zh"] and control["shape"] and control["state"] and control["retry"]):
        print("ABORT the known bilingual-sentence site did not read as zh + shape + into_state + retry, "
              "so these axes are not measuring what the source shows")
        return 7
    control_none = next((item for item in rows if item["says_nothing"] and not item["state"]
                         and not item["console"]), None)

    out = ["WHAT THE PANELS SAY INSTEAD bw327",
           "SAME-SOURCE CHECK catch bodies read here = %d, equal to bw326's published catch=%d (the %d "
           "mounted files of trial/results/20261026_gozero/bw326-what-the-panels-do-with-a-refusal.txt:28)"
           % (total, expected, len(mounted_keys)),
           "TALLY catch=%d says_zh=%d says_en_only=%d says_nothing=%d bilingual_shape=%d into_state=%d "
           "into_console=%d nowhere=%d retry_shaped=%d reads_the_error=%d"
           % (total, zh, en_only, says_nothing, shape, state, console, nowhere, retry,
              sum(1 for item in rows if item["reads"])),
           "REVERSE_CHECK zh-without-the-`zh ?`-shape = %d and shape-without-any-Chinese = %d; the two "
           "counts above being equal is only meaningful because both reverse sets read %s"
           % (zh_no_shape, shape_no_zh,
              "empty" if zh_no_shape == 0 and shape_no_zh == 0 else "NOT empty - the axes differ"),
           "SENTENCE_DISTINCT %d different Chinese sentences across %d occurrences; %d of those "
               "occurrences are a sentence already used somewhere else, so the same words are re-asked "
               "rather than re-answered per failure"
           % (distinct, sum(len(where) for _, where in sentences.items()), stocked),
           "MOST_REUSED %s" % ("; ".join("%d 处 · %s（首见 %s）" % (count, text[:40], where[0])
                                          for count, text, where in repeated[:5] if count > 1)
                               or "no sentence is reused"),
    ]
    for count, text, where in repeated[:12]:
        out.append("  「%s」 出现在 %d 处：%s" % (text[:70], count, ", ".join(where[:3])))
    out.append("CONTROLS the LiveRecovery handler at `frontend/src/features/execution/LiveRecovery.tsx:281` "
               "read as Chinese + `zh ?` shape + into_state + retry-shaped (the ruler aborts otherwise); "
               "%s" % ("a body with no literal at all and no setter read as says_nothing + nowhere, as "
                       "the axes claim" if control_none else
                       "no body in this set reads as says_nothing, so that class is untested here"))
    out.append("COUNTING_RULE a body says_zh when it carries a string literal with at least one CJK "
                "character; bilingual_shape is the `zh ?` conditional; into_state means a setXxx(...) call "
                "appears in the same body, into_console a console.* call; retry_shaped matches "
                "重试/再试/刷新/try again/refresh")
    out.append("COVERAGE_LIMIT into_state proves the sentence reaches component state, not that anything "
               "renders it, and a body can hold both a state setter and an unrelated literal. Whether a "
               "sentence names the actual blocker is left to the sentences printed above - this ruler does "
               "not proxy that judgement with a keyword test.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for line in out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
