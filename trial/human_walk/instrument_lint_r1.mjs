/**
 * A mechanical check for the one bug shape that bit this family four times on 2026-10-24: calling a Node-side
 * helper (`flat`, `say`, `now`) inside page.evaluate.  Inside the page those names do not exist, so the call
 * throws -- and when the call site is wrapped in try/catch or `.catch(() => null)`, the instrument reports an
 * absence it invented.  first_tap_layers_r2 lost its journey pointer that way and printed "same" from two empty
 * strings; play_stack_smoke_r1 died on the first line.
 *
 * Usage: node instrument_lint_r1.mjs [dir]   -- prints one line per file, exit 1 if any evaluate body uses a
 * host-only name without defining it inside the body.  It is deliberately dumb: brace-balanced slice of each
 * evaluate call, then a name test.  Run it before running any instrument.
 */
import fs from "node:fs";
import path from "node:path";

const ROOT = process.argv[2] || "D:/moodle/_cmdr_v3_port_1022";
const HOST_ONLY = ["flat", "say", "now"];
const files = fs.readdirSync(ROOT).filter((name) => name.endsWith(".mjs"));
let offenders = 0;

const callTextOf = (text, start) => {
  // Paren-balance the whole .evaluate(...) call instead of grabbing the next "{": the first cut used the next
  // brace, so a concise arrow body (page.evaluate(() => cond ? "PRESENT" : "absent")) swallowed the following
  // function's block and reported a fault that was not there.  A ruler with false reds is worse than none.
  const open = text.indexOf("(", start);
  if (open < 0) return null;
  let depth = 0;
  for (let index = open; index < text.length; index += 1) {
    if (text[index] === "(") depth += 1;
    else if (text[index] === ")") {
      depth -= 1;
      if (depth === 0) return text.slice(open, index + 1);
    }
  }
  return null;
};

for (const name of files) {
  const text = fs.readFileSync(path.join(ROOT, name), "utf8");
  const problems = [];
  let cursor = 0;
  while (true) {
    const at = text.indexOf(".evaluate(", cursor);
    if (at < 0) break;
    cursor = at + 4;
    const body = callTextOf(text, at);
    if (!body) continue;
    for (const helper of HOST_ONLY) {
      const used = new RegExp(`(?<![A-Za-z0-9_$.])${helper}\\(`).test(body);
      const defined = new RegExp(`(const|let|function)\\s+${helper}\\b`).test(body);
      if (used && !defined) {
        const line = text.slice(0, at).split("\n").length;
        problems.push("line " + line + " uses host-only " + helper + "() inside evaluate without defining it");
      }
    }
  }
  if (problems.length) {
    offenders += 1;
    for (const problem of problems) console.log("RED " + name + " " + problem);
  } else {
    console.log("ok  " + name);
  }
}
console.log("files=" + files.length + " offenders=" + offenders);
process.exit(offenders ? 1 : 0);
