"""
Daily intelligence briefing schemas for MedIntel API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class BriefItem(BaseModel):
    """Prioritized operational intelligence item."""
    id: str = Field(..., description="Unique item identifier")
    category: str = Field(..., description="Category: ACT, WATCH, OPPORTUNITY, LEARN")
    title: str = Field(..., description="Headline summary")
    medication_id: Optional[str] = None
    medication_name: Optional[str] = None
    location_id: Optional[str] = None
    location_name: Optional[str] = None
    severity: str = Field("INFO", description="Severity level: CRITICAL, HIGH, MEDIUM, LOW, INFO")
    metric_highlight: str = Field(..., description="Key quantitative metric (e.g. '0.0 DOS', '+76% Burn')")
    detail: str = Field(..., description="Comprehensive clinical / supply context")
    recommended_action: str = Field(..., description="Specific recommended clinical or supply intervention")


class DailyIntelligenceBrief(BaseModel):
    """MedIntel Daily Intelligence Brief organized into ACT, WATCH, OPPORTUNITY, and LEARN."""
    date: str = Field(..., description="Brief date (YYYY-MM-DD)")
    headline: str = Field(..., description="Executive top-level summary headline")
    act: List[BriefItem] = Field(..., description="High-priority actionable issues requiring immediate intervention")
    watch: List[BriefItem] = Field(..., description="Emerging risks and acceleration trends requiring heightened monitoring")
    opportunity: List[BriefItem] = Field(..., description="Redistribution, optimization, and waste-reduction opportunities")
    learn: List[BriefItem] = Field(..., description="Knowledge nuggets based on the day's operational patterns")
