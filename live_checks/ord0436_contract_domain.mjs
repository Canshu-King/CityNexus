/**
 * ORD-0436 -- read the server's own sharing domain out of the two artifacts the server publishes.
 *
 * The screen's visibility ladder has to offer exactly the levels `ShareVisibility` has, and the only
 * honest sources for that are `contracts/openapi.yaml` and the generated `frontend/src/generated/api.ts`.
 * This module reads those two and nothing else: no source file's literals, no remembered list. It
 * returns `null` when neither artifact names the domain yet, which is the truth at this tip, and the
 * caller has to say so out loud instead of passing vacuously.
 */
import { readFileSync } from "node:fs";

const SOURCES = [
  { where: "contracts/openapi.yaml", path: "contracts/openapi.yaml" },
  { where: "frontend/src/generated/api.ts", path: "frontend/src/generated/api.ts" },
];

const fromYaml = (body) => {
  const m = body.match(/ShareVisibility:[\s\S]{0,900}?enum:\s*\[([^\]]*)\]/);
  if (!m) return null;
  return m[1].split(",").map((s) => s.trim()).filter(Boolean);
};

const fromGenerated = (body) => {
  const m = body.match(/^\s*ShareVisibility:\s*([^;]+);/m);
  if (!m) return null;
  return m[1].split("|").map((s) => s.trim().replace(/^"(.*)"$/, "$1")).filter(Boolean);
};

export function contractDomain(repo) {
  for (const source of SOURCES) {
    let body = "";
    try {
      body = readFileSync(`${repo}/${source.path}`, "utf8");
    } catch {
      continue;
    }
    const levels = source.path.endsWith(".yaml") ? fromYaml(body) : fromGenerated(body);
    if (levels && levels.length > 0) return { where: source.where, levels };
  }
  return null;
}
