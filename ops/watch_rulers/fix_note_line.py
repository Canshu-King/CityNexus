import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"C:\Users\仓鼠王\Desktop\CityNexus_包工头留言.txt"
s = io.open(p, encoding="utf-8", newline="").read()
old = "   但**完整那条"
idx = s.find(old)
if idx < 0:
    print("anchor not found; nothing changed")
    raise SystemExit(0)
end = s.find("\n", idx)
new = ("   **完整那条\"准备→预订→开始→中断→重规划\"我在 19:5x 在数据库副本上重走过一遍**（不碰你手机现场）："
       "每步都是 200/201，受保护承诺在重规划前后一字未动。演示顺序铁律不变：**建承诺要在\"进入执行\"之前**。")
s2 = s[:idx] + new + s[end:]
io.open(p, "w", encoding="utf-8", newline="").write(s2)
print("replaced line:", repr(s[idx:end][:60]), "->", repr(new[:60]))
