"""Archive inbox blocks that the applier already inserted into the shared ledger.

Move  ->  _processed/<name>.inserted_HHMMSS
Index ->  _processed/_landed_index.tsv  (sha1 of the original bytes \t archived name)

Refuses to move a block whose title line is absent from the ledger, so an archive can never
mean more than "this text is inside the ledger".
"""

import glob
import hashlib
import io
import os
import sys
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROCESSED = os.path.join(INBOX, "_processed")
INDEX = os.path.join(PROCESSED, "_landed_index.tsv")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"


def main(argv):
    if len(argv) < 2:
        print("USAGE: archive_landed_blocks_r1.py <block file> [more blocks...]")
        return 2
    ledger = io.open(LEDGER, encoding="utf-8", newline="").read()
    moved = []
    for spec in argv[1:]:
        matches = sorted(glob.glob(spec)) if not os.path.isfile(spec) else [spec]
        if len(matches) != 1:
            print("ABORT %s resolves to %d inbox files" % (spec, len(matches)))
            return 3
        path = matches[0]
        raw = io.open(path, encoding="utf-8", newline="").read()
        title = raw.strip("\n").splitlines()[0].strip()
        if ledger.count(title) == 0:
            print("ABORT %s title line is not in the ledger: %s" % (os.path.basename(path), title[:60]))
            return 4
        sha1 = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        stamp = time.strftime("%H%M%S", time.localtime())
        archived = "%s.inserted_%s" % (os.path.basename(path), stamp)
        destination = os.path.join(PROCESSED, archived)
        if os.path.exists(destination):
            print("ABORT archive already exists: %s" % archived)
            return 5
        os.rename(path, destination)
        read_back = io.open(destination, encoding="utf-8", newline="").read()
        if hashlib.sha1(read_back.encode("utf-8")).hexdigest() != sha1:
            print("ABORT archived bytes changed while moving: %s" % archived)
            return 6
        with io.open(INDEX, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("%s\t%s\n" % (sha1, archived))
        moved.append((os.path.basename(path), archived, sha1, ledger.count(title)))
    for name, archived, sha1, hits in moved:
        print("MOVED %s -> _processed/%s sha1=%s ledger_title_hits=%d" % (name, archived, sha1, hits))
    tail = io.open(INDEX, encoding="utf-8", newline="").read().splitlines()[-len(moved):]
    print("INDEX_TAIL_ROWS %d" % len(tail))
    for row in tail:
        print("  " + row.replace("\t", " | "))
    print("STILL_IN_INBOX %d" % len(glob.glob(os.path.join(INBOX, "*.md"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
