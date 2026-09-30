import hashlib
import pathlib
import subprocess

TREE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0477")
FINAL = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run/ord0477_api_final.ts")
INSTALLED = TREE / "frontend/src/generated/api.ts"

report = []
for label, path in (("final", FINAL), ("installed", INSTALLED)):
    data = path.read_bytes()
    report.append(
        "%s bytes=%d crlf=%d lf=%d foreign=%d sort_lines=%d sha1=%s"
        % (
            label,
            len(data),
            data.count(b"\r\n"),
            data.count(b"\n"),
            data.count(b"V13NamedRejection"),
            data.count(b'sort?: "RECENT_UPDATE"'),
            hashlib.sha1(data).hexdigest(),
        )
    )

same = FINAL.read_bytes() == INSTALLED.read_bytes()
report.append("installed_equals_generated=%s" % same)
blob = subprocess.run(
    ["git", "-C", r"D:/moodle/CityNexus", "hash-object", str(INSTALLED)],
    capture_output=True, text=True,
)
report.append("git_hash_object_rc=%s blob=%s" % (blob.returncode, blob.stdout.strip()))
print("\n".join(report))
