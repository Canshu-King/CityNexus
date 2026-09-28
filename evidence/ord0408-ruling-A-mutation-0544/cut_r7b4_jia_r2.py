"""Cut ORD-0408 ruling A as a NEW generation: ui_exposure_taint_ast_r7b4.cjs.

Base = the published r7b1, byte for byte, so ruling B (exempt-by-field-name, shipped as r7b3 and
then rejected by the ledger) can never re-enter through an inherited edit.  Onto it go three things
and nothing else:

  1. the module-scope contract machinery (read from the WIP source, kept in one place so the parser
     has one home), spliced before `function main(`;
  2. in the per-file exoneration loop, a `*_code` branch: a cell whose own element names a
     `data-cnx-field` ending in `code` is judged against the closed set the CONTRACT declares for
     that field - the name is a lookup key, not a permission;
  3. the bookkeeping that makes an exoneration impossible to lose quietly: `contract_exempted` and
     `contract_blocked` surface in both `--file` and `--tree` reports, and a code cell the contract
     does not vouch for is kept red and is NOT handed to the disclosure fold either (the same
     `data-cnx-field` that performs the lookup must not then vouch for the panel around it).

A contract that declares no enum for the field is a named red, `CONTRACT_MISSING_ENUM`, carrying the
contract path, its blob id and the field names that DO declare a set.
"""
import hashlib
import io
import os
import subprocess
import sys

ROOT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0408"
SRC = os.path.join(ROOT, "ui_exposure_taint_ast_r7b1.cjs")          # published, never written to
WIP = os.path.join(WORK, "ui_exposure_taint_ast_r7b2.WIP_NOT_FOR_DOOR.cjs")
DST = os.path.join(ROOT, "ui_exposure_taint_ast_r7b4.cjs")


def machinery(wip):
    start = wip.find("let CONTRACT_PATH = null;")
    assert start >= 0
    end = wip.find("function main() {", start)
    assert end > start
    block = wip[start:end].rstrip() + "\n"
    for needle in ("function readContract(path) {", "function contractSetFor(field) {",
                   "function enumTokenEvidence(hit, field) {", "function contractFromTarget("):
        assert needle in block, needle
    assert block.count("function enumTokenEvidence") == 1, "two definitions would hoist over each other"
    return block


BRANCH_ANCHOR = """      const context = h.sink === 'jsx-text' ? foldContext(h._node) : null;"""

BRANCH = """      /* ORD-0408 ruling A (the ledger, not the relay, is authoritative): a `*_code` cell is
         exonerated ONLY because the contract names a closed set for that field, and only while
         nothing on the value's own chain falls outside that set.  The field name is a lookup key,
         never a permission - ruling B's exempt-by-field-name was rejected. */
      let contractBlocked = false;
      const codeField = cnxFieldNamedOnCell(h._node);
      if (codeField) {
        const ev = enumTokenEvidence(h, codeField);
        if (ev.ok) {
          contract_exempted.push({ file_line: h.line, rule: h.rule, sink: h.sink, snippet: h.snippet,
            taint_chain: h.taint_chain, field: codeField, basis: ev.basis,
            tokens_seen: ev.tokens, enum_size: ev.set_size, contract: ev.contract,
            contract_blob: ev.contract_blob, contract_enum_line: ev.contract_line });
          continue;
        }
        contract_blocked.push({ file_line: h.line, rule: h.rule, sink: h.sink, snippet: h.snippet,
          field: codeField, why: ev.why, examples: ev.examples || [], enum_size: ev.set_size,
          contract: ev.contract, contract_blob: ev.contract_blob || null,
          fields_with_enum: ev.fields_with_enum || [] });
        /* red, and not for sale to the fold either */
        contractBlocked = true;
      }
      const context = (!contractBlocked && h.sink === 'jsx-text') ? foldContext(h._node) : null;"""

HELPER = """  /* Which `*_code` field this cell's OWN element names, if any.  Only the innermost enclosing
     element is consulted, so a code value rendered inside an unrelated shell does not inherit that
     shell's field name; the two readings (the span and the div around it) are two cells. */
  function cnxFieldNamedOnCell(node) {
    for (let cur = node; cur; cur = cur.parent) {
      if (!ts.isJsxElement(cur)) continue;
      const attrs = (cur.openingElement.attributes.properties || [])
        .filter((p) => ts.isJsxAttribute(p));
      for (const at of attrs) {
        if (!at.name || at.name.getText(sf) !== 'data-cnx-field' || !at.initializer) continue;
        let v = at.initializer;
        if (ts.isJsxExpression(v)) v = v.expression;
        if (v && v.kind === ts.SyntaxKind.StringLiteral && /^[a-z][a-z0-9_]*_code$/.test(v.text)) {
          return v.text;
        }
      }
      return null;
    }
    return null;
  }
"""


def main():
    s = io.open(SRC, encoding="utf-8").read()
    base_sha = hashlib.sha1(s.encode("utf-8")).hexdigest()

    a = "\nfunction main("
    assert s.count(a) == 1
    s = s.replace(a, "\n" + machinery(io.open(WIP, encoding="utf-8").read()) + a, 1)

    assert s.count(BRANCH_ANCHOR) == 1
    s = s.replace(BRANCH_ANCHOR, BRANCH, 1)

    anchor = "  function foldContext(node) {"
    assert s.count(anchor) == 1
    s = s.replace(anchor, HELPER + "\n" + anchor, 1)

    s = s.replace("    const kept = [], folded = [], foldless = [];",
                  "    const kept = [], folded = [], foldless = [], contract_exempted = [],"
                  " contract_blocked = [];", 1)
    s = s.replace("""    return { hits: kept.sort((a, b) => a.line - b.line), attributed_in_fold: folded,
      fold_without_anchor: foldless,""",
                  """    return { hits: kept.sort((a, b) => a.line - b.line), attributed_in_fold: folded,
      contract_exempted: contract_exempted, contract_blocked: contract_blocked,
      contract: { path: CONTRACT.path, readable: CONTRACT.readable, bytes: CONTRACT.bytes,
        blob: CONTRACT.blob, fields_with_enum: Object.keys(CONTRACT.enums),
        enum_lines: CONTRACT.enum_lines, enum_forms: CONTRACT.enum_forms,
        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },
      fold_without_anchor: foldless,""", 1)

    # the CLI file-mode report: it aggregates fold lists but knew nothing about contract lists, so a
    # `*_code` judgement would have been computed and then dropped on the floor.  Measured first: an
    # A3 run printed hits while `contract` came back absent.
    FILE_OLD = """    for (const f of res.fold_without_anchor) { f.file = label; foldless.push(f); }
    perFile.push({ file: label, hits: res.hits.length, parse_diagnostics: res.diagnostics,
      attributed_in_fold: res.attributed_in_fold.length,"""
    FILE_NEW = """    for (const f of res.fold_without_anchor) { f.file = label; foldless.push(f); }
    for (const f of (res.contract_exempted || [])) { f.file = label; cex.push(f); }
    for (const f of (res.contract_blocked || [])) { f.file = label; cbk.push(f); }
    perFile.push({ file: label, hits: res.hits.length, parse_diagnostics: res.diagnostics,
      attributed_in_fold: res.attributed_in_fold.length,
      contract_exempted: (res.contract_exempted || []).length,
      contract_blocked: (res.contract_blocked || []).length,"""
    assert s.count(FILE_OLD) == 1
    s = s.replace(FILE_OLD, FILE_NEW, 1)

    assert s.count("  const folded = [], foldless = [];\n  for (const [label, text] of targets) {") == 1
    s = s.replace("  const folded = [], foldless = [];\n  for (const [label, text] of targets) {",
                  "  const folded = [], foldless = [], cex = [], cbk = [];\n"
                  "  for (const [label, text] of targets) {", 1)

    FILE_OUT_OLD = """    fold_without_anchor: foldless, fold_without_anchor_count: foldless.length,
    /* r6's published bytes print 40 here"""
    FILE_OUT_NEW = """    fold_without_anchor: foldless, fold_without_anchor_count: foldless.length,
    contract_exempted: cex, contract_exempted_count: cex.length,
    contract_blocked: cbk, contract_blocked_count: cbk.length,
    contract: { path: CONTRACT.path, readable: CONTRACT.readable, bytes: CONTRACT.bytes,
      blob: CONTRACT.blob, fields_with_enum: Object.keys(CONTRACT.enums),
      enum_lines: CONTRACT.enum_lines, enum_forms: CONTRACT.enum_forms,
        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },
    /* r6's published bytes print 40 here"""
    assert s.count(FILE_OUT_OLD) == 1
    s = s.replace(FILE_OUT_OLD, FILE_OUT_NEW, 1)

    # --tree aggregation, so a judgement computed inside a file can never disappear at the tree level
    TREE_DECL_OLD = "    const folded = [], foldless = [];"
    assert s.count(TREE_DECL_OLD) == 1, s.count(TREE_DECL_OLD)
    s = s.replace(TREE_DECL_OLD, "    const folded = [], foldless = [], cex = [], cbk = [];", 1)

    TREE_ACC_OLD = "      for (const f of r.fold_without_anchor) { f.file = k; foldless.push(f); }"
    assert s.count(TREE_ACC_OLD) == 1
    s = s.replace(TREE_ACC_OLD, TREE_ACC_OLD + "\n"
                  "      for (const f of (r.contract_exempted || [])) { f.file = k; cex.push(f); }\n"
                  "      for (const f of (r.contract_blocked || [])) { f.file = k; cbk.push(f); }", 1)

    TREE_OUT_OLD = "    return { hits: hits, attributed_in_fold: folded, fold_without_anchor: foldless,"
    assert s.count(TREE_OUT_OLD) == 1
    s = s.replace(TREE_OUT_OLD, TREE_OUT_OLD + "\n"
                  "      contract_exempted: cex, contract_blocked: cbk,\n"
                  "      contract: { path: CONTRACT.path, readable: CONTRACT.readable,\n"
                  "        bytes: CONTRACT.bytes, blob: CONTRACT.blob,\n"
                  "        fields_with_enum: Object.keys(CONTRACT.enums), enum_lines: CONTRACT.enum_lines,\n"
                  "        enum_forms: CONTRACT.enum_forms,\n"
                  "        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },", 1)

    # main()'s tree-mode report is assembled by NAME from the scan result, so fields that are not
    # listed there are computed and thrown away.  Measured: a B10 run printed contract null and no
    # blocked list even though the same file reports both under --file.
    TREE_MAIN_OLD = """      fold_without_anchor: r.fold_without_anchor,
      fold_without_anchor_count: r.fold_without_anchor.length,"""
    assert s.count(TREE_MAIN_OLD) == 1, s.count(TREE_MAIN_OLD)
    s = s.replace(TREE_MAIN_OLD, TREE_MAIN_OLD + """
      contract_exempted: r.contract_exempted,
      contract_exempted_count: (r.contract_exempted || []).length,
      contract_blocked: r.contract_blocked,
      contract_blocked_count: (r.contract_blocked || []).length,
      contract: { path: CONTRACT.path, readable: CONTRACT.readable, bytes: CONTRACT.bytes,
        blob: CONTRACT.blob, fields_with_enum: Object.keys(CONTRACT.enums),
        enum_lines: CONTRACT.enum_lines, enum_forms: CONTRACT.enum_forms,
        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },""", 1)

    # the usage line names the new flag, or the next reader cannot find it
    s = s.replace("| --ref <sha> --path <in-tree path> | --selftest",
                  "| --ref <sha> --path <in-tree path> [--contract <path to contracts/openapi.yaml>] | --selftest", 1)

    s = s.replace("        attributed_in_fold: r.attributed_in_fold.length,",
                  "        attributed_in_fold: r.attributed_in_fold.length,\n"
                  "        contract_exempted: (r.contract_exempted || []).length,\n"
                  "        contract_blocked: (r.contract_blocked || []).length,", 1)

    # the contract travels with the tree being scanned unless --contract names one explicitly
    s = s.replace("""  if (args.contract) CONTRACT = readContract(args.contract);
  if (args.selftest)""",
                  """  if (args.selftest)""", 1)
    s = s.replace("  const ts = loadTs();\n  if (!ts) {",
                  """  const firstTarget = args.contract ? null : (args.tree || (args.file || '').split(',')[0] || null);
  const contractPath = args.contract
    || (firstTarget ? contractFromTarget(firstTarget) : null)
    || (fs.existsSync('contracts/openapi.yaml') ? 'contracts/openapi.yaml' : null);
  CONTRACT = readContract(contractPath || CONTRACT_PATH);
  if (args.contract) CONTRACT_PATH = args.contract;
  if (!contractPath) CONTRACT = { path: CONTRACT_PATH, readable: false, bytes: 0, blob: null,
    enums: {}, enum_lines: {}, note: 'CONTRACT_FILE_ABSENT' };
  if (contractPath && CONTRACT.readable) CONTRACT.auto = !args.contract;
  const ts = loadTs();
  if (!ts) {""", 1)

    # the report carries the SET MEMBERS themselves, not just the count: a reader of the JSON has to
    # be able to check the exemption against the contract without re-running anything
    n_forms = s.count("fields_with_enum: Object.keys(CONTRACT.enums),")
    # 4 sites exist in the published r7b1 shape and a 5th is the tree-main report added above
    assert n_forms >= 4, n_forms
    s = s.replace("fields_with_enum: Object.keys(CONTRACT.enums),",
                  "fields_with_enum: Object.keys(CONTRACT.enums), enums: CONTRACT.enums,")
    print("contract report sites patched:", n_forms)

    s = s.replace("ui_exposure_taint_ast_r7b1.cjs", "ui_exposure_taint_ast_r7b4.cjs")
    s = s.replace("supersedes_blob: 'd3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2'",
                  "supersedes_blob: 'b6716d9a3c67dafc72fef501bfaff101c84e918a'")
    # NO APOSTROPHE IN THIS SPAN: it is spliced into a single-quoted JS literal, and "the contract's"
    # broke the parse on the first cut (SyntaxError at the lineage line).
    s = s.replace("-> r7b1 a fold anchor recognised through a spread, but only beside a provenance label",
                  "-> r7b1 a fold anchor recognised through a spread, but only beside a provenance label"
                  " -> r7b4 ORD-0408 ruling A: a *_code cell is exonerated only by the closed set that"
                  " the contract in the scanned tree names for that field, never by the field name;"
                  " a contract declaring no enum for the field is a named red"
                  " (CONTRACT_MISSING_ENUM) and the cell is not handed to the fold either")

    io.open(DST, "w", encoding="utf-8", newline="\n").write(s)
    raw = open(DST, "rb").read()
    ck = subprocess.run(["node", "--check", DST], capture_output=True, text=True)
    print("base r7b1 local sha1(bytes)", base_sha, len(io.open(SRC, encoding='utf-8').read().encode('utf-8')), "B")
    print("wrote", os.path.basename(DST), len(raw), "B  node --check rc", ck.returncode,
          (ck.stderr or "").strip()[:300])
    print("contract_exempted refs", s.count("contract_exempted"),
          "| contract_blocked refs", s.count("contract_blocked"),
          "| cnxFieldNamedOnCell refs", s.count("cnxFieldNamedOnCell"))
    return ck.returncode


if __name__ == "__main__":
    sys.exit(main())
