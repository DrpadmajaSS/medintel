"""
What-If interactive scenario simulation schemas for MedIntel API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class WhatIfRequest(BaseModel):
    """Input parameters for non-destructive What-If scenario simulation."""
    medication_id: str = Field(..., description="Target medication ID (e.g. MED022)")
    location_id: str = Field(..., description="Target facility ID (e.g. LOC002)")
    demand_change_percent: float = Field(0.0, description="Percentage change in daily demand (e.g. +50.0 or -20.0)")
    supplier_delay_days: float = Field(0.0, description="Additional days of supplier delivery delay (e.g. 10.0)")
    inventory_change_percent: float = Field(0.0, description="Percentage change in physical on-hand inventory (e.g. -30.0)")
    inventory_transfer_units: float = Field(0.0, description="Absolute units transferred to this location (e.g. +150.0)")
    transfer_source_location_id: Optional[str] = Field(None, description="Optional facility ID providing the transfer units")


class WhatIfBaseline(BaseModel):
    """Current baseline state before simulation."""
    medication_id: str
    generic_name: str
    location_id: str
    location_name: str
    quantity_on_hand: float
    average_daily_usage: float
    days_of_supply: float
    risk_score: float
    risk_level: str
    days_to_stockout: Optional[float]
    predicted_stockout_date: Optional[str]
    supplier_lead_time_days: float
    key_signals: List[str]


class WhatIfScenario(BaseModel):
    """Projected simulated scenario state after applying perturbations."""
    projected_quantity_on_hand: float
    projected_daily_usage: float
    projected_days_of_supply: float
    projected_risk_score: float
    projected_risk_level: str
    projected_days_to_stockout: Optional[float]
    projected_stockout_date: Optional[str]
    projected_supplier_lead_time_days: float
    simulated_signals: List[str]


class WhatIfImpact(BaseModel):
    """Comparative impact analysis between baseline and simulated scenario."""
    delta_days_of_supply: float
    delta_days_to_stockout: Optional[float]
    delta_risk_score: float
    risk_level_transition: str
    stockout_status_change: str
    affected_locations: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: str
    clinical_implication: str


class WhatIfResponse(BaseModel):
    """Complete What-If simulation response."""
    simulation_id: str
    medication_id: str
    location_id: str
    parameters_applied: Dict[str, Any]
    baseline: WhatIfBaseline
    scenario: WhatIfScenario
    impact: WhatIfImpact
