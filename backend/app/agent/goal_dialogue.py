"""Traveler-facing questions and choices inside the existing GoalTask runtime."""
import re
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException


# Measured on a real Chrome walk: two traveller-facing sentences arrived with the JSON envelope
# still attached — 「…你更想选哪片水域？"}]」 and 「…怎么就近安排）」 followed by a stray quote. The
# words are the model's; this residue belongs to neither the model nor the traveller, so it is
# dropped where the sentence becomes something a traveller reads. Only ASCII envelope punctuation at
# the very end is removed; a Chinese sentence keeps every one of its own characters.
_ENVELOPE_TAIL = re.compile(r'(?:\s*["\}\],])+$')


def plain_traveller_text(value: str) -> str:
    return _ENVELOPE_TAIL.sub("", str(value or "").strip()).strip()


# A round that ends on a question is the shape this Agent uses most: it writes 「收到，按你说的改…
# 其余安排原封不动」 and then asks what to refine next. When the saved schedule did not move in that
# same round, the sentence and the schedule disagree, and only one of them is the traveller's next
# action. These are the words that tell the server the message is reporting a change it claims is done.
_CLAIMED_CHANGE_MARKS = ("已改", "改成", "换成", "已把", "替换", "已更新", "原封不动", "其余都不动", "其他都不动", "不动",
                         "已按", "已调整")


def claims_written_change(text: str) -> bool:
    value = plain_traveller_text(text)
    return any(mark in value for mark in _CLAIMED_CHANGE_MARKS)


# Measured twice on a real browser: the traveller wrote 「11 月 3 日下午…改成什刹海边一家咖啡馆坐着，
# 其他安排都别动」 and the round ended on a question about something else entirely, without claiming a
# change at all. Word-detection on the Agent's sentence alone cannot catch that shape, so the traveller's
# own request is read too: a change verb plus a word that pins it to a part of the day.
_CHANGE_VERBS = ("改成", "换成", "改为", "不要安排", "别安排", "取消", "去掉", "挪到", "调到", "不去", "替换成", "不要排")
_SCHEDULE_WORDS = ("上午", "下午", "晚上", "第一天", "第二天", "第三天", "半天", "安排", "行程", "时间")


def asks_for_schedule_change(text: str) -> bool:
    value = plain_traveller_text(text)
    return any(mark in value for mark in _CHANGE_VERBS) and any(word in value for word in _SCHEDULE_WORDS)


def latest_traveller_request(task: dict) -> str:
    """The traveller's own last words, read fresh from the stored conversation.

    The round's local copy of the task is re-read every model turn, so this must not be captured once
    before the loop: the message that matters is appended to the conversation only after that copy.
    """
    return next((str(item.get("text") or "") for item in reversed(task.get("conversation") or [])
                 if item.get("role") == "user"), "")


# 「按轻松少走、省钱、本地特色三种想法各出一版，让我三选一」 was asked twice on two browsers and both
# times the three versions came back as paragraphs, so the comparison screen had nothing to show.
# That sentence is a request for plan versions, and discussion mode does not even offer the tool that
# makes them (goal_tasks keeps the allowlist to ask_traveler and inspect_journey there).
_VERSION_MARKS = ("各出一版", "各出几种", "各给一版", "各排一版", "三选一", "二选一", "几种方案", "两种方案",
                  "三种方案", "两个版本", "对比一下", "各来一版", "分别出一版")


def asks_for_plan_versions(text: str) -> bool:
    value = plain_traveller_text(text)
    return any(mark in value for mark in _VERSION_MARKS)


# Measured on the blank-trip walk (2026-10-26): six ask_traveler calls in a row, a pending question after
# every answer, and the research button hidden while a question is on screen. The traveller's way out is to
# say so; when they do, the Agent must stop asking and save what it has. Only explicit "stop asking" words
# count -- a message that merely mentions research keeps the normal door.
_STOP_ASKING_MARKS = ("不用再问我", "不要再问我", "不用问我", "别再问", "别问了", "不要再问",
                      "直接开始研究", "按现在的方向开始研究", "按已经定下的方向开始研究",
                      "stop asking", "start research now")


def asks_to_end_questions(text: str) -> bool:
    value = plain_traveller_text(text)
    return any(mark in value for mark in _STOP_ASKING_MARKS)


def dialogue_definition() -> dict:
    return {"type": "function", "function": {"name": "ask_traveler",
        "description": "Ask one useful travel question with concrete choices and wait for the traveler. Use for preferences or tradeoffs, not internal execution details.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string", "maxLength": 600},
            "options": {"type": "array", "minItems": 2, "maxItems": 4, "items": {
                "type": "object", "properties": {"label": {"type": "string", "maxLength": 100},
                    "description": {"type": "string", "maxLength": 250}}, "required": ["label", "description"], "additionalProperties": False}}},
            "required": ["question", "options"], "additionalProperties": False}}}


def validate_question(raw: dict) -> dict:
    question = plain_traveller_text(raw.get("question") if isinstance(raw.get("question"), str) else "")
    if set(raw) != {"question", "options"} or not 1 <= len(question) <= 600:
        raise HTTPException(422, "TRAVELER_QUESTION_INVALID")
    options = raw.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 4:
        raise HTTPException(422, "TRAVELER_OPTIONS_INVALID")
    result = []
    for option in options:
        if not isinstance(option, dict) or set(option) != {"label", "description"}:
            raise HTTPException(422, "TRAVELER_OPTIONS_INVALID")
        label = plain_traveller_text(option.get("label") if isinstance(option.get("label"), str) else "")
        description = plain_traveller_text(option.get("description") if isinstance(option.get("description"), str) else "")
        if any(len(value) > limit for value, limit in ((label, 100), (description, 250))) or not label:
            raise HTTPException(422, "TRAVELER_OPTIONS_INVALID")
        result.append({"label": label, "description": description})
    return {"question": question, "options": result}


def ask_question(task: dict, args: dict, round_start_revision: int | None = None) -> dict:
    question = {"id": str(uuid4()), **validate_question(args)}
    task["pending_question"] = question
    task["assistant_summary"] = question["question"]
    transcript = list(task.get("conversation") or [])
    revision = (task.get("draft_artifact") or {}).get("revision")
    # The receipt a traveller reads beside a question is about the round that produced it. A round can
    # save the schedule and then stop on a question; claiming the question "changed nothing" would
    # hide the six arrangements that appeared on screen in the same turn.
    before = revision if round_start_revision is None else round_start_revision
    transcript.append({"role": "assistant", "text": question["question"], "message_id": question["id"],
        "at": datetime.now(timezone.utc).isoformat(),
        "draft_revision_before": before, "draft_revision_after": revision})
    task["conversation"] = transcript
    return {"status": "WAITING_FOR_TRAVELER", "options": question["options"]}
