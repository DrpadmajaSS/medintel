"""
Common Pydantic schemas for MedIntel API.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("healthy", description="Application runtime status")
    version: str = Field("1.0.0", description="MedIntel API version")
    data_status: str = Field("loaded", description="Status of synthetic healthcare data repository")
    snapshot_date: str = Field(..., description="Active inventory snapshot date (YYYY-MM-DD)")
    medications_count: int = Field(..., description="Total medications monitored")
    locations_count: int = Field(..., description="Total healthcare facilities monitored")
    assessed_skus_count: int = Field(..., description="Total facility-medication pairs assessed")


class MetadataResponse(BaseModel):
    """Metadata response detailing available facilities and drug classes."""
    facilities: List[Dict[str, str]]
    therapeutic_classes: List[str]
    criticality_levels: List[str]
    risk_levels: List[str]
    snapshot_date: str


class ErrorResponse(BaseModel):
    """Standardized error response."""
    detail: str = Field(..., description="Error message details")
    error_code: Optional[str] = Field(None, description="Specific operational error code")
