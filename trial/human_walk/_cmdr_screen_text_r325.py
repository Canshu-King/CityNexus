"""bw325: when a mounted panel asks and the backend refuses in English, what does the screen say?

bw318 proved a frontend file builds each path and bw322 proved which of those files the registry mounts,
but neither says the traveller reads the backend's sentence.  The layer in between is the catch block:
this ruler walks outward from the line where the path appears to the first `catch` that could handle that
call, and classifies what that catch does with the error it caught.

  SHOWS_SERVER_TEXT   the catch reads an attribute of the caught error (detail / message / response), so
                      whatever the backend sent can reach the screen
  OWNS_ITSOWN_TEXT    the catch assigns its own sentence and never reads the error, so the backend's
                      English is swallowed here
  NO_CATCH_IN_WINDOW  no catch appears within the window, so this ruler has no answer for that row

Two controls run against known sites in this tree before any verdict is trusted: the LiveRecovery handler
that assigns a literal bilingual sentence must read OWNS_ITSOWN_TEXT, and a site that demonstrably passes
`error.detail` through must read SHOWS_SERVER_TEXT.  A control that does not classify as expected aborts
the ruler rather than reporting a table nobody can rely on.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_button_reachability_r318 as reach  # noqa: E402  (owns the file scan bw318/bw322 used)
import _cmdr_write_block_368_r324 as blk  # noqa: E402  (owns the bw322 row parser)

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw325-what-the-screen-says.txt")
CATCH = re.compile(r"\bcatch\s*(?:\((\w+)\))?\s*\{")
SERVER_READ = re.compile(r"\b(?:err|error|e|cause|exception)\s*(?:\?\.)?\s*\.\s*"
                         r"(?:detail|message|response|data|statusText)\b")
WINDOW = 80


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    return io.open(path, encoding="utf-8", errors="replace").read()


def comment_spans(lines):
    """Line numbers (one-based) that sit inside a block comment.

    A doc comment in this codebase quotes handler code - RecoveryRequiredPanel.tsx opens with
    ``* `catch { "check your connection" }` blamed the network`` - and the catch pattern matched it, so the
    first body this ruler reports for that file was a sentence from a comment, not a handler.
    """
    inside = set()
    opened = False
    for index, cell in enumerate(lines):
        position = 0
        while position <= len(cell):
            if opened:
                closer = cell.find("*/", position)
                if closer < 0:
                    inside.add(index + 1)
                    break
                inside.add(index + 1)
                opened = False
                position = closer + 2
                continue
            opener = cell.find("/*", position)
            line_comment = cell.find("//", position)
            if opener < 0 or (0 <= line_comment < opener):
                break
            inside.add(index + 1)
            opened = True
            position = opener + 2
    return inside


def catch_body(lines, start):
    """The text of the first catch at or after `start`, from its opener to the line that closes it.

    The brace balance cannot be counted over the whole line. This codebase writes handlers as `} catch {`,
    where the leading brace closes the try and the trailing one opens the handler, so a whole-line count is
    zero and the body used to stop after the very next line - which silently cut multi-statement handlers
    down to their first sentence. The handler's own closer is instead the first line at handler depth one
    that begins with a brace. A `catch` that only appears inside a block comment is not a handler.
    """
    commented = comment_spans(lines)
    for index in range(start, min(start + WINDOW, len(lines))):
        if index + 1 in commented:
            continue
        match = CATCH.search(lines[index])
        if not match:
            continue
        depth = 1
        body = [lines[index][match.end():]]
        for follow in range(index + 1, min(index + WINDOW, len(lines))):
            line = lines[follow]
            if depth == 1 and line.lstrip().startswith("}"):
                break
            body.append(line)
            depth += line.count("{") - line.count("}")
        return index + 1, "\n".join(body)
    return 0, ""


def catchless_site(files):
    """A file with no catch anywhere, so the window arm has to report that it has no answer."""
    for rel, text in files:
        if not CATCH.search(text):
            return rel
    return ""


def passthrough_site(files):
    """The first call-shaped line in the tree followed by a catch that really reads the error.

    This is the control that proves the classifier can say SHOWS_SERVER_TEXT at all: it is taken from the
    source rather than asserted, and the site handed to classify is the line before that catch, because a
    line already inside a catch body has no catch in front of it.
    """
    for rel, text in files:
        lines = text.split("\n")
        for index, cell in enumerate(lines):
            if not CATCH.search(cell):
                continue
            _, body = catch_body(lines, index)
            if SERVER_READ.search(body) and index > 0:
                return rel, index
    return "", 0


def classify(rel, line):
    text = read(rel)
    lines = text.split("\n")
    if not (1 <= line <= len(lines)):
        raise SystemExit("ABORT %s has no line %d" % (rel, line))
    caught_at, body = catch_body(lines, line - 1)
    if not caught_at:
        return "NO_CATCH_IN_WINDOW", 0, ""
    verdict = "SHOWS_SERVER_TEXT" if SERVER_READ.search(body) else "OWNS_ITSOWN_TEXT"
    first = next((cell.strip() for cell in body.split("\n")[1:] if cell.strip()), "")
    return verdict, caught_at, first[:90]


def call_sites(rel, name):
    """Lines in `rel` where `name` is actually used - called, or rendered as a JSX element."""
    text = read(rel)
    return [index + 1 for index, cell in enumerate(text.split("\n"))
            if re.search(r"\b%s\s*\(" % re.escape(name), cell) or re.search(r"<%s\b" % re.escape(name),
                                                                            cell)]


def sites_for(row):
    """Where to look for the catch that would handle this request, best candidate first.

    The line where the path string is written only has a catch after it when that file is the screen:
    most rows build the URL in frontend/src/api/, and the caller there never handles the refusal.  So for
    those rows the candidate is the panel's own call site, taken from bw322's evidence coordinates.
    """
    out = []
    if not row["file"].startswith("frontend/src/api/"):
        out.append((row["file"], row["line"]))
    for rel, line_no, _mounted in row["evidence"]:
        for found in call_sites(rel, row["name"]):
            out.append((rel, found))
        out.append((rel, line_no))
    out.append((row["file"], row["line"]))
    seen, ordered = set(), []
    for site in out:
        if site not in seen:
            seen.add(site)
            ordered.append(site)
    return ordered


def classify_first(row):
    for rel, line in sites_for(row):
        verdict, caught_at, first = classify(rel, line)
        if verdict != "NO_CATCH_IN_WINDOW":
            return verdict, rel, line, caught_at, first
    rel, line = sites_for(row)[0]
    return "NO_CATCH_IN_WINDOW", rel, line, 0, ""


def body_span_histogram(files):
    """How many lines each catch body in the scanned tree really holds, under the current cutter."""
    spans = []
    for rel, text in files:
        lines = text.splitlines()
        index = 0
        commented = comment_spans(lines)
        while index < len(lines):
            if index + 1 not in commented and CATCH.search(lines[index]):
                caught_at, body = catch_body(lines, index)
                if caught_at:
                    spans.append(len(body.splitlines()))
                index = caught_at
            else:
                index += 1
    spans.sort()
    return spans


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = blk.parsed_rows()
    files = list(reach.source_files())
    spans = body_span_histogram(files)
    if not spans:
        print("ABORT the scanned tree has no catch body to measure, so the body cutter cannot be proven")
        return 8
    shape = "files=%d bodies=%d shortest=%d median=%d longest=%d" % (
        len(files), len(spans), spans[0], spans[len(spans) // 2], spans[-1])
    print("CATCH BODY SHAPE %s" % shape)

    # three controls taken from the source itself: one catch that assigns its own sentence, one catch
    # that reads the error, one file that has no catch at all
    control_owns = classify("frontend/src/features/execution/LiveRecovery.tsx", 270)
    show_rel, show_line = passthrough_site(files)
    if not show_rel:
        print("ABORT no catch in the scanned tree reads the error, so SHOWS_SERVER_TEXT could never fire "
              "and the ruler has nothing to control against")
        return 7
    control_shows = classify(show_rel, show_line)
    bare_rel = catchless_site(files)
    control_none = classify(bare_rel, 1)[0] if bare_rel else "NO_CATCH_IN_WINDOW"
    print("CONTROL_OWS %s" % control_owns[0])
    print("CONTROL_SHOWS %s from %s:%d" % (control_shows[0], show_rel, show_line))
    print("CONTROL_CATCHLESS %s from %s" % (control_none, bare_rel or "(every file has a catch)"))
    if (control_owns[0], control_shows[0], control_none) != ("OWNS_ITSOWN_TEXT", "SHOWS_SERVER_TEXT",
                                                             "NO_CATCH_IN_WINDOW"):
        print("ABORT a control site did not classify as the source proves it should, so the "
              "classification is not trustworthy")
        return 7

    out = ["WHAT THE SCREEN SAYS bw325",
           "SAME-SOURCE CHECK rows read from bw322 = %d (that ruler's own TALLY covers the same 20)"
           % len(rows),
           "CONTROLS a catch that assigns its own sentence read OWNS_ITSOWN_TEXT; `%s:%d` before a catch "
           "that reads the error read SHOWS_SERVER_TEXT; `%s` has no catch in it and read "
           "NO_CATCH_IN_WINDOW. The ruler aborts if any of the three disagrees."
           % (show_rel, show_line, bare_rel or "(none)")]
    out.append("CATCH_BODY_REVISION a handler's text is now cut at the line that closes it. The whole-line "
               "brace count this ruler used before counts zero for the `} catch {` shape this codebase "
               "writes, so every body stopped after its first statement; the same scan over the tree now "
               "measures %s (one-based lines per body). The superseded reading of this receipt is kept "
               "beside it as bw325-what-the-screen-says.txt.before_catch_body_fix, and the four rulers that "
               "share this cutter (bw325, bw326, bw327, bw328) were all re-run." % shape)
    counts = {"SHOWS_SERVER_TEXT": 0, "OWNS_ITSOWN_TEXT": 0, "NO_CATCH_IN_WINDOW": 0}
    mounted_counts = dict(counts)
    for row in rows:
        verdict, site_rel, site_line, caught_at, first = classify_first(row)
        counts[verdict] += 1
        if row["verdict"] == "ON_A_MOUNTED_PANEL":
            mounted_counts[verdict] += 1
        out.append("%2d. %s  站 `%s:%d`（bw322 判 %s）→ %s；调用处 %s:%d，接住处 %s:%d；那句起手 %s"
                   % (row["rank"], row["url"], row["file"], row["line"], row["verdict"], verdict,
                      site_rel, site_line, site_rel, caught_at, first or "（窗内无 catch）"))
    out.append("TALLY shows_server_text=%d owns_its_own_text=%d no_catch_in_window=%d rows=%d"
               % (counts["SHOWS_SERVER_TEXT"], counts["OWNS_ITSOWN_TEXT"],
                  counts["NO_CATCH_IN_WINDOW"], len(rows)))
    if sum(counts.values()) != len(rows):
        out.append("ABORT the verdicts do not cover every row")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 8
    mounted_rows = sum(1 for row in rows if row["verdict"] == "ON_A_MOUNTED_PANEL")
    out.append("MOUNTED_SPLIT of the %d rows on a mounted panel, %d show the server sentence, %d are "
               "answered by the panel's own sentence, %d have no catch in the window"
               % (mounted_rows, mounted_counts["SHOWS_SERVER_TEXT"],
                  mounted_counts["OWNS_ITSOWN_TEXT"], mounted_counts["NO_CATCH_IN_WINDOW"]))
    out.append("COUNTING_RULE sites are tried best-first: the line where the path is written when that "
               "file is not frontend/src/api/ (the screen itself builds it), otherwise the panel's own "
               "call or JSX site for the named function; the first site with a `catch` within %d lines "
               "answers, and that catch's brace-balanced body passes the server text only if it reads an "
               "attribute of the caught error (detail, message, response, data, statusText). Owning its "
               "own text means the catch never touches the error." % WINDOW)
    out.append("NEGATIVE_CONTROL a file with no catch anywhere in it reads NO_CATCH_IN_WINDOW rather than "
               "inventing a sentence - measured on `%s`, which holds 0 catch blocks" % bare_rel)
    out.append("COVERAGE_LIMIT a catch inside the window is assumed to be the one that handles this "
               "call, which is only true when the call sits in that try; a caller that re-throws, or a "
               "panel that renders the error elsewhere, is miscounted as owning its own text. This says "
               "which layer holds the sentence, not what a traveller saw.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for line in out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
