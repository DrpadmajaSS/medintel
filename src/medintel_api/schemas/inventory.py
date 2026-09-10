"""
Inventory intelligence schemas for MedIntel API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    """Inventory intelligence record for a facility-medication SKU."""
    inventory_id: str
    medication_id: str
    generic_name: str
    location_id: str
    location_name: str
    snapshot_date: str
    quantity_on_hand: float
    reorder_level: float
    average_daily_usage: float
    days_of_supply: float
    unit_cost: float
    total_inventory_value: float
    criticality: str
    therapeutic_class: str


class InventoryListResponse(BaseModel):
    """Response containing inventory intelligence items."""
    total: int
    total_value_usd: float
    items: List[InventoryItem]
