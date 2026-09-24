"""ORD-0274 ordering step 1: a generation is its BYTES, judged with the Q20 ruler's own functions.

Commander's Q20 ruling was that I must stop inferring 换代 from index membership or file names, and the
coordinates he named are this ruler:
  subject  live_checks/deploy_bundle_v2_draft_r4.py   blob 0686670743c079647aa678370aa5481562c4c0a8
  in-store live_checks/deploy_bundle.py               blob 149e9c6dbe6debcac92041bb192761c1cf1aa2a7 (untouched)

So this module does not re-implement a judgement. It takes the ruler's own three pure functions
(`strip_js_comments`, `sw_register_verdict`, `_ord0277_generation_verdict`) plus `asset_refs`, extracts
them by AST from the verified copy (blob sha re-computed at import, fail closed), and applies them to the
bytes of a generation - read from disk or fetched over HTTP.

What "old -> new" means then, per layer, all three reported separately:
  bytes_fingerprint          sha256 over sorted "ref:sha256(bytes)" pairs + the index bytes
  content_fingerprint   the same pairs with the NAMES removed  -> a rename cannot fake a 换代
  generation_verdict         the ruler's registration contract over the index-named scripts

--selftest builds the fixtures a filename judge would get wrong and requires both directions for every
strictness (killers plus their positive controls), so an arm that is merely vacuous cannot pass.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RULER = pathlib.Path(os.environ.get("CNX_RULER_PATH")
                     or r"D:\moodle\_qoder_b_ord0274sw_20260924\deploy_bundle_v2_draft_r4.py")
RULER_BLOB = "0686670743c079647aa678370aa5481562c4c0a8"
WANT_FNS = ("strip_js_comments", "sw_register_verdict", "_ord0277_generation_verdict", "asset_refs",
            "precache_urls")
WANT_CONSTS = ("SW_REGISTER_RULE", "DECLARED_NO_PRECACHE")


def blob_sha(path: pathlib.Path) -> str | None:
    """Git's own hash-object, so the coordinate means the same thing to every other lane."""
    r = subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (r.stdout or "").strip() or None


def load_ruler() -> dict:
    sha = blob_sha(RULER)
    if sha != RULER_BLOB:
        raise SystemExit(f"RULER_NOT_THE_ADVERTISED_BLOB got={sha} want={RULER_BLOB} path={RULER}")
    src = RULER.read_text(encoding="utf-8")
    keep, found = [], set()
    for node in ast.parse(src).body:
        name = getattr(node, "name", None)
        if isinstance(node, ast.FunctionDef) and name in WANT_FNS:
            keep.append(ast.get_source_segment(src, node))
            found.add(name)
            continue
        if isinstance(node, ast.Assign):
            targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
            hit = targets & set(WANT_CONSTS)
            if hit:
                keep.append(ast.get_source_segment(src, node))
                found.update(hit)
    missing = set(WANT_FNS) - {n for n in found if n in WANT_FNS}
    if missing:
        raise SystemExit(f"RULER_EXTRACT_INCOMPLETE missing={sorted(missing)} in {RULER.name}")
    ns: dict = {"re": re, "json": json}
    exec("\n\n".join(k for k in keep if k), ns)
    ns["_provenance"] = {"path": str(RULER), "blob_sha": sha,
                         "extracted": sorted(found), "bytes_extracted": sum(len(k.encode("utf-8")) for k in keep)}
    return ns


R = load_ruler()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _pairs_fingerprint(per: dict, include_names: bool, index_sha: str | None) -> str:
    """Two gauges, deliberately different:

    bytes_fingerprint   every index-named script as "ref=sha256" plus the index bytes -> the identity of
                        the graph the user was served.  A rename moves it, because the index moved too.
    content_fingerprint the script sha256 values alone, names and index dropped -> the CODE level.  A pure
                        rename leaves it where it was, so "old -> new" can never be paid for with a file
                        name, which is exactly what Q20 forbids me from inferring.
    """
    if include_names:
        seg = "|".join(f"{ref}={per[ref]['sha256']}" for ref in sorted(per))
        if index_sha:
            seg += f"||index={index_sha}"
    else:
        seg = "|".join(sorted(v["sha256"] for v in per.values()))
    return _sha(seg.encode("utf-8"))


def identity(label: str, index_bytes: bytes, body_of) -> dict:
    """`body_of(ref) -> bytes | None` for every script the built index names."""
    index_text = index_bytes.decode("utf-8", "replace")
    refs = R["asset_refs"](index_text)
    js_refs = [r for r in refs if r.endswith(".js")]
    per, rows = {}, []
    for ref in js_refs:
        body = body_of(ref)
        text = body.decode("utf-8", "replace") if body is not None else None
        v = R["sw_register_verdict"](text, f"{label}:{ref}")
        v["ref"] = ref
        v["readable"] = text is not None
        v["sha256"] = _sha(body) if body is not None else None
        v["body_size"] = len(body) if body is not None else 0
        per[ref] = v
        rows.append({"ref": ref, "readable": v["readable"], "calls": v.get("calls"),
                     "unresolved": v.get("unresolved_registrations")})
    gen = R["_ord0277_generation_verdict"](rows)
    ix = _sha(index_bytes)
    out = {"label": label, "index_sha256": ix, "index_body_size": len(index_bytes),
           "index_named_refs": refs, "scripts_observed": js_refs,
           "per_script": per,
           "generation_verdict": gen["verdict"], "generation_reason": gen.get("reason"),
           "owner_refs": gen["owner_refs"],
           "register_calls_parsed_total": sum(len(p.get("calls") or []) for p in per.values()),
           "unresolved_total": sum(p.get("unresolved_registrations") or 0 for p in per.values()),
           "bytes_fingerprint": _pairs_fingerprint(per, True, ix),
           "content_fingerprint": _pairs_fingerprint(per, False, None),
           "ruler": R["_provenance"]}
    out["sw_bytes"] = None
    for c in (p.get("calls") or [] for p in per.values()):
        for e in c:
            if e.get("sw_url"):
                b = body_of(e["sw_url"])
                if b is not None:
                    out["sw_bytes"] = {"sw_url": e["sw_url"], "sha256": _sha(b), "body_size": len(b)}
                break
        if out["sw_bytes"]:
            break
    return out


def disk_body(dist: pathlib.Path):
    def get(ref: str) -> bytes | None:
        f = dist / ref.lstrip("/")
        return f.read_bytes() if f.is_file() else None
    return get


def http_body(base: str):
    def get(ref: str) -> bytes | None:
        try:
            with urllib.request.urlopen(base + ref, timeout=15) as r:
                if r.status != 200:
                    return None
                return r.read()
        except Exception:  # noqa: BLE001 - a body I cannot read is None, and None is RED downstream
            return None
    return get


def disk_identity(label: str, dist: pathlib.Path) -> dict:
    idx = dist / "index.html"
    if not idx.is_file():
        raise SystemExit(f"NO_INDEX for {label}: {idx}")
    return identity(label, idx.read_bytes(), disk_body(dist))


def served_identity(label: str, base: str) -> dict:
    return identity(label, http_body(base)("/") or b"", http_body(base))


def executed_binding(browser_shas: dict, served: dict) -> dict:
    """Prove the text the parser read is the bytes the document is executing.

    The browser hashes the body it fetched for each ref; python hashes the body it fetched for the same
    ref. Equal per-ref sha means the ruler's judgement was applied to the executing bytes, not to a copy.
    """
    rows = {}
    for ref, got in (browser_shas or {}).items():
        want = (served.get("per_script", {}).get(ref) or {}).get("sha256")
        rows[ref] = {"browser_sha256": got, "parser_side_sha256": want,
                     "equal": bool(got and want and got == want)}
    all_equal = bool(rows) and all(r["equal"] for r in rows.values())
    return {"per_ref": rows, "refs_compared": len(rows),
            "executed_equals_parsed": all_equal,
            "verdict": "GREEN" if all_equal else "RED"}


def refuse_if_unusable(gen: dict, what: str) -> None:
    """Fail closed: an arm run against a generation whose registration contract is RED proves nothing."""
    if gen["generation_verdict"] != "GREEN":
        raise SystemExit(f"UNUSABLE_GENERATION ({what}): {gen['label']} verdict={gen['generation_verdict']} "
                         f"reason={str(gen['generation_reason'])[:200]}")


# ---------------------------------------------------------------- selftest -----------------------------------------
ENTRY_TMPL = ('import("./{second}");\n'
              'navigator.serviceWorker.register("/v10-sw.js", {{scope: "/", updateViaCache: "{uvc}"}});\n'
              'export const gen = "{tag}";\n')
SW_BODY = b"self.addEventListener('install',e=>self.skipWaiting());"


def _mk_gen(root: pathlib.Path, *, entry_name: str, entry_bytes: bytes, dir_tag: str,
            second_name: str = "chunk.js", extra_scripts: tuple[str, ...] = ()) -> pathlib.Path:
    """One generation on disk. Only what the caller passes varies: the chunk body is a fixed constant, so
    F3 (rename) and F4 (same name, new bytes) each move exactly one thing."""
    d = root / dir_tag
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "assets" / entry_name).write_bytes(entry_bytes)
    (d / "assets" / second_name).write_bytes(b"export const chunk = 'constant';\n")
    (d / "v10-sw.js").write_bytes(SW_BODY)
    refs = [entry_name, second_name] + list(extra_scripts)
    (d / "index.html").write_text(
        '<!doctype html><html><body><div id="root"></div>'
        + "".join(f'<script type="module" src="/assets/{r}"></script>' for r in refs)
        + "</body></html>", "utf-8", newline="\n")
    return d


def selftest() -> int:
    arms = []
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cnx274ident_"))
    try:
        real_old = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923\genB\frontend\dist_ord0268")
        real_new = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_0274sw")

        # F1: two REAL generations.  Both must satisfy the ruler's contract, and their bytes must differ.
        if real_old.is_dir() and real_new.is_dir():
            g1a, g1b = disk_identity("real-old", real_old), disk_identity("real-new", real_new)
            arms.append({"arm": "F1_real_generations_both_green", "expect": "GREEN",
                         "got": {"verdict": "GREEN" if {g1a["generation_verdict"], g1b["generation_verdict"]} == {"GREEN"}
                                 else f'{g1a["generation_verdict"]}/{g1b["generation_verdict"]}',
                                 "error": str(g1a["generation_reason"])[:120] + " | " + str(g1b["generation_reason"])[:120]}})
            arms.append({"arm": "F2_real_generations_bytes_differ", "expect": "True",
                         "got": {"bytes_fingerprint": g1a["bytes_fingerprint"] != g1b["bytes_fingerprint"],
                                 "content_fingerprint": g1a["content_fingerprint"] != g1b["content_fingerprint"]}})
        else:
            arms.append({"arm": "F1_real_generations_both_green", "expect": "GREEN",
                         "got": {"error": f"missing dist old={real_old.is_dir()} new={real_new.is_dir()}"}})

        # F3 killer: a pure RENAME.  Same bytes, different file name -> the name judge says 换代, the
        # byte judge must say the content did not move.
        base_bytes = ENTRY_TMPL.format(second="chunk.js", uvc="none", tag="A").encode()
        a = _mk_gen(tmp / "rename", entry_name="index-A.js", entry_bytes=base_bytes, dir_tag="A")
        b = _mk_gen(tmp / "rename", entry_name="index-B.js", entry_bytes=base_bytes, dir_tag="B")
        ga, gb = disk_identity("rename-A", a), disk_identity("rename-B", b)
        arms.append({"arm": "F3_rename_only_is_not_a_content_change", "expect": "True",
                     "got": {"content_fingerprint_equal": ga["content_fingerprint"] == gb["content_fingerprint"],
                             "names_differ": ga["index_named_refs"] != gb["index_named_refs"]}})
        arms.append({"arm": "F3b_rename_still_moves_the_name_fingerprint", "expect": "True",
                     "got": {"bytes_fingerprint": ga["bytes_fingerprint"] != gb["bytes_fingerprint"]}})

        # F4 killer: SAME file name, different bytes -> the name judge sees no 换代, the byte judge must.
        c = _mk_gen(tmp / "samename", entry_name="index-S.js",
                    entry_bytes=ENTRY_TMPL.format(second="chunk.js", uvc="none", tag="A").encode(), dir_tag="C")
        d = _mk_gen(tmp / "samename", entry_name="index-S.js",
                    entry_bytes=ENTRY_TMPL.format(second="chunk.js", uvc="none", tag="D").encode(), dir_tag="D")
        gc, gd = disk_identity("same-C", c), disk_identity("same-D", d)
        arms.append({"arm": "F4_same_name_different_bytes_is_a_change", "expect": "True",
                     "got": {"content_fingerprint": gc["content_fingerprint"] != gd["content_fingerprint"],
                             "names_equal": (gc["index_named_refs"] == gd["index_named_refs"])}})

        # F5/F6: the registration parameters must be load-bearing in the byte judge, in both directions.
        bad = _mk_gen(tmp / "uvc", entry_name="index-A.js",
                      entry_bytes=ENTRY_TMPL.format(second="chunk.js", uvc="all", tag="E").encode(), dir_tag="E")
        ge = disk_identity("uvc-all", bad)
        arms.append({"arm": "F5_updateViaCache_all_in_bytes_is_RED", "expect": "RED",
                     "got": {"verdict": ge["generation_verdict"], "error": str(ge["generation_reason"])[:150]}})
        prose = _mk_gen(tmp / "uvc", entry_name="index-A.js",
                        entry_bytes=("// keep this comment: register(\"/v10-sw.js\", {scope:\"/\", updateViaCache:\"none\"})\n"
                                     + ENTRY_TMPL.format(second="chunk.js", uvc="all", tag="F")).encode(),
                        dir_tag="F")
        gf = disk_identity("prose-good-code-bad", prose)
        arms.append({"arm": "F6_good_call_in_a_comment_does_not_whiten_bad_code", "expect": "RED",
                     "got": {"verdict": gf["generation_verdict"], "error": str(gf["generation_reason"])[:150]}})
        prose_only = _mk_gen(tmp / "uvc", entry_name="index-A.js",
                             entry_bytes=("// register(\"/v10-sw.js\", {scope:\"/\", updateViaCache:\"all\"})\n"
                                          + ENTRY_TMPL.format(second="chunk.js", uvc="none", tag="G")).encode(),
                             dir_tag="G")
        gg = disk_identity("prose-bad-code-good", prose_only)
        arms.append({"arm": "F7_comment_claiming_all_does_not_blacken_good_code", "expect": "GREEN",
                     "got": {"verdict": gg["generation_verdict"], "error": str(gg["generation_reason"])[:150]}})

        # F8: no registration anywhere stays RED (the killer that made arm I exist).
        none_sw = _mk_gen(tmp / "none", entry_name="index-A.js",
                          entry_bytes=b"export const gen = 'H';\n", dir_tag="H")
        gh = disk_identity("no-registration", none_sw)
        arms.append({"arm": "F8_generation_without_any_registration_is_RED", "expect": "RED",
                     "got": {"verdict": gh["generation_verdict"], "error": str(gh["generation_reason"])[:150]}})

        # F9: a second chunk that names no registration must NOT be dragged in (multi-entry is legal).
        arms.append({"arm": "F9_silent_second_chunk_is_not_a_defect", "expect": "GREEN",
                     "got": {"verdict": gc["generation_verdict"],
                             "scripts_observed": len(gc["per_script"]),
                             "owners": gc["owner_refs"],
                             "error": str(gc["generation_reason"])[:150]}})

        # F10: an unresolved registration mention must be RED, not "partially read".
        unres = _mk_gen(tmp / "unres", entry_name="index-A.js",
                        entry_bytes=(ENTRY_TMPL.format(second="chunk.js", uvc="none", tag="I").encode()
                                     + b"const u = swUrl; navigator.serviceWorker.register(u, opts);\n"),
                        dir_tag="I")
        gi = disk_identity("variable-url-call", unres)
        arms.append({"arm": "F10_unparseable_second_call_is_RED", "expect": "RED",
                     "got": {"verdict": gi["generation_verdict"], "unresolved": gi["unresolved_total"],
                             "error": str(gi["generation_reason"])[:150]}})

        # F11: the refuse-if-unusable guard must fire on a RED generation and stay quiet on a GREEN one.
        refused = None
        try:
            refuse_if_unusable(ge, "selftest-F11")
        except SystemExit as e:
            refused = str(e)
        arms.append({"arm": "F11a_RED_generation_is_refused_as_a_host", "expect": "True",
                     "got": {"refused": bool(refused and refused.startswith("UNUSABLE_GENERATION"))}})
        quiet = True
        try:
            refuse_if_unusable(gc, "selftest-F11b")
        except SystemExit:
            quiet = False
        arms.append({"arm": "F11b_GREEN_generation_is_not_refused", "expect": "True",
                     "got": {"not_refused": quiet}})

        # F12/F13: the executed-binding judge needs its own two-way control, otherwise "the parsed text is
        # the executed bytes" is a sentence and not a measurement.
        fake_same = {r: v["sha256"] for r, v in gc["per_script"].items()}
        fake_diff = dict(fake_same)
        first = sorted(fake_diff)[0]
        fake_diff[first] = "0" * 64
        bind_ok, bind_bad = executed_binding(fake_same, gc), executed_binding(fake_diff, gc)
        arms.append({"arm": "F12_executed_equals_parsed_when_shas_agree", "expect": "GREEN",
                     "got": {"verdict": bind_ok["verdict"], "refs_compared": bind_ok["refs_compared"]}})
        arms.append({"arm": "F13_one_differing_ref_is_RED", "expect": "RED",
                     "got": {"verdict": bind_bad["verdict"], "error": f"refs_compared={bind_bad['refs_compared']}"}})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    for a in arms:
        exp, got = a["expect"], a["got"]
        facts = {k: v for k, v in got.items() if k != "error"}
        if exp in ("True", "False"):
            keys = sorted(facts)
            ok = all(bool(facts[k]) for k in keys) if exp == "True" else all(facts[k] is False for k in keys)
        else:
            ok = got.get("verdict") == exp
        a["derived"] = "MET" if ok else "NOT_MET"
        print(f"  {'MET    ' if ok else 'NOT_MET'} {a['arm']:52s} expect={exp:5s} got="
              f"{json.dumps(facts, ensure_ascii=False)[:120]}")
    met = sum(1 for a in arms if a["derived"] == "MET")
    print(f"\nselftest {met}/{len(arms)} MET  ruler blob={R['_provenance']['blob_sha'][:12]} "
          f"extracted={len(R['_provenance']['extracted'])} symbols {R['_provenance']['bytes_extracted']:,} B")
    p = pathlib.Path(os.environ.get("CNX_IDENT_SELFTEST",
                                   r"D:\moodle\_qoder_b_ord0274sw_20260924\ord0274_ident_selftest.json"))
    p.write_text(json.dumps({"ruler": R["_provenance"], "arms": [{k: v for k, v in a.items() if k != "_key"}
                                                                  for a in arms],
                             "met": met, "arms_total": len(arms)},
                            ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("->", p.name)
    return 0 if met == len(arms) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dist", nargs="+", default=[])
    ap.add_argument("--label", nargs="+", default=[])
    ap.add_argument("--base", nargs="+", default=[])
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    out = []
    for i, d in enumerate(a.dist):
        out.append(disk_identity((a.label[i] if i < len(a.label) else pathlib.Path(d).name), pathlib.Path(d)))
    for i, b in enumerate(a.base):
        out.append(served_identity((a.label[len(a.dist) + i] if len(a.dist) + i < len(a.label) else b), b))
    text = json.dumps({"ruler": R["_provenance"], "generations": out}, ensure_ascii=False, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text, "utf-8", newline="\n")
        print("->", a.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
