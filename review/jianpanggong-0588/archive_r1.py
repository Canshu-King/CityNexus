# ORD-0588 archiver: moves the union of the eight family-B branches' evidence/gpt-assist/
# artifacts into docs/revolution-archive/gpt-assist/, byte for byte, and writes a manifest
# naming the source branch, source sha, source path, archived path, lines and blob id.
#
# Nothing is written unless every source blob was read, hashed and found absent from the
# target tree first. Content travels as raw bytes (no newline translation), and the blob id
# is recomputed with the git object header so a corrupted byte cannot pass.
import hashlib
import io
import json
import os
import subprocess
import sys

SRC_REPO = r"D:/moodle/CityNexus"
TREE = r"D:/moodle/_qoder_jianpanggong_0555"
TIP = "3bf57cc0e15ee4defc833e3a3c7463d0be0d2f60"
SRCDIR = "evidence/gpt-assist/"
DSTDIR = "docs/revolution-archive/gpt-assist/"
BRANCHES = [
    "refs/heads/gpt/revolution-r6-h11-r61-prep-20260923",
    "refs/heads/gpt/revolution-r61-h12-r62-prep-20260923",
    "refs/heads/gpt/revolution-r62-r63-prep-20260923",
    "refs/heads/gpt/revolution-r7-r71-prep-20260923",
    "refs/heads/gpt/revolution-r71-r72-prep-20260923",
    "refs/heads/gpt/revolution-r72-r73-prep-20260923",
    "refs/heads/gpt/revolution-r73-r74-prep-20260924",
    "refs/heads/gpt/revolution-r74-r75-breakthrough-20260924",
]
MANIFEST = DSTDIR + "ARCHIVE_MANIFEST.tsv"
EVIDENCE = DSTDIR + "archive_evidence_r1.json"


def git(args, cwd):
    p = subprocess.Popen(["git", "-c", "core.quotepath=false"] + args, cwd=cwd,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError("%s :: %s" % (" ".join(args), err.decode("utf-8", "replace")[:160]))
    return out


def die(msg):
    sys.stdout.write("ABORT (nothing written) :: " + msg + "\n")
    sys.exit(1)


def blob_id(data):
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def main():
    head = git(["rev-parse", "HEAD"], TREE).decode().strip()
    if head != TIP:
        die("工作树不在本批基座上：%s vs %s" % (head, TIP))
    entries = []
    seen_target = {}
    for ref in BRANCHES:
        sha = git(["ls-remote", "origin", ref], SRC_REPO).decode().split()[0]
        git(["cat-file", "-e", sha + "^{commit}"], SRC_REPO)
        listing = git(["ls-tree", "-r", "--long", sha, "--", SRCDIR], SRC_REPO).decode("utf-8", "replace")
        for line in listing.splitlines():
            meta, path = line.split("\t", 1)
            parts = meta.split()
            if parts[1] != "blob":
                die("%s 上 %s 不是普通文件" % (ref, path))
            data = git(["cat-file", "blob", "%s:%s" % (sha, path)], SRC_REPO)
            want = parts[2]
            got = blob_id(data)
            if got != want:
                die("哈希不成 %s :: 声明 %s 实算 %s" % (path, want, got))
            if not path.startswith(SRCDIR):
                die("源路径不在评审目录下：" + path)
            target = DSTDIR + path[len(SRCDIR):]
            if b"\r" in data:
                die("源带 CR 字节：" + path)
            if target in seen_target:
                die("目标撞名：%s 来自 %s 与 %s" % (target, seen_target[target], ref))
            seen_target[target] = ref
            entries.append(dict(branch=ref, sha=sha, src=path, dst=target, blob=got,
                                bytes=len(data), lines=data.decode("utf-8").split("\n").__len__()))
    if len(entries) != 28:
        die("枚数不对：%d，不是一开始数到的 28" % len(entries))
    for e in entries:
        try:
            git(["cat-file", "-e", "%s:%s" % (TIP, e["dst"])], SRC_REPO)
            die("目标在线上已存在：" + e["dst"])
        except RuntimeError:
            pass

    manifest = ["# ORD-0588 归档清单：族B 八枚枝的 gpt-assist 评审产物并集，来源枝 + 仓内路径 + 行数 + blob。"]
    manifest.append("source_branch\tsource_sha\tsource_path\tarchived_path\tlines\tbytes\tblob")
    for e in sorted(entries, key=lambda x: (x["branch"], x["src"])):
        manifest.append("\t".join([e["branch"], e["sha"], e["src"], e["dst"],
                                   str(e["lines"]), str(e["bytes"]), e["blob"]]))
    manifest_bytes = ("\n".join(manifest) + "\n").encode("utf-8")

    written = {}
    for e in entries:
        raw = git(["cat-file", "blob", "%s:%s" % (e["sha"], e["src"])], SRC_REPO)
        written[e["dst"]] = raw
    written[MANIFEST] = manifest_bytes
    written[EVIDENCE] = json.dumps(dict(tip=TIP, branches=len(BRANCHES), files=len(entries),
                                       total_lines=sum(e["lines"] for e in entries),
                                       entries=sorted(entries, key=lambda x: x["dst"])),
                                   ensure_ascii=False, indent=1).encode("utf-8")

    for path, data in written.items():
        full = os.path.join(TREE, path.replace("/", os.sep))
        d = os.path.dirname(full)
        if not os.path.isdir(d):
            os.makedirs(d)
        with open(full, "wb") as fh:
            fh.write(data)
    bad = []
    for path, data in written.items():
        with open(os.path.join(TREE, path.replace("/", os.sep)), "rb") as fh:
            back = fh.read()
        if back != data:
            bad.append(path)
    for e in entries:
        with open(os.path.join(TREE, e["dst"].replace("/", os.sep)), "rb") as fh:
            if blob_id(fh.read()) != e["blob"]:
                bad.append(e["dst"])
    if bad:
        die("回读不符的枚数：%d（%s）" % (len(bad), bad[:3]))
    sys.stdout.write("ARCHIVED files=%d manifest_lines=%d total_lines=%d bytes=%d 回读不符=%d\n"
                     % (len(entries), manifest_bytes.decode("utf-8").count("\n"),
                        sum(e["lines"] for e in entries),
                        sum(len(v) for v in written.values()), len(bad)))


main()
