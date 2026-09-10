"""
Opportunities, network redistribution, and expiry salvage schemas for MedIntel API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RedistributionOpportunity(BaseModel):
    """Inter-facility lateral rebalancing opportunity."""
    medication_id: str
    generic_name: str
    therapeutic_class: str
    unit_cost: float
    deficit_location_id: str
    deficit_location_name: str
    deficit_days_of_supply: float
    deficit_quantity_on_hand: float
    surplus_location_id: str
    surplus_location_name: str
    surplus_days_of_supply: float
    surplus_quantity_on_hand: float
    recommended_transfer_units: int
    estimated_cost_avoidance_usd: float
    urgency: str
    action_directive: str


class ExpiryOpportunity(BaseModel):
    """Near-expiry medication batch write-off salvage opportunity."""
    lot_id: str
    medication_id: str
    generic_name: str
    location_id: str
    location_name: str
    days_to_expiry: int
    expiry_date: str
    lot_quantity: int
    projected_unconsumed_units: int
    unit_cost: float
    projected_financial_waste_usd: float
    suggested_target_location_id: Optional[str]
    suggested_target_location_name: Optional[str]
    action_directive: str


class OpportunitiesResponse(BaseModel):
    """Aggregate opportunities response."""
    total_opportunities_count: int
    total_value_at_stake_usd: float
    redistribution_opportunities: List[RedistributionOpportunity]
    expiry_salvage_opportunities: List[ExpiryOpportunity]
