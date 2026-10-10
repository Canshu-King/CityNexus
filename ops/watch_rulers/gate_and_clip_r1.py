"""Gate an outbound note, append the standing closing line, and load it onto the clipboard with proof.

Used for the arbiter window (paste, never hand-typing) so the bytes that reach the composer are the
same bytes the Q43 gate approved: the clipboard is read back and both its character count and its code
sum must equal the gated text's.
"""
import hashlib
import io
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = sys.argv[1]
cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
text = io.open(src, encoding="utf-8").read().strip("\n")
body = text + "\n\n" + cl + "\n"
io.open("_gated_out.txt", "w", encoding="utf-8", newline="\n").write(body)

if len(cl) != 35 or sum(ord(c) for c in cl) != 765852:
    raise SystemExit("REFUSED: closing line file altered")
p = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_gated_out.txt", "--expect-clean"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
last = [l for l in (p.stdout or "").strip().splitlines() if "claims checked" in l]
print("gate:", last[-1] if last else (p.stdout or "")[-300:], "rc", p.returncode)
if p.returncode:
    print((p.stdout or "")[-1500:])
    raise SystemExit("REFUSED by the Q43 gate (claims 0 means it never measured - rewrite as F1)")
codesum = sum(ord(c) for c in body)
print("chars", len(body), "codesum", codesum, "sha256", hashlib.sha256(body.encode("utf-8")).hexdigest()[:16])
if "--clip" not in sys.argv:
    print("DRY (pass --clip)")
    raise SystemExit(0)
r = subprocess.run(["powershell", "-NoProfile", "-Command",
                    "$c = Get-Content -Raw -Encoding UTF8 'D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_gated_out.txt'; Set-Clipboard -Value $c"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("set rc", r.returncode, (r.stderr or "")[:200])
v = subprocess.run(["powershell", "-NoProfile", "-Command",
                    "$s = Get-Clipboard -Raw; $t = 0; foreach ($ch in $s.ToCharArray()) { $t += [int]$ch }; Write-Output ('chars ' + $s.Length + ' codesum ' + $t)"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
got = (v.stdout or "").strip().replace("\r", "").splitlines()[-1] if (v.stdout or "").strip() else "<empty>"
want = "chars %d codesum %d" % (len(body), codesum)
print("clipboard:", got)
print("expected :", want)
print("CLIPBOARD OK" if got == want else "CLIPBOARD MISMATCH - do not paste")
