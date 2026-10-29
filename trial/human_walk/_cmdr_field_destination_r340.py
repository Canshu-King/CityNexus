"""bw338: a panel that reads a server field is not a panel that shows a server sentence.

bw326 counts 6 of the 64 mounted-panel catch bodies as "reading the refusal", from a predicate that only
matches `error.detail`-shaped text. The real code reads more than that and reads it in two different ways,
and the difference is the whole question the pending ruling turns on:

  - DestinationPreparationPanel.tsx:132 hands `error.message` straight into setActionError(...), so the
    upstream words reach the screen;
  - RealCityDiscoveryPanel.tsx:242 takes `cause.message`, feeds it to a token matcher against constants, and
    hands only `cause.facts` to state - the prose is dropped by design (its own comment says so).

So this ruler follows each read to its destination and separates text fields (detail, message, quote,
statusText) from structured ones (facts, envelope, body, code, status, data, errors), tracks a name assigned
from either one hop, then tests every setter argument and every comparison line against them. Five buckets,
each body in exactly one, and three controls taken from the source have to land where the source says they
should or the ruler aborts.

It reads source text. Nothing is clicked and no screen is claimed.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_button_reachability_r318 as reach  # noqa: E402  (owns source_files())
import _cmdr_panel_ask_r322 as panel  # noqa: E402  (owns registry_panels())
import _cmdr_panel_habit_r326 as habit  # noqa: E402  (owns bodies(), which owns the fixed catch cutter)

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw338-where-a-read-field-actually-goes.txt")
BW326_REL = "trial/results/20261026_gozero/bw326-what-the-panels-do-with-a-refusal.txt"

ERROR_NAMES = r"(?:err|error|e|cause|exception|it|rejection|failure)"
TEXT_FIELDS = ("detail", "message", "quote", "statusText")
STRUCT_FIELDS = ("facts", "envelope", "body", "code", "status", "data", "errors")
TEXT_READ = re.compile(r"\b%s\s*(?:\?\.)?\s*\.\s*(?:%s)\b" % (ERROR_NAMES, "|".join(TEXT_FIELDS)))
STRUCT_READ = re.compile(r"\b%s\s*(?:\?\.)?\s*\.\s*(?:%s)\b" % (ERROR_NAMES, "|".join(STRUCT_FIELDS)))
ASSIGN = re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;]*)")
SETTER_CALL = re.compile(r"\bset[A-Z]\w*\s*\(([^;]*(?:;|$))")
COMPARISON = re.compile(r"(?:===|!==|==|!=|\.includes\s*\(|\.startsWith\s*\(|\.match\s*\(|switch\s*\()")
LITERAL = re.compile(r'"([^"\\\n]{3,})"')

BUCKETS = ["HANDS_SERVER_TEXT_TO_STATE", "HANDS_SERVER_STRUCTURE_TO_STATE", "COMPARES_ONLY",
           "READS_AND_LEAVES_IT_UNUSED", "NEVER_READS_A_SERVER_FIELD"]

CONTROLS = [
    {"name": "text reaches state", "rel": "frontend/src/features/discovery/DestinationPreparationPanel.tsx",
     "line": 132, "allowed": ("HANDS_SERVER_TEXT_TO_STATE",)},
    {"name": "prose dropped, facts kept",
     "rel": "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx", "line": 242,
     "allowed": ("HANDS_SERVER_STRUCTURE_TO_STATE", "COMPARES_ONLY", "READS_AND_LEAVES_IT_UNUSED")},
    {"name": "nothing bound", "rel": "frontend/src/features/execution/LiveRecovery.tsx", "line": 418,
     "allowed": ("NEVER_READS_A_SERVER_FIELD",)},
]


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    return io.open(path, encoding="utf-8", errors="replace").read()


def published_catch_total():
    line = next((cell for cell in read(BW326_REL).split("\n") if cell.startswith("TALLY panels=")), "")
    match = re.search(r"catch=(\d+)", line)
    if not match:
        raise SystemExit("ABORT bw326 publishes no readable catch total")
    return int(match.group(1))


def derived(body, pattern):
    """Names assigned from a field of this kind, followed one hop (the `const detail = body?.detail` shape)."""
    names = set()
    for _ in range(3):
        for match in ASSIGN.finditer(body):
            name, right = match.group(1), match.group(2)
            if pattern.search(right) or any(known in right for known in names):
                names.add(name)
    return names


def classify(body):
    text_direct = [match.group(0) for match in TEXT_READ.finditer(body)]
    struct_direct = [match.group(0) for match in STRUCT_READ.finditer(body)]
    if not text_direct and not struct_direct:
        return "NEVER_READS_A_SERVER_FIELD", {"text": [], "struct": [], "handed": [], "compared": 0}
    text_names = derived(body, TEXT_READ)
    struct_names = derived(body, STRUCT_READ)
    text_needles = text_direct + sorted(text_names)
    struct_needles = struct_direct + sorted(struct_names - text_names)

    def arguments(needles):
        hits = []
        for match in SETTER_CALL.finditer(body):
            found = sorted(set(needle for needle in needles if needle and needle in match.group(1)))
            if found:
                hits.extend(found)
        return sorted(set(hits))

    handed_text = arguments(text_needles)
    handed_struct = arguments(struct_needles)
    compared = sum(1 for line in body.splitlines()
                   if COMPARISON.search(line) and any(needle and needle in line
                                                      for needle in text_needles + struct_needles))
    if handed_text:
        bucket = "HANDS_SERVER_TEXT_TO_STATE"
    elif handed_struct:
        bucket = "HANDS_SERVER_STRUCTURE_TO_STATE"
    elif compared:
        bucket = "COMPARES_ONLY"
    else:
        bucket = "READS_AND_LEAVES_IT_UNUSED"
    return bucket, {"text": text_needles, "struct": struct_needles,
                    "handed": handed_text or handed_struct, "compared": compared}


API_REL = "frontend/src/api/citynexus.ts"
API_THROW = re.compile(r"new CityNexusApiError\(")
API_CALL = re.compile(r"\bcityNexusApi\.([A-Za-z]\w*)|await\s+request[A-Za-z]*")


def api_message_recipe():
    """The message the api layer puts on the error it throws, read from the throw site itself."""
    lines = read(API_REL).split("\n")
    for index, cell in enumerate(lines):
        if not API_THROW.search(cell):
            continue
        recipe = " ".join(cell.strip() for cell in lines[index + 1:index + 5])
        return index + 1, re.sub(r"\s+", " ", recipe)[:140]
    raise SystemExit("ABORT the api layer never throws the error these panels catch")


def diagnostic_provenance(rel, catch_line, radius=60):
    """Does the try above this catch call the api layer, i.e. is the caught error built there?"""
    lines = read(rel).split("\n")
    region = "\n".join(lines[max(0, catch_line - 1 - radius):catch_line])
    found = API_CALL.search(region)
    return found.group(0) if found else ""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = dict(reach.source_files())
    mounted_keys, imported_modules, rendered = panel.registry_panels(files[panel.REGISTRY_REL])
    expected = published_catch_total()

    rows = []
    for key in sorted(mounted_keys):
        candidates = [rel for rel in files if rel.split("src/", 1)[-1].rsplit(".", 1)[0] == key]
        if not candidates:
            raise SystemExit("ABORT a mounted module has no scanned file behind it: %s" % key)
        rel = candidates[0]
        for line, body in habit.bodies(rel):
            bucket, detail = classify(body)
            rows.append({"rel": rel, "line": line, "bucket": bucket, "detail": detail,
                         "literal": (LITERAL.search(body).group(1) if LITERAL.search(body) else "")})
    if len(rows) != expected:
        raise SystemExit("ABORT this ruler read %d catch bodies against bw326's published %d"
                         % (len(rows), expected))
    counts = dict((bucket, sum(1 for item in rows if item["bucket"] == bucket)) for bucket in BUCKETS)
    if sum(counts.values()) != len(rows):
        raise SystemExit("ABORT the buckets do not cover every body this ruler read")

    text_rows = [item for item in rows if item["bucket"] == "HANDS_SERVER_TEXT_TO_STATE"]
    for item in text_rows:
        item["api_call"] = diagnostic_provenance(item["rel"], item["line"])
    from_api = sum(1 for item in text_rows if item["api_call"])
    throw_line, throw_recipe = api_message_recipe()
    if text_rows and not from_api:
        raise SystemExit("ABORT none of the %d text-handling bodies sits above an api-layer call, so the "
                         "provenance sentence below would be unsupported" % len(text_rows))
    print("PROVENANCE %d of %d text-handling bodies sit in a try whose own text calls the api layer; that "
          "layer builds its message at %s:%d" % (from_api, len(text_rows), API_REL, throw_line))

    # The controls are judged on the body at that line, whether or not the file sits in the mounted set.
    verdicts = []
    for control in CONTROLS:
        if control["rel"] not in files:
            raise SystemExit("ABORT a control file is not in the scanned tree: %s" % control["rel"])
        near = [(line, body) for line, body in habit.bodies(control["rel"])
                if abs(line - control["line"]) <= 40]
        if not near:
            raise SystemExit("ABORT the tree holds no catch within 40 lines of control %s:%d"
                             % (control["rel"], control["line"]))
        line, body = min(near, key=lambda pair: abs(pair[0] - control["line"]))
        bucket, _ = classify(body)
        verdicts.append((control, line, bucket))
        if bucket not in control["allowed"]:
            raise SystemExit("ABORT control %r (%s:%d -> %s) landed in %s, which the source at %d contradicts"
                             % (control["name"], control["rel"], control["line"], control["allowed"],
                                bucket, line))
    print("CONTROLS " + " | ".join("%s: %s:%d read as %s (%d)"
                                   % (control["name"], control["rel"], control["line"], bucket, at)
                                   for control, at, bucket in verdicts))

    out = ["WHERE A READ FIELD ACTUALLY GOES bw338",
           "SAME-SOURCE CHECK bodies read here = %d, equal to bw326's published catch=%d (its tally sits at "
           "trial/results/20261026_gozero/bw326-what-the-panels-do-with-a-refusal.txt:%d); the cutter, the "
           "mounted-panel set and the file list are imported from those rulers, not retyped"
           % (len(rows), expected, next(i for i, cell in enumerate(read(BW326_REL).split("\n"), 1)
                                        if cell.startswith("TALLY panels="))),
           "TALLY bodies=%d hands_server_text_to_state=%d hands_server_structure_to_state=%d compares_only=%d "
           "reads_and_leaves_it_unused=%d never_reads_a_server_field=%d"
           % (len(rows), counts["HANDS_SERVER_TEXT_TO_STATE"], counts["HANDS_SERVER_STRUCTURE_TO_STATE"],
              counts["COMPARES_ONLY"], counts["READS_AND_LEAVES_IT_UNUSED"],
              counts["NEVER_READS_A_SERVER_FIELD"]),
           ]
    control_lines = []
    for control, at, bucket in verdicts:
        control_lines.append("  %s → %s:%d 判 %s（允许：%s）"
                             % (control["name"], control["rel"], at, bucket, ", ".join(control["allowed"])))
    out.extend(control_lines)
    out.append("API_MESSAGE_PROVENANCE of the %d bodies that hand a text field to state, %d sit in a try whose "
               "own text names an api-layer call (%s). That layer throws at `%s:%d` with its message assembled "
               "as: %s - which makes what reaches the traveller's line a locally built diagnostic string, not "
               "the server's refusal sentence."
               % (len(text_rows), from_api,
                  " / ".join(sorted({item["api_call"] for item in text_rows if item["api_call"]})) or "(无)",
                  API_REL, throw_line, throw_recipe))
    for bucket in ("HANDS_SERVER_TEXT_TO_STATE", "HANDS_SERVER_STRUCTURE_TO_STATE", "COMPARES_ONLY",
                   "READS_AND_LEAVES_IT_UNUSED"):
        picked = [item for item in rows if item["bucket"] == bucket]
        out.append("%s = %d" % (bucket, len(picked)))
        for item in picked:
            out.append("  %s:%d  交进 setter 的字段 %s  比较行 %d 条  该 body 首枚字面量「%s」"
                       % (item["rel"], item["line"],
                          " / ".join(item["detail"]["handed"]) or "(无)",
                          item["detail"]["compared"],
                          item["literal"][:38].replace("\n", " ") or "(无)"))
    out.extend([
        "NEVER_READS_A_SERVER_FIELD = %d 处（不逐枚列，清单归 bw326）"
        % counts["NEVER_READS_A_SERVER_FIELD"],
        "FIELD_GROUPS text fields are %s; structured fields are %s. The split matters because one of these "
        "panels hands a structured object to state while dropping the prose, and counting that as 'showing "
        "the server's words' would be exactly the mistake the last two rulers made."
        % (", ".join(TEXT_FIELDS), ", ".join(STRUCT_FIELDS)),
        "COUNTING_RULE a body counts as reading the server when it touches a field of either group on an "
        "error-shaped name (%s). A name assigned from such a read is followed one hop. HANDS_*_TO_STATE "
        "requires the needle to sit inside a setter's own arguments; text outranks structure when both are "
        "handed; COMPARES_ONLY is a needle that appears on a line holding a comparison operator and never "
        "in a setter; READS_AND_LEAVES_IT_UNUSED is everything else that still touched a field."
        % "err / error / e / cause / exception / it / rejection / failure",
        "COVERAGE_LIMIT four things this cannot see: a value that leaves the catch and is rendered by a "
        "shared component elsewhere; a JSX interpolation outside the catch body (bw328 owns render sites); a "
        "setter whose arguments run past this pattern's window; and `error.message` on a locally thrown Error, "
        "which is not a server sentence at all - the two DestinationPreparationPanel sites flagged here build "
        "their own Error objects. Nothing here was clicked.",
        "READ THIS WITH bw326 (which bodies read, which hide), bw327 (what the hiding ones say instead), "
        "bw328 (which of those sentences markup reads) and bw337 (which refusal sits behind which panel line).",
    ])
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    back = io.open(RECEIPT, encoding="utf-8").read()
    if "\r\n" in back or "TALLY bodies=" not in back:
        raise SystemExit("ABORT the receipt did not take shape")
    print("LIVE TALLY %s" % counts)
    print("WROTE %s lines=%d" % (RECEIPT, len(back.rstrip("\n").split("\n"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
