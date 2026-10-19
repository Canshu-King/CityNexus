"""Local Windows credential storage for the Amap Web Service key.

The key is encrypted with the current Windows user's DPAPI and stored outside
the checkout. Applications should call :func:`load_amap_key` at startup and
must never log its return value.
"""

from __future__ import annotations

import ctypes
import os
import tempfile
from ctypes import wintypes
from pathlib import Path


ENV_KEY_NAME = "CITYNEXUS_AMAP_WEB_KEY"
_DPAPI_ENTROPY = b"CityNexus/Amap/WebKey/v1"
_DPAPI_UI_FORBIDDEN = 0x1
_MAX_KEY_LENGTH = 512
_CREDENTIAL_FILENAME = "amap-web-key.dpapi"


class AmapCredentialError(RuntimeError):
    """A safe-to-display credential configuration error."""


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def credential_path() -> Path:
    """Return the per-user encrypted credential path without creating it."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise AmapCredentialError("LOCALAPPDATA is unavailable for this user.")
    return Path(local_app_data) / "CityNexus" / "credentials" / _CREDENTIAL_FILENAME


def _make_blob(data: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    if not data:
        raise AmapCredentialError("Credential data is empty.")
    storage = ctypes.create_string_buffer(data, len(data))
    blob = _DataBlob(
        len(data),
        ctypes.cast(storage, ctypes.POINTER(ctypes.c_byte)),
    )
    return blob, storage


def _protect_bytes(plaintext: bytes) -> bytes:
    if os.name != "nt":
        raise AmapCredentialError("Windows DPAPI is required to store this credential.")

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    source, source_storage = _make_blob(plaintext)
    entropy, entropy_storage = _make_blob(_DPAPI_ENTROPY)
    protected = _DataBlob()
    ok = crypt32.CryptProtectData(
        ctypes.byref(source),
        "CityNexus Amap Web key",
        ctypes.byref(entropy),
        None,
        None,
        _DPAPI_UI_FORBIDDEN,
        ctypes.byref(protected),
    )
    # Keep source buffers alive until DPAPI has copied their contents.
    _ = source_storage, entropy_storage
    if not ok:
        raise AmapCredentialError(
            f"Windows DPAPI could not protect the credential (code {ctypes.get_last_error()})."
        )
    try:
        return ctypes.string_at(protected.pbData, protected.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(protected.pbData, ctypes.c_void_p))


def _unprotect_bytes(ciphertext: bytes) -> bytes:
    if os.name != "nt":
        raise AmapCredentialError("Windows DPAPI is required to read this credential.")

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    source, source_storage = _make_blob(ciphertext)
    entropy, entropy_storage = _make_blob(_DPAPI_ENTROPY)
    plaintext = _DataBlob()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        ctypes.byref(entropy),
        None,
        None,
        _DPAPI_UI_FORBIDDEN,
        ctypes.byref(plaintext),
    )
    _ = source_storage, entropy_storage
    if not ok:
        raise AmapCredentialError(
            f"Windows DPAPI could not read the credential for this user (code {ctypes.get_last_error()})."
        )
    try:
        return ctypes.string_at(plaintext.pbData, plaintext.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(plaintext.pbData, ctypes.c_void_p))


def _normalize_key(value: str) -> str:
    key = value.strip()
    if not key or len(key) > _MAX_KEY_LENGTH or "\n" in key or "\r" in key:
        raise AmapCredentialError("The Amap Web key is empty or has an unsupported format.")
    return key


def save_amap_key(key: str) -> Path:
    """Encrypt and atomically save a key in the current user's Local AppData."""
    normalized = _normalize_key(key)
    path = credential_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ciphertext = _protect_bytes(normalized.encode("utf-8"))

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".amap-key-", suffix=".tmp", dir=path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(ciphertext)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise AmapCredentialError("The encrypted Amap credential could not be saved.") from exc
    return path


def load_amap_key() -> str | None:
    """Load the environment key first, then the current user's DPAPI value."""
    environment_key = os.environ.get(ENV_KEY_NAME, "")
    if environment_key.strip():
        return _normalize_key(environment_key)

    if not os.environ.get("LOCALAPPDATA"):
        return None
    path = credential_path()
    if not path.is_file():
        return None
    try:
        plaintext = _unprotect_bytes(path.read_bytes())
        key = plaintext.decode("utf-8")
        return _normalize_key(key)
    except (OSError, UnicodeError) as exc:
        raise AmapCredentialError("The saved Amap credential could not be read.") from exc


def key_status() -> dict[str, bool | str]:
    """Return only whether a usable credential exists and where it comes from."""
    if os.environ.get(ENV_KEY_NAME, "").strip():
        return {"configured": True, "source": "environment"}
    try:
        configured = load_amap_key() is not None
    except AmapCredentialError:
        configured = False
    return {
        "configured": configured,
        "source": "dpapi" if configured else "none",
    }


def credential_status() -> dict[str, bool | str]:
    """Backward-compatible descriptive alias for :func:`key_status`."""
    return key_status()
