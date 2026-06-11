from __future__ import annotations

from typing import Any


PRIMARY_PROVIDER = "pantheon_ziwei"


def build_ziwei_fusion(
    primary_chart: dict[str, Any],
    external_charts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """融合多個紫微來源；目前只包裝 primary，保留 external 接口。"""
    external_charts = external_charts or []
    fields = [
        "five_elements_class",
        "life_palace",
        "body_palace",
        "life_palace_stars",
        "body_palace_stars",
        "palaces",
        "soul_star",
        "body_star",
        "hour_index",
    ]
    resolved = {
        field: _resolve_field(field, primary_chart, external_charts)
        for field in fields
        if _has_field(primary_chart, field) or any(_has_field(chart, field) for chart in external_charts)
    }
    return {
        "strategy": "primary_with_secondary_validation",
        "primary_provider": PRIMARY_PROVIDER,
        "secondary_providers": sorted(
            {str(chart.get("provider", "external")) for chart in external_charts}
        ),
        "resolved": resolved,
        "conflicts": [
            item for item in resolved.values() if item["confidence"] == "conflict"
        ],
    }


def _resolve_field(
    field: str,
    primary_chart: dict[str, Any],
    external_charts: list[dict[str, Any]],
) -> dict[str, Any]:
    primary_has_value = _has_field(primary_chart, field)
    primary_value = primary_chart.get(field)
    candidates = [
        {
            "provider": str(chart.get("provider", "external")),
            "value": chart.get(field),
        }
        for chart in external_charts
        if _has_field(chart, field)
    ]

    if primary_has_value:
        mismatches = [candidate for candidate in candidates if candidate["value"] != primary_value]
        if mismatches:
            confidence = "conflict"
        elif candidates:
            confidence = "high"
        else:
            confidence = "primary"
        return {
            "key": field,
            "value": primary_value,
            "confidence": confidence,
            "primary": {"provider": PRIMARY_PROVIDER, "value": primary_value},
            "candidates": candidates,
        }

    if candidates:
        return {
            "key": field,
            "value": candidates[0]["value"],
            "confidence": "external_only",
            "primary": None,
            "candidates": candidates,
        }

    return {
        "key": field,
        "value": None,
        "confidence": "missing",
        "primary": None,
        "candidates": [],
    }


def _has_field(chart: dict[str, Any], field: str) -> bool:
    value = chart.get(field)
    return value is not None and value != [] and value != {}
