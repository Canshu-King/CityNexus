import subprocess
import sys
from pathlib import Path

B = Path(r"D:\moodle\_ord0488\mut\backend")
SESSION = B / "app" / "db" / "session.py"
SCHEMA = B / "db" / "schema.sql"
ORIG_SESSION = Path(r"D:\moodle\_ord0488\session.orig")
ORIG_SCHEMA = Path(r"D:\moodle\_ord0488\schema.orig")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"

APPLY = '        if hasattr(raw, "executescript"):\n            raw.executescript(sql)\n'
LOOP = '            for statement in sql.split(";"):\n                if statement.strip():\n                    connection.exec_driver_sql(statement)\n'
CREATED = "        created = sorted(after - before)\n"


def restore() -> None:
    SESSION.write_bytes(ORIG_SESSION.read_bytes())
    SCHEMA.write_bytes(ORIG_SCHEMA.read_bytes())


def mutate(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{label}: anchor appears {text.count(old)} times"
    path.write_text(text.replace(old, new), encoding="utf-8", newline="")
    again = path.read_text(encoding="utf-8")
    assert new in again and old not in again, f"{label}: mutation did not land"
    print(f"  mutation landed: {label}")


def run(name: str) -> None:
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests/test_qoder_ord0488_schema_catchup.py",
         "-p", "no:cacheprovider", "-v", "--tb=line"],
        cwd=str(B), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    Path(rf"D:\moodle\_ord0488\mut_{name}.txt").write_text(out, encoding="utf-8")
    killed = [ln.split("::")[1].split(" ")[0] for ln in out.splitlines() if "FAILED" in ln and "::" in ln]
    tail = [ln for ln in out.splitlines() if " passed" in ln or " failed" in ln]
    print(f"  {name}: {tail[-1].strip() if tail else 'NO SUMMARY'}")
    for cell in killed:
        print(f"     killed {cell}")
    restore()


restore()
print("M1  no-heal: the DDL is never applied")
mutate(SESSION, APPLY, '        if hasattr(raw, "executescript"):\n            pass  # MUTANT M1\n', "M1a")
mutate(SESSION, LOOP, '            pass  # MUTANT M1b\n', "M1b")
run("M1_no_heal")

print("M2  silent-heal: the DDL applies but the report names nothing")
mutate(SESSION, CREATED, "        created = []  # MUTANT M2\n", "M2")
run("M2_silent_heal")

print("M3  undeclared-table: one CREATE block is deleted from the DDL")
text = SCHEMA.read_text(encoding="utf-8")
start = text.index("CREATE TABLE IF NOT EXISTS journey_checkins")
end = text.index("\n\n", start) + 2
block = text[start:end]
assert block.count("CREATE TABLE IF NOT EXISTS journey_checkins") == 1
SCHEMA.write_text(text[:start] + text[end:], encoding="utf-8", newline="")
assert "CREATE TABLE IF NOT EXISTS journey_checkins" not in SCHEMA.read_text(encoding="utf-8")
print(f"  mutation landed: M3 (removed {len(block)} B of DDL)")
run("M3_undeclared_model")

print("restored; verifying the tree is green again")
run("Z_after_restore")
