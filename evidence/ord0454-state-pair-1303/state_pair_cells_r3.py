"""Third prototype, and the one whose numbers go into the ruler: compound-level parsing, explicit vocabulary.

v2's class-position logic still mis-called twins because it treated a whole selector as one compound. A CSS
selector is a chain of compounds separated by descendant/child combinators, and "the unselected twin of
`.v8-map-panel .v9-map-marker.selected`" means a rule for the compound `.v9-map-marker` WITHOUT the state
modifier -- anywhere in the shipped layer. This parses compounds properly and enumerates the twin forms the
shipped tree actually uses, then reports every state name it deliberately left out of scope instead of
silently ignoring it.

Twin forms accepted (each named in the output so a reader can audit which one answered):
  base_rule                 a rule for the same base class carrying no toggle state
  not_pseudo_twin           `base:not(.state)`
  named_unselected_twin     `base.unselected` / `base-not-selected` spelled out
  attribute_false_twin      `[data-k="false"]` beside `[data-k="true"]` for the same base
Written side (TSX): a toggle attribute must be written as both values, or as a ternary with both branches.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
REV = os.environ.get("CNX_REV", "4ee14229f80691cf8e5ea913375c0caf83ac02ee")
WORK = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")

TOGGLES = ("selected", "picked", "checked", "pressed")
OUT_OF_SCOPE_STATES = ("active", "current", "done", "failed", "busy", "idle", "muted", "neutral",
                       "blocked", "disrupted", "protected", "stay", "user", "near", "next", "ok",
                       "large", "compact", "explicit", "learned", "chosen", "approval")
COMBINATOR = re.compile(r"[\s>+~,]+")
CLASS_TOKEN = re.compile(r"\.(-?[_A-Za-z][-\w]*)")
PSEUDO_OTHER = re.compile(r":(not|is|where|has|hover|focus|focus-visible|disabled|active)\b")
ATTR_EQ = re.compile(r"\[\s*([*^$|~]?[\w-]+)\s*=\s*[\"']([^\"']*)[\"']\s*\]")


def git(*args):
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900, env=ENV)
    assert r.returncode == 0, (args, r.stderr[:200])
    return r.stdout


def names(suffix):
    return [f for f in git("ls-tree", "-r", "--name-only", REV, "--", "frontend/src").splitlines()
            if f.endswith(suffix)]


def strip_comments(text):
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)


def rules_of(text):
    out = []
    clean = strip_comments(text)
    for m in re.finditer(r"([^{}]+)\{", clean):
        sel = m.group(1).strip()
        if sel and not sel.startswith("@"):
            out.append((sel, clean[:m.start()].count("\n") + 1))
    return out


def compounds(sel):
    return [c.strip() for c in COMBINATOR.split(sel) if c.strip()]


def toggle_state_of(cls):
    """The state word when this class is a bare toggle (`.selected`) or a `<something>.selected` modifier."""
    return cls if cls in TOGGLES else None


def main():
    css = {f: git("show", "%s:%s" % (REV, f)) for f in names(".css")}
    parsed = {}
    for f, text in css.items():
        rows = []
        for sel, line in rules_of(text):
            for comp in compounds(sel):
                classes = CLASS_TOKEN.findall(comp)
                attrs = ATTR_EQ.findall(comp)
                rows.append({"selector": sel[:80], "line": line, "compound": comp[:60],
                             "classes": tuple(classes), "attrs": tuple(attrs),
                             "not_state": bool(re.search(r":not\(\s*\.[\w-]*(?:%s)" % "|".join(TOGGLES),
                                                     comp))})
        parsed[f] = rows
    on_cells, base_only, not_twins, named_unselected, attr_sites = [], set(), set(), set(), {}
    for f, rows in parsed.items():
        for r in rows:
            states = [c for c in r["classes"] if toggle_state_of(c)]
            if states:
                base = tuple(c for c in r["classes"] if c not in TOGGLES)
                on_cells.append({"file": f, "line": r["line"], "compound": r["compound"],
                                 "state": states[0], "base": base[-1] if base else None})
            elif r["classes"] and not r["attrs"]:
                base_only.update(r["classes"])
            for c in r["classes"]:
                if c.startswith("un") and c[2:] in TOGGLES:
                    named_unselected.add(c[2:])
            for n, v in r["attrs"]:
                if n.startswith("data-") or n.startswith("aria-"):
                    attr_sites.setdefault((n, v), []).append("%s:%s" % (f, r["line"]))
            if r["not_state"] and r["classes"]:
                not_twins.add((r["classes"][-1], r["compound"]))
    cells = []
    for c in on_cells:
        twins = []
        if c["base"] and c["base"] in base_only:
            twins.append("base_rule(.%s)" % c["base"])
        if c["base"] and any(nt[0] == c["base"] for nt in not_twins):
            twins.append("not_pseudo_twin")
        if c["base"] and ("un" + c["state"]) in named_unselected:
            twins.append("named_unselected_twin")
        for (n, v), where in attr_sites.items():
            if v == "false" and (n, "true") in attr_sites and c["base"] and any(
                    c["base"] in w.split(":")[0] for w in where):
                twins.append("attribute_false_twin(%s)" % n)
        cells.append(dict(c, twins=sorted(set(twins)), paired=bool(twins)))
    out_of_scope_seen = sorted({c for rows in parsed.values() for r in rows for c in r["classes"]
                                if any(r["compound"].endswith("." + s) or c in OUT_OF_SCOPE_STATES
                                       for s in ("active", "current"))})
    written = {}
    for f in names((".tsx", ".ts")):
        text = git("show", "%s:%s" % (REV, f))
        for m in re.finditer(r"(data-picked|data-selected|aria-pressed|aria-selected)=[\"{]([^}]{0,120})[\"}]",
                             text):
            name, rhs = m.group(1), m.group(2)
            has_true = "true" in rhs
            has_false = "false" in rhs
            written.setdefault(name, {"true_sites": 0, "false_sites": 0, "one_sided": [],
                                      "sample_files": set()})
            w = written[name]
            w["true_sites"] += int(has_true)
            w["false_sites"] += int(has_false)
            w["sample_files"].add(f.split("/")[-1])
            if has_true != has_false:
                w["one_sided"].append("%s:%s" % (f.split("/")[-1],
                                                 text[:m.start()].count("\n") + 1))
    out = {"rev": REV, "css_files": len(css), "source_files_measured": len(names((".tsx", ".ts"))),
           "toggle_vocabulary": list(TOGGLES), "on_state_cells": len(cells),
           "paired": sum(1 for c in cells if c["paired"]),
           "unpaired": [c for c in cells if not c["paired"]],
           "cells": cells, "base_only_classes": len(base_only),
           "attribute_sites": {("%s=%s" % k): v for k, v in attr_sites.items()},
           "written_side": {k: {"true_sites": v["true_sites"], "false_sites": v["false_sites"],
                                "one_sided": v["one_sided"], "files": sorted(v["sample_files"])}
                            for k, v in written.items()},
           "state_names_left_out_of_scope": out_of_scope_seen}
    io.open(os.path.join(WORK, "state_pair_cells_r3.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in ("rev", "css_files", "on_state_cells", "paired", "unpaired",
                                          "attribute_sites", "written_side",
                                          "state_names_left_out_of_scope")},
                     ensure_ascii=False, indent=1)[:3200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
