"""
Inventory intelligence router for MedIntel API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
import pandas as pd

from medintel_api.schemas.inventory import InventoryItem, InventoryListResponse
from medintel_api.services.data_service import DataService, get_data_service

router = APIRouter(prefix="/inventory", tags=["Inventory Intelligence"])


@router.get("", response_model=InventoryListResponse, summary="Get Current Inventory Intelligence")
def get_inventory(
    location_id: Optional[str] = Query(None, description="Filter by facility ID"),
    medication_id: Optional[str] = Query(None, description="Filter by medication ID"),
    min_dos: Optional[float] = Query(None, description="Minimum days of supply"),
    max_dos: Optional[float] = Query(None, description="Maximum days of supply"),
    limit: int = Query(100, ge=1, le=525, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset index"),
    ds: DataService = Depends(get_data_service)
) -> InventoryListResponse:
    """Returns current on-hand physical stock, DOS, reorder thresholds, and total valuation."""
    raw = ds.raw_data
    snapshot_dt = ds.snapshot_dt
    meds_dict = ds.medications_by_id
    locs_dict = ds.locations_by_id
    
    df = raw.inventory[raw.inventory["snapshot_date"] == snapshot_dt].copy()
    
    if location_id:
        df = df[df["location_id"].str.upper() == location_id.upper()]
    if medication_id:
        df = df[df["medication_id"].str.upper() == medication_id.upper()]
    if min_dos is not None:
        df = df[df["days_of_supply"] >= min_dos]
    if max_dos is not None:
        df = df[df["days_of_supply"] <= max_dos]
        
    total = len(df)
    
    # Calculate total value
    items = []
    total_val = 0.0
    
    for _, row in df.iterrows():
        m_id = row["medication_id"]
        l_id = row["location_id"]
        m_meta = meds_dict.get(m_id, {})
        l_meta = locs_dict.get(l_id, {})
        
        cost = float(m_meta.get("unit_cost", 10.0))
        qoh = float(row["quantity_on_hand"])
        val = qoh * cost
        total_val += val
        
        items.append(InventoryItem(
            inventory_id=row["inventory_id"],
            medication_id=m_id,
            generic_name=m_meta.get("generic_name", m_id),
            location_id=l_id,
            location_name=l_meta.get("location_name", l_id),
            snapshot_date=ds.snapshot_date_str,
            quantity_on_hand=qoh,
            reorder_level=float(row["reorder_level"]),
            average_daily_usage=float(row["average_daily_usage"]),
            days_of_supply=float(row["days_of_supply"]),
            unit_cost=cost,
            total_inventory_value=round(val, 2),
            criticality=m_meta.get("criticality", "Medium"),
            therapeutic_class=m_meta.get("therapeutic_class", "General")
        ))
        
    page_items = items[offset:offset + limit]
    
    return InventoryListResponse(
        total=total,
        total_value_usd=round(total_val, 2),
        items=page_items
    )
