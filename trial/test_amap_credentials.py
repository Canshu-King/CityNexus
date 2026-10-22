from __future__ import annotations

import trial.amap_credentials as credentials


def test_saves_only_protected_bytes_and_loads_for_current_user(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv(credentials.ENV_KEY_NAME, raising=False)
    monkeypatch.setattr(credentials, "_protect_bytes", lambda data: b"test-dpapi:" + data[::-1])
    monkeypatch.setattr(
        credentials,
        "_unprotect_bytes",
        lambda data: data.removeprefix(b"test-dpapi:")[::-1],
    )
    synthetic_key = "synthetic-test-value-never-used-for-network"

    target = credentials.save_amap_key(synthetic_key)

    assert target == tmp_path / "CityNexus" / "credentials" / "amap-web-key.dpapi"
    assert target.read_bytes().startswith(b"test-dpapi:")
    assert synthetic_key.encode("utf-8") not in target.read_bytes()
    assert credentials.load_amap_key() == synthetic_key
    assert credentials.key_status() == {"configured": True, "source": "dpapi"}


def test_environment_key_has_priority_and_status_never_contains_a_key(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(credentials, "_protect_bytes", lambda data: b"ciphertext")
    monkeypatch.setattr(credentials, "_unprotect_bytes", lambda data: b"stored-test-key")
    credentials.save_amap_key("stored-test-key")
    monkeypatch.setenv(credentials.ENV_KEY_NAME, "environment-test-key")

    assert credentials.load_amap_key() == "environment-test-key"
    assert credentials.key_status() == {
        "configured": True,
        "source": "environment",
    }
