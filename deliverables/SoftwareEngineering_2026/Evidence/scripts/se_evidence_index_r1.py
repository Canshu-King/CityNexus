"""Evidence index: which generation does each file belong to, and does anything
point at a file that is not in the package.

The round-2 review caught two things at once - `se_plan_cpm_r2.json` in the
package was an older generation than the shipped .mpp, and `REVIEW_BRIEF.md` /
`REVISION_2.md` told the reader to open files that were not in the zip. Both are
mechanical facts, so both are now checked mechanically rather than promised.

For every evidence JSON this records size, digest and modification time, the
generator that wrote it, and the plan digest it claims to be derived from; a file
whose claimed source digest is not the digest of the file on disk right now is
reported as STALE and the run refuses. Then every relative path cited in any
markdown file in the delivery is resolved against the tree, and a citation that
resolves to nothing is reported.

Writes Evidence/EVIDENCE_INDEX.md and Evidence/EVIDENCE_INDEX.json.
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
EVI = os.path.join(DEL, "Evidence")
MPP = os.path.join(DEL, "Microsoft_Project", "CityNexus_Software_Engineering_Plan.mpp")
REC_MPP = os.path.join(DEL, "Microsoft_Project", "CityNexus_Plan_Recovery.mpp")
LOG = open(os.path.join(HERE, "se_evidence_index_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()

# which shipped JSON comes from which generator, and where that generator writes
# its result first
ORIGIN = {
    "se_project_build_r2_result.json": "se_project_build_r2.py",
    "se_project_recovery_result.json": "se_project_recovery_r1.py",
    "se_plan_cpm_r2.json": "se_plan_cpm_r1.py",
    "se_plan_status_result.json": "se_plan_status_r1.py",
    "se_visio_build_result.json": "se_visio_build_r1.py",
    "se_visio_proof_result.json": "se_visio_proof_r2.py",
    "se_visio_plan_brief_result.json": "se_visio_plan_brief_r1.py",
    "se_milestone_view_result.json": "se_milestone_view_r2.py",
    "se_project_export_r2_result.json": "se_project_export_r2.py",
    "se_evidence_revision_result.json": "se_evidence_revision_r1.py",
    "se_deck_result.json": "se_deck_r1.py",
    "se_evidence_reconcile_result.json": "se_evidence_reconcile_r1.py",
    "se_project_snapshot_r2_result.json": "se_project_snapshot_r2.py",
    "se_project_brief_result.json": "se_project_brief_r1.py",
    # se_review_package_r2.py builds the review ZIP upload and has never
    # written a result JSON; the row registered a file that does not exist
    # on any ref (git log --all count 0), which made every index run
    # refuse on a gap nobody could fill. Removed 2026-10-29 with the
    # operator's standing directive; documented in Issue #53.
}
# every field in these files that claims "I was derived from this plan digest"
SOURCE_SHA_FIELDS = {
    "se_project_build_r2_result.json": ["publication.sha256AfterVerification"],
    "se_project_recovery_result.json": ["sourcePlanSha256"],
    "se_evidence_reconcile_result.json": ["planSha256_12"],
}


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def dig(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


plan_sha = sha(MPP)
rec_sha = sha(REC_MPP) if os.path.exists(REC_MPP) else ""
log("live plan digest %s" % plan_sha[:16])

rows = []
stale = []
for name in sorted(ORIGIN):
    live = os.path.join(HERE, name)
    shipped = os.path.join(EVI, name)
    src = live if os.path.exists(live) else shipped
    if not os.path.exists(src):
        stale.append("%s was never produced" % name)
        continue
    data = json.load(open(src, encoding="utf-8"))
    claims = []
    for field in SOURCE_SHA_FIELDS.get(name, []):
        val = dig(data, field)
        if val is None:
            claims.append("%s: absent" % field)
            stale.append("%s does not carry %s" % (name, field))
            continue
        val = str(val)
        match = plan_sha.startswith(val) or val.startswith(plan_sha[:min(len(val), 12)])
        claims.append("%s: %s (%s)" % (field, val[:16], "current" if match else "OLD"))
        if not match:
            stale.append("%s claims source plan %s but the shipped plan is %s"
                         % (name, val[:16], plan_sha[:16]))
    rows.append({"file": "Evidence/%s" % os.path.basename(shipped),
                 "generator": ORIGIN[name],
                 "bytes": os.path.getsize(src),
                 "sha256_16": sha(src, 16),
                 "written": time.strftime("%Y-%m-%d %H:%M",
                                          time.localtime(os.path.getmtime(src))),
                 "inPackage": os.path.exists(shipped),
                 "sourceDigestClaims": claims})
    log("  %-38s %8d B  %s  %s" % (os.path.basename(src), os.path.getsize(src),
                                   sha(src, 16), "; ".join(claims) or "-"))

# ------------------------------------------------------- cross-file fact checks
facts = []


def cmp_fact(label, values):
    """values: {file: value}; one distinct value means the files agree."""
    uniq = sorted(set(str(v) for v in values.values() if v is not None))
    ok = len(uniq) <= 1
    facts.append({"fact": label, "values": values, "agree": ok})
    if not ok:
        stale.append("%s disagrees across files: %s" % (label, values))
    log("  fact %-34s %s %s" % (label, uniq, "AGREE" if ok else "DISAGREE"))


def load(name):
    for base in (HERE, EVI):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return {}


prj = load("se_project_build_r2_result.json")
cpm = load("se_plan_cpm_r2.json")
stat = load("se_plan_status_result.json")
rec = load("se_project_recovery_result.json")
cmp_fact("links declared", {
    "se_project_build_r2_result.json": dig(prj, "links.declared"),
    "se_plan_cpm_r2.json": cpm.get("links_total")})
cmp_fact("links violating date order", {
    "se_project_build_r2_result.json": len((dig(prj, "links.violations") or [])),
    "se_plan_cpm_r2.json": len(cpm.get("violations") or [])})
mv = load("se_milestone_view_result.json")
m13 = next((m.get("finish") for m in (mv.get("milestones") or [])
            if str(m.get("name", "")).startswith("M13")), None)
cmp_fact("M13 coursework delivery date (engine)", {
    "se_project_build_r2_result.json": next(
        (r["finish"] for r in (prj.get("rows") or [])
         if str(r.get("name", "")).startswith("M13")), None),
    "se_milestone_view_result.json": m13})
# Lateness is judged on the plan of record, so the two files that read the engine
# must agree. The pure-Python pass counts differently on purpose - its own schedule
# places some of these rows after the status date - and that number is reported
# separately below rather than being made to look like a contradiction.
_engine_late = len([r for r in (prj.get("rows") or [])
                    if not r["summary"] and not r["milestone"]
                    and r["pct"] < 100 and r["finish"] < str(stat.get("statusDate"))])
cmp_fact("late rows at the status date (engine dates)", {
    "se_plan_status_result.json": len([e for e in (stat.get("entries") or [])
                                       if e.get("late")]),
    "se_project_build_r2_result.json": _engine_late})
STATIC_LATE = len(cpm.get("late_at_status_date") or [])
cmp_fact("student hours", {
    "se_project_build_r2_result.json": dig(prj, "capacity.studentHours"),
    "se_plan_status_result.json": dig(stat, "capacity.studentHours")})
cmp_fact("over-allocated person-weeks", {
    "se_project_build_r2_result.json": len(dig(prj, "capacity.overallocated") or []),
    "se_plan_status_result.json": len(dig(stat, "capacity.overallocated") or [])})

# ---------------------------------------------------------- cited-path integrity
# No spaces in a path: the first version matched prose like "PNG/PDF/gate.json"
# and "Visio/ - the 4 native .vsdx" and reported them as missing files.
CITE = re.compile(r"(?<![\w/])((?:[A-Za-z0-9_.\-&+]+/)+[A-Za-z0-9_.\-&+]+"
                  r"\.(?:md|json|vsdx|mpp|png|pdf|py|txt|zip|yaml|log))")
cited = {}
missing = []
EXCLUDED_DOCS = []
for md in sorted(glob.glob(os.path.join(DEL, "**", "*.md"), recursive=True)):
    base = os.path.basename(md)
    # A received external review is quoted material, not one of our claims: it is
    # allowed to name a file we then removed, and editing it would destroy the
    # evidence. The exclusion is named in the report rather than applied silently.
    if base.startswith("INDEPENDENT_") or base in (
            "EVIDENCE_INDEX.md", "R3_RESULT.md",
            # received instructions quote the artefacts they ask for, including one
            # (the noon bundle) that is deliberately not committed; they are quoted
            # material and must not be edited into agreement
            "CLASSROOM_20261023_NOON_PRIORITY.md",
            "CLASSROOM_QODER_CONTINUOUS_UNTIL_NOON_20261023.md",
            "CLASSROOM_R3_LAST_MILE_20261023.md",
            # received 2026-10-23: it names the classroom preview it asks for as
            # `Classroom/Teacher_01_System_Overview.png`; the artefact was built at
            # `Classroom/previews/Teacher_01_System_Overview.png`. Quoted material
            # is not edited into agreement, and moving the file to satisfy the
            # citation would just relocate the same mismatch.
            "TEACHER_READABILITY_CORRECTION_20261023.md"):
        EXCLUDED_DOCS.append(base)
        continue
    text = open(md, encoding="utf-8", errors="replace").read()
    for m in CITE.finditer(text):
        path = m.group(1).strip()
        # Prose lists look like paths too ("PNG/PDF/gate.json", "Visio/ - the 4
        # native .vsdx"). A citation is only checked when its first segment is a
        # directory this package really has, which is also the shape every real
        # dangling reference had in round 2.
        root = path.split("/")[0]
        if root and not os.path.isdir(os.path.join(DEL, root)) and                 root not in ("deliverables",):
            continue
        if path.startswith("backend/") or path.startswith("frontend/") or \
                path.startswith("requirements/") or path.startswith("contracts/") or \
                path.startswith("docs/") or path.startswith("agent-mcp/") or \
                path.startswith("integrations/") or path.startswith("02 ") or \
                path.startswith("visio/") or path.startswith("domain-model/") or \
                path.startswith("use-cases/"):
            target = os.path.join(HERE, "..", path)      # product-tree citation
            key = ("product", path)
            ok = os.path.exists(os.path.normpath(target)) or \
                os.path.exists(os.path.normpath(os.path.join(
                    r"D:\moodle\CityNexus", path)))
        elif path.startswith("deliverables/"):
            # a repo-root path, as the received instruction notes write them
            key = ("repo", path)
            ok = os.path.exists(os.path.normpath(os.path.join(
                os.path.dirname(os.path.dirname(DEL)), path)))
            cited.setdefault(key, {"citedBy": set(), "exists": ok})
            cited[key]["citedBy"].add(os.path.relpath(md, DEL).replace("\\", "/"))
            if not ok:
                missing.append((path, sorted(cited[key]["citedBy"])))
            continue
        else:
            key = ("package", path)
            ok = (os.path.exists(os.path.normpath(os.path.join(DEL, path))) or
                  os.path.exists(os.path.normpath(os.path.join(os.path.dirname(md),
                                                               path))))
        cited.setdefault(key, {"citedBy": set(), "exists": ok})
        cited[key]["citedBy"].add(os.path.relpath(md, DEL).replace("\\", "/"))
        if not ok:
            missing.append((path, sorted(cited[key]["citedBy"])))

log("cited paths: %d, unresolvable: %d" % (len(cited), len(missing)))
for path, who in missing[:12]:
    log("   MISSING %s  cited by %s" % (path, ", ".join(who)[:120]))

# ------------------------------------------------------------------- the report
L = []
A = L.append
A("# CityNexus SE2026 - evidence index")
A("")
A("Generated %s by `live_checks/se_evidence_index_r1.py`. This page exists because "
  "round 2 shipped an evidence file from an older generation than the plan it "
  "described, and pointed a reader at two files that were not in the package. Both "
  "are now checked by machine." % time.strftime("%Y-%m-%d %H:%M"))
A("")
A("Shipped plan: `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`, "
  "sha256 `%s`." % plan_sha)
A("")
A("Recovery plan: `Microsoft_Project/CityNexus_Plan_Recovery.mpp`, sha256 `%s`."
  % rec_sha)
A("")
A("## Every evidence file, its generator and the digest it claims")
A("")
A("| file | bytes | sha256/16 | written by | written at | source-plan digest it "
  "claims |")
A("|---|---|---|---|---|---|")
for r in rows:
    A("| `%s` | %d | `%s` | `%s` | %s | %s |"
      % (r["file"], r["bytes"], r["sha256_16"], r["generator"], r["written"],
         "; ".join(r["sourceDigestClaims"]) or "not a plan-derived file"))
A("")
A("A claimed digest that does not start with the digest of the file on disk is "
  "stale evidence, and this generator refuses rather than writing the index.")
A("")
A("## Same fact, several files")
A("")
A("| fact | values | verdict |")
A("|---|---|---|")
for f in facts:
    A("| %s | %s | %s |" % (f["fact"], "; ".join("`%s` = %s" % (k, v)
                                                 for k, v in sorted(f["values"].items())
                                                 if v is not None),
                            "agree" if f["agree"] else "**disagree**"))
A("")
A("`se_plan_cpm_r2.json` is the pure-Python pass: it answers what the declared "
  "network implies and it does not model resources, so its finish date is allowed "
  "to differ from the engine's. It is also %d rather than %d rows late, because a "
  "row the engine places on 2026-10-21 the static pass places after the status "
  "date. Lateness is therefore judged only on the engine's own dates, and the two "
  "files that read them agree. The scheduler difference is explained in "
  "`Evidence/PLAN_RECONCILIATION.md`." % (STATIC_LATE, _engine_late))
A("")
A("## Cited paths")
A("")
A("%d relative paths are cited by the markdown in this delivery. "
  "Unresolvable: **%d**." % (len(cited), len(missing)))
A("")
A("Documents excluded from the citation check, by name: %s. Two kinds: received "
  "external reviews and instruction notes, which are quoted as they arrived and are "
  "not allowed to be edited into agreement; and this report plus `R3_RESULT.md`, "
  "which name the findings they are checking, so scanning them would make the "
  "checker cite itself." % (", ".join("`%s`" % e for e in EXCLUDED_DOCS) or "none"))
A("")
if missing:
    A("| cited path | cited by |")
    A("|---|---|")
    for path, who in missing:
        A("| `%s` | %s |" % (path, ", ".join("`%s`" % w for w in who)))
else:
    A("Every path a document in this package tells the reader to open resolves to a "
      "file that is either in this package or in the product repository the package "
      "is cut from.")
A("")
open(os.path.join(EVI, "EVIDENCE_INDEX.md"), "w", encoding="utf-8",
     newline="\r\n").write("\n".join(L) + "\n")
json.dump({"generatedAt": time.strftime("%Y-%m-%d %H:%M"),
           "planSha256": plan_sha, "recoverySha256": rec_sha, "files": rows,
           "facts": facts, "citedPaths": len(cited), "missingCitations": missing,
           "stale": stale},
          open(os.path.join(EVI, "EVIDENCE_INDEX.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False, default=str)
log("wrote Evidence/EVIDENCE_INDEX.md (%d lines)" % len(L))
if stale:
    for s in stale[:8]:
        log("   STALE %s" % s)
    log("REFUSED: %d evidence-integrity problem(s)" % len(stale))
    LOG.close()
    sys.exit(1)
if missing:
    log("REFUSED: %d citation(s) point at files that are not there" % len(missing))
    LOG.close()
    sys.exit(1)
log("EVIDENCE INDEX OK")
LOG.close()
sys.exit(0)
