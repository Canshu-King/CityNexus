# -*- coding: utf-8 -*-
"""一眼的机器负载：物理可用、页面文件已用、C:/D:/E: 剩余。给号令者判「还要不要十六扇同开」用。"""
import ctypes
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
G = 2.0 ** 30


class MSAX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64)]


m = MSAX()
m.dwLength = ctypes.sizeof(MSAX)
ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print(u"物理可用 %.1f GB / 共 %.1f GB（已用 %.0f%%）｜提交内存已用 %.1f GB / 上限 %.1f GB" % (
    m.ullAvailPhys / G, m.ullTotalPhys / G, m.dwMemoryLoad,
    (m.ullTotalPageFile - m.ullAvailPageFile) / G, m.ullTotalPageFile / G))
for d in (u"C:/", u"D:/", u"E:/"):
    print(u"%s 剩余 %.2f GB" % (d, shutil.disk_usage(d).free / G))
