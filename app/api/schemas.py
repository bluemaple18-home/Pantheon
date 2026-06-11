from datetime import date, time
from typing import Any, Literal

from app.ai.report import UnifiedReport
from pydantic import BaseModel, Field


class PersonalityAnswer(BaseModel):
    question_id: str
    dimension: Literal["EI", "SN", "TF", "JP", "AO", "HC"]
    direction: Literal["E", "I", "S", "N", "T", "F", "J", "P", "A", "O", "H", "C"]
    value: int = Field(ge=1, le=5)


class BirthInput(BaseModel):
    name: str | None = None
    birth_date: date
    birth_time: time
    gender: Literal["male", "female", "other"] = "other"
    timezone: str = "Asia/Taipei"
    utc_offset: str | None = "+08:00"
    calendar: Literal["solar", "lunar"] = "solar"
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    use_true_solar_time: bool = False
    birth_time_confidence: Literal["exact", "approximate", "unknown"] = "exact"
    target_year: int = 2026
    bazi_strength_model: Literal["pantheon_strength_v1"] = "pantheon_strength_v1"
    ziwei_school: Literal["iztro_default"] = "iztro_default"
    nameology_luck_table: Literal["disabled_until_audited"] = "disabled_until_audited"
    include_reserved_plugins: bool = False
    personality_answers: list[PersonalityAnswer] = Field(default_factory=list)


class PersonalityInput(BaseModel):
    name: str | None = None
    personality_answers: list[PersonalityAnswer] = Field(default_factory=list)


class PredictionResponse(BaseModel):
    input: BirthInput
    charts: dict[str, Any]
    report: UnifiedReport
    ai: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalityResponse(BaseModel):
    input: PersonalityInput
    chart: dict[str, Any]
    report: UnifiedReport
    ai: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
