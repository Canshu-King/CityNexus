"""Counter-arm for the Select lane.

Reads a tree root (default: this repo) and states what this lane claims to have
done. Point it at a copy whose three product files are restored to the parent bytes
and the change assertions must go red -- that is the only reason the arm exists.

Cells marked SURVIVE are deliberately green in both states: they pin down what this
lane was NOT allowed to touch, so an arm that reads green cannot be read as
"this file is finished".
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
SRC = ROOT / "frontend" / "src"

ADOPTED = [
    SRC / "features" / "access" / "AccessPanel.tsx",
    SRC / "features" / "discovery" / "RealCityDiscoveryPanel.tsx",
    SRC / "features" / "inbox" / "JourneyInboxWorkbench.tsx",
]
LEGACY = SRC / "main.tsx"
COMPONENT = SRC / "components" / "CnxSelect.tsx"
CSS = SRC / "components" / "cnx-select.css"
STORY = SRC / "stories" / "CnxSelect.stories.tsx"

results = []


def cell(name, ok, detail, kind="CHANGE"):
    results.append((name, bool(ok), detail, kind))


def read(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def code_only(text):
    """Markup and rendered expressions, with the comments taken out.

    The first revision of this arm counted `<select` in the raw file and called
    AccessPanel.tsx un-adopted: the one hit was inside `{/* ORD-0518: the list is rows
    now, not a closed `<select>` */}`, a sentence about the past. Same for " of " in a
    comment. A ruler that reads prose out of a comment reports a defect that is its own.
    """
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"^\s*//.*$", " ", text, flags=re.M)
    return text


# --- the component itself -------------------------------------------------------------
comp = read(COMPONENT)
comp_code = code_only(comp)
cell("component file exists", COMPONENT.exists(), str(COMPONENT))
cell(
    "component exports the threshold it documents",
    "export const ENHANCED_MIN_OPTIONS" in comp,
    "ENHANCED_MIN_OPTIONS",
)
cell(
    "short arm renders a real select element",
    re.search(r"<select\b", comp_code) is not None,
    "a <select> is still in the component, which is what selectOption() needs",
)
cell(
    "long arm filters on every keystroke, with no debounce timer",
    "setTimeout" not in comp_code and re.search(r"onChange=\{?\(event\)", comp_code) is not None,
    "no setTimeout in the code",
)
cell(
    "long arm windows the list instead of painting it whole",
    "PAGE_ROWS" in comp_code and "IntersectionObserver" in comp_code,
    "PAGE_ROWS + IntersectionObserver",
)
count_region = re.search(
    r'(?s:className="cnx-select__count".*?>(?P<body>.*?)</p>)', comp_code
)
count_rendered = count_region.group("body") if count_region else ""
# The claim is about what lands on the glass, so the JSX expressions are taken out
# first: `{filtered.length} / {options.length}` renders "54 / 320", and the identifiers
# inside the braces never reach a traveller.
count_literal_text = re.sub(r"\{[^{}]*\}", "", count_rendered)
cell(
    "the count line renders no prose",
    count_region is not None and re.search(r"[A-Za-z]{2,}", count_literal_text) is None,
    f"literal text outside the braces = {count_literal_text.strip()!r}",
)

# --- adoption -------------------------------------------------------------------------
for path in ADOPTED:
    text = code_only(read(path))
    cell(
        f"{path.name} no longer hand-rolls a select",
        "<select" not in text,
        f"raw <select> in code = {text.count('<select')}",
    )
    cell(
        f"{path.name} imports the shared control",
        "components/CnxSelect" in text,
        "import",
    )

joined = "\n".join(code_only(read(p)) for p in ADOPTED)
for testid in ("access-invite-visibility", "manual-type", "v13-2-anchor-role"):
    cell(
        f"testid {testid} survived adoption",
        f'"{testid}"' in joined,
        "the product's own E2E arms address the control by this name",
    )
cell(
    "the discovery control is now addressable",
    'data-testid="v13-discovery-mode"' in code_only(read(ADOPTED[1])),
    "it carried no testid at all before",
)

# --- SURVIVE: what this lane was not allowed to touch ---------------------------------
legacy_text = code_only(read(LEGACY))
cell(
    "SURVIVE legacy dropdowns untouched",
    legacy_text.count("<select") == 2,
    f"main.tsx still holds its own two <select>: {legacy_text.count('<select')}",
    "SURVIVE",
)
cell(
    "SURVIVE no dictionary key invented",
    't("cnx.' not in comp and 't("select.' not in comp,
    "the component asks the dictionary for nothing",
    "SURVIVE",
)

# --- the stylesheet -------------------------------------------------------------------
css = read(CSS)
cell("stylesheet exists", CSS.exists(), str(CSS))
cell(
    "touch floor is 44px under a coarse arm",
    "min-height: 44px" in css and "pointer: coarse" in css,
    "44px + pointer: coarse",
)
cell(
    "a selected option has an unselected twin",
    '[aria-selected="true"]' in css and '[aria-selected="false"]' in css,
    "the defect class this repo names in discovery-batch.css",
)
cell(
    "the mobile panel is a sheet, not a floating box",
    re.search(r"position:\s*fixed", css) is not None
    and "safe-area-inset-bottom" in css,
    "position: fixed + safe area padding",
)
cell(
    "the list owns its scroll and stops chaining",
    "overscroll-behavior: contain" in css,
    "overscroll-behavior: contain",
)

# --- the mount that proves the long arm -----------------------------------------------
story = read(STORY)
cell(
    "story mounts both arms",
    "ShortListNativeArm" in story and "LongListSearchableArm" in story,
    "one below the threshold, one above",
)
cell(
    "the long story is actually past the threshold",
    re.search(r"length:\s*(\d{3,})", story) is not None,
    "a three-digit option count",
)

bad = [r for r in results if not r[1]]
for name, ok, detail, kind in results:
    print(f"{'ok  ' if ok else 'RED '} {kind:<7} {name}  --  {detail}")
print(
    f"cells={len(results)} "
    f"change={len([r for r in results if r[3] == 'CHANGE'])} "
    f"survive={len([r for r in results if r[3] == 'SURVIVE'])} "
    f"bad={len(bad)}"
)
sys.exit(1 if bad else 0)
