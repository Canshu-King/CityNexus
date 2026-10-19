"""Interactive, opt-in configuration for the local Amap Web key."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from amap_credentials import (
    ENV_KEY_NAME,
    AmapCredentialError,
    key_status,
    load_amap_key,
    save_amap_key,
)


AMAP_TEXT_SEARCH_ENDPOINT = "https://restapi.amap.com/v3/place/text"
_MAX_VERIFY_TIMEOUT_SECONDS = 15
_MAX_RESPONSE_BYTES = 2_000_000


def verify_amap_once(
    *, keywords: str, city: str, timeout_seconds: int = 8
) -> dict[str, int | str]:
    """Make exactly one explicit text-search request and return allowlisted fields."""
    clean_keywords = keywords.strip()
    clean_city = city.strip()
    if not clean_keywords or not clean_city:
        return {"reason": "PARAMETERS_REQUIRED", "poi_count": 0, "adcode": "unknown"}

    try:
        key = load_amap_key()
    except AmapCredentialError:
        return {"reason": "CREDENTIAL_UNAVAILABLE", "poi_count": 0, "adcode": "unknown"}
    if not key:
        return {"reason": "NOT_CONFIGURED", "poi_count": 0, "adcode": "unknown"}

    bounded_timeout = max(1, min(int(timeout_seconds), _MAX_VERIFY_TIMEOUT_SECONDS))
    query = urlencode(
        {
            "key": key,
            "keywords": clean_keywords,
            "city": clean_city,
            "offset": "10",
            "page": "1",
            "extensions": "base",
            "output": "JSON",
        }
    )
    request = Request(
        f"{AMAP_TEXT_SEARCH_ENDPOINT}?{query}",
        headers={"Accept": "application/json", "User-Agent": "CityNexus local Amap setup"},
        method="GET",
    )
    try:
        # Do not log or surface this request object: Amap's Web API accepts the key
        # in the query string, so its URL contains the credential.
        with urlopen(request, timeout=bounded_timeout) as response:
            body = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(body) > _MAX_RESPONSE_BYTES:
            return {"reason": "RESPONSE_TOO_LARGE", "poi_count": 0, "adcode": "unknown"}
    except HTTPError:
        return {"reason": "HTTP_ERROR", "poi_count": 0, "adcode": "unknown"}
    except (URLError, TimeoutError, OSError, ValueError):
        return {"reason": "NETWORK_ERROR", "poi_count": 0, "adcode": "unknown"}

    try:
        payload: Any = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return {"reason": "INVALID_RESPONSE", "poi_count": 0, "adcode": "unknown"}

    if not isinstance(payload, dict):
        return {"reason": "INVALID_RESPONSE", "poi_count": 0, "adcode": "unknown"}
    if str(payload.get("status", "")) != "1":
        error_code = str(payload.get("infocode", ""))
        reason = {
            "10001": "INVALID_KEY",
            "10002": "KEY_PERMISSION",
            "10003": "QUOTA_OR_PERMISSION",
            "10004": "QUOTA_OR_PERMISSION",
            "10005": "KEY_PERMISSION",
            "10006": "KEY_PERMISSION",
            "10008": "KEY_PERMISSION",
            "10011": "KEY_PERMISSION",
        }.get(error_code, "PROVIDER_REJECTED")
        return {"reason": reason, "poi_count": 0, "adcode": "unknown"}

    pois = payload.get("pois")
    if not isinstance(pois, list):
        return {"reason": "INVALID_RESPONSE", "poi_count": 0, "adcode": "unknown"}
    adcode = "unknown"
    for poi in pois:
        if isinstance(poi, dict):
            candidate = poi.get("adcode")
            if isinstance(candidate, (str, int)) and str(candidate).isdigit():
                adcode = str(candidate)[:12]
                break
    count_value = payload.get("count", len(pois))
    try:
        count = max(0, int(count_value))
    except (TypeError, ValueError):
        count = len(pois)
    return {
        "reason": "OK" if count else "NO_RESULTS",
        "poi_count": count,
        "adcode": adcode,
    }


def _print_status() -> None:
    status = key_status()
    print(f"configured={str(status['configured']).lower()} source={status['source']}")


def _configure_from_prompt() -> bool:
    key = os.environ.get(ENV_KEY_NAME, "").strip()
    if key:
        print(f"Using {ENV_KEY_NAME} from this process environment.")
    else:
        try:
            key = getpass.getpass("Amap Web key (hidden input): ")
        except (EOFError, KeyboardInterrupt):
            print("Configuration cancelled.")
            return False
    try:
        save_amap_key(key)
    except AmapCredentialError as exc:
        print(f"Configuration failed: {exc}", file=sys.stderr)
        return False
    print("Encrypted Amap credential saved for this Windows user.")
    _print_status()
    return True


def _confirm(prompt: str) -> bool:
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        return False


def _run_verify(keywords: str, city: str, timeout: int) -> int:
    result = verify_amap_once(keywords=keywords, city=city, timeout_seconds=timeout)
    print(
        "reason={reason} poi_count={poi_count} adcode={adcode}".format(**result)
    )
    return 0 if result["reason"] == "OK" else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure a local Amap Web key; no network request is made by default."
    )
    parser.add_argument("--status", action="store_true", help="show configured/source only")
    parser.add_argument("--configure", action="store_true", help="save an encrypted local key")
    parser.add_argument(
        "--verify", action="store_true", help="make one explicit Amap place-search request"
    )
    parser.add_argument("--keywords", help="place name or search phrase for --verify")
    parser.add_argument("--city", help="city for --verify")
    parser.add_argument("--timeout", type=int, default=8, help="verify timeout in seconds (max 15)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verify and (not args.keywords or not args.city):
        parser.error("--verify requires both --keywords and --city.")
    if not args.verify and (args.keywords is not None or args.city is not None):
        parser.error("--keywords and --city are accepted only with --verify.")
    if args.status and (args.configure or args.verify):
        parser.error("--status is a read-only mode; do not combine it with other modes.")

    if args.status:
        _print_status()
        return 0

    if args.configure:
        if not _configure_from_prompt():
            return 2
    elif not args.verify:
        _print_status()
        status = key_status()
        if not status["configured"] or _confirm("Configure or replace the local Amap key?"):
            if not _configure_from_prompt():
                return 2
        if key_status()["configured"] and _confirm("Run one real Amap lookup now?"):
            keywords = input("Place name or search phrase: ").strip()
            city = input("City: ").strip()
            return _run_verify(keywords, city, args.timeout)
        return 0

    if args.verify:
        return _run_verify(args.keywords, args.city, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
