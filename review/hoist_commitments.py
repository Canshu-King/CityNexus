"""Splice the extracted commitment cards out of Bookings and hoist them above the phone's disclosure.

Line-range edits by hand retype 65 lines of JSX and risk losing a brace; this rewrites the two
ranges and prints what it removed and added so the change can be read back.
"""

import sys

PATH = "D:/moodle/_qoder_integration_20260919/frontend/src/app/V8Experience.tsx"
START = 3374  # the ORD-0087 comment inside Bookings
END = 3438  # the closing `})}` of the commitments map

REPLACEMENT = """          {/* The cards live in their own component so the phone's Trips -> 预订 tab can draw them
              above its 高级 / 开发者 disclosure instead of buried inside it. */}
          {showCommitments ? (
            <WalletCommitments wallet={wallet} timezone={data.journey.timezone || undefined} />
          ) : null}"""

src = open(PATH, encoding="utf-8", newline="").read()
lines = src.split("\n")
removed = lines[START - 1 : END]
if not removed[0].lstrip().startswith("{/* ORD-0087"):
    print(f"ABORT: line {START} is {removed[0][:60]!r}, not the expected comment")
    sys.exit(2)
if removed[-1].strip() != "})}":
    print(f"ABORT: line {END} is {removed[-1][:60]!r}, not the expected map close")
    sys.exit(3)

lines[START - 1 : END] = REPLACEMENT.split("\n")
out = "\n".join(lines)

# Bookings gains the switch; the mount inside Trips' developer disclosure turns it off because the
# same section is drawn above that disclosure.
prop_anchor = """  wallet: Wallet | null;
  onImport: (reservation: Record<string, unknown>) => Promise<void>;
  busy: boolean;
}) {"""
if out.count(prop_anchor) != 1:
    print(f"ABORT: Bookings' prop block matched {out.count(prop_anchor)} times")
    sys.exit(4)
out = out.replace(
    prop_anchor,
    """  wallet: Wallet | null;
  onImport: (reservation: Record<string, unknown>) => Promise<void>;
  busy: boolean;
  /* False where the caller draws `WalletCommitments` itself, which is what the phone's Trips tab
     does -- the alternative was a confirmed promise reachable only under 高级 / 开发者. */
  showCommitments?: boolean;
}) {""",
    1,
)

sig_anchor = """function Bookings({
  data,
  selected,
  chosen,
  wallet,
  onImport,
  busy,
}: {"""
if out.count(sig_anchor) != 1:
    print(f"ABORT: Bookings' signature matched {out.count(sig_anchor)} times")
    sys.exit(5)
out = out.replace(
    sig_anchor,
    """function Bookings({
  data,
  selected,
  chosen,
  wallet,
  onImport,
  busy,
  showCommitments = true,
}: {""",
    1,
)

trips_anchor = """          <details className="trips-advanced">
            <summary>{zh ? "高级 / 开发者" : "Advanced / developer"}</summary>
            <Bookings"""
if out.count(trips_anchor) != 1:
    print(f"ABORT: the Trips disclosure matched {out.count(trips_anchor)} times")
    sys.exit(6)
out = out.replace(
    trips_anchor,
    """          <div className="v8-booking-grid" data-testid="trips-commitments">
            <WalletCommitments wallet={wallet} timezone={data.journey.timezone || undefined} />
          </div>
          <details className="trips-advanced">
            <summary>{zh ? "高级 / 开发者" : "Advanced / developer"}</summary>
            <Bookings
              showCommitments={false}""",
    1,
)

open(PATH, "w", encoding="utf-8", newline="").write(out)
again = open(PATH, encoding="utf-8", newline="").read()
print(
    f"removed {len(removed)} lines, added {len(REPLACEMENT.split(chr(10)))}; "
    f"wallet-commitment renders now: {again.count('data-testid=\"wallet-commitment\"')}; "
    f"WalletCommitments uses: {again.count('<WalletCommitments')}; "
    f"showCommitments mentions: {again.count('showCommitments')}"
)
