"""ORD-0521 r26 - Census: count all inline bilingual returns (zh ? en : zh) across frontend.

This counts every `return.*?zh\s*\?\s*[^:]*:` pattern which represents:
- Functions with hardcoded bilingual returns → need dictionary migration
- Data lookups like entry.zh/entry.en → keep as-is (server data)
- Intl.DateTimeFormat → keep as-is (not display text)
"""
import re
from pathlib import Path

ROOT = Path("frontend/src")
PATTERNS = {
    "hardcoded_returns": re.compile(r'return\s+(?:\([^)]*\)\s*)?(?:\(\))?[\w\d\s]*\?\s*[\'"]([^\'"]+)[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]'),
    "entry_lookups": re.compile(r'(?:entry|type|COLLECTION|LIFECYCLE|toolLabels)\[[^]]*\]\[?\s*zh\s*\]?'),
    "intl_format": re.compile(r'Intl\.DateTimeFormat\(zh\s*\?\s*[\'"]zh-CN[\'"]\s*:\s*[\'"]en[-a-zA-Z]+[\'"]'),
}

results = {"total_files": 0, "total_patterns": 0, "files": [], "categories": {"hardcoded": [], "entry": [], "intl": []}}

for file in ROOT.rglob("*.tsx"):
    if file.is_file() and ".spec" not in str(file):
        results["total_files"] += 1
        text = file.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("//"):
                continue
            
            # Check for patterns
            if PATTERNS["hardcoded_returns"].search(line):
                match = PATTERNS["hardcoded_returns"].search(line)
                results["categories"]["hardcoded"].append({
                    "file": f"{file.relative_to(ROOT)}:{i}",
                    "line": line.strip()[:80],
                })
                results["total_patterns"] += 1
            
            elif PATTERNS["entry_lookups"].search(line):
                results["categories"]["entry"].append({
                    "file": f"{file.relative_to(ROOT)}:{i}",
                    "line": line.strip()[:80],
                })
                results["total_patterns"] += 1
            
            elif PATTERNS["intl_format"].search(line):
                results["categories"]["intl"].append({
                    "file": f"{file.relative_to(ROOT)}:{i}",
                    "line": line.strip()[:80],
                })
                results["total_patterns"] += 1

print(f"Total files scanned: {results['total_files']}")
print(f"Total patterns found: {results['total_patterns']}")
print(f"\nHardcoded returns needing dict migration: {len(results['categories']['hardcoded'])}")
print(f"Entry lookups (keep as-is): {len(results['categories']['entry'])}")
print(f"Intl formats (keep as-is): {len(results['categories']['intl'])}")

# Save results to file
output_file = Path("review/ord0521/r26_bilingual_census_v1.txt")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"# ORD-0521 r26 bilingual census\n")
    f.write(f"## Summary\n")
    f.write(f"- Total files: {results['total_files']}\n")
    f.write(f"- Total patterns: {results['total_patterns']}\n")
    f.write(f"- Hardcoded returns: {len(results['categories']['hardcoded'])}\n")
    f.write(f"- Entry lookups: {len(results['categories']['entry'])}\n")
    f.write(f"- Intl formats: {len(results['categories']['intl'])}\n")
    
    if results["categories"]["hardcoded"]:
        f.write(f"\n## Hardcoded Returns (needs dictionary migration)\n")
        for item in sorted(results["categories"]["hardcoded"], key=lambda x: x["file"]):
            f.write(f"- `{item['file']}`: {item['line']}\n")

print(f"\nResults saved to: {output_file}")
