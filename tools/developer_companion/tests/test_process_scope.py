from __future__ import annotations

import os
import subprocess
import sys
import unittest

from tools.developer_companion.process_scope import ProcessScope


class ProcessScopeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows Job Object acceptance")
    def test_closing_scope_stops_child_after_executor_parent_exits(self):
        import ctypes
        from ctypes import wintypes
        script = "import subprocess,sys; sys.stdin.readline(); p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print(p.pid,flush=True); sys.stdin.readline()"
        process = subprocess.Popen([sys.executable, "-u", "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        scope = ProcessScope(process)
        handle = None
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        try:
            process.stdin.write(b"start\n")
            process.stdin.flush()
            child_pid = int(process.stdout.readline())
            handle = kernel.OpenProcess(0x00100000, False, child_pid)  # SYNCHRONIZE
            self.assertTrue(handle)
            self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)  # WAIT_TIMEOUT
            process.stdin.write(b"exit\n")
            process.stdin.flush()
            process.wait(timeout=3)
            scope.close()
            self.assertEqual(kernel.WaitForSingleObject(handle, 3000), 0)
        finally:
            scope.kill()
            scope.close()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()
            if handle:
                kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
