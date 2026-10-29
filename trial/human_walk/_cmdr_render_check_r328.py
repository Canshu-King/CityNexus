"""bw328: the sentence a panel writes is only a screen text if something renders it - does it?

#370 listed the 19 catch bodies that replace the server's refusal with their own Chinese sentence.  One
link is still open between that line of code and a traveller's eyes: the sentence has to be handed to a
state that some JSX actually reads.  For each of the 19, this ruler finds the setter whose call carries
that exact literal, derives the state it writes, and looks for a render site for that state - a JSX brace
expression or a conditional in front of one.

  RENDERED            at least one sentence in that body is handed to a state some markup reads
  SET_BUT_NOT_RENDERED every sentence is stored, and nothing in the file reads those states in a render
  NO_SETTER_FOR_TEXT  the body carries Chinese sentences but no setXxx(...) call contains any of them

Sentences are taken from the catch body itself, not from bw327's printed text, because that display joins
several literals with " / " and matching a joined string against a single call would report a rendered
sentence as unmatched - the first version of this ruler made exactly that mistake and read 2 rows as
NO_SETTER_FOR_TEXT.

A derived name is matched only inside `{...}` or as a condition, never as a bare word, because the first
version of this test used an alternation without a group and "message" matched every occurrence of the
word in the file, reporting 44 renders from one line of code.  Two controls and a negative control run
against this tree: the LiveRecovery message handler must read RENDERED, a text with no setter must not be
called rendered, and a state name nobody defines must produce zero render sites.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_button_reachability_r318 as reach  # noqa: E402
import _cmdr_panel_habit_r326 as habit  # noqa: E402  (owns bodies())
import _cmdr_sentence_shape_r327 as shape  # noqa: E402  (owns literals())

CJK = re.compile(r"[一-鿿]")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw328-is-that-sentence-on-screen.txt")
BW327_REL = "trial/results/20261026_gozero/bw327-what-the-panels-say-instead.txt"
ROW = re.compile(r"^\s{2}(\S+?):(\d+)\s+「(.+?)」")
SETTER_CALL = re.compile(r"\bset([A-Z]\w*)\s*\(([^;]*)\)?")


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    return io.open(path, encoding="utf-8", errors="replace").read()


def setter_for(text, body):
    """The state name a setXxx(...) call hands this exact sentence to, or None."""
    for match in SETTER_CALL.finditer(body):
        if ("'%s'" % text in match.group(2)) or ('"%s"' % text in match.group(2)) or (
                "`%s`" % text in match.group(2)):
            name = match.group(1)
            return name[0].lower() + name[1:]
    return None


def render_sites(source, name):
    """Lines where `name` is read inside a JSX brace expression or guards one."""
    pattern = re.compile(r"\{[^{}]*\b%s\b|\b%s\s*(&&|\?|\|\|)" % (re.escape(name), re.escape(name)))
    return [index + 1 for index, cell in enumerate(source.split("\n")) if pattern.search(cell)]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = dict(reach.source_files())
    rows = []
    unread = []
    for cell in read(BW327_REL).split("\n"):
        match = ROW.match(cell)
        if match:
            rows.append((match.group(1), int(match.group(2)), match.group(3)))
        elif cell.startswith("  frontend/") and "交state=" in cell:
            unread.append(cell)
    if not rows:
        raise SystemExit("ABORT bw327 lists no per-site rows, so there is nothing to check")
    says_zh = int(re.search(r"says_zh=(\d+)", read(BW327_REL)).group(1))
    if len(rows) != says_zh or unread:
        raise SystemExit("ABORT this ruler parsed %d of bw327's published %d rows and left these unread: %s "
                         "- a row that does not parse must never be dropped silently"
                         % (len(rows), says_zh, " || ".join(unread[:3]) or "(none unread)"))

    control_body = dict(habit.bodies("frontend/src/features/execution/LiveRecovery.tsx")).get(281, "")
    control_state = setter_for("无法记录这个选择，请刷新后重试。", control_body)
    control_sites = render_sites(files["frontend/src/features/execution/LiveRecovery.tsx"],
                                 control_state or "")
    if control_state != "message" or not control_sites:
        print("ABORT the known render case did not resolve: state=%r sites=%s"
              % (control_state, control_sites))
        return 7
    negative = render_sites(files["frontend/src/features/execution/LiveRecovery.tsx"],
                            "cmdrNoSuchStateAtAll")
    if negative:
        print("ABORT a state name defined nowhere still produced render sites, so the pattern is too "
              "loose")
        return 7

    out = ["IS THAT SENTENCE ON SCREEN bw328",
           "SAME-SOURCE CHECK rows read from bw327 = %d (the says_zh list of "
           "trial/results/20261026_gozero/bw327-what-the-panels-say-instead.txt)" % len(rows),
           "CONTROLS the LiveRecovery handler hands 「无法记录这个选择，请刷新后重试。」 to state %r, read at "
           "lines %s; a state name nobody defines yields %d render sites"
           % (control_state, ", ".join(str(line) for line in control_sites[:3]), len(negative))]
    counts = {"RENDERED": 0, "SET_BUT_NOT_RENDERED": 0, "NO_SETTER_FOR_TEXT": 0}
    for rel, line, shown in rows:
        body = dict(habit.bodies(rel)).get(line)
        if body is None:
            raise SystemExit("ABORT bw327 names a catch this ruler cannot re-read: %s:%d" % (rel, line))
        # the display string bw327 prints can join several literals with " / ", so matching against it
        # would call a rendered sentence unmatched; the literals are taken from the body instead
        found = []
        for text in [cell for cell in shape.literals(body) if CJK.search(cell)]:
            state = setter_for(text, body)
            if state is None:
                continue
            found.append((text, state, render_sites(files[rel], state)))
        if not found:
            verdict = "NO_SETTER_FOR_TEXT"
        elif any(sites for _, _, sites in found):
            verdict = "RENDERED"
        else:
            verdict = "SET_BUT_NOT_RENDERED"
        counts[verdict] += 1
        out.append("  %s:%d  %d 枚中文句子，%s → %s；%s"
                   % (rel, line, len([cell for cell in shape.literals(body) if CJK.search(cell)]),
                      shown[:26] + ("…" if len(shown) > 26 else ""), verdict,
                      "; ".join("「%s」state=%s 渲染点=%s"
                                % (text[:20], state, ", ".join(str(site) for site in sites[:2]) or "无")
                                for text, state, sites in found) or "该 body 里没有句子出现在 setXxx 调用内"))
    out.append("TALLY rows=%d rendered=%d set_but_not_rendered=%d no_setter_for_text=%d"
               % (len(rows), counts["RENDERED"], counts["SET_BUT_NOT_RENDERED"],
                  counts["NO_SETTER_FOR_TEXT"]))
    if sum(counts.values()) != len(rows):
        out.append("ABORT the verdicts do not cover every row")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 8
    out.append("COUNTING_RULE the setter is the setXxx(...) call whose own arguments contain this exact "
                "literal; its state name is the setter with the leading Set removed and the first letter "
                "lowered; a render site is a line where that name appears inside a {...} expression or as "
                "a && / || / ternary condition in front of one")
    out.append("COVERAGE_LIMIT a render site proves the state is read by markup, not that the traveller "
                "was looking at that panel when the failure happened, and a sentence can be rendered by a "
                "shared component that receives it as a prop - this ruler only follows the same-file state "
                "path. Nothing here was clicked.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for line in out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
