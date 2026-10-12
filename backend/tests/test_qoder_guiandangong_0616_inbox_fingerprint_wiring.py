from __future__ import annotations

import json

from app.db.models import Journey
from app.journey_inbox import inbox_artifact_fingerprint
from app.operations.v9 import import_reservation_artifact


class RecordingSession:
    """只记录对象的假 session：这道门的全部副作用就是 session.add 与 flush。"""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None


def _import(session, payload):
    journey = Journey(id="j-0616")
    return journey, import_reservation_artifact(
        session, journey, artifact_type="STRUCTURED_JSON", payload=payload)


def test_import_audit_carries_a_replay_identity():
    s = RecordingSession()
    _, draft = _import(s, {"reservation": {"confirmation_code": "HX-7781", "origin": "Xiamen"}})
    audits = [o for o in s.added if type(o).__name__ == "AuditLog"]
    assert len(audits) == 1, "导入这处应当只落一条审计"
    after = json.loads(audits[0].after_json)
    fp = after["artifact_fingerprint"]
    assert isinstance(fp, str) and len(fp) == 64 and all(c in "0123456789abcdef" for c in fp)
    assert fp == inbox_artifact_fingerprint(source_kind="STRUCTURED_JSON",
                                           normalized_text=draft.raw_payload_json)
    assert after["extraction_mode"] == "DETERMINISTIC"


def test_same_artifact_same_identity_and_different_artifact_different():
    def fp_of(payload):
        s = RecordingSession()
        _import(s, payload)
        return json.loads([o for o in s.added if type(o).__name__ == "AuditLog"][0].after_json)[
            "artifact_fingerprint"]

    a = {"reservation": {"confirmation_code": "HX-1", "origin": "Xiamen"}}
    b = {"reservation": {"confirmation_code": "HX-2", "origin": "Xiamen"}}
    assert fp_of(a) == fp_of(dict(a))
    assert fp_of(a) != fp_of(b)
    # 身份不吃时间戳与运行号：同一份内容在两次调用里必须等值
    assert fp_of(a) == fp_of(a)


def test_other_keys_of_that_audit_are_untouched():
    s = RecordingSession()
    _, draft = _import(s, {"reservation": {"confirmation_code": "HX-9"}})
    after = json.loads([o for o in s.added if type(o).__name__ == "AuditLog"][0].after_json)
    assert after["status"] == draft.status
    assert set(after) == {"status", "unresolved_fields", "extraction_mode", "artifact_fingerprint"}
