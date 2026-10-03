"""ORD-0504 book-screen hand -- prove the 回答事实 arms bite, by moving the product's own words.

The baseline reading left reds, and a red is only evidence if the code path that caused it can be
pointed at. So this file does six one-line mutations of the 预订 face, rebuilds the bundle, serves it on
this lane's own front, re-runs the arms, and restores the source byte for byte:

  R1  break    an unpriced *ticket* prints a zero instead of the word   -> the ticket zero arm goes red
  R1b break    an unpriced *commitment* prints a zero instead of the word-> the commitment zero arm goes red
  R2  break    the 模拟承诺 badge is never drawn                          -> the reference arm goes red
  F1  fix-check 已确认 is derived from the server's status word           -> the status arm goes green
  F2  fix-check the naive "print the ISO code" repair, which divides every currency by 100
              -> the zero-decimal arm goes RED: the naive repair is itself the defect I shipped
                 in `frontend/src/features/trip/spendFacts.ts` (`moneyText`)
  F3  fix-check code display that keeps each currency's own exponent      -> the currency arm goes green

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/book_screen_controls_r1.py

Environment: `BOOK_CTRL_OUT` names the report (default `book_screen_controls_r1.txt`) and each control
writes its own arms reading to `book_screen_control_arms_<label>.json`.
Leaves the source restored. Rebuild the real bundle afterwards with the command the report prints.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
TARGET = TREE / "frontend" / "src" / "app" / "V8Experience.tsx"
OUT = TREE / "review" / "ord0504" / os.environ.get(
    "BOOK_CTRL_OUT", "book_screen_controls_r1.txt")
BASELINE_DIST = LANE / "dist_book_tip"
BASELINE_ENTRY_SHA1 = ""  # filled below, from the bundle the baseline pass actually graded
PROXY = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_static_api_proxy_r1.py")
PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
NODE = "node"

TICKET_PRICE_BLOCK = """                <strong>
                  {item.price.amount_minor == null
                    ? t("bookings.priceUnknown")
                    : money(
                        item.price.amount_minor,
                        item.price.currency ?? "CNY",
                        locale,
                      )}
                </strong>"""

# (label, find, replace, arm expected to change, direction)
CONTROLS = [
    ("R1 an unpriced ticket prints 0.00 instead of the word",
     """                  {item.price.amount_minor == null
                    ? t("bookings.priceUnknown")
                    : money(
                        item.price.amount_minor,
                        item.price.currency ?? "CNY",
                        locale,
                      )}""",
     """                  {money(
                        item.price.amount_minor ?? 0,
                        item.price.currency ?? "CNY",
                        locale,
                      )}""",
     "book_screen/an_unlearned_ticket_price_stays_a_word_not_a_zero", "to red"),
    ("R1b an unlearned commitment price prints 0.00 instead of the word",
     """                {known && amountMinor != null
                  ? money(amountMinor, item.monetary_value?.currency ?? "CNY", locale)""",
     """                {amountMinor != null
                  ? money(amountMinor, item.monetary_value?.currency ?? "CNY", locale)""",
     "book_screen/an_unlearned_price_stays_a_word_not_a_zero", "to red"),
    ("R2 the simulated badge is never drawn",
     'const simulated = String(item.external_ref ?? "").startsWith("mock-");',
     "const simulated = false;",
     "book_screen/the_simulated_word_only_covers_a_mock_reference", "to red"),
    ("F1 the confirmed word is read off the server's status",
     """              <span className={`v8-booking-state${item.commitment_id ? " safe" : ""}`}>
                {item.commitment_id
                  ? zh
                    ? "已确认 · 受保护"
                    : "Confirmed · protected"
                  : zh
                    ? "已确认 · 未成承诺"
                    : "Confirmed · no commitment"}
              </span>""",
     """              <span className={`v8-booking-state${item.commitment_id ? " safe" : ""}`}>
                {!["CONFIRMED", "FULFILLED", "COMPLETED"].includes(String(item.status))
                  ? (zh ? "待确认 · 服务器未确认" : "Pending · not confirmed by the server")
                  : item.commitment_id
                    ? zh
                      ? "已确认 · 受保护"
                      : "Confirmed · protected"
                    : zh
                      ? "已确认 · 未成承诺"
                      : "Confirmed · no commitment"}
              </span>""",
     "book_screen/confirmed_words_only_where_the_server_said_confirmed", "to green"),
    ("F2 the naive ISO-code fix (always divide by 100)",
     TICKET_PRICE_BLOCK,
     """                <strong>
                  {item.price.amount_minor == null
                    ? t("bookings.priceUnknown")
                    : `${item.price.currency ?? "CNY"} ${(item.price.amount_minor / 100).toFixed(2)}`}
                </strong>""",
     "book_screen/a_zero_decimal_currency_is_not_divided_by_100", "to red"),
    ("F3 the code-display fix that keeps each currency's own exponent",
     TICKET_PRICE_BLOCK,
     """                <strong>
                  {item.price.amount_minor == null
                    ? t("bookings.priceUnknown")
                    : new Intl.NumberFormat(locale, {
                        style: "currency",
                        currencyDisplay: "code",
                        currency: item.price.currency ?? "CNY",
                        maximumFractionDigits: ["JPY", "KRW", "VND", "IDR"].includes(
                          String(item.price.currency ?? "CNY").toUpperCase(),
                        )
                          ? 0
                          : 2,
                      }).format(
                        item.price.amount_minor /
                          (["JPY", "KRW", "VND", "IDR"].includes(
                            String(item.price.currency ?? "CNY").toUpperCase(),
                          )
                            ? 1
                            : 100),
                      )}
                </strong>""",
     "book_screen/every_ticket_price_is_traceable_to_the_currency_answered", "to green"),
]

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def run(cmd: list[str], cwd: Path | None = None,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd or TREE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


def rebuild(dist: str) -> None:
    r = run([NODE, "node_modules/vite/bin/vite.js", "build", "--outDir",
             str(LANE / dist), "--emptyOutDir"], cwd=TREE / "frontend")
    if r.returncode:
        raise SystemExit("BUILD FAILED\n" + (r.stdout + r.stderr)[-2000:])


def listeners() -> list[str]:
    out = run(["bash", "-c", "netstat -ano | grep ':4931 ' | grep LISTENING | awk '{print $5}' | sort -u"]).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def stop_port_holders() -> None:
    """This proxy answers on 4931 from a child process, so killing the child alone gets it re-raised
    a second later. Kill the whole tree of every holder, then re-check."""
    for _ in range(4):
        holders = listeners()
        if not holders:
            return
        for pid in holders:
            # single slashes: this goes straight to CreateProcess, so the MSYS `//PID` habit that
            # works in a bash line is silently rejected here -- and a silent failure to kill is
            # exactly how four controls ended up grading a stale bundle.
            killed = run(["taskkill", "/PID", pid, "/T", "/F"])
            # taskkill answers in the console codepage; printing that here killed the run, so keep
            # the message to ascii and never let a report line depend on it
            note = " ".join((killed.stdout + killed.stderr).split())[:120].encode("ascii", "ignore").decode()
            print("taskkill %s -> rc=%s %s" % (pid, killed.returncode, note))
            if killed.returncode:
                raise SystemExit("REFUSE: taskkill could not stop %s (%s)" % (pid, note))
        time.sleep(1.5)
    raise SystemExit("REFUSE: %s still holds port 4931 after four rounds; a control that grades a "
                     "stale bundle proves nothing" % listeners())


def restart_front(dist: str) -> None:
    stop_port_holders()
    env = dict(os.environ, NO_PROXY="*", HTTP_PROXY="", HTTPS_PROXY="")
    subprocess.Popen([str(PY), str(PROXY), "--dist", str(LANE / dist), "--port", "4931",
                      "--api", "8731", "--log", str(LANE / "run" / f"front_4931_{dist.replace('/', '_')}.log")],
                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(45):
        try:
            OPENER.open("http://127.0.0.1:4931/", timeout=3).read()
            break
        except Exception:
            time.sleep(1)
    else:
        raise SystemExit("front never came up")


def served_entry() -> dict[str, object]:
    """The entry JS the port actually answers with, and its sha1: proof the bundle was swapped."""
    shell = OPENER.open("http://127.0.0.1:4931/", timeout=15).read()
    import re
    match = re.search(rb"(/[A-Za-z0-9_./-]*assets/index-[A-Za-z0-9_-]+\.js)", shell)
    asset = match.group(1).decode() if match else "/__none__"
    body = OPENER.open("http://127.0.0.1:4931" + asset, timeout=30).read()
    return {"entry": asset, "sha1": sha1(body), "bytes": len(body)}


def arms(sink: str) -> dict[str, object]:
    """Run the 11 arms against whatever this port is answering, and park this control's own reading in
    `sink` -- two controls sharing one evidence file is how the last round lost the trail."""
    r = run([NODE, "review/ord0504/book_screen_facts_r1.js"], cwd=TREE,
            env=dict(os.environ, BOOK_OUT=sink))
    verdict = {}
    for line in (r.stdout or "").splitlines():
        if line.startswith(("PASS  ", "FAIL  ")):
            verdict[line[6:].split(" ")[0]] = line.startswith("PASS")
    tail = [line for line in (r.stdout or "").splitlines() if line.startswith("ARMS=")]
    problems = [line for line in (r.stdout or "").splitlines()
                if line.startswith("DRIVER_ERROR") or line.startswith("BUILD FAILED")]
    return {"verdict": verdict, "summary": tail[-1] if tail else "no-summary",
            "exit": r.returncode, "problems": problems, "stderr": (r.stderr or "")[-300:]}


def baseline_entry_sha1() -> str:
    import re
    shell = (BASELINE_DIST / "index.html").read_bytes()
    match = re.search(rb"(/[A-Za-z0-9_./-]*assets/index-[A-Za-z0-9_-]+\.js)", shell)
    if not match:
        raise SystemExit("REFUSE: no entry asset in %s" % BASELINE_DIST)
    return sha1((BASELINE_DIST / match.group(1).decode().lstrip("/")).read_bytes())


def main() -> int:
    global BASELINE_ENTRY_SHA1
    BASELINE_ENTRY_SHA1 = baseline_entry_sha1()
    print("baseline served-bundle witness: entry sha1 %s" % BASELINE_ENTRY_SHA1)
    original = TARGET.read_bytes()
    before = sha1(original)
    lines = ["ORD-0504 book-screen controls", "V8Experience.tsx sha1 before = %s" % before, ""]
    chosen = sys.argv[1:]
    for index, (label, find, replace, arm, direction) in enumerate(CONTROLS):
        if chosen and str(index + 1) not in chosen:
            lines.append("=== %s" % label)
            lines.append("    skipped by argument")
            lines.append("")
            continue
        find_b, replace_b = find.encode("utf-8"), replace.encode("utf-8")
        if original.count(find_b) != 1:
            raise SystemExit("REFUSE: %s appears %d times, cannot mutate uniquely" % (label, original.count(find_b)))
        TARGET.write_bytes(original.replace(find_b, replace_b, 1))
        rebuild("dist_book_mut")
        restart_front("dist_book_mut")
        served = served_entry()
        sink = "review/ord0504/book_screen_control_arms_%s.json" % label.split(" ", 1)[0].lower()
        result = arms(sink)
        observed = result["verdict"].get(arm)
        # an arm that never reported is not a caught arm: it says the run broke, not that the code moved
        if observed is None:
            expected_text = "INCONCLUSIVE (the arms never reached that judgement)"
        else:
            expected_text = "CAUGHT" if (direction == "to green") == observed else "MISSED"
        lines.append("=== %s" % label)
        lines.append("    arms reading: %s" % sink)
        lines.append("    expected %s %s" % (arm, direction))
        lines.append("    observed %s" % ("absent-from-run" if observed is None else ("PASS" if observed else "FAIL")))
        lines.append("    %s" % result["summary"])
        lines.append("    served entry %s sha1 %s (%s B) baseline sha1 %s"
                     % (served["entry"], served["sha1"], served["bytes"], BASELINE_ENTRY_SHA1))
        built = sha1((LANE / "dist_book_mut" / served["entry"].lstrip("/")).read_bytes())
        lines.append("    served bytes == bytes of the bundle this control built: %s" % (built == served["sha1"]))
        if served["sha1"] == BASELINE_ENTRY_SHA1:
            lines.append("    MUTANT_NOT_IN_SERVED_BYTES: the port still answers the baseline bundle")
        lines.append("    red arms: %s" % (sorted(k for k, v in result["verdict"].items() if not v) or "none"))
        if result["problems"]:
            lines.append("    run problems: %s" % result["problems"])
            lines.append("    stderr tail: %s" % " ".join(result["stderr"].split())[:200])
        lines.append("    verdict: %s" % expected_text)
        lines.append("")
    TARGET.write_bytes(original)
    same = TARGET.read_bytes() == original
    lines.append("restored: bytes_equal_to_before=%s sha1=%s" % (same, sha1(TARGET.read_bytes())))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    print("rebuild the real bundle: node node_modules/vite/bin/vite.js build --outDir %s --emptyOutDir"
          % (LANE / "dist_book_tip"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
