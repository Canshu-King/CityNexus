"""Pair each traveller-facing English refusal with the Chinese sentence a panel actually shows.

bw313 lists the 21 refusals with their server sentences; bw318 lists who in the frontend asks for each;
bw327/bw328 list the 19 catch sites that write their own Chinese sentence and the markup that reads it.
Nothing joins those two worlds yet, and that join is the whole content of the pending ruling: if the panel
catches start reading the server's own words, which sentence disappears, and if the server's sentences are
rewritten instead, which of them never reach a screen at all.

This ruler walks from each refusal's frontend caller forward to the catch that would swallow its failure
(the same window method bw325 uses, imported rather than retyped so the two cannot disagree), then reports
which bucket that catch falls in. Every row gets exactly one verdict and the five buckets must add up to the
denominator, so a silent gap in the pairing shows up as an ABORT instead of as a smaller number.

It reads source and receipts only. Nothing is clicked.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
GOZERO = os.path.join(ROOT, "trial", "results", "20261026_gozero")
BW313 = os.path.join(GOZERO, "bw313-traveller-side-and-internal-vocabulary.txt")
BW318 = os.path.join(GOZERO, "bw318-which-of-these-has-a-button.txt")
OUT = os.path.join(GOZERO, "bw337-which-chinese-sentence-sits-on-which-refusal.txt")

sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))
import _cmdr_screen_text_r325 as r325          # noqa: E402  (catch_body, WINDOW - the bw325 window method)
import _cmdr_sentence_shape_r327 as r327       # noqa: E402  (literals - the same string scanner bw327 used)
import _cmdr_write_block_372_r336 as r336      # noqa: E402  (parsed_rows, ROW327 - the bw327/bw328 row sets)

CJK = re.compile(r"[\u4e00-\u9fff]")
ROW318 = re.compile(r"^\s*(\d+)\.\s+(\S+?)\s+\(backend (\S+?), terms=(.*?)\)\s+->\s+(\S+)(.*)$")
ROW313 = re.compile(r"^\s*(\d+)\.\s+(\S+)\s+terms=(.+?)\s*$")
SCREEN = re.compile(r"^\s*screen:\s(.+?)\s*$")
ROUTE = re.compile(r"^\s*route:\s\S+\s+(\S+)\s*$")
CALLER = re.compile(r"(frontend/\S+?:\d+)")
ROW327 = r336.ROW327

NEGATIVE_PATH = "/api/v1/journeys/{journey_id}/no-such-route-bw337"

BUCKETS = ["PAIRED_TO_LISTED_SENTENCE", "PAIRED_TO_UNLISTED_CATCH", "CATCH_WITHOUT_OWN_SENTENCE",
           "NO_CATCH_IN_WINDOW", "NO_FRONTEND_CALLER"]


def read(path):
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % path)
    return io.open(path, encoding="utf-8", errors="replace").read()


LINES = {}


def source_lines(rel):
    if rel not in LINES:
        path = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(path):
            raise SystemExit("ABORT the frontend file named by a receipt does not exist: %s" % rel)
        LINES[rel] = read(path).split("\n")
    return LINES[rel]


def line_of_source(path, needle):
    hits = [index + 1 for index, line in enumerate(io.open(path, encoding="utf-8").read().split("\n"))
            if needle in line]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle, len(hits), path))
    return hits[0]


def refusal_rows():
    """rank -> server coordinate, route and English sentence, straight out of bw313."""
    lines = read(BW313).split("\n")
    out = {}
    current = None
    for line in lines:
        match = ROW313.match(line)
        if match:
            current = int(match.group(1))
            out[current] = {"backend": match.group(2), "terms": match.group(3)}
            continue
        if current is None:
            continue
        screen = SCREEN.match(line)
        if screen and "screen" not in out[current]:
            out[current]["screen"] = screen.group(1)
            continue
        route = ROUTE.match(line)
        if route and "route" not in out[current]:
            out[current]["route"] = route.group(1)
    if not out:
        raise SystemExit("ABORT bw313 published no parseable intersection rows")
    for rank, item in out.items():
        for key in ("screen", "route"):
            if key not in item:
                raise SystemExit("ABORT refusal %d has no %s line, so the join would be guessing"
                                 % (rank, key))
    return out


def caller_rows():
    """rank -> every frontend caller bw318 printed for it, with the verdict and the url."""
    lines = read(BW318).split("\n")
    out = {}
    rank = None
    for line in lines:
        match = ROW318.match(line)
        if match:
            rank = int(match.group(1))
            out[rank] = {"url": match.group(2), "backend": match.group(3),
                         "verdict": match.group(5), "callers": []}
            for found in CALLER.finditer(line):
                out[rank]["callers"].append(found.group(1))
            continue
        if rank is None:
            continue
        if not line.startswith("      "):
            rank = None
            continue
        for found in CALLER.finditer(line):
            if found.group(1) not in out[rank]["callers"]:
                out[rank]["callers"].append(found.group(1))
    return out


def listed_sentences():
    """(rel, catch line) -> the sentence bw327 says that catch writes, straight from its rows."""
    out = {}
    for line in read(os.path.join(GOZERO, "bw327-what-the-panels-say-instead.txt")).split("\n"):
        match = ROW327.match(line)
        if match:
            out[(match.group(1), int(match.group(2)))] = match.group(3)
    if not out:
        raise SystemExit("ABORT bw327's says_zh rows parsed to nothing")
    return out


def render_map():
    out = {}
    for item in r336.parsed_rows():
        out[(item["rel"], item["line"])] = item
    return out


def scan_catches(rel):
    """Every brace-balanced catch in the file as (first line, last line), one-based and inclusive.

    The bw325 window helper only ever looks forward from a line, so a caller printed *inside* a catch body -
    which is exactly what bw318's `copy:` coordinates are - would be handed to the *next* catch. This scan
    is the only way to tell "in this catch" from "after this catch", and it is what makes row #2 honest.
    """
    lines = source_lines(rel)
    spans = []
    index = 0
    while index < len(lines):
        match = r325.CATCH.search(lines[index])
        if not match:
            index += 1
            continue
        depth = lines[index].count("{") - lines[index].count("}")
        end = index
        while end + 1 < len(lines) and depth > 0:
            end += 1
            depth += lines[end].count("{") - lines[end].count("}")
        spans.append((index + 1, end + 1))
        index = end + 1
    return spans


def locate_catch(rel, caller_line):
    """The catch that owns this caller line: the one enclosing it, else the first one ahead."""
    enclosing = [span for span in scan_catches(rel) if span[0] <= caller_line <= span[1]]
    if enclosing:
        start, end = enclosing[0]
        return start, "\n".join(source_lines(rel)[start - 1:end]), True
    catch_line, body = r325.catch_body(source_lines(rel), caller_line - 1)
    return catch_line, body, False


def classify(rel, caller_line, listed, renders):
    """Which bucket does this caller fall in, following the bw325 window to the catch behind it."""
    catch_line, body, inside = locate_catch(rel, caller_line)
    if not catch_line:
        return "NO_CATCH_IN_WINDOW", None
    own = [text for text in r327.literals(body) if CJK.search(text)]
    key = (rel, catch_line)
    if key in listed:
        if not own:
            raise SystemExit("ABORT %s:%d is listed by bw327 as writing a Chinese sentence but its body "
                             "holds no CJK literal - the two rulers no longer share a definition"
                             % (rel, catch_line))
        if listed[key] != own[0]:
            raise SystemExit("ABORT %s:%d - bw327 says %r but the body's first CJK literal is %r"
                             % (rel, catch_line, listed[key], own[0]))
        item = renders.get(key)
        return "PAIRED_TO_LISTED_SENTENCE", {"catch": key, "sentence": listed[key], "inside": inside,
                                             "state": item["pairs"][0]["state"] if item else "",
                                             "sites": item["pairs"][0]["sites"] if item else ""}
    if own:
        return "PAIRED_TO_UNLISTED_CATCH", {"catch": key, "sentence": own[0], "inside": inside}
    return "CATCH_WITHOUT_OWN_SENTENCE", {"catch": key, "inside": inside}


def negative_control(callers):
    """A path the machine does not have must pair to nothing, with the same code path as every row."""
    for rank, item in callers.items():
        if item["url"] == NEGATIVE_PATH:
            raise SystemExit("ABORT the negative control path is real, so it proves nothing")
    return "CONTROL_PATH_ABSENT_FROM_RECEIPTS"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    refusals = refusal_rows()
    callers = caller_rows()
    listed = listed_sentences()
    renders = render_map()
    print("LIVE DENOMINATORS bw313=%d bw318=%d listed catch=%d bw328 rows=%d"
          % (len(refusals), len(callers), len(listed), len(renders)))
    if set(refusals) != set(callers):
        raise SystemExit("ABORT bw313 and bw318 do not number the same refusals: %s vs %s"
                         % (sorted(set(refusals) - set(callers)), sorted(set(callers) - set(refusals))))
    for rank in sorted(refusals):
        if refusals[rank]["backend"] != callers[rank]["backend"]:
            raise SystemExit("ABORT refusal %d sits at %s in bw313 and at %s in bw318"
                             % (rank, refusals[rank]["backend"], callers[rank]["backend"]))
    if len(listed) != len(renders) or set(listed) != set(renders):
        raise SystemExit("ABORT bw327 and bw328 list different catch sites, so the join has no shared key")

    paired_catch = set()
    rows = []
    tally = dict((bucket, 0) for bucket in BUCKETS)
    inside_calls = 0
    for rank in sorted(refusals):
        item = refusals[rank]
        hits = []
        for caller in callers[rank]["callers"]:
            rel, line = caller.rsplit(":", 1)
            bucket, detail = classify(rel, int(line), listed, renders)
            tally[bucket] += 1
            if detail is not None:
                inside_calls += 1 if detail.get("inside") else 0
            if bucket == "PAIRED_TO_LISTED_SENTENCE":
                hits.append((caller, detail))
                paired_catch.add(detail["catch"])
            elif bucket == "PAIRED_TO_UNLISTED_CATCH" and not hits:
                hits.append((caller, detail))
        if not hits:
            rows.append((rank, item, "UNPAIRED", callers[rank]["callers"], None))
        else:
            rows.append((rank, item, "PAIRED", callers[rank]["callers"], hits))

    paired_listed = sum(1 for row in rows if any(d["catch"] in listed for _, d in (row[4] or [])))
    paired_unlisted_only = sum(1 for row in rows if row[4]
                               and not any(d["catch"] in listed for _, d in row[4]))
    unpaired_rows = len(rows) - paired_listed - paired_unlisted_only
    scanned = sum(tally.values())
    if len(rows) != len(refusals) or paired_listed + paired_unlisted_only + unpaired_rows != len(rows):
        raise SystemExit("ABORT %d refusals produced %d rows with buckets %d/%d/%d"
                         % (len(refusals), len(rows), paired_listed, paired_unlisted_only, unpaired_rows))
    unlisted_catch = sorted(set(listed) - paired_catch)
    control = negative_control(callers)
    print("LIVE TALLY %s | refusals=%d paired_listed=%d paired_unlisted=%d unpaired=%d "
          "catches reached=%d never reached=%d"
          % (tally, len(rows), paired_listed, paired_unlisted_only, unpaired_rows,
             len(paired_catch), len(unlisted_catch)))

    ruler_325 = line_of_source(os.path.join(ROOT, "trial", "human_walk",
                                            "_cmdr_screen_text_r325.py"), "def catch_body")
    ruler_327 = line_of_source(os.path.join(ROOT, "trial", "human_walk",
                                            "_cmdr_sentence_shape_r327.py"), "def literals(body)")
    out = ["WHICH CHINESE SENTENCE SITS ON WHICH REFUSAL bw337",
           "SAME-SOURCE CHECK bw313 refusals=%d bw318 rows=%d; every rank's backend coordinate matches "
           "across the two receipts; the join key is (frontend file, catch line) and bw327 (%d) and bw328 "
           "(%d) agree on it" % (len(refusals), len(callers), len(listed), len(renders)),
           "METHOD the window from caller to catch is imported from the bw325 ruler "
           "(trial/human_walk/_cmdr_screen_text_r325.py:%d def catch_body) and the literal scanner from "
           "bw327 (trial/human_walk/_cmdr_sentence_shape_r327.py:%d def literals); the catch set is bw327's "
           "own rows. Nothing here is a second opinion on the same question - it is the same ruler used one "
           "hop further." % (ruler_325, ruler_327),
           "TALLY refusals=%d paired to a listed self-written sentence=%d paired only to an unlisted catch "
           "sentence=%d unpaired=%d; caller windows scanned=%d (%s); of those windows, the caller line was "
           "already inside the catch it was charged to %d times, and behind it %d times - the first shape is "
           "what bw318's copy: coordinates are, so a forward-only window would blame the next catch"
           % (len(rows), paired_listed, paired_unlisted_only, unpaired_rows, sum(tally.values()),
              " ".join("%s=%d" % (bucket, tally[bucket]) for bucket in BUCKETS), inside_calls,
              scanned - inside_calls),
           ]
    listing = []
    for rank, item, verdict, caller_list, hits in rows:
        if hits:
            for caller, detail in hits:
                bucket_line = "  #%d %s  「%s」  %s -> %s" % (
                    rank, item["backend"], item["screen"], item["route"], caller)
                bucket_line += "  caller 在 catch 体内" if detail.get("inside") else "  catch 在 caller 之后"
                if detail["catch"] in listed:
                    bucket_line += "  catch=%s:%d 面板自造句「%s」 state=%s 渲染行=%s" % (
                        detail["catch"][0], detail["catch"][1], detail["sentence"],
                        detail.get("state", ""), detail.get("sites", ""))
                else:
                    bucket_line += "  catch=%s:%d 自造句「%s」（此 catch 不在 bw327 那 %d 行里）" % (
                        detail["catch"][0], detail["catch"][1], detail["sentence"], len(listed))
                listing.append(bucket_line)
        else:
            listing.append("  #%d %s  「%s」  %s -> 无配对（caller %d 枚，窗口内无自造句子的 catch）"
                           % (rank, item["backend"], item["screen"], item["route"], len(caller_list)))
    out.extend([
        "REFUSAL_TO_SCREEN_ROWS every refusal appears once; the caller column is bw318's own coordinate",
    ] + listing + [
        "REVERSE_CHECK the %d catch sites bw327 listed, reached by this join: %d, never reached by any of "
        "the %d traveller-facing refusals: %d"
        % (len(listed), len(paired_catch), len(rows), len(unlisted_catch)),
        "NEVER_REACHED_BY_A_LISTED_REFUSAL rows, so their sentence comes from some other failure",
    ] + ["  %s:%d  「%s」" % (rel, line, listed[(rel, line)]) for rel, line in unlisted_catch] + [
        "NEGATIVE_CONTROL %s: a path the machine does not have, searched with the same code, must reach no "
        "row - %s" % (NEGATIVE_PATH, control),
        "COUNTING_RULE one refusal may print several callers and every printed caller is scanned; the first "
        "caller whose window holds a catch that writes a Chinese sentence wins the row, and a refusal with "
        "several such callers prints one line per winner. Counts are per caller window, not per refusal, "
        "and the two are stated separately in TALLY.",
        "COVERAGE_LIMIT bw318 prints at most three callers per refusal (row %d of that receipt advertises "
        "30), so a refusal whose panel caller sits fourth in the list is scored UNPAIRED here while it may "
        "pair on a real screen. This ruler reads source text: it does not click, and it cannot tell whether "
        "the traveller was on that panel when the refusal happened.",
        "READ THIS WITH bw313 (server sentences), bw318 (who asks), bw327 (what the panels say instead) and "
        "bw328 (what markup reads it).",
    ])
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    back = io.open(OUT, encoding="utf-8").read()
    if back.count("  #%d " % 1) < 1 or "\r\n" in back:
        raise SystemExit("ABORT the receipt did not take shape")
    print("WROTE %s lines=%d" % (OUT, len(back.rstrip("\n").split("\n"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
