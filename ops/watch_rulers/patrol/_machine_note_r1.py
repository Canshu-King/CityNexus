# -*- coding: utf-8 -*-
"""一行的机器账（内存＋盘），专门给 BB 机当 evidence 用：一跑一行，中枢摘录得到。

为什么单独造它：BB 机要求正文每个数都要出现在证据输出的出处里，而一条会漂的读数
（盘的剩余字节数）不能靠「先跑一遍再抄」——那等于赌两次跑之间不掉数。所以把要给号令者看的
数全部由这一条命令现取，消息正文只写判语、不写数。
"""
import ctypes
import shutil
import sys

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
c = shutil.disk_usage(u"C:/").free / G
d = shutil.disk_usage(u"D:/").free / G
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print(u"机器账｜物理内存已用百分之%d、可用 %.1f GB、提交内存已用 %.1f GB、上限 %.1f GB｜"
      u"C: 剩 %.2f GB、D: 剩 %.2f GB" % (m.dwMemoryLoad, m.ullAvailPhys / G,
                                        (m.ullTotalPageFile - m.ullAvailPageFile) / G,
                                        m.ullTotalPageFile / G, c, d))
