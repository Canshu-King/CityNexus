# -*- coding: utf-8 -*-
"""ORD-0568 landing arm r3 (lane 加闸工): refuse internal code names that reach the traveller's eyes.

What it defends.  The commander's screen probe (`live_checks/_cmdr_screen_code_probe_r1.py:46`) fails a
served page when a rendered sentence contains an uppercase code -- he measured CODES_ON_SCREEN 3 on the
trial wizard (`_screen_probe_r1.txt:3`: HYDRATABLE, NO_CANONICAL_IDENTITY, UNKNOWN_RETRYABLE).  A
landing gate cannot render every candidate, so this arm judges the same class statically.

Two axes, both learned the hard way inside this order:

  position -- a string is judged only where it becomes a word the traveller reads: a value inside a
  `[中文, 英文]` pair or any array literal, the right side of `"key": "value"`, a ternary arm, an
  assigned or returned sentence, a template literal's own text, and JSX text between tags.  Object and
  array KEYS, the argument of a lookup call (`roleLabel("ARRIVAL", zh)`, `t("live.x")`), comparisons
  (`=== "X"`), `case "X":` labels, type unions, JSX attributes and comments are names handed to the
  machine and are never judged.

  name -- a token is refused only when something actually names with it: the server quotes it as a
  value under `backend/` or `contracts/`, or the judged file itself uses it in a non-rendered position.
  Without this axis the replay raised 90 refusals of deliberate all-caps UI copy ("NOTIFICATIONS",
  "POLICY", "TRAVEL"); one false rejection makes a gate undeliverable, which is what the order says.

Kebab slugs (`not-asked`) are reported as information and never refused, because the probe reports them
without failing and hyphenated English would otherwise turn a sentence into a red.

Arm shape follows the landing door: default is report-only, `--refuse` turns a refusal-class problem
into exit code 9, and every finding carries file / line / entry line / token / who names it / the source
line, so the outbox receipt can quote the reason instead of leaving one bare verdict word.
"""

import argparse
import io
import json
import re
import subprocess
import sys

CODE_TOKEN = re.compile(r"\b[A-Z][A-Z0-9_]{5,}\b")
SLUG_TOKEN = re.compile(r"\b[a-z][a-z]+-[a-z]+(?:-[a-z]+)*\b")
ENTRY_RE = re.compile(r"^\s*[A-Za-z_$][A-Za-z0-9_$]*\s*:\s*[\[{(]?\s*$")
QUOTED_ANY = re.compile(r"[\"']([A-Z][A-Z0-9_]{4,})[\"']")
NAME_POSITIONS = ("key", "comparison_or_case", "type_union", "call_argument",
                  "jsx_attribute", "type_position", "module_path")

REPO = "."
_CORPUS = {}


def _git(args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)


def git_show(ref, path):
    out = _git(["show", "%s:%s" % (ref, path)])
    if out.returncode:
        return None
    return out.stdout.decode("utf-8", "replace")


def machine_names(ref):
    """Tokens the server quotes as values -- the vocabulary a traveller must never be shown."""
    key = (REPO, ref)
    if key not in _CORPUS:
        out = _git(["grep", "-h", "-o", "-E", r"[\"'][A-Z][A-Z0-9_]{4,}[\"']", ref, "--", "backend/", "contracts/"])
        names = set()
        for line in out.stdout.decode("utf-8", "replace").splitlines():
            m = QUOTED_ANY.search(line.strip())
            if m:
                names.add(m.group(1))
        _CORPUS[key] = names
    return _CORPUS[key]


def mask_comments(src):
    """Blank comments and escape pairs, keeping every offset and newline."""
    chars = list(src)
    i, n = 0, len(src)
    state, quote = None, ""
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                state = "line"
                i += 2
                continue
            if c == "/" and nxt == "*":
                chars[i] = chars[i + 1] = " "
                state = "block"
                i += 2
                continue
            if c in "\"'`":
                state, quote = "str", c
            i += 1
            continue
        if state == "line":
            if c == "\n":
                state = None
            else:
                chars[i] = " "
            i += 1
            continue
        if state == "block":
            if c == "*" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                state = None
                i += 2
                continue
            if c != "\n":
                chars[i] = " "
            i += 1
            continue
        if state == "str":
            if c == "\\":
                if i + 1 < n and src[i + 1] != "\n":
                    chars[i + 1] = " "
                i += 2
                continue
            if c == quote:
                state = None
            i += 1
            continue
    return "".join(chars)


def literal_spans(masked):
    """Every string or template literal in comment-free source."""
    i, n = 0, len(masked)
    while i < n:
        c = masked[i]
        if c in "\"'`":
            quote = c
            j = i + 1
            while j < n:
                if masked[j] == "\\":
                    j += 2
                    continue
                if masked[j] == quote:
                    break
                if masked[j] == "\n" and quote != "`":
                    break
                j += 1
            yield (i, j + 1, masked[i + 1 : j], "template" if quote == "`" else "string")
            i = j + 1
            continue
        i += 1


def jsx_text_spans(masked):
    """Text between tags, e.g. `<dt>ARRIVED_LATE</dt>` -- words with no quote around them."""
    for m in re.finditer(r">([^<>{}\n]{1,200})<", masked):
        if m.group(1).strip():
            yield (m.start(1), m.end(1), m.group(1), "jsx_text")


def nearest_opener(masked, start):
    depth = {"(": 0, "[": 0, "{": 0}
    for j in range(start - 1, -1, -1):
        c = masked[j]
        if c == ")":
            depth["("] += 1
        elif c == "]":
            depth["["] += 1
        elif c == "}":
            depth["{"] += 1
        elif c in depth:
            if depth[c] > 0:
                depth[c] -= 1
            else:
                return c, j
    return (None, -1)


def classify_position(masked, start, end):
    raw_before = masked[:start]
    before = raw_before.rstrip()
    after = masked[end:].lstrip()
    prev_char = before[-1] if before else ""
    next_char = after[0] if after else ""

    if next_char.startswith(":"):
        return "key"
    if re.search(r"(===|!==|==|!=|\bcase)$", before):
        return "comparison_or_case"
    if prev_char == "|" or next_char.startswith("|"):
        return "type_union"
    if raw_before.endswith("=") and re.search(r"[A-Za-z0-9_$-]$", raw_before[:-1]):
        return "jsx_attribute"
    opener, op_pos = nearest_opener(masked, start)
    if opener == "(":
        head = masked[:op_pos].rstrip()
        if re.search(r"[A-Za-z_$][A-Za-z0-9_$]*$", head):
            return "call_argument"
        if re.search(r"\bfrom$", head):
            return "module_path"
        return "grouping"
    if re.search(r"\btype\s+\w+\s*=$", before):
        return "type_position"
    return "rendered"


def entry_line_of(lines, idx):
    for k in range(idx, max(idx - 8, -1), -1):
        if k < 0:
            break
        if ENTRY_RE.match(lines[k]):
            return k + 1
    return idx + 1


def judge(path, text, allowed=None, only_lines=None):
    masked = mask_comments(text)
    lines = masked.split("\n")
    raw_lines = text.split("\n")
    line_starts = []
    pos = 0
    for ln in lines:
        line_starts.append(pos)
        pos += len(ln) + 1

    def line_of(offset):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    units = list(literal_spans(masked)) + list(jsx_text_spans(masked))
    local_names = set()
    for start, end, body, kind in units:
        if kind == "jsx_text":
            continue
        if classify_position(masked, start, end) in NAME_POSITIONS:
            local_names.update(CODE_TOKEN.findall(body))

    findings = []
    for start, end, body, kind in units:
        idx = line_of(start)
        position = "jsx_text" if kind == "jsx_text" else classify_position(masked, start, end)
        if position != "rendered" and kind != "jsx_text":
            continue
        codes = sorted(set(CODE_TOKEN.findall(body)))
        if only_lines is not None:
            codes = [c for c in codes if (idx + 1) in only_lines]
        if allowed is not None:
            codes = [c for c in codes if c in allowed or c in local_names]
        slugs = sorted(set(SLUG_TOKEN.findall(body)))
        for tok in codes:
            if allowed is not None and tok in allowed:
                named = "server_corpus"
            elif tok in local_names:
                named = "this_file_names_it"
            else:
                named = "unqualified"
            findings.append({
                "file": path,
                "line": idx + 1,
                "entry_line": entry_line_of(lines, idx),
                "token": tok,
                "position": position,
                "named_by": named,
                "class": "refuse",
                "text": (raw_lines[idx] if idx < len(raw_lines) else "").strip()[-90:],
            })
        if slugs and not codes:
            findings.append({
                "file": path,
                "line": idx + 1,
                "entry_line": entry_line_of(lines, idx),
                "token": ",".join(slugs[:6]),
                "position": position,
                "class": "info_slug_only",
                "text": (raw_lines[idx] if idx < len(raw_lines) else "").strip()[-90:],
            })
    return findings


def added_lines(base, ref):
    files = {}
    diff = _git(["diff", "-U0", "%s...%s" % (base, ref), "--", "frontend/"]).stdout.decode("utf-8", "replace").split("\n")
    cur = None
    for line in diff:
        if line.startswith("+++ b/"):
            cur = line[6:].strip()
            files.setdefault(cur, set())
        elif line.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2) or 1)
                for n in range(start, start + max(count, 1)):
                    files[cur].add(n)
    return files


def collect(opts, base):
    if opts.path:
        return [(opts.path, io.open(opts.path, encoding="utf-8", errors="replace").read())]
    if opts.files:
        paths = [p for p in opts.files.split(",") if p]
    else:
        paths = _git(["diff", "--name-only", "%s...%s" % (base, opts.ref), "--", "frontend/"]).stdout.decode("utf-8", "replace").splitlines()
    if not opts.path and not opts.include_nonproduct:
        # a spec fixture is data handed to the server, not a word a traveller reads -- the replay
        # showed judging frontend/e2e/** is a false rejection, so the shipped face is frontend/src/**
        paths = [p for p in paths if p.startswith("frontend/src/")]
    items = []
    for p in paths:
        if p.endswith(".tsx") or p.endswith(".ts"):
            body = git_show(opts.ref, p)
            if body is not None:
                items.append((p, body))
    return items


def selftest():
    """26 assertions, each naming the position class or the naming axis it protects."""
    cases = [
        ("pair value is spoken words", 'const G = { a: ["已支持", "Supported", "NO_CANONICAL_IDENTITY"] };\n', ["NO_CANONICAL_IDENTITY"], None, None),
        ("dictionary value on the en side", 'const D = {"x.zh": "标题", "x.en": "READY_NOT_PRESENT title"};\n', ["READY_NOT_PRESENT"], None, None),
        ("ternary arm", 'return zh ? "没有" : "UNKNOWN_RETRYABLE here";\n', ["UNKNOWN_RETRYABLE"], None, None),
        ("template literal", 'return `verdict ${row.code} HYDRATABLE needed`;\n', ["HYDRATABLE"], None, None),
        ("JSX text between tags", 'return (<dt>ARRIVED_LATE</dt>);\n', ["ARRIVED_LATE"], None, None),
        ("assigned sentence", 'const note = "PROVIDER_UNREACHABLE 这一次没答上";\n', ["PROVIDER_UNREACHABLE"], None, None),
        ("comparison is not a word", 'if (row.reason_code === "NO_CANONICAL_IDENTITY") return "needs";\n', [], None, None),
        ("case label is not a word", 'switch (k) { case "DESTINATION_AMBIGUOUS": return 1; }\n', [], None, None),
        ("object key is not a word", 'const M = { "DESTINATION_RESOLVER_UNAVAILABLE": "来源没答上" };\n', [], None, None),
        ("t() key argument is a name", 'return t("live.no_canonical_identity");\n', [], None, None),
        ("lookup call argument is a name", 'return roleLabel("ARRIVAL_STATION", zh);\n', [], None, None),
        ("JSX attribute is not a word", 'return (<b data-testid="NO_CANONICAL_IDENTITY">x</b>);\n', [], None, None),
        ("type union is not a word", 'type Kind = "READY_STATE" | "UNKNOWN_RETRYABLE";\n', [], None, None),
        ("line comment is not judged", "const x = 1; // NO_CANONICAL_IDENTITY is the server's\n", [], None, None),
        ("block comment is not judged", '/* HYDRATABLE and UNKNOWN_RETRYABLE are codes */\nconst y = 2;\n', [], None, None),
        ("code inside a commented block", '/*\nconst z = "PROVIDER_UNREACHABLE";\n*/\nconst w = 1;\n', [], None, None),
        ("short caps is below the threshold", 'const a = ["READY", "TODO"];\n', [], None, None),
        ("lowercase slug never refuses", 'const b = ["not-asked", "trial-city"];\n', [], None, None),
        ("empty file", '', [], None, None),
        ("plain English sentence", 'const c = ["the server names it and holds material"];\n', [], None, None),
        ("Chinese only", 'const d = ["这台服务器认不出这个名字"];\n', [], None, None),
        ("name axis: token nobody names is display copy", 'const e = ["NOTIFICATIONS"];\n', [], {"NOT_A_TOKEN"}, None),
        ("name axis: token the server quotes is refused", 'const f = ["NO_SCENARIO"];\n', ["NO_SCENARIO"], {"NO_SCENARIO"}, None),
        ("name axis: this file names it elsewhere", 'if (s === "STAGE_LIVE") return null;\nconst t = ["状态 STAGE_LIVE 在台上"];\n', ["STAGE_LIVE"], set(), None),
        ("only-added: a line the lane did not write is left alone", 'const g = ["NO_CANONICAL_IDENTITY"];\nconst h = ["UNKNOWN_RETRYABLE"];\n', ["UNKNOWN_RETRYABLE"], {"NO_CANONICAL_IDENTITY", "UNKNOWN_RETRYABLE"}, {2}),
        ("only-added with an empty set judges nothing", 'const i = ["NO_CANONICAL_IDENTITY"];\n', [], {"NO_CANONICAL_IDENTITY"}, set()),
    ]
    bad = []
    for label, src_text, expected, allowed, only in cases:
        got = sorted({f["token"] for f in judge("selftest.tsx", src_text, allowed, only) if f["class"] == "refuse"})
        if got != sorted(expected):
            bad.append("%s: expected %s got %s" % (label, sorted(expected) or "[]", got or "[]"))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--base", default="")
    ap.add_argument("--path", default="")
    ap.add_argument("--files", default="")
    ap.add_argument("--require-name", action="store_true", help="refuse only tokens the server or this file names with")
    ap.add_argument("--only-added", action="store_true", help="judge only the lines the candidate wrote")
    ap.add_argument("--include-nonproduct", action="store_true", help="also judge frontend/e2e/** and other non-shipped paths")
    ap.add_argument("--refuse", action="store_true", help="exit 9 when a refusal-class problem exists")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", default="")
    opts = ap.parse_args()

    global REPO
    REPO = opts.repo

    if opts.selftest:
        bad = selftest()
        print("SELFTEST assertions=26 failures=%d" % len(bad))
        for line in bad:
            print("  FAIL " + line)
        return 1 if bad else 0

    base = opts.base or _git(["rev-parse", "origin/mirror/integration-frontend-apple-pass1"]).stdout.decode().strip()
    items = collect(opts, base)
    allowed = machine_names(opts.ref) if opts.require_name else None
    added = added_lines(base, opts.ref) if opts.only_added else {}
    findings = []
    for path, body in items:
        findings.extend(judge(path, body, allowed, added.get(path)))
    refuses = [f for f in findings if f["class"] == "refuse"]
    infos = [f for f in findings if f["class"] != "refuse"]

    sys.stdout.buffer.write(("arm codes-on-screen r3 | ref=%s base=%s files_judged=%d refuse=%d info=%d require_name=%s only_added=%s corpus=%d\n" % (
        opts.ref, base[:10], len(items), len(refuses), len(infos), opts.require_name, opts.only_added,
        len(allowed) if allowed is not None else -1)).encode("utf-8", "replace"))
    for f in refuses:
        sys.stdout.buffer.write(("REFUSE %s:%s (entry :%s) token=%s named_by=%s in %s | %s\n" % (
            f["file"], f["line"], f["entry_line"], f["token"], f["named_by"], f["position"], f["text"])).encode("utf-8", "replace"))
    for f in infos:
        sys.stdout.buffer.write(("INFO   %s:%s slug=%s\n" % (f["file"], f["line"], f["token"])).encode("utf-8", "replace"))
    if opts.json:
        io.open(opts.json, "w", encoding="utf-8", newline="").write(json.dumps(
            {"arm": "codes-on-screen-r3", "ref": opts.ref, "base": base, "require_name": opts.require_name,
             "only_added": opts.only_added, "files_judged": len(items), "problems": refuses,
             "informational": infos}, ensure_ascii=False, indent=1))
    return 9 if (opts.refuse and refuses) else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
