"""R97/R98 contract semantics must match the running FastAPI OpenAPI document."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.main import app


CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"

R97_R98_SCHEMAS = (
    "BootstrapDiscoveryCandidate",
    "BootstrapDiscoveryResponse",
    "BootstrapCitySearchResult",
    "BootstrapCitySearchResponse",
    "BootstrapSelectionResponse",
    "BootstrapMapPreviewDestination",
    "BootstrapMapPreviewOpening",
    "BootstrapMapPreviewResponse",
    "BootstrapShortlistItem",
    "BootstrapShortlistResumeIntent",
    "BootstrapShortlistResponse",
    "BootstrapShortlistDeleteResponse",
    "BootstrapShortlistPreviewDestination",
    "BootstrapShortlistPreviewOpening",
    "BootstrapShortlistPreviewResponse",
    "BootstrapTwoStopWalkRequest",
    "BootstrapTwoStopWalkResponseStop",
    "BootstrapTwoStopWalkResponse",
    "BootstrapTwoStopWalkabilityRequest",
    "BootstrapTwoStopWalkStop",
    "BootstrapTwoStopWalkabilityResponse",
)

R97_R98_OPERATIONS = (
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist/two-stop-walk",
        "BootstrapTwoStopWalkRequest",
        "BootstrapTwoStopWalkResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist/two-stop-walkability",
        "BootstrapTwoStopWalkabilityRequest",
        "BootstrapTwoStopWalkabilityResponse",
    ),
)

R97_BOOTSTRAP_OPERATIONS = (
    (
        "/api/v1/journeys/{journey_id}/bootstrap-discovery",
        "post",
        "BootstrapDiscoveryRequest",
        "BootstrapDiscoveryResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/real-city/bootstrap",
        "post",
        "BootstrapDiscoveryRequest",
        "BootstrapDiscoveryResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-city-search",
        "post",
        "BootstrapCitySearchRequest",
        "BootstrapCitySearchResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-discovery/select",
        "post",
        "BootstrapSelectRequest",
        "BootstrapSelectionResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/real-city/bootstrap/select",
        "post",
        "BootstrapSelectRequest",
        "BootstrapSelectionResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-discovery/preview",
        "post",
        "BootstrapMapPreviewRequest",
        "BootstrapMapPreviewResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/real-city/bootstrap/preview",
        "post",
        "BootstrapMapPreviewRequest",
        "BootstrapMapPreviewResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist",
        "get",
        None,
        "BootstrapShortlistResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist",
        "post",
        "BootstrapShortlistSaveRequest",
        "BootstrapShortlistItem",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist/{shortlist_id}/resume",
        "post",
        None,
        "BootstrapShortlistResumeIntent",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist/{shortlist_id}",
        "delete",
        None,
        "BootstrapShortlistDeleteResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist/{shortlist_id}/preview",
        "post",
        "BootstrapShortlistPreviewRequest",
        "BootstrapShortlistPreviewResponse",
    ),
    (
        "/api/v1/journeys/{journey_id}/bootstrap-shortlist/{shortlist_id}/navigate",
        "post",
        "BootstrapShortlistNavigationRequest",
        "BootstrapShortlistPreviewResponse",
    ),
)


def _semantic_schema(value):
    """Ignore presentation metadata and normalize Pydantic's singleton const form."""

    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key in {"description", "title"}:
                continue
            if key == "const":
                normalized["enum"] = [_semantic_schema(item)]
                continue
            normalized[key] = _semantic_schema(item)
        return normalized
    if isinstance(value, list):
        return [_semantic_schema(item) for item in value]
    return value


def _formal_operation(spec: dict, runtime_path: str, method: str = "post") -> dict:
    return spec["paths"][runtime_path.removeprefix("/api/v1") or "/"][method]


def _schema_ref(operation: dict, response_code: str) -> str:
    return operation["responses"][response_code]["content"]["application/json"]["schema"]["$ref"]


@pytest.fixture(scope="module")
def openapi_documents() -> tuple[dict, dict]:
    formal = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return formal, app.openapi()


def test_r97_r98_operations_keep_typed_request_and_response_refs(openapi_documents):
    formal, runtime = openapi_documents
    for path, request_schema, response_schema in R97_R98_OPERATIONS:
        formal_operation = _formal_operation(formal, path)
        runtime_operation = runtime["paths"][path]["post"]
        assert formal_operation["operationId"] == runtime_operation["operationId"]
        assert formal_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"] == (
            f"#/components/schemas/{request_schema}"
        )
        assert runtime_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"] == (
            f"#/components/schemas/{request_schema}"
        )
        assert _schema_ref(formal_operation, "200") == f"#/components/schemas/{response_schema}"
        assert _schema_ref(runtime_operation, "200") == f"#/components/schemas/{response_schema}"


def test_r97_bootstrap_operations_keep_typed_request_and_response_refs(openapi_documents):
    formal, runtime = openapi_documents
    for path, method, request_schema, response_schema in R97_BOOTSTRAP_OPERATIONS:
        formal_operation = _formal_operation(formal, path, method)
        runtime_operation = runtime["paths"][path][method]
        assert formal_operation["operationId"] == runtime_operation["operationId"]
        if request_schema is None:
            assert "requestBody" not in formal_operation
            assert "requestBody" not in runtime_operation
        else:
            assert formal_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"] == (
                f"#/components/schemas/{request_schema}"
            )
            assert runtime_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"] == (
                f"#/components/schemas/{request_schema}"
            )
        assert _schema_ref(formal_operation, "200") == f"#/components/schemas/{response_schema}"
        assert _schema_ref(runtime_operation, "200") == f"#/components/schemas/{response_schema}"


def test_r97_r98_schema_semantics_match_runtime(openapi_documents):
    formal, runtime = openapi_documents
    formal_schemas = formal["components"]["schemas"]
    runtime_schemas = runtime["components"]["schemas"]
    for schema_name in R97_R98_SCHEMAS:
        assert schema_name in formal_schemas
        assert schema_name in runtime_schemas
        assert _semantic_schema(formal_schemas[schema_name]) == _semantic_schema(
            runtime_schemas[schema_name]
        ), schema_name
