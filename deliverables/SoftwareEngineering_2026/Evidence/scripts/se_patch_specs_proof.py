"""Splice the corrected diagrams 03/04 in, and make the Visio proof assert the
Shape Data of every node and connector on every page.

The previous proof only used the recorded Shape.IDs to check glue and never
looked at shape data, which is exactly how 535 silent property failures slipped
through. It now counts them per page and fails on any shortfall.
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 1. splice specs
P = os.path.join(HERE, "se_visio_specs_r1.py")
s = open(P, encoding="utf-8").read()
i = s.index("# ==========================================================================  03")
body = open(os.path.join(HERE, "_specs_034_v2.py"), encoding="utf-8").read()
s = s[:i] + body
open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("diagrams 03 and 04 replaced")

# ---------------------------------------------------------------- 2. proof asserts shape data
P2 = os.path.join(HERE, "se_visio_proof_r1.py")
t = open(P2, encoding="utf-8").read()
t = t.replace('''        audit = step(rec, "glueAudit", glue_audit)''',
'''        audit = step(rec, "glueAudit", glue_audit)

        # ---- B2: every node must still carry its three Shape Data rows and
        #      every connector its FlowEdge, read out of the file on disk
        def shape_data_audit():
            live = dict((pg.Shapes.Item(i).ID, pg.Shapes.Item(i))
                        for i in range(1, pg.Shapes.Count + 1))
            need = {}
            for nid, sid in node_ids.items():
                need.setdefault(sid, []).append(("NodeId", nid))
                need[sid].append(("State", None))
                need[sid].append(("SourceRef", None))
            for ekey, cid in edge_ids.items():
                need.setdefault(cid, []).append(("FlowEdge", ekey))
            ok = miss = 0
            examples = []
            for sid, props in need.items():
                sh = live.get(sid)
                if sh is None:
                    miss += len(props)
                    examples.append("shape id %s absent from the file" % sid)
                    continue
                for cell, expect in props:
                    try:
                        f = sh.CellsU("Prop.%s.Value" % cell).FormulaU
                    except Exception as exc:
                        miss += 1
                        if len(examples) < 6:
                            examples.append("id %s Prop.%s: %s" % (sid, cell,
                                                                   type(exc).__name__))
                        continue
                # read the values back and compare where a value is known
                good = True
                for cell, expect in props:
                    try:
                        f = sh.CellsU("Prop.%s.Value" % cell).FormulaU
                    except Exception:
                        good = False
                        break
                    val = f[1:-1] if len(f) >= 2 and f[0] == '"' and f[-1] == '"' else f
                    if expect is not None and val != expect:
                        good = False
                        if len(examples) < 6:
                            examples.append("id %s Prop.%s = %r, expected %r"
                                            % (sid, cell, val[:40], expect))
                        break
                    if expect is None and not val:
                        good = False
                        if len(examples) < 6:
                            examples.append("id %s Prop.%s is empty" % (sid, cell))
                        break
                if good:
                    ok += len(props)
                else:
                    miss += len(props)
            total = sum(len(v) for v in need.values())
            return {"shapes": len(need), "propsOk": ok, "propsTotal": total,
                    "propsMissing": miss, "examples": examples[:6]}
        sd = step(rec, "shapeDataAudit", shape_data_audit)''')
t = t.replace('''        checks = {
            "allEdgesGlued": bool(audit) and audit["proven"] == audit["expected"],''',
'''        checks = {
            "allEdgesGlued": bool(audit) and audit["proven"] == audit["expected"],
            "allShapeDataPresent": bool(sd) and sd["propsMissing"] == 0
            and sd["propsOk"] == sd["propsTotal"],''')
t = t.replace('''        if audit:
            log("     glue: %d/%d edges proven to both endpoints; missing=%s"
                % (audit["proven"], audit["expected"], audit["missing"][:4]))''',
'''        if audit:
            log("     glue: %d/%d edges proven to both endpoints; missing=%s"
                % (audit["proven"], audit["expected"], audit["missing"][:4]))
        if sd:
            log("     shape data: %d/%d property values read back over %d shapes; missing=%d %s"
                % (sd["propsOk"], sd["propsTotal"], sd["shapes"],
                   sd["propsMissing"], sd["examples"][:3]))''')
# multi-page: index every page, not just page 1
t = t.replace('''        pg = d.Pages.Item(1)
        info = step(rec, "index", lambda: shape_ids(pg)) or {}''',
'''        pages = []
        info = {}
        for pi in range(1, (step(rec, "pageCount", lambda: d.Pages.Count) or 1) + 1):
            pgx = d.Pages.Item(pi)
            sub = step(rec, "index_p%d" % pi, lambda g=pgx: shape_ids(g)) or {}
            info.update(sub)
            pages.append(pgx)
        pg = pages[0]
        live_all = step(rec, "liveAll", lambda: dict(
            (pages[i].Shapes.Item(k).ID, pages[i].Shapes.Item(k))
            for i in range(len(pages))
            for k in range(1, pages[i].Shapes.Count + 1))) or {}
        info = live_all''')
t = t.replace('''        connects0 = step(rec, "connects0", lambda: pg.Connects.Count)''',
'''        connects0 = step(rec, "connects0", lambda: sum(p.Connects.Count for p in pages))''')
t = t.replace('''        connects3 = step(rec, "connectsAfter", lambda: d3.Pages.Item(1).Connects.Count)''',
'''        connects3 = step(rec, "connectsAfter", lambda: sum(
            d3.Pages.Item(i).Connects.Count for i in range(1, d3.Pages.Count + 1)))''')
t = t.replace('''            live = dict((pg.Shapes.Item(i).ID, pg.Shapes.Item(i))
                        for i in range(1, pg.Shapes.Count + 1))
            pairs = {}''', '''            live = live_all
            pairs = {}''')
t = t.replace('''            live = dict((pg.Shapes.Item(i).ID, pg.Shapes.Item(i))
                        for i in range(1, pg.Shapes.Count + 1))
            for key, cid in edge_ids.items():''', '''            live = live_all
            for key, cid in edge_ids.items():''')
t = t.replace('''        sh2 = step(rec, "findAfterReopen", lambda: find_shape(d2, tid))''',
'''        sh2 = step(rec, "findAfterReopen", lambda: find_shape(d2, tid))''')
open(P2, "w", encoding="utf-8").write(t)
ast.parse(t)
print("proof now audits shape data across every page")
