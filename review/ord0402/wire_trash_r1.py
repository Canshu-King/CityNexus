"""ORD-0402 slice 2 -- wire the recycle bin: nav pair, route key, registry entry.

Written as a script rather than as hand edits so each insertion is asserted to be unique before it
lands: a silent double-insert into the shared dictionary is the failure mode this lane was told to
avoid, and `assert` here is the door.
"""
from pathlib import Path

ROOT = Path("frontend/src")

# 1. The two nav labels, next to the other nav.* keys in each dictionary.
p = ROOT / "i18n/LocaleContext.tsx"
s = p.read_text(encoding="utf-8")
en_anchor = '  "nav.trips": "Trips",\n'
zh_anchor = '  "nav.trips": "\u884c\u7a0b",\n'
assert s.count(en_anchor) == 1, "en nav.trips anchor not unique"
assert s.count(zh_anchor) == 1, "zh nav.trips anchor not unique"
en_add = (
    en_anchor
    + "  /* ORD-0402 slice 2: the recycle bin nav label. The screen owns its own copy in\n"
    + "     `features/trash/journeyTrashCopy.ts`; this pair has to live in the shared dictionary only\n"
    + "     because the nav strip looks labels up as t(\"nav.\" + key) with no fallback\n"
    + "     (app/V8Experience.tsx:1672). */\n"
    + '  "nav.trash": "Recycle bin",\n'
)
zh_add = zh_anchor + '  "nav.trash": "\u56de\u6536\u7ad9",\n'
s = s.replace(en_anchor, en_add).replace(zh_anchor, zh_add)
p.write_text(s, encoding="utf-8", newline="\n")

# 2. The route key, so /v8/trash survives a hard refresh.
r = ROOT / "routes/v8Routes.ts"
t = r.read_text(encoding="utf-8")
anchor = '  { key: "twin", label: "Traveler Twin", icon: "calendar", group: "SYSTEM" },\n'
assert t.count(anchor) == 1, "route anchor not unique"
t = t.replace(
    anchor,
    anchor
    + "  /* ORD-0402 slice 2: putting the key here is what makes `/v8/trash` a route instead of a\n"
    + "     dead URL -- KNOWN_ROUTES (app/V8Experience.tsx:467) is built from these two tables, and a\n"
    + "     key outside them sends a hard refresh back to Today. The panel is mounted from the\n"
    + "     registry, so the shell still holds no mount for it. */\n"
    + '  { key: "trash", label: "Recycle bin", icon: "calendar", group: "SYSTEM" },\n',
)
r.write_text(t, encoding="utf-8", newline="\n")

# 3. The registry entry on the route surface.
g = ROOT / "app/v8PanelRegistry.tsx"
u = g.read_text(encoding="utf-8")
imp = 'import { V10LiveExecutionPanel } from "../features/execution/V10LiveExecutionPanel";\n'
assert u.count(imp) == 1, "import anchor not found"
if "JourneyTrashPanel" not in u:
    u = u.replace(
        imp,
        'import { JourneyTrashPanel } from "../features/trash/JourneyTrashPanel";\n' + imp,
    )
entry_anchor = """  {
    id: "me",
    surface: "route",
    testId: "v8-me",
    when: (s) => s.route === "me",
    render: (s) => <>{s.slots.me()}</>,
  },
"""
assert u.count(entry_anchor) == 1, "me entry anchor not unique"
u = u.replace(
    entry_anchor,
    entry_anchor
    + """  {
    /* ORD-0402 slice 2: the recycle bin, on the route surface -- the shell holds no mount for it, and
       the screen owns its two server calls (see features/trash/journeyTrash.ts for which of them is
       landed and which waits on slice 1). */
    id: "trash",
    surface: "route",
    testId: "journey-trash-panel",
    when: (s) => s.route === "trash",
    render: () => <JourneyTrashPanel />,
  },
""",
)
g.write_text(u, encoding="utf-8", newline="\n")
print("wired: nav pair (en+zh), route key, registry entry")
