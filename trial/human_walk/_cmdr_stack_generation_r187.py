"""Record that the classroom stack now serves the newest frontend without being restarted.

A worktree moved to a new commit is only 'the user sees the new code' if the dev server actually
transforms from disk. This asks both vite ports for the same module and shows which one carries this
shift's disclosure string, then names the classroom API's live health answer so nobody has to trust
a port number from memory.
"""

import io
import json
import subprocess
import sys
import urllib.error
import urllib.request

RECEIPT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_gozero\bz187-stack-generation.txt"
MODULE = "/src/trial/mobile/WorkspaceActions.tsx"
NEEDLE = "rev-agent-tool-source"
STACKS = {
    14462: "classroom vite (worktree E:/_cmdr_clean_1028)",
    14464: "tip vite (worktree E:/_cmdr_tip_113)",
}
APIS = {60362: "classroom api", 60364: "tip api"}


def git(worktree, *args):
    return subprocess.run(
        ["git", "-C", worktree] + list(args), capture_output=True, text=True, errors="replace"
    ).stdout.strip()


def fetch(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc).encode()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines = [
        "STACK GENERATION bz187",
        "AUTHORITATIVE_TIP %s" % git(r"D:\moodle\_cmdr_rescue_v3_1022", "rev-parse", "HEAD"),
        "CLASSROOM_WORKTREE %s porcelain=%d" % (
            git(r"E:\_cmdr_clean_1028", "rev-parse", "HEAD")[:10],
            len([x for x in git(r"E:\_cmdr_clean_1028", "status", "--porcelain").splitlines() if x]),
        ),
        "TIP_WORKTREE %s" % git(r"E:\_cmdr_tip_113", "rev-parse", "HEAD")[:10],
    ]
    for port, label in sorted(STACKS.items()):
        status, body = fetch("http://127.0.0.1:%d%s" % (port, MODULE))
        lines.append(
            "VITE %d %s module_status=%s bytes=%d serves_disclosure=%s"
            % (port, label, status, len(body), NEEDLE in body.decode("utf-8", "replace"))
        )
    for port, label in sorted(APIS.items()):
        status, body = fetch("http://127.0.0.1:%d/api/v1/health" % port)
        snippet = body.decode("utf-8", "replace")[:120].replace("\n", " ")
        lines.append("API %d %s health_status=%s body=%s" % (port, label, status, snippet))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
