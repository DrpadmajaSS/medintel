"""
Risk assessment and detailed intelligence schemas for MedIntel API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RiskAssessmentItem(BaseModel):
    """Summary risk assessment for a specific medication-location pair."""
    medication_id: str = Field(..., description="Medication ID")
    generic_name: str = Field(..., description="Generic name")
    location_id: str = Field(..., description="Location ID")
    location_name: str = Field(..., description="Location name")
    therapeutic_class: str = Field(..., description="Therapeutic class")
    criticality: str = Field(..., description="Criticality level")
    risk_score: float = Field(..., description="Continuous risk score [0.0 - 100.0]")
    risk_level: str = Field(..., description="Risk tier: CRITICAL, HIGH, MEDIUM, LOW")
    days_of_supply: float = Field(..., description="Days of supply on hand")
    quantity_on_hand: float = Field(..., description="Physical inventory units on hand")
    average_daily_usage: float = Field(..., description="Recent average daily usage (7-day or 30-day)")
    trend_ratio: float = Field(..., description="7d vs 30d usage velocity ratio")
    predicted_stockout_date: Optional[str] = Field(None, description="Projected stockout date (YYYY-MM-DD)")
    days_to_stockout: Optional[float] = Field(None, description="Days remaining until zero stock")
    primary_risk_factors: str = Field(..., description="Semicolon-delimited top driving risk signals")
    contributing_factors: str = Field(..., description="Semicolon-delimited contributing operational signals")
    mitigating_factors: str = Field(..., description="Semicolon-delimited mitigating operational signals")
    confidence: float = Field(..., description="Model statistical confidence [0.0 - 1.0]")
    recommended_review: str = Field(..., description="Actionable clinical or operational review recommendation")


class RiskListResponse(BaseModel):
    """Paginated list of ranked risk assessments."""
    total: int = Field(..., description="Total matching items")
    items: List[RiskAssessmentItem] = Field(..., description="List of risk items")


class FacilityRiskDetail(BaseModel):
    """Diagnostic detail for a medication at a specific facility."""
    location_id: str
    location_name: str
    location_type: str
    risk_score: float
    risk_level: str
    quantity_on_hand: float
    reorder_level: float
    average_daily_usage: float
    days_of_supply: float
    trend_ratio: float
    volatility_cv: float
    predicted_stockout_date: Optional[str]
    days_to_stockout: Optional[float]
    primary_risk_factors: str
    contributing_factors: str
    mitigating_factors: str
    confidence: float
    recommended_review: str
    
    # Active pipeline POs
    open_pos: List[Dict[str, Any]] = Field(default_factory=list)
    # Active batches & expiry lots
    expiry_lots: List[Dict[str, Any]] = Field(default_factory=list)
    # Primary & alternate suppliers
    primary_supplier: Optional[Dict[str, Any]] = None
    alternate_suppliers: List[Dict[str, Any]] = Field(default_factory=list)
    # Regional surplus options at sister facilities
    regional_surplus: List[Dict[str, Any]] = Field(default_factory=list)


class RiskDetailResponse(BaseModel):
    """Comprehensive medication diagnostic intelligence response."""
    medication_id: str
    generic_name: str
    strength: str
    dosage_form: str
    unit_of_measure: str
    therapeutic_class: str
    unit_cost: float
    criticality: str
    facilities: List[FacilityRiskDetail]
