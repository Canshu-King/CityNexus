import hashlib
import io
import os
import subprocess
import sys

ROOT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
SRC = os.path.join(ROOT, "ui_exposure_taint_ast_r7b1.cjs")
DST = os.path.join(ROOT, "ui_exposure_taint_ast_r7b3.cjs")

OLD = """      const context = h.sink === 'jsx-text' ? foldContext(h._node) : null;"""
NEW = """      /* ORD-0408 ruling B (commander, 2026-09-29 01:3x): the attribute slot is the sanctioned side.
         A cell that writes an upstream token into `data-cnx-value=` on an element that names the field
         (`data-cnx-field="reason_code"`) is exonerated by the ruler and recorded, not hidden.  Text
         positions are NOT covered - `UPSTREAM_TEXT_VIA_HELPER_TO_DOM@233` stays red, and the commander
         called that red "the ruler working", not a cost.  No shape regex, no contract enum: today
         `contracts/openapi.yaml` declares `reason_code: {type: string}` with no enum, so a closed set
         could not be read (ruling A deferred until the contract carries one). */
      const slotAnchor = h.sink === 'dom-attribute' ? cnxValueAnchorOf(h._node) : null;
      if (slotAnchor) {
        anchor_attributed.push({ file_line: h.line, rule: h.rule, sink: h.sink, snippet: h.snippet,
          taint_chain: h.taint_chain, attribute_written: slotAnchor.writes,
          anchor_field: slotAnchor.field, anchor_line: slotAnchor.line });
        continue;
      }
      const context = h.sink === 'jsx-text' ? foldContext(h._node) : null;"""

HELPER = """
  /* The cell's own element, writing `data-cnx-value=` while naming the field on the same element. */
  function cnxValueAnchorOf(node) {
    for (let cur = node; cur; cur = cur.parent) {
      if (!ts.isJsxAttribute(cur)) continue;
      const owner = cur.parent && cur.parent.parent ? cur.parent.parent : null;
      const name = cur.name ? cur.name.getText(sf) : '';
      if (name !== 'data-cnx-value' || !owner) return null;
      let field = null, fieldLine = null;
      for (const a of jsxAttrsOf(owner)) {
        if (!a.name || a.name.getText(sf) !== 'data-cnx-field' || !a.initializer) continue;
        let v = a.initializer;
        if (ts.isJsxExpression(v)) v = v.expression;
        if (v && v.kind === ts.SyntaxKind.StringLiteral) { field = v.text; fieldLine = lineOf(owner); }
      }
      if (!field || !/^[a-z][a-z0-9_]*code$/i.test(field)) return null;
      return { writes: name, field: field, line: fieldLine };
    }
    return null;
  }
"""


def main():
    src = io.open(SRC, encoding="utf-8").read()
    assert src.count(OLD) == 1
    s = src.replace(OLD, NEW, 1)
    anchor = "  function foldContext(node) {"
    assert s.count(anchor) == 1
    s = s.replace(anchor, HELPER + "\n" + anchor, 1)
    s = s.replace("    const kept = [], folded = [], foldless = [];",
                  "    const kept = [], folded = [], foldless = [], anchor_attributed = [];", 1)
    s = s.replace("""    return { hits: kept.sort((a, b) => a.line - b.line), attributed_in_fold: folded,
      fold_without_anchor: foldless,""",
                  """    return { hits: kept.sort((a, b) => a.line - b.line), attributed_in_fold: folded,
      attributed_by_cnx_value_anchor: anchor_attributed,
      fold_without_anchor: foldless,""", 1)
    s = s.replace("ui_exposure_taint_ast_r7b1.cjs", "ui_exposure_taint_ast_r7b3.cjs")
    s = s.replace("supersedes_blob: 'd3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2'",
                  "supersedes_blob: 'b6716d9a3c67dafc72fef501bfaff101c84e918a'")
    s = s.replace("-> r7b1 a fold anchor recognised through a spread, but only beside a provenance label",
                  "-> r7b1 a fold anchor recognised through a spread, but only beside a provenance label"
                  " -> r7b3 ruling B: the data-cnx-value attribute slot named by data-cnx-field is "
                  "exonerated by the ruler; text positions stay red")
    io.open(DST, "w", encoding="utf-8", newline="\n").write(s)
    ck = subprocess.run(["node", "--check", DST], capture_output=True, text=True)
    raw = open(DST, "rb").read()
    print("written", os.path.basename(DST), len(raw), "B  node --check rc", ck.returncode,
            (ck.stderr or "").strip()[:160])
    return ck.returncode


if __name__ == "__main__":
    sys.exit(main())
