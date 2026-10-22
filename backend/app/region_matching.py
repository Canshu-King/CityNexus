"""Compare only explicit public administrative labels and address levels."""
from __future__ import annotations

from typing import Any

_PUBLIC_ADDRESS_FIELDS = ("county", "city", "state", "district")


def public_address(metadata: Any) -> dict[str, str]:
    if not isinstance(metadata, dict):
        return {}
    result: dict[str, str] = {}
    for key in _PUBLIC_ADDRESS_FIELDS:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip() and len(value.strip()) <= 120 \
                and not any(ord(char) < 32 for char in value):
            result[key] = value.strip()
    return result


def public_address_from_tags(tags: Any) -> dict[str, str]:
    if not isinstance(tags, dict):
        return {}
    explicit = {}
    for key in _PUBLIC_ADDRESS_FIELDS:
        value = tags.get(f"addr:{key}")
        if value is None:
            value = tags.get(key)
        if isinstance(value, str):
            explicit[key] = value
    return public_address(explicit)


def _county_level_label(value: str) -> bool:
    return value.endswith(("自治县", "自治縣", "县", "縣", "市辖区", "市轄區", "新区", "新區",
                           "特区", "特區", "区", "區", "自治旗", "旗", "县级市", "縣級市"))


def _administrative_level(value: str) -> str | None:
    if _county_level_label(value):
        return "county"
    if value.endswith(("省", "自治区", "自治區")):
        return "state"
    if value.endswith(("市", "自治州", "地区", "地區", "盟")):
        return "city"
    return None


def public_region_status(region_label: str, address: dict[str, str]) -> str:
    """Return MATCHED/CONFLICT only when names and admin levels are explicit.

    County and district labels are both county-level divisions in the Chinese
    administrative naming used by Photon/Nominatim. Other cross-level pairs
    remain UNKNOWN; this intentionally does not use coordinates or transliteration.
    """
    label = region_label.strip() if isinstance(region_label, str) else ""
    if not label or not address:
        return "UNKNOWN"
    level = _administrative_level(label)
    if level is None:
        return "MATCHED" if any(value == label for value in address.values()) else "UNKNOWN"

    fields = {"county": ("county", "district"), "city": ("city",), "state": ("state",)}[level]
    comparable = [address.get(field, "") for field in fields
                  if _administrative_level(address.get(field, "")) == level]
    if not comparable:
        return "UNKNOWN"
    # Conflicting labels at the same administrative level outweigh a partial
    # exact match: contradictory source addresses must not become selectable.
    if any(value != label for value in comparable):
        return "CONFLICT"
    return "MATCHED"
