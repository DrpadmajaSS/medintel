"""
Healthcare location and facility schemas for MedIntel API.
"""

from typing import List
from pydantic import BaseModel, Field


class LocationItem(BaseModel):
    """Healthcare facility location record."""
    location_id: str = Field(..., description="Unique facility identifier (e.g. LOC001)")
    location_name: str = Field(..., description="Healthcare institution / facility name")
    location_type: str = Field(..., description="Facility archetype (e.g. Academic Medical Center, Trauma Center)")
    region: str = Field(..., description="Geographic health system service area")


class LocationListResponse(BaseModel):
    """Response containing list of healthcare locations."""
    total: int = Field(..., description="Total facilities count")
    items: List[LocationItem] = Field(..., description="List of healthcare facilities")
