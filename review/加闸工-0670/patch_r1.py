# -*- coding: utf-8 -*-
"""ORD-0670 (r77 public place facts): let the public places door carry the row's own identity and
place facts.  Two asserted replacements; no test file, no main.py, no contract file touched.
"""
import io
import sys

WT = "D:/moodle/_jz_0670/wt/"
SCHEMA = WT + "backend/app/schemas.py"
SERVICES = WT + "backend/app/services.py"

EDITS = [
    (
        SCHEMA,
        "    # What the provider actually handed us; None means it was never recorded --\n"
        "    # which is a different fact from \"WGS84\" and must not collapse into it.\n"
        "    source_coordinate_system: str | None\n",
        "    # What the provider actually handed us; None means it was never recorded --\n"
        "    # which is a different fact from \"WGS84\" and must not collapse into it.\n"
        "    source_coordinate_system: str | None\n"
        "    # The same rule for the place's own facts: a traveller comparing two entries needs the\n"
        "    # identity the provider gave, and opening hours / cost evidence must arrive as the row\n"
        "    # holds them.  An unknown cost stays unknown -- it is never folded into zero here.\n"
        "    external_id: str\n"
        "    opening_hours: dict[str, Any]\n"
        "    cost_evidence: dict[str, Any]\n",
    ),
    (
        SERVICES,
        "        source_coordinate_system=item.source_coordinate_system,\n    )\n",
        "        source_coordinate_system=item.source_coordinate_system,\n"
        "        external_id=item.external_id,\n"
        "        opening_hours=json.loads(item.opening_hours_json or \"{}\"),\n"
        "        cost_evidence=json.loads(item.metadata_json or \"{}\").get(\n"
        "            \"cost_evidence\", {\"status\": \"UNKNOWN\"}\n"
        "        ),\n"
        "    )\n",
    ),
]


def main():
    cache = {}
    for i, (path, old, new) in enumerate(EDITS, 1):
        body = cache.get(path) or io.open(path, encoding="utf-8").read()
        n = body.count(old)
        if n != 1:
            print("ABORT hunk %d in %s matched %d times (need exactly 1)" % (i, path, n))
            return 1
        cache[path] = body.replace(old, new, 1)
    for path, body in cache.items():
        io.open(path, "w", encoding="utf-8", newline="\n").write(body)
        print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
