"""
Supplier intelligence schemas for MedIntel API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DisruptionEventItem(BaseModel):
    """Supplier disruption event."""
    event_id: str
    event_date: str
    event_type: str
    delay_days: int
    description: str


class SupplierItem(BaseModel):
    """Supplier intelligence record."""
    supplier_id: str
    supplier_name: str
    medications_supplied_count: int
    medication_ids: List[str]
    standard_lead_time_days: float
    current_lead_time_days: float
    lead_time_surge_days: float
    reliability_score: float
    active_disruptions_count: int
    total_delayed_orders_count: int
    active_events: List[DisruptionEventItem] = Field(default_factory=list)


class SupplierListResponse(BaseModel):
    """Response containing supplier intelligence."""
    total: int
    items: List[SupplierItem]
