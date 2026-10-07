import io
import os
import re
import subprocess

REPO = r"D:/moodle/_qoder_exec_r1"
SPEC = os.path.join(REPO, "frontend", "e2e", "qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts")

ARM = u'''
/* The hub was only the first screen. This arm walks every .ts/.tsx under frontend/src so a counted
   English noun cannot soften itself into `(s)` on some other screen while the ruler only guards three
   files. The decision is per OCCURRENCE, not per line: a line can hold both an arrow parameter named `s`
   and a real screen string, and a per-line test produced a false positive on the first run. Comment lines
   are skipped, because plural.ts's own header names the dodge it rejects. */
function sources(dir: string, into: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) sources(full, into);
    else if (/\\.(ts|tsx)$/.test(entry)) into.push(full);
  }
  return into;
}

function softenedInStrings(line: string): number[] {
  const found: number[] = [];
  let quote = "";
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quote) {
      if (ch === "\\\\") { i += 1; continue; }
      if (ch === quote) quote = "";
      else if (ch === "(" && /^\\\\(s\\\\)/.test(line.slice(i)) && !/^\\\\(s\\\\)\\\\s*=>/.test(line.slice(i))) found.push(i);
      continue;
    }
    if (ch === "`" || ch === '"' || ch === "'") { quote = ch; continue; }
    if (ch !== "(") continue;
    if (/^\\\\(s\\\\)/.test(line.slice(i)) && !/^\\\\(s\\\\)\\\\s*=>/.test(line.slice(i))) found.push(i);
  }
  return found;
}

test("no screen under frontend/src softens a counted English noun into `(s)`", () => {
  const files = sources(join(ROOT, "frontend", "src"));
  const hits: string[] = [];
  const posix = (p: string) => p.split("\\\\").join("/");
  for (const file of files) {
    const relative = posix(file).slice(posix(ROOT).length + 1);
    const lines = readFileSync(file, "utf8").split("\\n");
    lines.forEach((line, index) => {
      const text = line.trim();
      if (text.startsWith("*") || text.startsWith("//") || text.startsWith("/*")) return;
      if (!softenedInStrings(text).length) return;
      hits.push(relative + ":" + (index + 1) + "  " + text.slice(0, 100));
    });
  }
  expect(hits, "a counted English noun on some screen went back to the `1 or more` dodge").toEqual([]);
  expect(files.length, "the walk found almost no sources, so this arm would pass on nothing").toBeGreaterThan(100);
});
'''

src = io.open(SPEC, encoding="utf-8").read()
if "no screen under frontend/src softens" in src:
    print("arm already present")
else:
    if not src.endswith("\n"):
        src += "\n"
    src += ARM
    io.open(SPEC, "w", encoding="utf-8", newline="\n").write(src)
    print("arm appended")

# syntax sanity: the arm must not contain the literal replacement char
assert "" not in src, "replacement char written into the spec"
print("no replacement char in spec")