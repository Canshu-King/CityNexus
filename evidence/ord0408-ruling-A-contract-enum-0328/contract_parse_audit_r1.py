"""Cross-check the ruler's line-based contract parse against a real YAML parse of the same document.

The ruler reads `contracts/openapi.yaml` by line because the door runs it on a working tree with no
dependency on a YAML library; that makes it worth asking whether the line rule invents or misses a
closed set.  A field the parser attributes a set to that the document does not declare would be a
false green waiting for a screen to name that field, so the answer has to be measured, not asserted.

Oracle: PyYAML over the identical bytes, collecting every schema node that carries `enum` together
with the property name it belongs to.  Run with the interpreter that has PyYAML:
    D:/moodle/CityNexus/.venv/Scripts/python.exe contract_parse_audit_r1.py
"""
import io
import json
import os
import sys

JIA = r"D:\moodle\_qoder_lane_S4_0926\work\ord0408\jia"
TIP_CONTRACT = os.path.join(JIA, "tip", "contracts", "openapi.yaml")
REPORT = os.path.join(JIA, "out_B10_tree.json")

TOKEN = None  # enum-shaped member test, mirrored from the ruler
import re
ENUM_SHAPE = re.compile(r"^[A-Z][A-Z0-9_]{3,}$")


def ground_truth(path):
    import yaml
    doc = yaml.safe_load(io.open(path, encoding="utf-8").read())
    found = {}      # property name -> {members, paths}

    def walk(node, prop_name):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "properties" and isinstance(v, dict):
                    for pname, pschema in v.items():
                        walk(pschema, pname)
                elif k in ("items", "additionalProperties", "not") and isinstance(v, dict):
                    walk(v, prop_name)
                elif k in ("allOf", "anyOf", "oneOf") and isinstance(v, list):
                    for part in v:
                        walk(part, prop_name)
                elif k == "enum":
                    if prop_name and isinstance(v, list):
                        members = [x for x in v if isinstance(x, str) and ENUM_SHAPE.match(x)]
                        if members:
                            e = found.setdefault(prop_name, {"members": [], "decls": 0})
                            e["decls"] += 1
                            for m in members:
                                if m not in e["members"]:
                                    e["members"].append(m)
                    # an enum key is not a property name; keep the enclosing name
                elif k == "schema" and isinstance(v, dict):
                    walk(v, prop_name)
                else:
                    walk(v, prop_name if k == prop_name else prop_name)
        elif isinstance(node, list):
            for x in node:
                walk(x, prop_name)

    walk(doc, None)
    return found


def main():
    rep = json.load(io.open(REPORT, encoding="utf-8"))
    c = rep["contract"]
    parser = {k: sorted(v) for k, v in (c.get("enums") or {}).items()}
    truth = {k: sorted(v["members"]) for k, v in ground_truth(TIP_CONTRACT).items()}

    rows = []
    for name in sorted(set(parser) | set(truth)):
        p, t = parser.get(name, []), truth.get(name, [])
        if p and t:
            state = "agree" if p == t else "members_differ"
        elif p and not t:
            state = "PARSER_INVENTED"          # the dangerous direction: a set nothing declared
        else:
            state = "parser_missed"            # the safe direction: a red that names no set
        rows.append({"field": name, "state": state,
                     "parser_line": (c.get("enum_lines") or {}).get(name),
                     "parser_form": (c.get("enum_forms") or {}).get(name),
                     "parser_members": p, "yaml_members": t,
                     "only_parser": sorted(set(p) - set(t)), "only_yaml": sorted(set(t) - set(p))})

    out = {"contract": {"path": c["path"], "bytes": c["bytes"], "blob": c["blob"]},
           "counts": {
               "fields_with_enum_per_ruler": len(parser),
               "fields_with_enum_per_pyyaml": len(truth),
               "agree": sum(1 for r in rows if r["state"] == "agree"),
               "members_differ": sum(1 for r in rows if r["state"] == "members_differ"),
               "parser_invented": sum(1 for r in rows if r["state"] == "PARSER_INVENTED"),
               "parser_missed": sum(1 for r in rows if r["state"] == "parser_missed")},
           "reason_code": {"per_ruler": parser.get("reason_code"),
                           "per_pyyaml": truth.get("reason_code"),
                           "declared_anywhere": "reason_code" in truth},
           "rows": rows}
    io.open(os.path.join(JIA, "contract_parse_audit.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["counts"], indent=1))
    print("reason_code:", json.dumps(out["reason_code"], ensure_ascii=False))
    for r in rows:
        if r["state"] != "agree":
            print("%-22s %-16s line %s form %s only_parser %s only_yaml %s" % (
                r["field"], r["state"], r["parser_line"], r["parser_form"],
                r["only_parser"], r["only_yaml"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
