"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class InputType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"


class Verdict(str, Enum):
    GENUINE = "likely_genuine"
    SUSPICIOUS = "suspicious"
    FAKE = "likely_fake"


class DimensionScores(BaseModel):
    rules: float = Field(ge=0, le=1, description="Rule engine score")
    nlp: float = Field(ge=0, le=1, description="NLP classifier score")
    ner: float = Field(ge=0, le=1, description="NER verification score")


class AnalysisRequest(BaseModel):
    text: Optional[str] = Field(None, description="Plain text input")
    session_id: str = Field(..., description="Anonymous browser session ID")


class AnalysisResponse(BaseModel):
    id: str
    confidence_score: float = Field(ge=0, le=100)
    verdict: Verdict
    dimension_scores: DimensionScores
    triggered_flags: list[dict]
    next_steps: list[str]
    company_name: Optional[str] = None
    input_type: InputType
    extraction_method: str
    processing_time_ms: int


class ScanRecord(BaseModel):
    id: str
    created_at: str
    confidence_score: float
    verdict: str
    company_name: Optional[str] = None
    input_type: str


class HistoryResponse(BaseModel):
    scans: list[ScanRecord]
    total: int
