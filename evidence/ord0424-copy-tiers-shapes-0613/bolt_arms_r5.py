"""Stage five of the ORD-0424 cut: self-test arms for the three new shapes, inside the tool.

Why arms and not just a tree measurement: the tree tells me what the face reports today, and nothing
about whether it would still report it tomorrow. Each arm below injects one shape and asserts both the
count and the SHAPE the face named, so a future edit that silently stops reading ternary false-branches
or template tails fails here instead of in someone else's preflight.

The quiet arms are the load-bearing half: `<Response>` is a type argument and not an element,
`zh-CN` is a locale tag and `not_json` is a machine token, `{/* … */}` is a comment. A face that flags
those gets muted, which is the failure mode the published K4i arm was written to guard against.
"""
import ast
import io
import os

TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
TARGET = os.path.join(TOOLS, "cnx_copy_tiers_r2.py")

FUNC = '''def shape_mutants():
    """ORD-0424: one arm per shape the ?? anchor cannot see, plus the shapes it must NOT invent.

    (label, source, expected hit count, expected shape substring). An expected count of 0 is a quiet
    arm: the face must produce nothing at all, which is what proves the candidate test and the element
    parse are load-bearing rather than decorative.
    """
    arms = [
        ("K8a_jsx_text_caught",
         '  return <h3 className="v8-capability-heading">Capability needs</h3>;\\n', 1, "JSX_TEXT_NODE"),
        ("K8b_jsx_text_wrapped_lines_caught",
         '  return (\\n    <button type="button">\\n      Refresh recovery\\n    </button>\\n  );\\n',
         1, "JSX_TEXT_NODE"),
        ("K8c_generic_is_not_an_element",
         '  const rows: Array<Place> = data.map((x): Promise<Row> => x);\\n', 0, ""),
        ("K8d_template_tail_caught",
         '  const label = hard.length ? `${hard.length} hard need(s) remain explicit` : "other";\\n',
         1, "TERNARY_BRANCH"),
        ("K8e_ternary_false_branch_caught",
         '  return <h2>{explicit.length ? explicit.join(" . ") : "No explicit preferences"}</h2>;\\n',
         # the join separator is not copy and the true branch is an expression, so the
         # honest expectation for this arm is exactly one branch literal
         1, "TERNARY_BRANCH"),
        ("K8f_state_default_caught",
         '  const [intent, setIntent] = useState<string>("I prefer quiet indoor culture");\\n',
         1, "STATE_DEFAULT"),
        ("K8g_state_default_without_generic_caught",
         '  const [intent, setIntent] = useState("I prefer quiet indoor culture");\\n',
         1, "STATE_DEFAULT"),
        ("K8h_cjk_element_quiet",
         '  return <p>这台服务器说还在回收站里的行程</p>;\\n', 0, ""),
        ("K8i_jsx_comment_not_text",
         '  return (\\n    <div>\\n      {/* ORD-0382: the run the traveller asked about */}\\n      <b>x</b>\\n    </div>\\n  );\\n',
         0, ""),
        ("K8j_locale_tag_quiet",
         '  const loc = zh ? "zh-CN" : "en-GB";\\n', 0, ""),
        ("K8k_machine_token_ternary_quiet",
         '  emptyAnswer ? "empty" : (contentType ?? "").includes("html") ? "html" : "not_json",\\n',
         0, ""),
        ("K8l_brand_word_excluded",
         '  return <span>CityNexus Copilot</span>;\\n', 0, ""),
        ("K8m_single_uppercase_label_caught",
         '  return <span>PROTECTED</span>;\\n', 1, "JSX_TEXT_NODE"),
    ]
    out = []
    for label, source, want, shape in arms:
        hits = [h for h in fallback_hits(source, label + ".tsx") if not h[0].endswith("-skipped")]
        shaped = [h for h in hits if shape and shape in h[4]]
        if want and len(shaped) < want:
            detail = "NOT CAUGHT -- %d hit(s) of shape %s, wanted >=%d. Source: %s" % (
                len(shaped), shape, want, source.strip()[:70])
            out.append((label, detail, False))
        elif not want and hits:
            detail = "FALSE POSITIVE -- flagged %r as %s" % (hits[0][3][:40], hits[0][4][:26])
            out.append((label, detail, False))
        else:
            out.append((label, "%d hit(s) of shape %s as expected" % (len(shaped), shape or "-"), True))
    return out


'''

CALL = '''        print("  -- ORD-0424 shape self-test: the three new shapes must be caught, the invented ones must stay quiet --")
        for label, detail, ok in shape_mutants():
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:34s} {detail}")
            rc |= 0 if ok else 1
'''

ANCHOR_PRINT = '''        print("  -- HARDCODED_FALLBACK self-test: injected copy must be caught, machine tokens must stay quiet --")'''


def main():
    s = io.open(TARGET, encoding="utf-8").read()
    assert s.count("def shape_mutants(") == 0, "arms already wired"
    i = s.index("def fallback_mutants():")
    s = s[:i] + FUNC + s[i:]
    assert s.count(ANCHOR_PRINT) == 1
    s = s.replace(ANCHOR_PRINT, CALL.replace("\\n", "\n") + ANCHOR_PRINT, 1)
    assert s.count("for label, detail, ok in shape_mutants():") == 1
    ast.parse(s)
    io.open(TARGET, "w", encoding="utf-8", newline="\n").write(s)
    print("shape arms wired into", os.path.basename(TARGET), len(s.encode("utf-8")), "B")


if __name__ == "__main__":
    main()
