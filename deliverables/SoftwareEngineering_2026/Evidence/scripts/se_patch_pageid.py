"""Multi-page identity fix.

A Visio Shape.ID is unique within a page, not within a document - so on the two
page use-case file, page 1's UC-04 and page 2's sub-UC-04.1 can carry the same
integer, and the proof was reading page 1's shape when it asked for page 2's.
Every recorded id is now scoped to its page: (page, ShapeID).
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- engine
P = os.path.join(HERE, "se_visio_lib_r1.py")
s = open(P, encoding="utf-8").read()
s = s.replace('''        self.node_ids[n["id"]] = sh.ID''',
              '''        self.node_ids[n["id"]] = (self.page_no, sh.ID)''')
s = s.replace('''        self.edge_ids["%s->%s" % (e["from"], e["to"])] = con.ID''',
              '''        self.edge_ids["%s->%s" % (e["from"], e["to"])] = (self.page_no, con.ID)''')
s = s.replace('''        self.spec_nodes = sh["nodes"]
        self.spec_edges = sh["edges"]''',
              '''        self.page_no = idx + 1
        self.spec_nodes = sh["nodes"]
        self.spec_edges = sh["edges"]''')
s = s.replace('''        self.prop_writes = {}
        self._rowcache = {}''', '''        self.prop_writes = {}
        self._rowcache = {}
        self.page_no = 1''')
# prop_writes is keyed by Shape.ID too - scope it the same way
s = s.replace('''            self.prop_writes.setdefault(sh.ID, {})[name] = got''',
              '''            self.prop_writes.setdefault((self.page_no, sh.ID), {})[name] = got''')
open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("engine records (page, ShapeID) pairs")

# ---------------------------------------------------------------- proof
P2 = os.path.join(HERE, "se_visio_proof_r1.py")
t = open(P2, encoding="utf-8").read()
t = t.replace('''        npages = step(rec, "pageCount", lambda: d.Pages.Count) or 1
        for pi in range(1, npages + 1):
            pgx = d.Pages.Item(pi)
            sub = step(rec, "index_p%d" % pi, lambda g=pgx: shape_ids(g)) or {}
            info.update(sub)
            pages.append(pgx)''',
'''        npages = step(rec, "pageCount", lambda: d.Pages.Count) or 1
        by_page = {}
        for pi in range(1, npages + 1):
            pgx = d.Pages.Item(pi)
            sub = step(rec, "index_p%d" % pi, lambda g=pgx: shape_ids(g)) or {}
            by_page[pi] = sub
            info.update(sub)
            pages.append(pgx)''')
t = t.replace('''        live_all = dict((k, v["shape"]) for k, v in info.items())''',
'''        def live(key):
            """key is (page, ShapeID) as recorded by the builder."""
            pg_i, sid = key
            return (by_page.get(pg_i) or {}).get(sid, {}).get("shape")

        live_all = dict((((pi, k), v["shape"]) for k, v in d_.items())
                        for pi, d_ in by_page.items())
        live_all = dict((k, v) for entry in live_all.values() for k, v in entry.items())''')
t = t.replace('''        def glue_audit():
            if not node_ids or not edge_ids:
                return {"expected": len(spec["edges"]), "proven": 0,
                        "missing": ["the shipped gate report carries no shape id map"]}
            live = dict((pg.Shapes.Item(i).ID, pg.Shapes.Item(i))
                        for i in range(1, pg.Shapes.Count + 1))
            pairs = {}''',
'''        nedges = sum(len(sh.get("edges", [])) for sh in spec.get("sheets", [spec]))
        nnodes = sum(len(sh.get("nodes", [])) for sh in spec.get("sheets", [spec]))

        def glue_audit():
            if not node_ids or not edge_ids:
                return {"expected": nedges, "proven": 0,
                        "missing": ["the shipped gate report carries no shape id map"]}
            pairs = {}''')
t = t.replace('''                cid = edge_ids.get(key)
                if cid not in live:
                    missing.append("%s: connector shape id %s is not in the file"
                                   % (key, cid))
                    continue
                ends = pairs.get(cid, set())
                a, z = node_ids.get(e["from"]), node_ids.get(e["to"])''',
'''                cid = edge_ids.get(key)
                conn = live(cid) if cid else None
                if conn is None:
                    missing.append("%s: connector (page %s, id %s) is not in the file"
                                   % (key, cid[0] if cid else "?", cid[1] if cid else "?"))
                    continue
                ends = pairs.get(cid[1], set())
                ak, zk = node_ids.get(e["from"]), node_ids.get(e["to"])
                a, z = ak[1] if ak else None, zk[1] if zk else None''')
t = t.replace('''            return {"expected": len(spec["edges"]), "proven": proven,
                    "missing": missing[:12]}
        audit = step(rec, "glueAudit", glue_audit)''',
'''            return {"expected": nedges, "proven": proven, "nodes": nnodes,
                    "missing": missing[:12]}
        audit = step(rec, "glueAudit", glue_audit)''')
# shape data audit: page-scoped
t = t.replace('''            need = {}
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
                    continue''',
'''            need = {}
            for nid, key in node_ids.items():
                need.setdefault(key, []).append(("NodeId", nid))
                need[key].append(("State", None))
                need[key].append(("SourceRef", None))
            for ekey, key in edge_ids.items():
                need.setdefault(key, []).append(("FlowEdge", ekey))
            ok = miss = 0
            examples = []
            for (pg_i, sid), props in need.items():
                sh = (by_page.get(pg_i) or {}).get(sid, {}).get("shape")
                if sh is None:
                    miss += len(props)
                    examples.append("page %s shape id %s absent" % (pg_i, sid))
                    continue''')
t = t.replace('''            total = sum(len(v) for v in need.values())
            return {"shapes": len(need), "propsOk": ok, "propsTotal": total,''',
'''            total = sum(len(v) for v in need.values())
            return {"shapes": len(need), "propsOk": ok, "propsTotal": total,
                    "pages": npages,''')
# the pairs map must be built across every page
t = t.replace('''            for i in range(1, pg.Connects.Count + 1):
                c = pg.Connects.Item(i)
                try:
                    f, t = c.FromSheet.ID, c.ToSheet.ID
                except Exception:
                    continue
                pairs.setdefault(f, set()).add(t)
                pairs.setdefault(t, set()).add(f)''',
'''            for pi in range(1, npages + 1):
                for i in range(1, pages[pi - 1].Connects.Count + 1):
                    c = pages[pi - 1].Connects.Item(i)
                    try:
                        f, tt = c.FromSheet.ID, c.ToSheet.ID
                    except Exception:
                        continue
                    pairs.setdefault(f, set()).add(tt)
                    pairs.setdefault(tt, set()).add(f)''')
# move proof / text round trip: page-scoped
t = t.replace('''            for key, cid in edge_ids.items():
                conn = live.get(cid)''', '''            for key, cid in edge_ids.items():
                conn = live(cid)''')
t = t.replace('''                ends = [live.get(x) for x in sorted(pairs.get(cid, set()))
                        if x in live]''',
'''                ends = [x for x in
                        ((by_page.get(cid[0]) or {}).get(s, {}).get("shape")
                         for s in sorted(pairs.get(cid[1], set())))
                        if x is not None]''')
t = t.replace('''                ends = [x for x in ends if x.ID in set(node_ids.values())]''',
'''                wanted = set(v[1] for v in node_ids.values())
                ends = [x for x in ends if x.ID in wanted]''')
t = t.replace('''        target = None
        for name, v in info.items():
            if v["id"] in set(node_ids.values()):
                target = v
                break
        if target is None:
            target = list(info.values())[0]''',
'''        wanted_ids = set(v[1] for v in node_ids.values())
        target = None
        for k, v in info.items():
            if v["id"] in wanted_ids and v.get("master"):
                target = v
                break
        if target is None:
            target = list(info.values())[0]''')
t = t.replace('''        sh2 = step(rec, "findAfterReopen", lambda: find_shape(d2, tid))''',
'''        tpg = node_page_of(tid)

        def find_shape2(doc, want):
            p = doc.Pages.Item(tpg)
            for i in range(1, p.Shapes.Count + 1):
                if p.Shapes.Item(i).ID == want:
                    return p.Shapes.Item(i)
            return None
        sh2 = step(rec, "findAfterReopen", lambda: find_shape2(d2, tid))''')
t = t.replace('''        sh3 = step(rec, "findFinal", lambda: find_shape(d3, tid))''',
'''        sh3 = step(rec, "findFinal", lambda: find_shape2(d3, tid))''')
t = t.replace('''        tid, original = target["id"], target["text"]''',
'''        tid, original = target["id"], target["text"]
        node_page_of = lambda sid: next((k[0] for k, _v in node_ids.items()
                                         if k[1] == sid), 1)''')
open(P2, "w", encoding="utf-8").write(t)
try:
    ast.parse(t)
    print("proof is page-scoped")
except SyntaxError as e:
    print("SYNTAX", e.lineno, repr(t.split(chr(10))[e.lineno - 1]))
