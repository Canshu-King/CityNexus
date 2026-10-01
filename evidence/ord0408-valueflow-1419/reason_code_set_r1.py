# -*- coding: utf-8 -*-
"""ORD-0408 follow-up r1 - the closed set of `error.reason_code`, measured on both sides.

The ruler says CONTRACT_MISSING_ENUM for the one live `*_code` cell on the tip (features/trash/
JourneyTrashPanel.tsx:233, per-file mode).  That verdict can only be answered by the contract declaring
a closed set - so before proposing one, the set has to be measured twice and compared:

  A) what the CONTRACT names: every `reason_code = X` written anywhere in contracts/openapi.yaml
     (prose, in `description:` strings - not a schema enum; that is the defect), and
  B) what the SERVER can actually emit: every `reason_code=<CONST>` / `"reason_code": "<literal>"` in
     backend/app, with each `<CONST>` resolved to the string it is assigned.

The two differences (A-B, B-A) are the whole answer: A-B are codes the contract promises but no code
path returns today, B-A are codes a traveller can receive that the contract has never heard of.  A
proposed enum that ignores B-A would be a contract that lies, and the ruler would then exempt a screen
showing a token outside the declared set - which is exactly the false green ORD-0408 was written to stop.

Read-only: everything here is `git show` / `git grep` over the tip.
"""
import io
import json
import os
import re
import subprocess

REPO = r"D:\moodle\CityNexus"
TIP = "514b397f96f3b5165b24865f4a544ab6f8020084"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0536"
ENV = dict(os.environ)
ENV.pop("HTTP_PROXY", None)
ENV.pop("HTTPS_PROXY", None)


def git(*args):
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900, env=ENV)
    return r.returncode, r.stdout or "", (r.stderr or "").strip()


def grep_files(patter, pathspec):
    """Every file at the tip matching a grep -E pattern, as {path: text}."""
    rc, out, _ = git("grep", "-l", "-E", patter, TIP, "--", pathspec)
    docs = {}
    for p in [x for x in out.split("\n") if x.strip()]:
        path = p.split(":", 1)[1] if p.startswith(TIP) else p
        rc2, text, _ = git("show", "%s:%s" % (TIP, path))
        if rc2 == 0:
            docs[path] = text
    return docs


def contract_named():
    rc, out, _ = git("show", "%s:contracts/openapi.yaml" % TIP)
    text = out
    named = sorted(set(re.findall(r"reason_code[^A-Za-z0-9]{0,4}=\s*([A-Z][A-Z0-9_]{3,})", text)))
    declared_prop = bool(re.search(r"^\s*reason_code\s*:", text, re.M))
    enum_for_it = re.findall(r"reason_code\s*:\s*\{[^}]*enum", text)
    lines = [i + 1 for i, l in enumerate(text.split("\n")) if "reason_code" in l]
    return {"codes_named_in_prose": named, "count": len(named),
            "reason_code_appears_as_a_schema_property": declared_prop,
            "schema_enum_declared_for_it": len(enum_for_it),
            "lines_mentioning_it": len(lines),
            "first_lines": lines[:12], "bytes": len(text.encode("utf-8"))}


def server_emittable():
    """`reason_code=<CONST>` and `"reason_code": "<LITERAL>"` in backend/app, CONST resolved."""
    docs = grep_files("reason_code", "backend/app")
    literal_uses = {}
    const_uses = {}
    for path, text in docs.items():
        for n, line in enumerate(text.split("\n"), 1):
            for m in re.finditer(r"reason_code\s*=\s*([A-Z][A-Z0-9_]{2,})\b", line):
                const_uses.setdefault(m.group(1), []).append("%s:%d" % (path.split("/")[-1], n))
            for m in re.finditer(r"reason_code\s*=\s*\"([A-Z][A-Z0-9_]{3,})\"", line):
                literal_uses.setdefault(m.group(1), []).append("%s:%d" % (path.split("/")[-1], n))
            for m in re.finditer(r"\"reason_code\"\s*:\s*\"([A-Z][A-Z0-9_]{3,})\"", line):
                literal_uses.setdefault(m.group(1), []).append("%s:%d" % (path.split("/")[-1], n))
    # resolve CONST -> its assigned string, anywhere in backend/
    values = {}
    allpy = grep_files(r"^(%s)\s*=\s*\"" % "|".join(sorted(const_uses)), "backend") if const_uses else {}
    for path, text in allpy.items():
        for n, line in enumerate(text.split("\n"), 1):
            m = re.match(r"^\s*([A-Z][A-Z0-9_]{2,})\s*=\s*\"([A-Z][A-Z0-9_]{3,})\"", line)
            if m and m.group(1) in const_uses:
                values.setdefault(m.group(1), {"value": m.group(2), "defined_at": "%s:%d" % (path.split("/")[-1], n)})
    unresolved = [c for c in const_uses if c not in values]
    emitted = {}
    for const, where in const_uses.items():
        if const in values:
            emitted.setdefault(values[const]["value"], []).extend(
                ["via %s at %s" % (const, w) for w in where])
    for lit, where in literal_uses.items():
        emitted.setdefault(lit, []).extend(["literal at %s" % w for w in where])
    return {"codes_emittable": sorted(emitted), "count": len(emitted),
            "per_code_sites": {k: v[:3] for k, v in sorted(emitted.items())},
            "constants_resolved": len(values), "constants_unresolved": sorted(unresolved),
            "resolution_note": "an unresolved CONST is reported as unresolved; it is NOT guessed at, "
                               "because a guessed value would widen or narrow a contract set by accident"}


def main():
    a = contract_named()
    b = server_emittable()
    sa, sb = set(a["codes_named_in_prose"]), set(b["codes_emittable"])
    out = {
        "tip": TIP,
        "contract": a,
        "server": b,
        "comparison": {
            "named_by_the_contract_only_A_minus_B": sorted(sa - sb),
            "emittable_by_the_server_only_B_minus_A": sorted(sb - sa),
            "in_both": sorted(sa & sb),
            "reading": "A-B are promises no code path keeps today; B-A are tokens a traveller can be "
                       "handed that the contract has never named. A declared enum that omits B-A would "
                       "make the ruler exempt a screen whose token is outside the set - the exact false "
                       "green ORD-0408 rejects - so the set must be B (what the server emits), reviewed "
                       "against A, not A alone.",
        },
        "the_cell_this_is_about": {
            "file_line": "features/trash/JourneyTrashPanel.tsx:233",
            "verdict_under_r8": "RED, why CONTRACT_MISSING_ENUM, examples [] (no token was blamed)",
            "field_named_on_the_element": "reason_code",
        },
    }
    io.open(os.path.join(WORK, "reason_code_set_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("contract names %d, server emits %d, A-B %d, B-A %d" % (
        a["count"], b["count"], len(sa - sb), len(sb - sa)))
    print("B-A:", ", ".join(sorted(sb - sa)) or "none")
    print("A-B:", ", ".join(sorted(sa - sb)) or "none")
    print("unresolved constants:", ", ".join(b["constants_unresolved"]) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
