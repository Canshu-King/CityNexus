"""ORD-0279 W1 instrument: hold the write lock on MY one-time DB for a bounded window.

Self-proving: immediately after arming, a second connection with timeout=0 attempts its own write and
the refusal message is printed - so "the lock is held" is a reading, not a claim.  The window is long
enough for both browser legs to arrive inside it; the process never touches a port, another DB, or the
product tree.

  usage: python o0279_lock.py <seconds>
"""
from __future__ import annotations

import sqlite3
import sys
import time

DB = 'D:/moodle/_hjp3_0279_0924/o0279.s3db'
J = '795d17ec-711f-43c0-960c-0a4b188a8cc0'
SECS = int(sys.argv[1]) if len(sys.argv) > 1 else 70

h = sqlite3.connect(DB, isolation_level=None)
h.execute('BEGIN IMMEDIATE')
h.execute('UPDATE journeys SET title = title WHERE id = ?', (J,))
print('HELD at %s (rows_touched=%d)' % (time.strftime('%H:%M:%S'), h.execute('SELECT changes()').fetchone()[0]),
      flush=True)

p = sqlite3.connect(DB, timeout=0)
try:
    p.execute('BEGIN IMMEDIATE')
    p.execute('UPDATE journeys SET title = title WHERE id = ?', (J,))
    p.commit()
    print('SELFPROOF: second writer WROTE - instrument did NOT hold the lock', flush=True)
except sqlite3.OperationalError as e:
    print('SELFPROOF: second writer refused with %r at %s' % (str(e), time.strftime('%H:%M:%S')), flush=True)
finally:
    p.close()

print('ARMED - browser legs may fire now', flush=True)
time.sleep(SECS)
h.execute('ROLLBACK')
h.close()
print('RELEASED at %s' % time.strftime('%H:%M:%S'), flush=True)
