"""
Daily intelligence brief router for MedIntel API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from medintel_api.schemas.intelligence import DailyIntelligenceBrief
from medintel_api.services.data_service import DataService, get_data_service
from medintel_api.services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/daily-intelligence", tags=["Daily Intelligence Brief"])


@router.get("", response_model=DailyIntelligenceBrief, summary="Get MedIntel Daily Intelligence Brief")
def get_daily_intelligence(
    location_id: Optional[str] = Query(None, description="Optional facility ID to isolate single location"),
    ds: DataService = Depends(get_data_service)
) -> DailyIntelligenceBrief:
    """Returns prioritized daily briefing categorized into ACT, WATCH, OPPORTUNITY, and LEARN."""
    service = IntelligenceService(ds)
    return service.generate_brief(location_id=location_id)
