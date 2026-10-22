import ctypes, ctypes.wintypes as wt, sys

user32 = ctypes.windll.user32
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
results = []

def cb(h, l):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, buf, n + 1)
    vis = bool(user32.IsWindowVisible(h))
    cls_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, cls_buf, 256)
    if buf.value or vis:
        results.append((pid.value, h, vis, cls_buf.value, buf.value))
    return True

user32.EnumWindows(EnumProc(cb), 0)

want = sys.argv[1].lower() if len(sys.argv) > 1 else ""
for pid, h, vis, cls, title in results:
    if want:
        if want not in title.lower() and want not in cls.lower():
            continue
    print("hwnd=%s pid=%s vis=%s class=%s title=%s" % (h, pid, vis, cls, title))
