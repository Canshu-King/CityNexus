import io, sys

P = r"D:/moodle/_qoder_pinggong_0557/frontend/src/main.tsx"
s = io.open(P, encoding="utf-8").read()

OPS = [
    ('{title || "未命名承诺 · 服务器没给名字"}',
     '{title || t("main.unnamedCommitmentServerGaveNoName")}'),
    ('? "verified feasible" : "not feasible"}',
     '? t("main.verifiedFeasible") : t("main.notFeasible")}'),
    ('? "preserved" : "not preserved"}',
     '? "preserved" : t("main.notPreserved")}'),
    ('? "verified evidence attached"', '? t("main.verifiedEvidenceAttached")'),
    (': "evidence unavailable"}', ': t("main.evidenceUnavailable")}'),
]

for old, new in OPS:
    n = s.count(old)
    if n != 1:
        sys.exit("ABORT needle %r hits=%d (need exactly 1)" % (old, n))
    s = s.replace(old, new, 1)
    print("ok", old[:40])

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("BATCH3_APPLIED=%d" % len(OPS))
