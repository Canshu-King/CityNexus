"""ORD-0556 follow-up, second leg: where do the twenty-one capital words actually come from?

The route sweep (route_sweep_dev_r1.py) counted words on screen. This leg answers a source-side question
for every distinct token it painted: does the literal all-caps word exist in the English half of the copy
dictionary, in another frontend file, in a server-side value (backend/app or contracts), or in none of
those? "None of those" is the interesting bucket -- a word the screen shows but no source string carries
can only arrive through code that upper-cases something at run time.

Scope, stated honestly: this is a WORD-PRESENCE read over the source tree at one generation. It proves a
string exists or does not exist; it does not attribute a specific painted text node on a specific screen
to a specific line. That per-slot attribution is the named gap in the delivery block, because the sweep's
teardown deleted the raw per-route reads that would have carried the painted text.

Zero product bytes: reads only, writes one receipt under review/.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
SWEEP_RECEIPT = ROOT / "review/ord0556/readouts/route_sweep_dev_20261004T180116Z.json"
DICT_FILE = "frontend/src/i18n/LocaleContext.tsx"
OUT_DIR = ROOT / "review/ord0556/readouts"


def git(*args: str) -> str:
    env = dict(os_environ_clean())
    return (subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env).stdout or "").strip()


def os_environ_clean() -> dict:
    env = dict(__import__("os").environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        env.pop(key, None)
    env["NO_PROXY"] = "*"
    return env


def tree_paths(ref: str, prefix: str) -> list[str]:
    out = git("ls-tree", "-r", "--name-only", ref, "--", prefix)
    return [p for p in out.split("\n") if p.strip()]


def blob(ref: str, path: str) -> str:
    env = os_environ_clean()
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-p", f"{ref}:{path}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    return r.stdout or ""


def section_bounds(text: str) -> tuple[int, int]:
    """Line ranges of the English table and the Chinese table, read from the file itself."""
    lines = text.split("\n")
    en_open = zh_open = None
    for i, line in enumerate(lines, 1):
        if re.match(r"^\s*const en\w*\s*:\s*Dict\s*=\s*\{", line):
            en_open = i
        if re.match(r"^\s*const (zhCN|zh)\w*\s*:\s*Dict\s*=\s*\{", line):
            zh_open = i
    if en_open is None or zh_open is None:
        raise SystemExit(f"ABORT dictionary table markers not found (en={en_open} zh={zh_open})")
    return (en_open, zh_open - 1), (zh_open, len(lines))


def value_form(line: str) -> str | None:
    """Shape of the copy value on a dictionary line: is the whole value shouting, or is the caps word
    embedded in a sentence? ORD-0556's ruling is that these are different classes of thing."""
    m = re.search(r'"\s*[^"]*"\s*:\s*"([^"]*)"', line)
    if not m:
        return None
    value = m.group(1)
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", value)
    if not words:
        return None
    caps = [w for w in words if w.isupper()]
    if len(caps) == len(words):
        return "LABEL_ALL_CAPS"
    if caps:
        return "PROSE_WITH_CAPS_WORD"
    return "PROSE_NO_CAPS"


def main() -> int:
    sweep = json.loads(SWEEP_RECEIPT.read_text(encoding="utf-8"))
    base_tip = sweep["generation"]["base_tip"]
    tokens = {
        "en": sweep["arms"]["en"]["tokens_total"],
        "zh": sweep["arms"]["zh"]["tokens_total"],
    }
    # routes each token was painted on, so a source hit can be read against the screens that showed it
    routes_by_token: dict[str, list[str]] = {}
    for arm in ("en", "zh"):
        for route, detail in sweep["arms"][arm]["per_route"].items():
            for tok in detail.get("tokens", []):
                routes_by_token.setdefault(tok, []).append(f"{arm}:{route}")

    dict_text = blob(base_tip, DICT_FILE)
    dict_sha = git("rev-parse", "--verify", f"{base_tip}:{DICT_FILE}")
    (en_lo, en_hi), (zh_lo, zh_hi) = section_bounds(dict_text)
    dict_lines = dict_text.split("\n")

    front_files = [p for p in tree_paths(base_tip, "frontend/src")
                   if p.endswith((".tsx", ".ts")) and p != DICT_FILE
                   and not p.startswith("frontend/src/generated/")]
    backend_files = [p for p in tree_paths(base_tip, "backend/app") if p.endswith(".py")]
    contract_files = [p for p in tree_paths(base_tip, "contracts") if p.endswith((".yaml", ".json", ".ts"))]

    # compiled bundle check is NOT part of this leg -- the sweep base is vite-dev, see FRONTSRC_BUILD_PREREQ
    front_text = {p: blob(base_tip, p) for p in front_files}
    back_text = {p: blob(base_tip, p) for p in backend_files}
    con_text = {p: blob(base_tip, p) for p in contract_files}

    per_token = {}
    for tok in sorted(set(tokens["en"]) | set(tokens["zh"])):
        pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![a-z0-9_])")
        dict_hits = []
        for n in range(en_lo, min(en_hi, len(dict_lines)) + 1):
            if pat.search(dict_lines[n - 1]):
                dict_hits.append({"line": n, "table": "en", "form": value_form(dict_lines[n - 1]),
                                  "text": dict_lines[n - 1].strip()[:110]})
        for n in range(zh_lo, min(zh_hi, len(dict_lines)) + 1):
            if pat.search(dict_lines[n - 1]):
                dict_hits.append({"line": n, "table": "zh", "form": value_form(dict_lines[n - 1]),
                                  "text": dict_lines[n - 1].strip()[:110]})
        front_hits = []
        for path, text in front_text.items():
            for n, line in enumerate(text.split("\n"), 1):
                if pat.search(line):
                    front_hits.append({"path": path, "line": n, "text": line.strip()[:110]})
        server_hits = []
        for bucket, mapping in (("backend", back_text), ("contracts", con_text)):
            for path, text in mapping.items():
                for n, line in enumerate(text.split("\n"), 1):
                    if pat.search(line):
                        server_hits.append({"bucket": bucket, "path": path, "line": n,
                                            "text": line.strip()[:110]})
        en_dict_hits = [h for h in dict_hits if h["table"] == "en"]
        forms = {h["form"] for h in en_dict_hits}
        if "LABEL_ALL_CAPS" in forms:
            source = "DICT_LABEL_ALL_CAPS"
        elif en_dict_hits:
            source = "DICT_PROSE_CAPS_WORD"
        elif server_hits:
            source = "SERVER_ECHO_CANDIDATE"
        elif front_hits:
            source = "OTHER_FRONTEND_LITERAL"
        else:
            source = "NOT_IN_SOURCE_STRINGS"
        per_token[tok] = {
            "seen_on": sorted(routes_by_token.get(tok, [])),
            "arms": sorted({e.split(":", 1)[0] for e in routes_by_token.get(tok, [])}),
            "source_class": source,
            "dict_en_forms": sorted({h["form"] for h in en_dict_hits if h["form"]}),
            "dict_en_hits": en_dict_hits,
            "dict_zh_hits": [h for h in dict_hits if h["table"] == "zh"],
            "other_frontend_hits": front_hits[:6],
            "server_hits": server_hits[:6],
            "counts": {"dict_en": len(en_dict_hits), "dict_zh": len([h for h in dict_hits if h["table"] == "zh"]),
                       "other_frontend": len(front_hits), "server": len(server_hits)},
        }

    kinds = {}
    for tok, row in per_token.items():
        kinds[row["source_class"]] = kinds.get(row["source_class"], 0) + 1

    doc = {
        "generation": {
            "base_tip": base_tip,
            "dict_blob": dict_sha,
            "dict_file": DICT_FILE,
            "dict_table_line_ranges": {"en": [en_lo, en_hi], "zh": [zh_lo, zh_hi]},
            "files_scanned": {"frontend_src": len(front_files), "backend_app": len(backend_files),
                              "contracts": len(contract_files)},
            "sweep_receipt": str(SWEEP_RECEIPT.relative_to(ROOT)).replace("\\", "/"),
            "sweep_receipt_sha256": hashlib.sha256(SWEEP_RECEIPT.read_bytes()).hexdigest(),
            "recorded_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "read_kind": "source-side word presence; no browser, no product write",
        },
        "tokens": {"en_distinct": len(tokens["en"]), "zh_distinct": len(tokens["zh"])},
        "source_class_counts": kinds,
        "class_roster": {c: sorted(t for t, r in per_token.items() if r["source_class"] == c)
                         for c in sorted(kinds)},
        "per_token": per_token,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"token_source_probe_{doc['generation']['recorded_at']}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"receipt": str(out.relative_to(ROOT)).replace("\\", "/"),
                      "source_class_counts": kinds,
                      "en_distinct": len(tokens["en"]), "zh_distinct": len(tokens["zh"])},
                     ensure_ascii=False))
    for tok, row in per_token.items():
        print(f"{tok} {row['source_class']} dict_en={row['counts']['dict_en']} "
              f"other_frontend={row['counts']['other_frontend']} server={row['counts']['server']} "
              f"on={'、'.join(row['seen_on'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
