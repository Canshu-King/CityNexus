"""Generate ORD-0408 instruments from the live ones, byte-faithfully.

r7b (the ruler) and r7 (the landing gate) are READ-ONLY inputs: the live gate runs them right now, so this
lane forks them to r8 instead of editing under the fleet's feet.  Every edit is an exact-string replacement
that must hit exactly once, or the generator aborts with the anchor printed -- a silently-missed replacement
would ship a gate that does not do what its receipt claims.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
STAGE = r"E:/puguang0408/stage/live_checks"

RULER_SRC = os.path.join(LIVE, "ui_exposure_taint_ast_r7b.cjs")
RULER_OUT = os.path.join(STAGE, "ui_exposure_taint_ast_r8.cjs")
GATE_SRC = os.path.join(LIVE, "preflight_and_land_r7.py")
GATE_OUT = os.path.join(STAGE, "preflight_and_land_r8.py")


def gitblob(raw):
    return hashlib.sha1(b"blob %d" % len(raw) + chr(0).encode() + raw).hexdigest()


def sub1(text, old, new, label, src):
    n = text.count(old)
    if n != 1:
        raise SystemExit("ANCHOR_%s_HITS_%d in %s -- refusing to write\nanchor begins: %r"
                         % (label, n, src, old[:120]))
    return text.replace(old, new, 1)


# ----------------------------------------------------------------- ruler r8
js = io.open(RULER_SRC, encoding="utf-8", newline="").read()

LEDGER_BLOCK = r'''
/* ------------------------------------------------------------------ Q64 structured exemptions
 * ORD-0408.  Before this, waiving the no-growth arm was a hand at the gate: `--exposure-arm off`, a re-pinned
 * ruler blob, or a candidate landed around the door by hand.  An exemption is now DATA the RULER reads and
 * applies, so a cell is either covered by a named ledger entry (whose id travels in the measurement document)
 * or it is not, and the same run can be re-audited without asking anybody what was waived.
 *
 * Fail-closed, three ways, because an exemption mechanism is exactly the thing a tired shift can use to switch
 * the gate off:
 *   ABSENT     no ledger file -> zero exemptions applied, the census reads exactly like r7b;
 *   REJECTED   malformed JSON, an unknown face, an active entry without a ruling named, or a grant wide enough
 *              to silence the arm (wildcard path AND wildcard rule) -> the ruler refuses to certify the run at
 *              all: measurement NOT_PERFORMED, hits emptied BY CONSTRUCTION, so the door cannot read zero cells
 *              as a clean tree;
 *   OK_ACTIVE/OK_HELD  the normal shapes; a `held` entry never exempts anything, it only reports how many cells
 *              it WOULD have covered so the commander can size a waiver before signing it.
 */
const EXEMPTION_LEDGER_DEFAULT = __dirname + '/q64_exposure_exemptions.json';
const WILDCARD_GLOBS = ['', '*', '**', '/**', './**', '**/*'];

function globToRegExp(glob) {
  let head = '', rest = String(glob);
  if (rest.indexOf('**/') === 0) { head = '(?:.*/)?'; rest = rest.slice(3); }
  let out = '';
  for (let i = 0; i < rest.length; i++) {
    const ch = rest.charAt(i);
    if (ch === '*') { out += (rest.charAt(i + 1) === '*') ? (i++, '.*') : '[^/]*'; }
    else if (ch === '.') { out += '\\.'; }
    else if ('+/'.indexOf(ch) >= 0) { out += ch === '/' ? '/' : '\\+'; }
    else if (/^[A-Za-z0-9_$\-]$/.test(ch)) { out += ch; }
    else { out += '\\' + ch; }
  }
  return new RegExp('^' + head + out + '$');
}

function isWildcardGlob(g) {
  return WILDCARD_GLOBS.indexOf(String(g || '').trim()) >= 0;
}

function loadExemptionLedger(args) {
  const p = args.exemptions || process.env.CNX_Q64_EXEMPTIONS || EXEMPTION_LEDGER_DEFAULT;
  let raw;
  try { raw = fs.readFileSync(p); }
  catch (e) {
    return { path: p, status: 'ABSENT', reason: 'no ledger file at ' + p, entries: [],
             bytes: 0, sha1: null };
  }
  const res = { path: p, bytes: raw.length, sha1: gitBlobId(raw), entries: [], status: null, reason: null };
  let doc;
  try { doc = JSON.parse(raw.toString('utf8')); }
  catch (e) {
    res.status = 'REJECTED_MALFORMED_JSON';
    res.reason = 'the ledger is not valid JSON, so no exemption can be trusted: ' + String(e).slice(0, 120);
    return res;
  }
  if (doc.schema !== 'CNX_Q64_EXPOSURE_EXEMPTIONS_V1' || !Array.isArray(doc.entries)) {
    res.status = 'REJECTED_UNKNOWN_SCHEMA';
    res.reason = 'schema is ' + JSON.stringify(doc.schema) + ' / entries is ' + typeof doc.entries;
    return res;
  }
  const faces = (doc.policy && Array.isArray(doc.policy.faces_vocabulary)) ? doc.policy.faces_vocabulary : [];
  res.entries = doc.entries;
  for (const en of res.entries) {
    const st = String(en.status || ''), match = en.match || {};
    if (['active', 'held'].indexOf(st) < 0) {
      res.status = 'REJECTED_ENTRY_STATUS'; res.reason = 'entry ' + en.id + ' status ' + JSON.stringify(en.status);
      return res;
    }
    if (faces.indexOf(String(en.face)) < 0) {
      res.status = 'REJECTED_ENTRY_FACE'; res.reason = 'entry ' + en.id + ' face ' + JSON.stringify(en.face)
        + ' is not in faces_vocabulary';
      return res;
    }
    if (st === 'active' && !String(en.decided_by || '').trim()) {
      res.status = 'REJECTED_ACTIVE_WITHOUT_RULING';
      res.reason = 'entry ' + en.id + ' is active but names no decided_by';
      return res;
    }
    if (isWildcardGlob(match.path_glob) && String(match.rule || '') === '*') {
      res.status = 'REJECTED_BLANKET_GRANT';
      res.reason = 'entry ' + en.id + ' matches any path and any rule: that is not an exemption, it is the arm '
        + 'switched off';
      return res;
    }
    en.__path_re = globToRegExp(match.path_glob || '');
    en.__rule = String(match.rule || '');
  }
  res.status = res.entries.some(function (e) { return e.status === 'active'; }) ? 'OK_ACTIVE' : 'OK_HELD';
  return res;
}

function gitBlobId(buf) {
  return crypto.createHash('sha1')
    .update('blob ' + buf.length + String.fromCharCode(0)).update(buf).digest('hex');
}

/* The one place that decides.  A hit carries `exempt` and the id of the entry that covered it, so the cell is
 * still in the document -- an exemption changes what the arm counts, never what the ruler saw. */
function applyExemptions(hits, ledger) {
  const sum = {
    schema: 'CNX_Q64_EXEMPTIONS_APPLIED_V1', path: ledger.path, bytes: ledger.bytes, sha1: ledger.sha1,
    status: ledger.status, reason: ledger.reason,
    entries_total: ledger.entries.length, entries_active: 0, entries_held: 0,
    applied_by_entry: {}, held_would_match: {},
    cells_total: hits.length, cells_exempt: 0, cells_product: hits.length,
    exempted_cells: [],
  };
  for (const en of ledger.entries) {
    if (en.status === 'active') { sum.entries_active++; sum.applied_by_entry[en.id] = 0; }
    else { sum.entries_held++; sum.held_would_match[en.id] = 0; }
  }
  for (const h of hits) {
    let covered = null, would = null;
    for (const en of ledger.entries) {
      const ruleOk = en.__rule === '*' || en.__rule === String(h.rule);
      if (!ruleOk || !en.__path_re.test(String(h.file))) continue;
      if (en.status === 'active') { covered = en; break; }
      if (!would) would = en;
      sum.held_would_match[en.id] = (sum.held_would_match[en.id] || 0) + 1;
    }
    if (covered) {
      h.exempt = true; h.exemption_id = covered.id; h.exemption_face = covered.face;
      sum.applied_by_entry[covered.id]++; sum.cells_exempt++;
      sum.exempted_cells.push({ file: h.file, line: h.line, rule: h.rule, exemption_id: covered.id });
    } else {
      h.exempt = false;
      if (would) { h.exemption_would_be = would.id; }
    }
  }
  sum.cells_product = hits.length - sum.cells_exempt;
  return sum;
}

'''

js = sub1(js, "const RULER = {", LEDGER_BLOCK + "const RULER = {", "RULER_CONST", "ruler")

js = sub1(js, "  name: 'ui_exposure_taint_ast_r7b.cjs',",
          "  name: 'ui_exposure_taint_ast_r8.cjs',", "RULER_NAME", "ruler")
js = sub1(js,
          "  supersedes: 'ui_exposure_taint_ast_r7.cjs (blob 3272a4336f60ddd183875000c11e5b5ead6be2be), which superseded '",
          "  supersedes: 'ui_exposure_taint_ast_r7b.cjs (blob e2ea5ce64ca67bb476006766db27b0612789dd36), which "
          "superseded r7 = ui_exposure_taint_ast_r7.cjs (blob 3272a4336f60ddd183875000c11e5b5ead6be2be), which superseded '",
          "RULER_SUPERSEDES", "ruler")
js = sub1(js, "  supersedes_blob: '3272a4336f60ddd183875000c11e5b5ead6be2be',",
          "  supersedes_blob: 'e2ea5ce64ca67bb476006766db27b0612789dd36',", "RULER_SUPERSEDES_BLOB", "ruler")
js = sub1(js, "  order: 'ORD-0354 (attribute slot + line-independent cell identity) + ORD-0348 (fold exoneration)',",
          "  order: 'ORD-0354 (attribute slot + line-independent cell identity) + ORD-0348 (fold exoneration) "
          "+ ORD-0408 (structured exemption ledger read by the ruler)',", "RULER_ORDER", "ruler")
js = sub1(js,
          "  generation: 'r7b / AST taint, module graph, both DOM surfaces, one auditable exception, stable cell ids',",
          "  generation: 'r8 / r7b + a data-shaped Q64 exemption ledger (nothing is waived by a hand at the gate)',",
          "RULER_GENERATION", "ruler")

# --- the --tree run: load the ledger, apply it, and refuse to certify a rejected one -----------------
js = sub1(
    js,
    "    const out = {\n      schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R7', ruler: RULER, typescript: ts.version,",
    "    const ledger = loadExemptionLedger(args);\n"
    "    const ex = applyExemptions(r.hits, ledger);\n"
    "    if (String(ledger.status).indexOf('REJECTED') === 0) {\n"
    "      // A ledger the ruler cannot trust must not produce a census.  Emitting hits=[] with NOT_PERFORMED is\n"
    "      // the same honesty rule as the missing-compiler path: an empty list here is empty BY CONSTRUCTION.\n"
    "      const refused = { schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8', ruler: RULER,\n"
    "        verdict: 'EXEMPTION_LEDGER_' + ledger.status, measurement: 'NOT_PERFORMED',\n"
    "        exemption_ledger: ex, hits: [], tree: args.tree,\n"
    "        note: 'the exemption ledger was rejected, so the run measured nothing; hits is empty because the '\n"
    "            + 'census was withheld, NOT because the tree was found clean' };\n"
    "      if (args.out) fs.writeFileSync(args.out, JSON.stringify(refused, null, 1), 'utf8');\n"
    "      process.stdout.write(JSON.stringify(refused, null, 1) + String.fromCharCode(10));\n"
    "      return 0;\n"
    "    }\n"
    "    const out = {\n      schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8', ruler: RULER, typescript: ts.version,",
    "TREE_OUT", "ruler")

js = sub1(
    js,
    "      per_file: r.perFile, hits: r.hits,\n      cells_by_slot: bySlot,\n      cells_total: r.hits.length,",
    "      per_file: r.perFile, hits: r.hits,\n"
    "      exemption_ledger: ex,\n"
    "      cells_by_slot: bySlot,\n"
    "      cells_total: r.hits.length,\n"
    "      cells_product: ex.cells_product, cells_exempt: ex.cells_exempt,\n"
    "      exempted_cells: ex.exempted_cells,",
    "TREE_FIELDS", "ruler")

# a product-only verdict, so a human reading the document is not told 'found' about a cell nobody counts
js = sub1(
    js,
    "      verdict: r.hits.length ? 'EXPOSURE_SHAPE_FOUND' : 'NO_EXPOSURE_SHAPE_FOUND',",
    "      verdict: r.hits.length ? 'EXPOSURE_SHAPE_FOUND' : 'NO_EXPOSURE_SHAPE_FOUND',\n"
    "      verdict_product: ex.cells_product ? 'EXPOSURE_SHAPE_FOUND' : 'NO_EXPOSURE_SHAPE_FOUND',\n"
    "      verdict_product_note: 'verdict counts every cell the ruler saw; verdict_product counts only the ones '\n"
    "        + 'the exemption ledger left in force. The pre-landing arm compares verdict_product cells.',",
    "TREE_VERDICT", "ruler")

# --- the crash path used to write stdout only, so the door saw 'ruler wrote no output (rc 0)' and refused ------
js = sub1(
    js,
    "      process.stdout.write(JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R5',\n"
    "        verdict: 'RULER_ERROR', tree: args.tree,\n"
    "        error: String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 4).join(' | ') }, null, 1)"
    " + String.fromCharCode(10));\n      return 8;",
    "      const errDoc = JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R5',\n"
    "        verdict: 'RULER_ERROR', tree: args.tree,\n"
    "        error: String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 4).join(' | ') }, null, 1);\n"
    "      // r7b wrote this document to stdout only, so a door that runs the ruler with --out saw 'ruler wrote no\n"
    "      // output (rc 0)' and refused three candidates on 2026-10-08 14:1x for an instrument reason.  The error\n"
    "      // document now lands wherever the caller asked for the result.\n"
    "      if (args.out) { try { fs.writeFileSync(args.out, errDoc, 'utf8'); } catch (e2) { /* stdout still carries it */ } }\n"
    "      process.stdout.write(errDoc + String.fromCharCode(10));\n      return 8;",
    "CRASH_PATH", "ruler")

io.open(RULER_OUT, "w", encoding="utf-8", newline="").write(js)
ruler_blob = gitblob(js.encode("utf-8"))
print("wrote %s (%d B) blob %s" % (RULER_OUT, len(js.encode("utf-8")), ruler_blob))

chk = subprocess.run(["node", "--check", RULER_OUT], capture_output=True)
if chk.returncode:
    raise SystemExit("NODE_CHECK_FAILED rc=%s %s" % (chk.returncode, chk.stderr.decode("utf-8", "replace")[:400]))
print("node --check rc=0")

# ----------------------------------------------------------------- gate r8
py = io.open(GATE_SRC, encoding="utf-8", newline="").read()

py = sub1(py, 'EXPOSURE_RULER = "ui_exposure_taint_ast_r7b.cjs"         # published name: r7b (lane S4)',
          'EXPOSURE_RULER = "ui_exposure_taint_ast_r8.cjs"         # ORD-0408: r7b + the structured exemption ledger',
          "GATE_RULER_NAME", "gate")
py = sub1(py, 'EXPOSURE_RULER_BLOB = "e2ea5ce64ca67bb476006766db27b0612789dd36"',
          'EXPOSURE_RULER_BLOB = "%s"\nSCRATCH_ROOT = os.environ.get("CNX_EXPOSURE_SCRATCH",\n'
          '                          "D:/moodle/_qoder_cmdr_ref_20260921")' % ruler_blob,
          "GATE_RULER_BLOB", "gate")
py = sub1(py, '    out = os.path.join(r"D:/moodle/_qoder_cmdr_ref_20260921", sub)',
          '    out = os.path.join(SCRATCH_ROOT, sub)', "GATE_SCRATCH", "gate")

# exposure_cells: obey the ruler's `exempt` field and hand the ledger identity back to the receipt
py = sub1(
    py,
    '    if doc.get("measurement") == "NOT_PERFORMED":\n'
    '        raise RuntimeError("NOT_MEASURED_NO_TS_COMPILER: ruler declined to measure (%s)"\n'
    '                           % str(doc.get("verdict"))[:80])\n'
    '    return {"%s:%s|%s" % (h["file"].split("/")[-1], h["line"], h.get("rule")) for h in doc.get("hits", [])}',
    '    if doc.get("measurement") == "NOT_PERFORMED":\n'
    '        # r7 hardcoded the missing-compiler wording here, so a withheld census of ANY other reason was\n'
    '        # reported as "no TypeScript".  The ruler now names its own verdict and this passes it through; the\n'
    '        # arm below still only exempts the compiler case by name, so a rejected ledger refuses loudly.\n'
    '        raise RuntimeError("%s: ruler declined to certify the census (ledger %s)"\n'
    '                           % (str(doc.get("verdict") or "NOT_MEASURED")[:60],\n'
    '                              str((doc.get("exemption_ledger") or {}).get("reason"))[:120]))\n'
    '    return cells_from_hits(doc)',
    "GATE_RAISE", "gate")

py = sub1(
    py,
    'def exposure_cells(rev, sub):',
    'def cells_from_hits(doc):\n'
    '    """(product cells, exempted cells, ledger identity) from one ruler document.\n\n'
    '    The DECISION is the ruler\'s, made from the ledger data; this only obeys the `exempt` field, so the door\n'
    '    can never waive a cell by itself and a lane cannot waive one by editing the door.  Everything the ruler\n'
    '    saw stays in the receipt: an exemption changes what is counted, never what is visible.\n'
    '    """\n'
    '    cells, waived = set(), []\n'
    '    for h in doc.get("hits", []):\n'
    '        key = "%s:%s|%s" % (h["file"].split("/")[-1], h["line"], h.get("rule"))\n'
    '        if h.get("exempt") is True:\n'
    '            waived.append({"cell": key, "path": h["file"], "exemption_id": h.get("exemption_id")})\n'
    '        else:\n'
    '            cells.add(key)\n'
    '    led = doc.get("exemption_ledger") or {}\n'
    '    ledger = {"path": led.get("path"), "sha1": led.get("sha1"), "bytes": led.get("bytes"),\n'
    '              "status": led.get("status"), "reason": led.get("reason"),\n'
    '              "entries_active": led.get("entries_active"), "entries_held": led.get("entries_held"),\n'
    '              "applied_by_entry": led.get("applied_by_entry"),\n'
    '              "held_would_match": led.get("held_would_match"),\n'
    '              "cells_total": led.get("cells_total"), "cells_product": led.get("cells_product"),\n'
    '              "cells_exempt": led.get("cells_exempt")}\n'
    '    return cells, waived, ledger\n'
    '\n'
    '\n'
    'def exposure_cells(rev, sub):',
    "GATE_HELPER", "gate")

# the arm block: unpack three, report the waivers, and keep the no-growth judgement on product cells
py = sub1(
    py,
    '            cells_tip = exposure_cells(tip, "exp_tip_%s" % stamp)\n'
    '            cells_cand = exposure_cells(cand, "exp_cand_%s" % stamp)',
    '            cells_tip, waived_tip, ledger_tip = exposure_cells(tip, "exp_tip_%s" % stamp)\n'
    '            cells_cand, waived_cand, ledger_cand = exposure_cells(cand, "exp_cand_%s" % stamp)',
    "GATE_ARM_CALLS", "gate")

py = sub1(
    py,
    '            run["exposure"].update({"tip_cells": len(cells_tip), "cand_cells": len(cells_cand),',
    '            run["exposure"].update({"tip_cells": len(cells_tip), "cand_cells": len(cells_cand),\n'
    '                                    "tip_cells_seen_by_ruler": len(cells_tip) + len(waived_tip),\n'
    '                                    "cand_cells_seen_by_ruler": len(cells_cand) + len(waived_cand),\n'
    '                                    "exempted_tip": len(waived_tip), "exempted_cand": len(waived_cand),\n'
    '                                    "exempted_cand_cells": waived_cand[:12],\n'
    '                                    "exemption_ledger": ledger_cand,',
    "GATE_ARM_FIELDS", "gate")

# the skip branch must key on the ruler's own verdict, not on a message string written in this file
py = sub1(
    py,
    '            err_str = str(e)\n'
    '            if ("TS_COMPILER_UNAVAILABLE" in err_str or "EXEMPTED_NO_TS_COMPILER" in err_str\n'
    '                    or "NOT_MEASURED_NO_TS_COMPILER" in err_str):',
    '            err_str = str(e)\n'
    '            # ONLY the compiler-less face is a skip.  A rejected exemption ledger says "the census was\n'
    '            # withheld", and treating that as a skip is how the arm goes idle while looking alive.\n'
    '            if ("TS_COMPILER_UNAVAILABLE" in err_str or "EXEMPTED_NO_TS_COMPILER" in err_str\n'
    '                    or "NOT_MEASURED_NO_TS_COMPILER" in err_str):',
    "GATE_SKIP_BRANCH", "gate")

py = sub1(
    py,
    '    A cell key is (basename, line, rule); a shifted line reads as add+remove, which is honest for a\n'
    '    no-GROW test (a genuinely new sink still shows up as an add with no matching remove)."""',
    '    A cell key is (basename, line, rule); a shifted line reads as add+remove, which is honest for a\n'
    '    no-GROW test (a genuinely new sink still shows up as an add with no matching remove).\n\n'
    '    ORD-0408: returns (product cells, exempted cells, ledger identity).  The exemption decision is made by\n'
    '    the ruler from the ledger data and arrives as a field on each hit; this function only obeys it."""',
    "GATE_DOCSTRING", "gate")

io.open(GATE_OUT, "w", encoding="utf-8", newline="").write(py)
compile(py, GATE_OUT, "exec")
print("wrote %s (%d B) compiles OK" % (GATE_OUT, len(py.encode("utf-8"))))
json.dump({"ruler_blob": ruler_blob, "ruler_bytes": len(js.encode("utf-8")),
           "gate_bytes": len(py.encode("utf-8"))},
          io.open(os.path.join(STAGE, "_ord0408_generated.json"), "w", encoding="utf-8"), indent=1)
