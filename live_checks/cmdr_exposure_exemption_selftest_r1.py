"""ORD-0408 two-way proof for the structured Q64 exemption ledger.

The claim being tested is narrow: an exemption is now DATA the ruler reads, and turning it on must not be able
to switch the no-growth arm off.  So every arm needs both directions, and a green from an instrument that never
spoke is worth nothing here:

  HELD entry   -> a cell in a dev-only face still grows the census (the shipped ledger changes nothing);
  ACTIVE entry -> the same cell is waived, BY NAME, and the receipt shows the ruler saw it;
  REAL product sink -> still red, even with the permissive ledger in force  <-- the required negative control;
  BLANKET grant -> the ruler withholds the census entirely and the door cannot read that as clean.

Nothing is pushed and no work tree is touched.  Poison commits are built with hash-object + read-tree /
update-index / commit-tree in a throwaway index on E:, so they exist only as dangling local objects.  The door
is run through its own main() with ONLY the ref resolver pointed at the local object store -- this lane does not
publish throwaway refs to GitHub.

  python cmdr_exposure_exemption_selftest_r1.py [--out FILE]
"""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time

STAGE = "E:/puguang0408/stage/live_checks"
LIVE = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = "E:/puguang0408/scratch"
LEDGERS = "E:/puguang0408/ledgers"
RECIPE = "E:/puguang0408/evidence"
TIP_TREE = "E:/puguang0408/frontend/src"
# The r8 door sits beside the r8 ruler; its OTHER imports (net guard, bundle builder) are shared instruments
# that live in the commander's instrument directory, exactly as they do for a real landing.  HERE goes first so
# this lane's fork is what gets tested, and LIVE is the fallback for the shared modules.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(LIVE)
os.chdir(HERE)

import preflight_and_land_r8 as gate  # noqa: E402

REPO = gate.REPO
SHIPPED_LEDGER = os.path.join(STAGE, "q64_exposure_exemptions.json")
R7B_BLOB = "e2ea5ce64ca67bb476006766db27b0612789dd36"
# The product-file regression the fleet already banned once, reused as the negative control: the pre-ORD-0323
# components/ProductErrorBoundary.tsx puts the reply's own sentence back into JSX text (the same bytes
# cmdr_exposure_arm_selftest_r1.py plants, which that script proves fires).
OLD_SHAPES = "09dffbb70c151e6734221d6d3d69d88775a1fbd0"
VICTIM_PRODUCT = "frontend/src/components/ProductErrorBoundary.tsx"
# The dev-only face under test: a VERBATIM copy of a file the tip already flags, placed sideways in its OWN
# directory so every relative import still resolves, and renamed to match E1's `**/*.stories.tsx` glob.
DONOR = "frontend/src/features/trip/ActivityDetail.tsx"
VICTIM_STORIES = "frontend/src/features/trip/Ord0408Probe.stories.tsx"


def blob_of(raw):
    return hashlib.sha1(b"blob %d" % len(raw) + chr(0).encode() + raw).hexdigest()


def git_bin(*args, **kw):
    env = dict(os.environ)
    if kw.get("idx"):
        env["GIT_INDEX_FILE"] = kw["idx"]
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, timeout=300, env=env,
                       input=kw.get("data"))
    if p.returncode:
        raise SystemExit("git %s rc %d: %s" % (" ".join(args[:2]), p.returncode,
                                               p.stderr.decode("utf-8", "replace")[:300]))
    return p.stdout.decode("utf-8", "replace").strip()


def show(rev, path):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)], capture_output=True, timeout=300)
    if p.returncode:
        raise SystemExit("FIXTURE BROKEN: no %s:%s" % (rev[:12], path))
    return p.stdout


def commit_with(path, content, parent, msg):
    blob = git_bin("hash-object", "-w", "--stdin", data=content)
    idx = os.path.join(tempfile.mkdtemp(prefix="ord0408_"), "idx")
    git_bin("read-tree", parent, idx=idx)
    git_bin("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, path), idx=idx)
    tree = git_bin("write-tree", idx=idx)
    return git_bin("commit-tree", tree, "-p", parent, "-m", msg), blob, tree


def write_ledger(name, entries):
    doc = json.load(io.open(SHIPPED_LEDGER, encoding="utf-8"))
    doc["entries"] = entries
    p = os.path.join(LEDGERS, name)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    return p


def measure(rev, tag, ledger_path=None):
    """One run of the DOOR'S OWN measuring leg against `rev`, with the ledger channel set the way a real
    landing sets it: the ruler reads CNX_Q64_EXEMPTIONS, and falls back to the shipped file beside it."""
    prev = os.environ.get("CNX_Q64_EXEMPTIONS")
    if ledger_path is None:
        os.environ.pop("CNX_Q64_EXEMPTIONS", None)
    else:
        os.environ["CNX_Q64_EXEMPTIONS"] = ledger_path
    try:
        return gate.exposure_cells(rev, "puguang0408_%s" % tag)
    finally:
        if prev is None:
            os.environ.pop("CNX_Q64_EXEMPTIONS", None)
        else:
            os.environ["CNX_Q64_EXEMPTIONS"] = prev


def door_main(cand_sha, tip, ledger_path, out_json):
    """Run the gate's own main() over a local poison commit.  Only `ref_sha` is redirected (GitHub cannot know
    about a dangling object); every other leg, including the exposure arm, is the shipped code path."""
    old_ref, old_argv, old_env = gate.ref_sha, list(sys.argv), os.environ.get("CNX_Q64_EXEMPTIONS")
    gate.ref_sha = lambda b: tip if b == gate.LINE else cand_sha
    if ledger_path is None:
        os.environ.pop("CNX_Q64_EXEMPTIONS", None)
    else:
        os.environ["CNX_Q64_EXEMPTIONS"] = ledger_path
    sys.argv = ["preflight_and_land_r8.py", "--candidate-ref", "local/ord0408-poison", "--order",
                "ORD-0408-SELFTEST", "--out", out_json, "--suite-collect", "off", "--frontend-build", "off"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            gate.main()
    except SystemExit:
        pass
    finally:
        gate.ref_sha, sys.argv = old_ref, old_argv
        if old_env is None:
            os.environ.pop("CNX_Q64_EXEMPTIONS", None)
        else:
            os.environ["CNX_Q64_EXEMPTIONS"] = old_env
    doc = json.load(io.open(out_json, encoding="utf-8"))
    doc["_stdout_tail"] = buf.getvalue()[-600:]
    return doc


def growth_of(tip_cells, cand_cells):
    ct, cc = gate.exposure_counts(tip_cells), gate.exposure_counts(cand_cells)
    return {k: cc[k] - ct.get(k, 0) for k in cc if cc[k] > ct.get(k, 0)}


def main():
    out_path = ""
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    for d in (SCRATCH, LEDGERS, RECIPE):
        os.makedirs(d, exist_ok=True)
    gate.SCRATCH_ROOT = SCRATCH
    tip = git_bin("rev-parse", "origin/mirror/integration-frontend-apple-pass1")

    checks = []

    def chk(name, ok, reading):
        checks.append({"arm": name, "holds": bool(ok), "reading": str(reading)[:400]})
        print("%s  %s\n      reading: %s" % ("HOLDS " if ok else "BREAKS", name, str(reading)[:300]), flush=True)

    # ---- 0. the live gate is untouched by this fork ----------------------------------------------------
    r7b_raw = open(os.path.join(LIVE, "ui_exposure_taint_ast_r7b.cjs"), "rb").read()
    chk("the ruler the LIVE gate runs is still byte-for-byte the blob its door declares (this lane forked to "
        "r8 rather than editing under the fleet's feet)",
        blob_of(r7b_raw) == R7B_BLOB, "r7b computes %s / r7 declares %s" % (blob_of(r7b_raw), R7B_BLOB))
    r8_raw = open(os.path.join(STAGE, gate.EXPOSURE_RULER), "rb").read()
    chk("the r8 ruler this lane's door pins == the bytes the door actually runs",
        blob_of(r8_raw) == gate.EXPOSURE_RULER_BLOB,
        "r8 computes %s / door declares %s" % (blob_of(r8_raw), gate.EXPOSURE_RULER_BLOB))

    # ---- 1. baseline on the real tip with the SHIPPED ledger ------------------------------------------
    cells_tip, waived_tip, led_tip = measure(tip, "tip")
    chk("shipped ledger is inert on the live line: every cell the ruler sees stays in the census",
        led_tip["status"] == "OK_HELD" and len(waived_tip) == 0 and led_tip["entries_held"] == 4,
        "status=%s product_cells=%d waived=%d entries_held=%d held_would_match=%s"
        % (led_tip["status"], len(cells_tip), len(waived_tip), led_tip["entries_held"],
           led_tip["held_would_match"]))
    r7b_out = os.path.join(SCRATCH, "r7b_tip.json")
    subprocess.run(["node", os.path.join(LIVE, "ui_exposure_taint_ast_r7b.cjs"), "--tree", TIP_TREE,
                    "--out", r7b_out], capture_output=True, timeout=1800)
    n7b = len(json.load(io.open(r7b_out, encoding="utf-8")).get("hits", []))
    chk("adopting r8 with the shipped ledger changes NO number a landing reads: r7b and r8 count the same tip",
        n7b == len(cells_tip), "r7b hits=%d / r8 product cells=%d" % (n7b, len(cells_tip)))
    chk("the ledger's own identity travels in the measurement (an audit can name the bytes it obeyed)",
        led_tip["sha1"] == blob_of(open(SHIPPED_LEDGER, "rb").read()),
        "ledger sha1=%s bytes=%s" % (led_tip["sha1"], led_tip["bytes"]))

    # ---- 2. fixtures ---------------------------------------------------------------------------------
    prod_raw, tip_prod = show(OLD_SHAPES, VICTIM_PRODUCT), show(tip, VICTIM_PRODUCT)
    if prod_raw == tip_prod:
        raise SystemExit("VACUOUS FIXTURE: the pre-ORD-0323 product file is identical to the tip's")
    cand_product, pblob, _ = commit_with(VICTIM_PRODUCT, prod_raw, tip,
                                         "ORD-0408 negative control: banned sink back in a PRODUCT file")
    cand_stories, sblob, _ = commit_with(VICTIM_STORIES, show(tip, DONOR), tip,
                                         "ORD-0408 fixture: verbatim copy of a flagged file renamed to a "
                                         "stories face")
    # The stories fixture is a VERBATIM copy, so its blob EQUALS the donor's by design; what has to be new is
    # the PATH, and the pair of checks that matter are: the product poison really differs from the line, and
    # both poison commits are descendants of the tip so no genealogy noise can masquerade as exposure growth.
    tip_prod_blob = git_bin("rev-parse", "%s:%s" % (tip, VICTIM_PRODUCT))
    stories_at_tip = subprocess.run(["git", "-C", REPO, "cat-file", "-e", "%s:%s" % (tip, VICTIM_STORIES)],
                                    capture_output=True).returncode
    descends_p = git_bin("merge-base", "--is-ancestor", tip, cand_product) == ""
    descends_s = git_bin("merge-base", "--is-ancestor", tip, cand_stories) == ""
    chk("fixtures are not vacuous: the product poison differs from the line's bytes, the stories path does not "
        "exist on the line yet, and both poisons descend from the current tip",
        pblob != tip_prod_blob and stories_at_tip != 0 and descends_p and descends_s,
        "product blob %s vs line %s | tip:%s exists=%s | descendants=%s,%s"
        % (pblob[:12], tip_prod_blob[:12], VICTIM_STORIES, stories_at_tip == 0, descends_p, descends_s))

    # ---- 3. HELD is inert: the dev-only face must still read as growth --------------------------------
    cells_h, waived_h, _ = measure(cand_stories, "stories_held")
    g_held = growth_of(cells_tip, cells_h)
    chk("a stories-face cell GROWS the census while the entry is held (a held entry never exempts)",
        len(g_held) > 0 and len(waived_h) == 0, "growth=%s waived=%d" % (g_held, len(waived_h)))

    # ---- 4. ACTIVE exempts it, by name, and the ruler is seen to have measured it ---------------------
    shipped = json.load(io.open(SHIPPED_LEDGER, encoding="utf-8"))["entries"]
    active_e1 = []
    for e in shipped:
        if e["id"] == "E1-storybook-face":
            e = dict(e)
            e["status"] = "active"
            e["decided_by"] = "SELFTEST ONLY - ORD-0408 mechanism proof, not a ruling on the line"
        active_e1.append(e)
    led_active = write_ledger("active_e1.json", active_e1)
    cells_a, waived_a, led_a = measure(cand_stories, "stories_active", led_active)
    g_active = growth_of(cells_tip, cells_a)
    chk("the waived cell was really MEASURED and not missed: the ruler saw more cells than the census "
        "counts (this is what keeps an exemption from becoming a blind spot)",
        led_a["cells_total"] == len(cells_a) + len(waived_a) and len(waived_a) > 0
        and led_a["cells_total"] > led_a["cells_product"]
        and led_a["cells_product"] == len(cells_a),
        "census=%d waived=%d cells_total=%d product=%d exempt=%d"
        % (len(cells_a), len(waived_a), led_a["cells_total"], led_a["cells_product"], led_a["cells_exempt"]))
    chk("an ACTIVE entry waives the dev-only face: the same candidate stops growing the census",
        g_active == {} and len(waived_a) > 0, "growth=%s waived=%s" % (g_active, waived_a[:2]))
    chk("the waiver is attributed to a NAMED ledger entry, not to a hand at the gate",
        all(w["exemption_id"] == "E1-storybook-face" for w in waived_a)
        and led_a["applied_by_entry"].get("E1-storybook-face") == len(waived_a),
        "applied_by_entry=%s ledger sha1=%s cells=%s" % (led_a["applied_by_entry"], led_a["sha1"][:12],
                                                         [w["cell"] for w in waived_a][:3]))

    # ---- 5. THE required negative control: real growth stays red under the same permissive ledger ------
    cells_p, waived_p, _ = measure(cand_product, "product_active", led_active)
    g_prod = growth_of(cells_tip, cells_p)
    chk("NEGATIVE CONTROL: real product exposure growth still reports RED with the permissive ledger in force",
        len(g_prod) > 0 and len(waived_p) == 0, "growth=%s waived=%d (E1 cannot reach components/)"
                                                % (g_prod, len(waived_p)))

    # ---- 6. the door's own main() carries both sides into its receipt ---------------------------------
    d_red = door_main(cand_product, tip, led_active, os.path.join(RECIPE, "door_product_growth.json"))
    ex_red = d_red["gate_run"]["exposure"]
    exposure_problems = [p for p in d_red["problems"] if "Q64 exposure" in p]
    chk("the gate's own exposure leg names the product growth as a problem",
        len(exposure_problems) == 1 and bool(ex_red.get("growth_by_file_and_rule")),
        "problem=%s growth=%s exempted_cand=%s" % ([p[:110] for p in exposure_problems],
                                                   ex_red.get("growth_by_file_and_rule"),
                                                   ex_red.get("exempted_cand")))
    d_green = door_main(cand_stories, tip, led_active, os.path.join(RECIPE, "door_stories_waived.json"))
    ex_green = d_green["gate_run"]["exposure"]
    chk("the gate's exposure leg goes silent on the waived face AND prints what it waived and on whose "
        "authority",
        not [p for p in d_green["problems"] if "Q64 exposure" in p]
        and ex_green.get("exempted_cand", 0) > 0 and ex_green.get("growth_by_file_and_rule") == {}
        and (ex_green.get("exemption_ledger") or {}).get("status") == "OK_ACTIVE",
        "exempted_cand=%s seen_by_ruler=%s census=%s ledger=%s applied=%s"
        % (ex_green.get("exempted_cand"), ex_green.get("cand_cells_seen_by_ruler"),
           ex_green.get("cand_cells"), (ex_green.get("exemption_ledger") or {}).get("status"),
           (ex_green.get("exemption_ledger") or {}).get("applied_by_entry")))

    # ---- 7. the exemption cannot be used to switch the arm off ----------------------------------------
    led_blanket = write_ledger("blanket.json",
                               [{"id": "E1-storybook-face", "status": "active", "face": "dev-only-surface",
                                 "match": {"path_glob": "**", "rule": "*"}, "decided_by": "blanket probe"}])
    raised = None
    try:
        measure(cand_product, "blanket", led_blanket)
    except Exception as e:  # noqa: BLE001
        raised = "%s: %s" % (type(e).__name__, str(e)[:220])
    chk("a BLANKET grant is refused and the census is withheld (a ledger cannot silence the arm by being wide)",
        raised is not None and "REJECTED_BLANKET_GRANT" in raised, raised)
    d_blind = door_main(cand_product, tip, led_blanket, os.path.join(RECIPE, "door_blanket_refused.json"))
    ex_bl = d_blind["gate_run"]["exposure"]
    chk("a withheld census is NOT booked as the compiler-skip face: the door refuses blind rather than "
        "certifying a zero",
        "skipped" not in ex_bl and any("never measured" in p for p in d_blind["problems"]),
        "exposure keys=%s problems=%s" % (sorted(ex_bl.keys()),
                                         [p[:90] for p in d_blind["problems"] if "exposure" in p][:2]))
    bad = os.path.join(LEDGERS, "malformed.json")
    io.open(bad, "w", encoding="utf-8", newline="\n").write('{ "schema": "CNX_Q64_EXPOSURE_EXEMPTIONS_V1", ')
    raised = None
    try:
        measure(cand_stories, "malformed", bad)
    except Exception as e:  # noqa: BLE001
        raised = str(e)[:200]
    chk("a malformed ledger is refused, not silently read as 'no exemptions'",
        raised is not None and "REJECTED_MALFORMED_JSON" in raised, raised)
    led_norul = write_ledger("active_no_ruling.json", [dict(shipped[0], status="active", decided_by="")])
    raised = None
    try:
        measure(cand_stories, "noruling", led_norul)
    except Exception as e:  # noqa: BLE001
        raised = str(e)[:200]
    chk("an active entry that names no ruling is refused",
        raised is not None and "REJECTED_ACTIVE_WITHOUT_RULING" in raised, raised)

    # ---- 8. the document stays honest about what it saw ------------------------------------------------
    doc = json.load(io.open(os.path.join(SCRATCH, "puguang0408_stories_active", "ruler.json"), encoding="utf-8"))
    waived_in_doc = [h for h in doc["hits"] if h.get("exempt") is True]
    chk("every cell the ruler saw is still in `hits`; the exemption is a field on the cell, never a deletion",
        doc["cells_total"] == len(doc["hits"]) and len(waived_in_doc) == doc["cells_exempt"]
        and doc["verdict"] == "EXPOSURE_SHAPE_FOUND" and doc["verdict_product"] == "EXPOSURE_SHAPE_FOUND"
        and doc["cells_product"] == doc["cells_total"] - doc["cells_exempt"],
        "hits=%d product=%s exempt=%s verdict=%s/%s exempted_cells=%s"
        % (len(doc["hits"]), doc["cells_product"], doc["cells_exempt"], doc["verdict"],
           doc["verdict_product"], doc["exempted_cells"][:2]))

    report = {"at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tip": tip,
              "ruler_r8_file": gate.EXPOSURE_RULER, "ruler_r8_blob": blob_of(r8_raw),
              "ruler_r8_declared_by_door": gate.EXPOSURE_RULER_BLOB,
              "r7b_blob_measured": blob_of(r7b_raw),
              "shipped_ledger": SHIPPED_LEDGER, "shipped_ledger_sha1": led_tip["sha1"],
              "fixtures": {"product_poison_commit": cand_product, "product_blob": pblob,
                           "stories_poison_commit": cand_stories, "stories_blob": sblob},
              "tip_product_cells": len(cells_tip),
              "arms": checks}
    report["n_checks"] = len(checks)
    report["n_holds"] = sum(1 for c in checks if c["holds"])
    report["all_holds"] = report["n_holds"] == report["n_checks"]
    print(json.dumps({"overall": "GREEN" if report["all_holds"] else "RED",
                      "arms": [{"arm": c["arm"][:78], "holds": c["holds"]} for c in checks],
                      "tip_product_cells": report["tip_product_cells"],
                      "ruler_r8_blob": report["ruler_r8_blob"]}, ensure_ascii=False, indent=1))
    if out_path:
        io.open(out_path, "w", encoding="utf-8", newline="\n").write(
            json.dumps(report, ensure_ascii=False, indent=1))
        print("out=%s (%d B)" % (out_path, os.path.getsize(out_path)))
    return 0 if report["all_holds"] else 1


if __name__ == "__main__":
    sys.exit(main())
