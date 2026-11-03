"""Draw the presentation Gantt from real mpp data (zh + en). v2: every drawn
element uses transAxes 0-1 coordinates consistently.
"""
import datetime
import json
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

matplotlib.rcParams["font.family"] = ["Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

DATA = r"D:\moodle\_se_gantt_data.json"
CLS = (r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
       r"\Classroom\previews")

GREEN = "#2E7D5B"
GREEN_L = "#A9CDBB"
BLUE = "#1F5C99"
BLUE_L = "#AFC9E3"
ORANGE = "#C05A1E"
ORANGE_L = "#EFC9AF"
INK = "#1F3A5F"
GREY = "#5A6B7D"
RED = "#C0392B"

TEXTS = {
    "zh": {
        "title": "CityNexus 软件工程 2026 · 进度总览（同一份 65 行计划的视图）",
        "sub": "条内深色 = 已完成，浅色 = 剩余；菱形 = 里程碑；红虚线 = 合同/检查节点。数据取自原生计划，未重排。",
        "done": "已完成 100%",
        "doing_ge": "进行中 ≥50%",
        "doing_lt": "进行中 <50%",
        "ms_lane": "里程碑",
        "fname": "Teacher_03_Gantt_Presentation_zh.png",
    },
    "en": {
        "title": "CityNexus Software Engineering 2026 · Progress at a glance",
        "sub": ("Dark bar = done, light = remaining; diamond = milestone; red "
                "dashed = contract/check dates. Drawn from the native plan, "
                "nothing rescheduled."),
        "done": "done 100%",
        "doing_ge": "doing ≥50%",
        "doing_lt": "doing <50%",
        "ms_lane": "Milestones",
        "fname": "Teacher_03_Gantt_Presentation_EN.png",
    },
}

D0 = datetime.date(2026, 8, 30)


def days(d):
    y, m, dd = (int(x) for x in d.split("-"))
    return (datetime.date(y, m, dd) - D0).days


data = json.load(open(DATA, encoding="utf-8"))

for lang in ("zh", "en"):
    tx = TEXTS[lang]
    tasks = data[lang]["tasks"]
    stages = [t for t in tasks if t["summary"]]
    milestones = sorted([t for t in tasks if t["milestone"]],
                        key=lambda t: t["start"])

    X0 = days("2026-08-30")
    X1 = days("2026-11-09")

    fig = plt.figure(figsize=(13.333, 7.5), dpi=200)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    px0, px1 = (0.168 if lang == "en" else 0.125), 0.975
    py0, py1 = 0.155, 0.815
    span = X1 - X0

    def tx_(day):
        return px0 + (day - X0) / span * (px1 - px0)

    # --- title block
    ax.text(0.035, 0.955, tx["title"], fontsize=17, fontweight="bold",
            color=INK, va="top", ha="left", transform=ax.transAxes)
    ax.text(0.035, 0.912, tx["sub"], fontsize=10.5, color=GREY, va="top",
            ha="left", transform=ax.transAxes)

    # --- month separators + labels
    for day, label in ((days("2026-09-01"), "2026年9月" if lang == "zh"
                        else "Sep 2026"),
                       (days("2026-10-01"), "2026年10月" if lang == "zh"
                        else "Oct 2026"),
                       (days("2026-11-01"), "2026年11月" if lang == "zh"
                        else "Nov 2026")):
        x = tx_(day)
        ax.plot([x, x], [py0 - 0.012, py1 - 0.010], color="#C3CEDD", lw=1.0,
                transform=ax.transAxes, zorder=1)
        ax.text(x + 0.006, py1 - 0.008, label, fontsize=10, color=GREY,
                va="top", ha="left", transform=ax.transAxes)

    # --- Monday ticks along the bottom axis
    d = datetime.date(2026, 9, 1)
    while d <= datetime.date(2026, 11, 8):
        if d.weekday() == 0:
            x = tx_((d - D0).days)
            ax.plot([x, x], [py0 - 0.006, py0 - 0.011], color="#C3CEDD",
                    lw=0.8, transform=ax.transAxes, zorder=1)
        d += datetime.timedelta(days=1)

    # --- stage rows
    n = len(stages)
    row_h = (py1 - py0) * 0.92 / n
    y_top = py1 - 0.004
    for i, s in enumerate(stages):
        yc = y_top - row_h * (i + 0.5)
        if lang == "en":
            import textwrap
            label = chr(10).join(textwrap.wrap(s["name"], 30))
            ax.text(0.033, yc, label, fontsize=11, color=INK, va="center",
                    ha="left", transform=ax.transAxes)
        else:
            ax.text(0.033, yc, s["name"], fontsize=12.5, color=INK,
                    va="center", ha="left", transform=ax.transAxes)
        x_s = tx_(days(s["start"]))
        x_f = tx_(days(s["finish"]))
        p = s["pct"]
        if p == 100:
            deep, light = GREEN, GREEN_L
        elif p >= 50:
            deep, light = BLUE, BLUE_L
        else:
            deep, light = ORANGE, ORANGE_L
        bh = min(row_h * 0.52, 0.034)
        ax.add_patch(FancyBboxPatch(
            (x_s, yc - bh / 2), (x_f - x_s), bh,
            boxstyle="round,pad=0,rounding_size=0.004", facecolor=light,
            edgecolor="none", transform=ax.transAxes, zorder=3))
        x_done = x_s + (x_f - x_s) * p / 100.0
        if p > 0:
            ax.add_patch(FancyBboxPatch(
                (x_s, yc - bh / 2), (x_done - x_s), bh,
                boxstyle="round,pad=0,rounding_size=0.004", facecolor=deep,
                edgecolor="none", transform=ax.transAxes, zorder=4))
        ax.text(x_f + 0.006, yc, "%d%%" % p, fontsize=10.5, color=INK,
                va="center", ha="left", transform=ax.transAxes, zorder=6)
        ax.text(x_s - 0.006, yc, s["start"][5:].replace("-", "/"),
                fontsize=8.5, color=GREY, va="center", ha="right",
                transform=ax.transAxes, zorder=6)

    # --- milestone lane
    ms_y = py0 - 0.042
    ax.text(0.033, ms_y, tx["ms_lane"], fontsize=11, fontweight="bold",
            color=INK, va="center", ha="left", transform=ax.transAxes)
    # alternate label heights so near-dated milestones do not overlap
    prev_x = None
    flip = 0
    for m in milestones:
        x = tx_(days(m["start"]))
        ax.plot([x, x], [ms_y - 0.018, py1 - 0.010], color="#B9C4D0", lw=0.8,
                ls=(0, (2, 2)), transform=ax.transAxes, zorder=2)
        hard = ("Part" in m["name"] or "contract" in m["name"]
                or "deadline" in m["name"])
        ax.plot([x], [ms_y], marker="D", markersize=7.5,
                color=RED if hard else INK, markeredgecolor="white",
                markeredgewidth=0.9, transform=ax.transAxes, zorder=6)
        if prev_x is not None and (x - prev_x) < 0.035:
            flip += 1
        else:
            flip = 0
        dy = -0.026 - 0.017 * (flip % 2)
        ax.text(x, ms_y + dy, m["name"].split()[0], fontsize=8.5,
                color=GREY, va="top", ha="center", transform=ax.transAxes,
                zorder=6)
        prev_x = x

    # --- three deadline lines
    for dd, label in (("2026-10-02",
                       "Part1 截止 10-02" if lang == "zh" else "Part 1 due"),
                      ("2026-10-23",
                       "中期会面 10-23" if lang == "zh" else "Mid-term"),
                      ("2026-11-06",
                       "Part2 截止 11-06" if lang == "zh" else "Part 2 due")):
        x = tx_(days(dd))
        ax.plot([x, x], [py0 - 0.012, py1 - 0.010], color=RED, lw=1.6,
                ls=(0, (5, 3)), transform=ax.transAxes, zorder=5)
        ha = "right" if x > 0.93 else "left"
        ax.text(x + (-0.003 if x > 0.93 else 0.003), py1 - 0.030, label,
                fontsize=9.5, color=RED, va="top", ha=ha,
                transform=ax.transAxes, zorder=6)

    # --- legend
    ly = 0.042
    ax.text(0.035, ly, ("图例:" if lang == "zh" else "Legend:"),
            fontsize=11, fontweight="bold", color=INK, va="center", ha="left",
            transform=ax.transAxes)
    lx = 0.115
    for c, label in ((GREEN, tx["done"]), (BLUE, tx["doing_ge"]),
                     (ORANGE, tx["doing_lt"])):
        ax.add_patch(FancyBboxPatch((lx, ly - 0.011), 0.030, 0.022,
                                    boxstyle="round,pad=0,rounding_size=0.004",
                                    facecolor=c, edgecolor="none",
                                    transform=ax.transAxes, zorder=6))
        ax.text(lx + 0.036, ly, label, fontsize=10.5, color=INK, va="center",
                ha="left", transform=ax.transAxes)
        lx += 0.036 + (0.088 if lang == "zh" else 0.098)
    ax.plot([lx + 0.010, lx + 0.028], [ly, ly], marker="D", markersize=7,
            color=INK, markerfacecolor="white", markeredgewidth=1.2,
            transform=ax.transAxes)
    ax.text(lx + 0.040, ly, "里程碑" if lang == "zh" else "Milestone",
            fontsize=10.5, color=INK, va="center", ha="left",
            transform=ax.transAxes)
    lx += 0.040 + (0.052 if lang == "zh" else 0.075)
    ax.plot([lx, lx + 0.014], [ly - 0.013, ly + 0.013], color=RED, lw=1.6,
            ls=(0, (4, 2)), transform=ax.transAxes)
    ax.text(lx + 0.022, ly, "合同/检查节点" if lang == "zh" else "contract dates",
            fontsize=10.5, color=INK, va="center", ha="left",
            transform=ax.transAxes)
    ax.text(0.975, ly, "generated " + time.strftime("%Y-%m-%d"),
            fontsize=8.5, color=GREY, va="center", ha="right",
            transform=ax.transAxes)

    out = os.path.join(CLS, tx["fname"])
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print("saved", out, os.path.getsize(out))
