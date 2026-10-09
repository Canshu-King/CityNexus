import subprocess, re, io
def show(*args):
    r = subprocess.run(["git", "-C", "D:/moodle/CityNexus"] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout
txt = show("show", "43711ebb3321c18131b8b3359b7da333a5335a9d:contracts/openapi.yaml")
lines = txt.splitlines()
i = 0
while i < len(lines):
    if "/journeys/{journey_id}/plans" in lines[i]:
        print("AT", i + 1, lines[i].strip())
        for j in range(i, min(i + 26, len(lines))):
            s = lines[j]
            if "200" in s or "schema" in s or "$ref" in s or "application/json" in s:
                print("   ", j + 1, s.strip()[:140])
        break
    i += 1
print("=== PlanStop / PlanActivity schema definitions mentioning place_name ===")
for n, s in enumerate(lines):
    if re.match(r"^    [A-Za-z]+:", s) and n < len(lines) - 1:
        name = s.strip().rstrip(":")
for n, s in enumerate(lines):
    if "place_name" in s:
        print("   place_name at", n + 1, s.strip()[:120])
