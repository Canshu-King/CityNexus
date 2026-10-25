from __future__ import annotations

from typing import Any

from app.agent.runtime import citynexus_tool_definitions


def _tool_parameters(tool_name: str) -> dict[str, Any]:
    tool = next(
        item["function"]
        for item in citynexus_tool_definitions()
        if item["function"]["name"] == tool_name
    )
    return tool["parameters"]["properties"]


def _string_array_satisfies_contract(value: object, schema: dict[str, Any]) -> bool:
    if schema.get("type") != "array" or not isinstance(value, list):
        return False
    if len(value) < schema.get("minItems", 0):
        return False
    if schema.get("uniqueItems") is True and len(value) != len(set(value)):
        return False
    item_schema = schema.get("items")
    return isinstance(item_schema, dict) and item_schema.get("type") == "string" and all(
        isinstance(item, str) for item in value
    )


def test_generate_plans_requires_two_distinct_returned_server_place_ids() -> None:
    properties = _tool_parameters("generate_plans")
    place_ids = properties["place_ids"]

    assert place_ids["minItems"] == 2
    assert place_ids["uniqueItems"] is True
    assert "At least two different server-owned Place IDs already returned" in place_ids[
        "description"
    ]
    assert not _string_array_satisfies_contract(["place-a"], place_ids)
    assert not _string_array_satisfies_contract(["place-a", "place-a"], place_ids)
    assert _string_array_satisfies_contract(["place-a", "place-b"], place_ids)

    candidate_count = properties["candidate_count"]
    assert candidate_count["minimum"] == 1
    assert candidate_count["maximum"] == 5
    assert "Number of alternative plans" in candidate_count["description"]
    assert "not the number of Places" in candidate_count["description"]


def test_request_replan_place_ids_schema_stays_unchanged() -> None:
    properties = _tool_parameters("request_replan")

    assert properties["place_ids"] == {
        "type": "array",
        "items": {"type": "string"},
        "description": (
            "Optional bounded Place hints from search_city_services; "
            "the server revalidates every fact."
        ),
    }
