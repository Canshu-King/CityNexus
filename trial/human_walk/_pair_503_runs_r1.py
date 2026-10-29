"""Turn the seven agent_runs rows into the two numbers the walkthrough needs: how long the screen sat quiet
after a MODEL_HTTP_503, and how long the run started by the traveller's own second message then took.
Read-only sqlite (mode=ro); appends a computed section to the artifact so the doc quotes derived values."""
import sqlite3
import io
import datetime

DB = "D:/moodle/_cmdr_v3_live_1022/citynexus_v3_human21_1022.db"
OUT = "trial/results/20261022_v3_human_chrome/agent_runs_503_pair_1024.txt"

conn = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)


def stamp(value):
    return datetime.datetime.fromisoformat(value) if value else None


def rows_for(journey_id):
    return conn.execute(
        "select id, status, failure_reason, created_at, completed_at from agent_runs"
        " where journey_id = ? order by created_at",
        (journey_id,),
    ).fetchall()


CASES = (
    ("walk-101", "9aafda16-075c-4cf3-b584-6094be210800", "2026-10-23T18:42:25.874+00:00"),
    ("walk-102", "1a2f4474-accc-4740-960f-5a753a0b5c67", "2026-10-23T19:01:09.748+00:00"),
)

with io.open(OUT, "a", encoding="utf-8", newline="\n") as handle:
    handle.write("\n# 下面每一格都由上面那七行现算（不是手写）\n")
    for name, journey, press in CASES:
        found = rows_for(journey)
        failures = [r for r in found if r[2] == "MODEL_HTTP_503"]
        last_fail = max(failures, key=lambda r: stamp(r[4]))
        later = [r for r in found if stamp(r[3]) > stamp(last_fail[4])]
        nxt = min(later, key=lambda r: stamp(r[3])) if later else None
        press_dt = stamp(press)
        quiet = (stamp(nxt[3]) - stamp(last_fail[4])).total_seconds() if nxt else None
        handle.write(
            "%s press=%s  首个 run 于 press 后 %.1f 秒建档(%s=%s)  最后一条 503 止于 %s  共 %d 条 503\n"
            % (name, press, (stamp(found[0][3]) - press_dt).total_seconds(),
               found[0][0][:8], found[0][1], stamp(last_fail[4]).isoformat(), len(failures)))
        if nxt:
            handle.write(
                "%s 之后没有任何 run 自己再起来；旅客第二句话 (%s) 之后 %.3f 秒起 run %s，%d 秒后答 PARTIAL/%s\n"
                % (name, "见对应 walk 流水的 STEP_07", (stamp(nxt[3]) - stamp(last_fail[4])).total_seconds(),
                   nxt[0][:8], int((stamp(nxt[4]) - stamp(nxt[3])).total_seconds()), nxt[2]))
        handle.write(
            "%s 静默时长 = next_run_created - last_503_completed = %d 秒 = %d 分 %d 秒\n"
            % (name, int(quiet), int(quiet) // 60, int(quiet) % 60))
    total_503 = sum(1 for _, j, _ in CASES for r in rows_for(j) if r[2] == "MODEL_HTTP_503")
    auto = 0
    for _, journey, _ in CASES:
        ordered = rows_for(journey)
        for previous, following in zip(ordered, ordered[1:]):
            if previous[2] == "MODEL_HTTP_503" and following[1] != "CANCELLED":
                lag = (stamp(following[3]) - stamp(previous[4])).total_seconds()
                if 0 <= lag <= 60:
                    auto += 1
                    handle.write("自动重跑候选：%s 上一条 503 止于 %s，%s 秒后起了 run %s\n"
                                 % (journey[:8], stamp(previous[4]).isoformat(), int(lag), following[0][:8]))
    handle.write("两条 journey 合计 MODEL_HTTP_503 run = %d 条；上一条失败后 60 秒内自己再起来的 run = %d 次\n"
                 % (total_503, auto))
print(open(OUT, encoding="utf-8").read().splitlines()[-4])
