import ipaddress
import socket
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.ai.agent import generate_interpretation
from app.ai.personality import generate_personality_interpretation
from app.ai.report import build_unified_report
from app.api.schemas import BirthInput, PersonalityInput, PersonalityResponse, PredictionResponse, SeoAuditInput
from app.core.registry import registry
from scripts.competitor_seo_tool import (
    DEFAULT_KEYWORD_MATRIX,
    DEFAULT_SOURCE_INTAKE,
    build_web_summary,
    crawl_site,
    normalize_base,
)


router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@router.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "calculators": registry.names()}


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: BirthInput) -> PredictionResponse:
    user_data = payload.model_dump(mode="json")
    requested = ["bazi", "ziwei"]
    if payload.name:
        requested.append("nameology")
    if payload.personality_answers:
        requested.append("mbti")
    if payload.include_reserved_plugins:
        requested.extend(name for name in ["human_design", "mbti", "tarot"] if name not in requested)
    charts = registry.calculate_many(requested, user_data)
    report = build_unified_report(charts)
    school_policy = _school_policy(payload, charts)
    ai = generate_interpretation(user_data, charts, report, school_policy)
    return PredictionResponse(
        input=payload,
        charts=charts,
        report=report,
        ai=ai,
        metadata={
            "calculator_version": "0.1.0",
            "data_status": "ziwei_samples_not_imported",
            "engine_status": _engine_status(charts),
            "school_policy": school_policy,
        },
    )


@router.post("/personality", response_model=PersonalityResponse)
def personality(payload: PersonalityInput) -> PersonalityResponse:
    user_data = payload.model_dump(mode="json")
    chart = registry.get("mbti").calculate(user_data)
    report = build_unified_report({"mbti": chart})
    ai = generate_personality_interpretation(chart, report)
    return PersonalityResponse(
        input=payload,
        chart=chart,
        report=report,
        ai=ai,
        metadata={
            "calculator_version": "0.1.0",
            "scope": "personality_only",
        },
    )


def _public_base_url(value: str) -> str:
    base_url = normalize_base(value.strip())
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="請輸入有效的公開 http(s) 網站網址。")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="網址連接埠格式不正確。") from exc
    if port not in {80, 443}:
        raise HTTPException(status_code=422, detail="內部工具只允許公開網站的 80 或 443 連接埠。")

    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise HTTPException(status_code=422, detail="不允許稽核本機或內部網路位址。")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(result[4][0])
                for result in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            }
        except (socket.gaierror, ValueError) as exc:
            raise HTTPException(status_code=422, detail="無法解析這個網站網址。") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise HTTPException(status_code=422, detail="不允許稽核本機或內部網路位址。")
    return base_url


@router.post("/seo/audit")
def seo_audit(payload: SeoAuditInput) -> dict[str, Any]:
    competitor_url = _public_base_url(payload.competitor_url)
    own_site_url = _public_base_url(payload.own_site_url) if payload.own_site_url.strip() else ""
    keyword_matrix = PROJECT_ROOT / DEFAULT_KEYWORD_MATRIX
    source_intake = PROJECT_ROOT / DEFAULT_SOURCE_INTAKE

    def run_site(base_url: str, name: str) -> dict[str, object]:
        hostname = urllib.parse.urlparse(base_url).netloc
        return crawl_site(
            base_url=base_url,
            site_name=name.strip() or hostname,
            since=None,
            max_feed_pages=3,
            max_category_pages=1,
            sample_limit=payload.sample_limit,
            keyword_matrix=keyword_matrix,
            source_intake_path=source_intake,
        )

    try:
        competitor_data = run_site(competitor_url, payload.competitor_name)
        own_data = run_site(own_site_url, payload.own_site_name) if own_site_url else None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"網站稽核失敗：{str(exc)[:180]}") from exc
    return build_web_summary(competitor_data, own_data)


def _engine_status(charts: dict[str, dict]) -> dict[str, dict[str, object]]:
    status: dict[str, dict[str, object]] = {}
    bazi = charts.get("bazi")
    if bazi:
        calendar_engine = bazi.get("calendar_engine", {})
        status["bazi"] = {
            "provider": calendar_engine.get("provider", "unknown"),
            "provider_status": calendar_engine.get("provider_status", "unknown"),
            "algorithm_level": bazi.get("algorithm_level"),
            "ruleset_version": bazi.get("ruleset_version"),
            "true_solar_time": calendar_engine.get("policies", {}).get("true_solar_time"),
        }
    ziwei = charts.get("ziwei")
    if ziwei:
        status["ziwei"] = {
            "provider": ziwei.get("provider", "unknown"),
            "provider_status": ziwei.get("provider_status", "unknown"),
            "algorithm_level": ziwei.get("algorithm_level"),
            "reference_dataset": ziwei.get("reference_dataset", {}).get("status"),
        }
    nameology = charts.get("nameology")
    if nameology:
        status["nameology"] = {
            "provider": nameology.get("provider", "unknown"),
            "provider_status": nameology.get("provider_status", "unknown"),
            "algorithm_level": nameology.get("algorithm_level"),
            "ruleset_version": nameology.get("ruleset_version"),
        }
    return status


def _school_policy(payload: BirthInput, charts: dict[str, dict]) -> dict[str, dict[str, object]]:
    bazi = charts.get("bazi", {})
    bazi_calendar = bazi.get("calendar_engine", {})
    bazi_solar_time = bazi.get("solar_time", {})
    bazi_luck = bazi.get("luck_cycles", {})
    ziwei = charts.get("ziwei", {})
    nameology = charts.get("nameology", {})
    policy: dict[str, dict[str, object]] = {
        "bazi": {
            "calendar_provider": bazi_calendar.get("provider"),
            "month_boundary": bazi_calendar.get("policies", {}).get("month_boundary"),
            "day_boundary": bazi_calendar.get("policies", {}).get("day_boundary"),
            "true_solar_time": {
                "computed": bazi_solar_time.get("status") == "computed",
                "applied": bazi_solar_time.get("applied", False),
                "correction_minutes": bazi_solar_time.get("total_correction_minutes"),
            },
            "qiyun_method": bazi_luck.get("qiyun", {}).get("basis"),
            "dayun_method": bazi_luck.get("algorithm_level"),
            "strength_model": payload.bazi_strength_model,
            "strength_engine_model": bazi.get("strength_analysis", {}).get("model"),
            "strength_status": bazi.get("strength_analysis", {}).get("status"),
            "ruleset_version": bazi.get("ruleset_version"),
            "caution": "旺衰、格局、用神仍屬候選分析，不輸出唯一絕對斷語。",
        },
        "ziwei": {
            "provider": ziwei.get("provider"),
            "provider_version": ziwei.get("provider_version"),
            "school": payload.ziwei_school,
            "algorithm_level": ziwei.get("algorithm_level"),
            "reference_dataset": ziwei.get("reference_dataset", {}).get("status"),
            "caution": "紫微派別尚未提供切換；目前使用 iztro 預設排盤規則。",
        },
        "ai": {
            "role": "interpretation_only",
            "allowed_sources": ["charts", "report.signals", "report.combo_cards", "metadata.school_policy"],
            "forbidden": ["自行重排命盤", "自行補未計算的吉凶表", "把候選模型寫成唯一結論"],
        },
    }
    if nameology:
        policy["nameology"] = {
            "provider": nameology.get("provider"),
            "stroke_source": "kangxi",
            "five_grid_formula": "single_surname_mvp",
            "luck_table": payload.nameology_luck_table,
            "ruleset_version": nameology.get("ruleset_version"),
            "input_name_present": bool(payload.name),
            "caution": "姓名學目前只輸出筆畫、五格與三才元素，不輸出未審吉凶斷語。",
        }
    return policy
