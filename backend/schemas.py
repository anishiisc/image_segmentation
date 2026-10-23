"""Pydantic request and response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    sample_name: Optional[str] = None
    smoothing_sigma: float = Field(default=3.0, ge=0, le=10)
    min_prominence_frac: float = Field(default=0.10, ge=0, le=1)
    polarity: str = Field(default="auto", pattern="^(auto|dark|bright)$")
    manual_threshold: Optional[int] = Field(default=None, ge=0, le=255)
    cleanup: bool = True
    sharpen_method: str = Field(default="mask_aware", pattern="^(unsharp|laplacian|mask_aware)$")
    radius: float = Field(default=1.5, ge=0.1, le=10)
    amount: float = Field(default=1.0, ge=0, le=5)
    amount_fg: float = Field(default=1.5, ge=0, le=5)
    amount_bg: float = Field(default=0.3, ge=0, le=5)


class AnalysisResponse(BaseModel):
    meta: Dict[str, Any]
    histogram: Dict[str, Any]
    bimodality: Dict[str, Any]
    threshold: Dict[str, Any]
    segmentation: Dict[str, Any]
    sharpening: Dict[str, Any]
    images: Dict[str, str]
    explanations: List[Dict[str, Any]]
    warnings: List[str]
