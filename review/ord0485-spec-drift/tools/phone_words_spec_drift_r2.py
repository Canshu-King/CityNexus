"""Can ORD-0485's phone word-spec be lifted onto the line as it stands?

The two product paths of that hand (the spec and its playwright config) have never been on the line, so the
question a landing decision needs is not "does the file exist somewhere" -- it does, on the ref -- but "does
the screen it freezes still say that".  A spec whose frozen copy no longer exists reddens the moment it is
landed, and that reads as if the fix broke the app.

Cut 1 of this tool was wrong in a way worth naming, because it is the classic failure: it collected the second
argument of `expect(...)`, which in this spec family is `node("<id>", "<diagnostic>")` -- the test's own
failure text.  Five of its nine rows were those labels reported as missing screen copy
(`phone_words_spec_drift_r1.json` keeps that reading).  This cut takes only the strings the spec freezes as
constants or iterates as a word list, pairs each frozen string with the dictionary key it was written about by
comparing the constant names, and then asks where that key lives on the line today.

Verdicts are about 词面 (necessary, not sufficient -- only a browser run proves a word reaches the screen), and
the run carries a must-find and a must-not-find control so a broken grep cannot masquerade as "everything
rotted" or an empty tree as "nothing rotted".  Nothing is written: only ref bytes and tip trees are read.
"""
import json
import os
import re
import subprocess
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
REF = "refs/heads/review/newlane-ord0485-phone-walkthrough-r4"
SPEC = "frontend/e2e/qoder-ord0485-phone-words.spec.ts"
I18N = "frontend/src/i18n/LocaleContext.tsx"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=300, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def head_of(ref):
    rc, out, err = git("ls-remote", "--refs", "origin", ref)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_UNREADABLE " + ref + err[:80])
    return out.split()[0]


def consts(text):
    return {m.group(1): m.group(2) for m in re.finditer(
        r'^const\s+([A-Za-z0-9_]+)\s*(?::\s*string)?\s*=\s*"([^"\n]{2,80})"', text, re.M)}


def frozen_literals(text):
    """`const NAME = "…"`, minus the module's own file path, plus the list a `for (const w of [...])` walks."""
    rows = []
    for name, lit in consts(text).items():
        if name == "FILE" or "/" in lit:
            continue
        rows.append({"role": "frozen_constant", "name": name, "literal": lit})
    for m in re.finditer(r"for \(const (\w+) of \[([^\]]+)\]", text):
        for s in re.findall(r'"([^"\n]{1,60})"', m.group(2)):
            rows.append({"role": "iterated_word", "name": m.group(1), "literal": s})
    return rows


def pairs(text):
    """Pair each FROZEN_<token>_<locale> string with the LEAKED_<token>_KEY dictionary entry it was written
    about, by the token in the constant's own name -- derived from the file, not typed here.  Keys with no
    frozen sibling are still returned (paired to nothing) because their carrier state is part of the answer."""
    cs = consts(text)
    out, paired = [], set()
    for name, lit in cs.items():
        if not name.startswith("FROZEN_"):
            continue
        token = re.sub(r"^FROZEN_|_(ZH|EN)$", "", name)
        key_name = "LEAKED_%s_KEY" % token
        if key_name in cs:
            paired.add(key_name)
            out.append({"token": token, "frozen_const": name, "frozen_literal": lit,
                        "key_const": key_name, "dictionary_key": cs[key_name]})
    for name, lit in cs.items():
        if name.startswith("LEAKED_") and name.endswith("_KEY") and name not in paired:
            out.append({"token": re.sub(r"^LEAKED_|_KEY$", "", name), "frozen_const": None,
                        "frozen_literal": None, "key_const": name, "dictionary_key": lit})
    return out


def grep(tip, needle, pathspec):
    rc, out, err = git("grep", "-F", "-l", "-e", needle, tip, "--", pathspec)
    if rc not in (0, 1):
        raise SystemExit("ABORT_GREP_BROKEN_READ rc=%s needle=%s %s" % (rc, needle[:40], err[:80]))
    return rc == 0, [l.split(":", 1)[1] for l in out.splitlines() if l.strip()]


def grep_lines(tip, needle, pathspec):
    """git prints `<rev>:<path>:<line>:<text>` -- split exactly three times, because the text itself is full of
    colons (`channelLocal: {`).  Splitting from the right made every object-literal line unreadable and turned
    a copy that IS on the line into 'absent from both trees': that was this tool's second version."""
    rc, out, _e = git("grep", "-n", "-F", "-e", needle, tip, "--", pathspec)
    if rc not in (0, 1):
        raise SystemExit("ABORT_GREP_BROKEN_READ rc=%s needle=%s" % (rc, needle[:40]))
    hits = []
    for l in out.splitlines():
        parts = l.split(":", 3)
        if len(parts) < 4 or not parts[2].strip().isdigit():
            continue
        hits.append({"path": parts[1], "line": int(parts[2]), "text": parts[3].strip()[:120]})
    return hits


def dictionary_state(tip, key):
    """What the i18n carrier says about the key, and -- separately -- where on the line any ENTRY for it lives.
    Without the second half, 'not in LocaleContext' could be read as 'the product lost the sentence'.

    The dotted key can itself have been retired while the sentence stayed, under the trailing segment -- that
    is what happened here -- so an empty search on the full key falls back to the last segment and says so in
    `matched_on`, instead of reporting the copy as gone.
    """
    rc, text, _e = git("show", "%s:%s" % (tip, I18N))
    i18n_hits = [{"line": n, "text": line.strip()[:120]} for n, line in enumerate(text.splitlines(), 1)
                 if key in line] if not rc else []

    def entries(needle):
        """Carriers only: an entry shape in a non-test source file.  Without the test exclusion the sentence
        'is not carried anywhere' gets contradicted by other specs' mentions of the same key -- those are
        claims about the product, not the product, and they have no values to read."""
        found, excluded = {}, 0
        for shape in ('"%s":' % needle, "%s: {" % needle, "%s:" % needle):
            for h in grep_lines(tip, shape, "frontend"):
                if not h["path"].endswith((".ts", ".tsx")):
                    continue
                if "/e2e/" in h["path"] or h["path"].endswith((".spec.ts", ".test.ts", ".config.ts")):
                    excluded += 1
                    continue
                found["%s:%d" % (h["path"], h["line"])] = {"path": h["path"], "line": h["line"],
                                                            "shape": shape, "text": h["text"]}
        return [found[k] for k in sorted(found)], excluded

    full, ex_full = entries(key)
    tail = key.split(".")[-1]
    seg, ex_seg = ([], 0) if full else entries(tail)
    chosen = full or seg
    return {"key": key, "i18n_readable": not rc, "i18n_mentions": len(i18n_hits),
            "i18n_lines": i18n_hits[:4],
            "matched_on": "full_key" if full else ("trailing_segment" if seg else "nothing"),
            "trailing_segment": tail, "test_mentions_excluded": ex_full + ex_seg, "entry_hits": chosen[:8]}


def zh_values(tip, path, line, span=4):
    rc, text, _e = git("show", "%s:%s" % (tip, path))
    if rc:
        return []
    block = "\n".join(text.splitlines()[max(0, line - 1): line - 1 + span])
    return re.findall(r'zh:\s*"([^"]+)"', block) + re.findall(r'"[^"]+"\s*:\s*"([^"]+)"', block)


def main():
    tip = head_of(TIP_REF)
    ref_head = head_of(REF)
    rc, spec, err = git("show", "%s:%s" % (ref_head, SPEC))
    if rc:
        raise SystemExit("ABORT_SPEC_UNREADABLE " + err[:120])
    rows = []
    for r in frozen_literals(spec):
        f_ok, f_hits = grep(tip, r["literal"], "frontend")
        b_ok, b_hits = grep(tip, r["literal"], "backend")
        r.update({"frontend_files": f_hits[:4], "backend_files": b_hits[:4],
                  "where": "frontend+backend" if f_ok and b_ok else
                           ("frontend" if f_ok else ("backend" if b_ok else "none")),
                  "verdict": "WORD_ON_LINE" if (f_ok or b_ok) else "WORD_ABSENT_ON_LINE"})
        rows.append(r)
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    relations = []
    for p in pairs(spec):
        st = dictionary_state(tip, p["dictionary_key"])
        # two carrier shapes, kept apart instead of blended into one list: an object table
        # (`key: { zh: "...", en: "..." }`) whose values come from the lines under it, and an inline entry
        # (`"key": "value"`) whose value is on that same line.  Reading a whole span for the inline shape is
        # how the first version pulled in the neighbouring state words.
        zhs, inline = [], []
        for e in st["entry_hits"]:
            if e["text"].rstrip().endswith("{"):
                zhs += zh_values(tip, e["path"], e["line"])
            else:
                m = re.search(r":\s*\"([^\"]+)\"", e["text"])
                if m:
                    inline.append(m.group(1))
        zhs, inline = sorted(set(zhs)), sorted(set(inline))
        frozen_present = (p["frozen_literal"] in {x["literal"] for x in rows
                          if x["verdict"] == "WORD_ON_LINE"}) if p["frozen_literal"] else None
        relations.append({**p, "frozen_present_on_line": frozen_present, "carried": st,
                          "entry_lines": [e["path"] + ":" + str(e["line"]) for e in st["entry_hits"]][:6],
                          "zh_values_now": zhs[:6], "inline_values_now": inline[:6],
                          "verdict": ("KEY_ONLY_NO_FROZEN_COPY" if p["frozen_literal"] is None else
                                      ("COPY_MATCHES_LINE" if frozen_present else
                                       ("COPY_REWORDED_ON_LINE" if zhs else "COPY_GONE_FROM_LINE"))),
                          "key_still_in_i18n": bool(st["i18n_lines"])})
    controls = []
    for arm, needle, want in (("positive", "poi-import", True), ("negative", "cn0485driftprobezzz", False)):
        ok, hits = grep(tip, needle, "frontend")
        controls.append({"arm": arm, "needle": needle, "found": ok, "files": hits[:3],
                         "as_expected": ok == want})
    # third arm, and it is the one that caught this tool's own parsing bug: pick a real source line that
    # contains a colon, from a file read out of the tip's tree, and require the line parser to find it back
    rc, listing, _e = git("ls-tree", "-r", "--name-only", tip, "--", "frontend")
    cand = [l for l in listing.splitlines() if l.endswith((".ts", ".tsx"))]
    colon_arm = {"arm": "colon_in_text", "as_expected": False, "attempted": False}
    for path in cand[:40]:
        rc2, body, _e2 = git("show", "%s:%s" % (tip, path))
        if rc2:
            continue
        line = next((l.strip() for l in body.splitlines() if l.count(":") >= 2 and len(l.strip()) > 10), "")
        if not line:
            continue
        colon_arm = {"arm": "colon_in_text", "attempted": True, "needle_path": path, "needle": line[:80],
                     "found_back": any(h["path"] == path for h in grep_lines(tip, line, "frontend"))}
        colon_arm["as_expected"] = colon_arm["found_back"]
        break
    controls.append(colon_arm)
    if not colon_arm["attempted"]:
        raise SystemExit("ABORT_COLON_CONTROL_NEVER_RAN")
    if not all(c["as_expected"] for c in controls):
        raise SystemExit("ABORT_GREP_CONTROLS_BROKEN " + json.dumps(controls, ensure_ascii=False)[:240])
    # denominators: "absent from both trees" is only a finding if both trees are actually there to search
    trees = {}
    for spec_path in ("frontend", "backend"):
        rc2, out2, _e2 = git("ls-tree", "-r", "--name-only", tip, "--", spec_path)
        trees[spec_path + "_files"] = len([l for l in out2.splitlines() if l.strip()])
    if min(trees.values()) <= 0:
        raise SystemExit("ABORT_EMPTY_TREE_DENOMINATOR " + json.dumps(trees))
    if not relations:
        raise SystemExit("ABORT_NO_FROZEN_TO_KEY_PAIRINGS_DERIVED")
    out = {"schema": "CNX_ORD0485_SPEC_DRIFT_V2", "tool": "phone_words_spec_drift_r2",
           "took_local": datetime.now().astimezone().isoformat(), "live_tip": tip, "ref": REF,
           "ref_head": ref_head, "spec_path": SPEC, "spec_bytes": len(spec),
           "frozen_literals_read": len(rows), "counts": counts, "rows": rows, "relations": relations,
           "controls": controls, "tree_denominators": trees, "worktree_written": False,
           "r1_defect": "expect(...) titles were collected as assertions; five of nine r1 rows were the "
                        "spec's own diagnostic labels",
           "limit": "词面在场是必要条件不是充分条件；只有浏览器跑一遍才知道那枚字有没有上屏"}
    dest = os.path.join(LANE, "evidence", "phone_words_spec_drift_r2.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"live_tip": tip, "ref_head": ref_head, "frozen": len(rows), "counts": counts,
                      "controls_ok": all(c["as_expected"] for c in controls),
                      "relations": [{"token": r["token"], "frozen": r["frozen_literal"],
                                     "key": r["dictionary_key"], "verdict": r["verdict"],
                                     "zh_now": r["zh_values_now"], "i18n_mentions": r["carried"]["i18n_mentions"]}
                                    for r in relations]}, ensure_ascii=False, indent=1))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
