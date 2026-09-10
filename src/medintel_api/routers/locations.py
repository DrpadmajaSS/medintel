"""
Locations & healthcare facilities router for MedIntel API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from medintel_api.schemas.location import LocationItem, LocationListResponse
from medintel_api.services.data_service import DataService, get_data_service

router = APIRouter(prefix="/locations", tags=["Locations & Facilities"])


@router.get("", response_model=LocationListResponse, summary="Get Healthcare Locations & Facilities")
def get_locations(
    location_type: Optional[str] = Query(None, description="Filter by facility archetype"),
    region: Optional[str] = Query(None, description="Filter by geographic region"),
    ds: DataService = Depends(get_data_service)
) -> LocationListResponse:
    """Returns available healthcare institutions and facility metadata."""
    raw = ds.raw_data
    df = raw.locations.copy()
    
    if location_type:
        df = df[df["location_type"].str.lower() == location_type.lower()]
    if region:
        df = df[df["region"].str.lower() == region.lower()]
        
    items = [
        LocationItem(
            location_id=row["location_id"],
            location_name=row["location_name"],
            location_type=row["location_type"],
            region=row["region"]
        )
        for _, row in df.iterrows()
    ]
    
    return LocationListResponse(total=len(items), items=items)
