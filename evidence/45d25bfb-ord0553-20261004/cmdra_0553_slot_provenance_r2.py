"""ORD-0553 r7 -- slot-level provenance ruler: a painted machine word is a server word only when the
component that paints it can actually be reading a contract value, not merely when the same letters appear
in some response.

Why this exists: the r5 census classified `SELECTED` and `COMMITMENT` as server words because those exact
strings were also answered by the backend that run.  Reading the emit sites (r6) proved both are this app's
own dictionary wording (`studio.noStaySelected`, `intel.commitment`), so string equality alone is a blind
rule and it produced two false positives.

This pass classifies every token the r5 walk painted into exactly three buckets --
  copy-word      the token occurs as a word inside a value of the app's own copy tables,
  contract-word  the token is a member of a status/type Literal the backend can answer,
  undetermined   neither, which is the shortlist a human should look at --
and it must satisfy five arms, including two negative controls (the false positives land in copy-word) and
one positive control (the pre-r2 generation's ARRIVED/COMPLETED land in contract-word, and are NOT painted
on the current generation).

Reads only local files and already-published readings; touches no browser, no port, no database.
"""
import glob
import io
import json
import os
import re
import sys

WT = r"D:/moodle/_qoder_cmdra_ord0553_r2_20261003\wt"
R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
EV = os.path.join(R1, "_evidence")
WORDS = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*\b")


def read(rel):
    return io.open(os.path.join(WT, rel.replace("/", os.sep)), encoding="utf-8", errors="replace").read()


copy_files = [os.path.join(WT, *rel.split("/")) for rel in (
    "frontend/src/i18n/LocaleContext.tsx", "frontend/src/lib/displayVocabulary.ts",
    "frontend/src/i18n/travelerLabels.ts", "frontend/src/features/planning/planRankingCopy.ts")]
copy_files += glob.glob(os.path.join(WT, "frontend", "src", "**", "*Copy.ts"), recursive=True)
out_path = os.environ.get("R7_REPORT_PATH") or os.path.join(EV, "r7b_slot_provenance_report.json")
copy_values = set()
copy_words = {}
for p in set(copy_files):
    if not os.path.isfile(p):
        continue
    text = io.open(p, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'"([^"\n]{2,120})"', text):
        val = m.group(1)
        if re.search(r"[A-Z]{4,}", val):
            copy_values.add(val.strip().upper())
        for w in WORDS.findall(val):
            if len(w) >= 4:
                copy_words.setdefault(w, []).append(os.path.relpath(p, WT).replace("\\", "/"))

contract_words = set()
schema = read("backend/app/schemas.py")
for lit in re.findall(r"\b(?:status|state|kind|mode|result_status|trigger_kind|provider_status)\w*:\s*Literal\[([^\]]+)\]", schema):
    for tok in re.findall(r'"([A-Z][A-Z0-9_]{3,})"', lit):
        contract_words.add(tok)

walk_en = json.load(io.open(os.path.join(EV, "r5_walk_en_49861.json"), encoding="utf-8"))
walk_zh = json.load(io.open(os.path.join(EV, "r5_walk_zh_49861.json"), encoding="utf-8"))
dirty_gen = json.load(io.open(os.path.join(EV, "r3_ctx_en_arrived_49852.json"), encoding="utf-8"))


def tokens_of(walk):
    out = {}
    for route, r in walk["perRoute"].items():
        for h in r["hits"]:
            out.setdefault(h["token"], []).append({"route": route, "line": (h.get("text_head") or h.get("node_text") or "")[:90],
                                                  "standalone": bool(h.get("standalone_line")), "buckets": classify_hit(h)})
    return out


def classify_hit(h):
    tok = h["token"]
    line = (h.get("text_head") or h.get("node_text") or tok).strip().upper()
    buckets = []
    if line in copy_values or (tok in copy_words and line != tok and tok in line):
        buckets.append("copy-word")
    if tok in contract_words:
        buckets.append("contract-word")
    if tok in contract_words or tok.replace("_", " ") in contract_words or tok in {c.replace("_", " ") for c in contract_words}:
        buckets.append("contract-word")
    space_forms = {c.replace("_", " ") for c in contract_words if "_" in c}
    if any(f and f in line for f in space_forms):
        buckets.append("contract-word")
    if not buckets:
        buckets.append("undetermined")
    return sorted(set(buckets))


en_tokens = tokens_of(walk_en)
zh_tokens = tokens_of(walk_zh)
sys.stderr.write("copy_values={} copy_words={} contract={} ".format(len(copy_values), len(copy_words), len(contract_words)))
table = {t: {"routes": sorted(set(x["route"] for x in v)), "count": len(v),
             "buckets": sorted(set(b for x in v for b in x["buckets"])),
             "lines": sorted(set(x["line"] for x in v))[:2],
             "standalone": any(x["standalone"] for x in v),
             "copy_sources": sorted(set(copy_words.get(t, [])))[:3]} for t, v in sorted(en_tokens.items())}
undetermined = sorted(t for t in table if table[t]["buckets"] == ["undetermined"])
both = sorted(t for t in table if "copy-word" in table[t]["buckets"] and "contract-word" in table[t]["buckets"])
dirty_hits = [{"token": h["token"], "line": (h.get("node_text") or h.get("text_head") or "")[:60],
               "buckets": classify_hit({"token": h["token"], "text_head": h.get("node_text") or h.get("text_head")})}
              for h in dirty_gen["hits"] if h["token"] in ("ARRIVED", "COMPLETED", "PROGRESS")]

dirty_tokens = sorted({h["token"] for h in dirty_gen["hits"] if h["token"] in ("ARRIVED", "COMPLETED", "PROGRESS")})
en_painted = set(en_tokens)
arms = []
arms.append({"id": "every_painted_token_classified", "ok": len(table) == len(en_tokens) and all(v["buckets"] for v in table.values()),
             "observed": "%d tokens in the en walk, all bucketed" % len(table)})
arms.append({"id": "false_positive_SELECTED_is_copy_word", "ok": "copy-word" in table["SELECTED"]["buckets"],
             "observed": "SELECTED buckets=%s line=%s sources=%s" % (table["SELECTED"]["buckets"], table["SELECTED"]["lines"], table["SELECTED"]["copy_sources"])})
arms.append({"id": "false_positive_COMMITMENT_is_copy_word", "ok": "copy-word" in table["COMMITMENT"]["buckets"],
             "observed": "COMMITMENT buckets=%s sources=%s" % (table["COMMITMENT"]["buckets"], table["COMMITMENT"]["copy_sources"])})
arms.append({"id": "contract_status_names_are_server_words", "ok": all(t in contract_words for t in ("ARRIVED", "COMPLETED", "SKIPPED")),
             "observed": "contract universe=%d names, sample=%s" % (len(contract_words), ",".join(sorted(x for x in contract_words if x in ("ARRIVED", "COMPLETED", "SKIPPED", "PLANNED", "READY"))[:5]))})
_missing = sorted({d["token"] for d in dirty_hits if "contract-word" not in d["buckets"]})
_overs = sorted(en_painted & {d["token"] for d in dirty_hits})
arms.append({"id": "positive_control_dirty_generation_would_flag",
             "ok": bool(dirty_hits) and not _missing and not _overs,
             "observed": "pre-r2 painted %d hits %s; tokens NOT bucketed contract-word=%s; still painted on this generation=%s" % (
                 len(dirty_hits), sorted({d["token"] for d in dirty_hits}), _missing, _overs)})
arms.append({"id": "no_undetermined_left_silent", "ok": True,
             "observed": "undetermined shortlist (%d): %s" % (len(undetermined), " / ".join(undetermined))})
arms.append({"id": "zh_arm_has_no_contract_word",
             "ok": not [t for t, v in zh_tokens.items() if any("contract-word" in x["buckets"] for x in v)],
             "observed": "zh tokens painted=%s buckets=%s" % (
                 sorted(zh_tokens), {t: sorted(set(b for x in v for b in x["buckets"])) for t, v in zh_tokens.items()})})

report = {"instrument": "cmdra_0553_slot_provenance_r2", "report_path": None, "worktree_head": None,
          "copy_word_universe": len(copy_words), "contract_word_universe": sorted(contract_words),
          "en_walk": {"entry": walk_en["entryAssets"], "tokens": len(en_tokens),
                      "painted_hits": sum(v["count"] for v in table.values())},
          "zh_walk": {"entry": walk_zh["entryAssets"], "tokens": len(zh_tokens)},
          "dual_bucket_tokens": both, "undetermined": undetermined, "table": table,
          "copy_value_lines": len(copy_values), "dirty_generation_hits": dirty_hits,
          "arms": [{"id": a["id"], "verdict": "PASS" if a["ok"] else "FAIL", "observed": a["observed"]} for a in arms],
          }
head = os.popen("git -C \"%s\" rev-parse HEAD" % WT).read().strip()
report["worktree_head"] = head
report["report_path"] = out_path
reds = [a["id"] for a in report["arms"] if a["verdict"] == "FAIL"]
report["verdict"] = "RED" if reds else "GREEN"
report["red_arms"] = reds
out = out_path
io.open(out, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({"out": out, "head": head, "verdict": report["verdict"], "red_arms": reds,
                  "copy_universe": report["copy_word_universe"], "contract_universe": len(contract_words),
                  "en_tokens": len(en_tokens), "undetermined": undetermined,
                  "dual_bucket": both}, ensure_ascii=False, indent=1))
for a in report["arms"]:
    print(" ", a["verdict"], a["id"], "|", a["observed"][:150])
sys.exit(1 if reds else 0)
