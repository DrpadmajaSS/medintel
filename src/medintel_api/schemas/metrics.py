"""
Dashboard metrics and executive KPI schemas for MedIntel API.
"""

from typing import Dict
from pydantic import BaseModel, Field


class DashboardMetricsResponse(BaseModel):
    """Executive KPI metrics for MedIntel dashboard."""
    medications_monitored: int = Field(..., description="Total medications monitored across formulary")
    locations_monitored: int = Field(..., description="Total healthcare facilities monitored")
    critical_risks: int = Field(..., description="Medications at acute critical risk")
    emerging_risks: int = Field(..., description="Medications with accelerating emerging risk")
    potential_stockouts: int = Field(..., description="Medications projected to stock out within 14 days")
    expiry_risks: int = Field(..., description="Lots with near-expiry write-off exposure")
    total_expiry_exposure_usd: float = Field(..., description="Total dollar value of inventory approaching expiration")
    supplier_risks: int = Field(..., description="Suppliers with active disruptions or lead time surges")
    potential_redistribution_opportunities: int = Field(..., description="Identified lateral transfer opportunities")
    estimated_rebalance_savings_usd: float = Field(..., description="Estimated cost avoidance from lateral rebalancing")
    risk_level_breakdown: Dict[str, int] = Field(..., description="SKU count breakdown by risk level")
