"""Register the two ORD-0126 补项 mutants in the kill harness.

Anchors are read from the product files in this run so a hand-copied string cannot silently miss.
"""

from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
HARNESS = ROOT / "review/ord0082_0087_kill_drivers.py"
ATTRIBUTION = ROOT / "frontend/src/lib/failureAttribution.ts"
EXPERIENCE = ROOT / "frontend/src/app/V8Experience.tsx"
MARKER = "        [(SURFACE_SPEC, ['ord0220-3-a-refused-press-brings-its-reason-on-screen'])],\n    ),\n"

M1_OLD = (
    '    if (status === 401) {\n'
    '      return make("UNAUTHORIZED", "HTTP_RESPONSE", status, "RESOURCE_STATE", false, "sign-in", "failure.unauthorized", code);\n'
    '    }\n'
    '    if (status === 403) {\n'
    '      return make("FORBIDDEN", "HTTP_RESPONSE", status, "RESOURCE_STATE", false, "choose-journey", "failure.forbidden", code);\n'
    '    }\n'
)
M1_NEW = (
    '    if (status === 401 || status === 403) {\n'
    '      return make("UNAUTHORIZED", "HTTP_RESPONSE", status, "RESOURCE_STATE", false, "sign-in", "failure.unauthorized", code);\n'
    '    }\n'
)
M2_OLD = "        <PlanWithAiSheet\n          journeyId={data.journey.id}\n"
M2_NEW = '        <PlanWithAiSheet\n          journeyId={(localStorage.getItem("citynexus.v8.journey_id") ?? data.journey.id) as string}\n'

NODE_A = "ord0126d-a-403-says-permission-and-not-login"
NODE_C = "ord0126d-c-the-screen-submits-the-journey-it-shows"


def main() -> int:
    if open(ATTRIBUTION, encoding="utf-8", newline="").read().count(M1_OLD) != 1:
        print("ABORT: the 401/403 branch is not a single exact block")
        return 2
    if open(EXPERIENCE, encoding="utf-8", newline="").read().count(M2_OLD) != 1:
        print(f"ABORT: the sheet's journeyId prop occurs {open(EXPERIENCE, encoding='utf-8', newline='').read().count(M2_OLD)} times")
        return 3
    text = open(HARNESS, encoding="utf-8", newline="").read()
    if "killAB1-403-wears-the-401-sentence" in text:
        print("already registered; nothing written")
        return 0
    if text.count(MARKER) != 1:
        print(f"ABORT: marker occurs {text.count(MARKER)} times")
        return 4
    block = (
        "    (\n"
        "        # ORD-0126 补项: 403 folds back into the 401 sentence again -- the traveller is told\n"
        "        # to sign in for a refusal that a sign-in cannot change.\n"
        "        \"killAB1-403-wears-the-401-sentence\",\n"
        "        FAILURE_LIB,\n"
        f"        {M1_OLD!r},\n"
        f"        {M1_NEW!r},\n"
        f"        [(REFUSAL_SPEC, [{NODE_A!r}])],\n"
        "    ),\n"
        "    (\n"
        "        # ORD-0126 ④: the planning sheet takes the journey id from storage again instead of\n"
        "        # from the journey on screen, so it can submit a trip the traveller is not looking at.\n"
        "        \"killAB2-sheet-submits-the-stored-journey\",\n"
        "        EXPERIENCE,\n"
        f"        {M2_OLD!r},\n"
        f"        {M2_NEW!r},\n"
        f"        [(REFUSAL_SPEC, [{NODE_C!r}])],\n"
        "    ),\n"
    )
    index = text.index(MARKER) + len(MARKER)
    updated = text[:index] + block + text[index:]
    if "REFUSAL_SPEC =" not in updated:
        updated = updated.replace(
            'SURFACE_SPEC = "e2e/qoder-wizard-hint-surface-readings.spec.ts"\n',
            'SURFACE_SPEC = "e2e/qoder-wizard-hint-surface-readings.spec.ts"\n'
            'REFUSAL_SPEC = "e2e/qoder-a-refusal-says-what-it-is.spec.ts"\n'
            'FAILURE_LIB = "src/lib/failureAttribution.ts"\n',
            1,
        )
    open(HARNESS, "w", encoding="utf-8", newline="").write(updated)
    import ast

    ast.parse(open(HARNESS, encoding="utf-8").read())
    print(f"registered bytes={len(updated.encode('utf-8')) - len(text.encode('utf-8'))} parses=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
