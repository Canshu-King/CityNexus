"""Mutation harness for the ORD-0326 spec: apply a named mutation, run the spec, report which tests went
red, then restore the file from git. A guard nobody ever broke is not an assertion.
"""
import io
import json
import os
import subprocess
import sys

FRONTEND = "D:/moodle/_qoder_ord0326_S1/frontend"
TARGET = os.path.join(FRONTEND, "src/lib/serverReason.ts")

MUTATIONS = {
    "A_sentence_into_main_copy": (
        '''      headline: zh
        ? "服务器给了原因，已放在下面的技术详情里。"
        : "The server gave a reason; it is in the technical detail below.",''',
        "      headline: reason.text,",
    ),
    "B_request_id_dropped_from_machine_line": (
        '''    `elapsed_ms=${reason.elapsed_ms ?? "absent"}`,
    `request_id=${reason.request_id ?? "absent"}`,
  ].join(" · ");''',
        '''    `elapsed_ms=${reason.elapsed_ms ?? "absent"}`,
  ].join(" · ");''',
    ),
}


def run_spec():
    p = subprocess.run([sys.executable if False else "node",
                        "node_modules/@playwright/test/cli.js", "test",
                        "--config", "playwright.logic.config.ts", "--reporter=list"],
                       capture_output=True, cwd=FRONTEND)
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    red = [ln.strip() for ln in out.splitlines() if ln.strip().startswith(("x ", "✘ ", "not ok"))]
    tail = [ln.strip() for ln in out.splitlines() if "passed" in ln or "failed" in ln]
    return red, tail[-2:]


def main():
    original = io.open(TARGET, encoding="utf-8").read()
    results = {}
    try:
        for name, (needle, replacement) in MUTATIONS.items():
            assert needle in original, "mutation anchor missing: " + name
            io.open(TARGET, "w", encoding="utf-8", newline="").write(original.replace(needle, replacement, 1))
            red, tail = run_spec()
            results[name] = {"red_tests": [r[:110] for r in red], "summary": tail,
                             "spec_caught_it": bool(red)}
        # mutation C: drop the multi-line refusal, addressed by line so no escape is needed
        lines = original.splitlines(keepends=True)
        idx = [i for i, l in enumerate(lines) if "if (t.includes(" in l and "return null" in l]
        if len(idx) == 1:
            mutated = list(lines)
            mutated[idx[0]] = "  // MUTANT-C guard removed\n"
            io.open(TARGET, "w", encoding="utf-8", newline="").write("".join(mutated))
            red, tail = run_spec()
            results["C_multiline_guard_removed"] = {"red_tests": [r[:110] for r in red], "summary": tail,
                                                    "spec_caught_it": bool(red)}
        else:
            results["C_multiline_guard_removed"] = {"error": "anchor not unique", "found": len(idx)}
    finally:
        io.open(TARGET, "w", encoding="utf-8", newline="").write(original)
        rc = subprocess.run(["git", "checkout", "--", TARGET], capture_output=True,
                            cwd="D:/moodle/_qoder_ord0326_S1").returncode
        results["restore"] = {"wrote_original_back": True, "git_checkout_rc": rc,
                              "tree_clean": subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                                            cwd="D:/moodle/_qoder_ord0326_S1").stdout.decode().strip() == ""}
    red, tail = run_spec()
    results["after_restore"] = {"unexpected_red": red, "summary": tail}
    io.open(os.path.join(FRONTEND, "_mutation_results.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(results, ensure_ascii=False, indent=1))
    print(json.dumps(results, ensure_ascii=False, indent=1)[:2200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
