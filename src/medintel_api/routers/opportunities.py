"""
Opportunities and lateral rebalancing router for MedIntel API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from medintel_api.schemas.opportunities import OpportunitiesResponse
from medintel_api.services.data_service import DataService, get_data_service
from medintel_api.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["Network Opportunities & Rebalancing"])


@router.get("", response_model=OpportunitiesResponse, summary="Get Inter-Facility Rebalancing & Expiry Salvage Opportunities")
def get_opportunities(
    location_id: Optional[str] = Query(None, description="Optional facility ID to isolate single location"),
    ds: DataService = Depends(get_data_service)
) -> OpportunitiesResponse:
    """Returns cross-location lateral stock transfer pairs and near-expiry write-off salvage opportunities."""
    service = OpportunityService(ds)
    return service.get_opportunities(location_id=location_id)
