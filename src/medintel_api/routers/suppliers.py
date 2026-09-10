"""
Supplier intelligence router for MedIntel API.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
import pandas as pd

from medintel_api.schemas.supplier import SupplierItem, SupplierListResponse, DisruptionEventItem
from medintel_api.services.data_service import DataService, get_data_service

router = APIRouter(prefix="/suppliers", tags=["Supplier Intelligence"])


@router.get("", response_model=SupplierListResponse, summary="Get Supplier Intelligence & Disruption Status")
def get_suppliers(
    medication_id: Optional[str] = Query(None, description="Filter by medication ID supplied"),
    supplier_id: Optional[str] = Query(None, description="Filter by supplier ID"),
    delayed_only: bool = Query(False, description="Filter only suppliers with active delays/surges"),
    ds: DataService = Depends(get_data_service)
) -> SupplierListResponse:
    """Returns supplier performance metrics, standard vs. current lead times, and active disruption events."""
    raw = ds.raw_data
    sups = raw.suppliers.copy()
    events = raw.supplier_events.copy()
    pos = raw.purchase_orders.copy()
    
    if medication_id:
        sups = sups[sups["medication_id"].str.upper() == medication_id.upper()]
    if supplier_id:
        sups = sups[sups["supplier_id"].str.upper() == supplier_id.upper()]
        
    items: List[SupplierItem] = []
    
    # Group by supplier_id
    for sup_id, grp in sups.groupby("supplier_id"):
        sup_name = grp.iloc[0]["supplier_name"]
        med_ids = grp["medication_id"].unique().tolist()
        
        std_lt = float(grp["standard_lead_time_days"].mean())
        curr_lt = float(grp["current_lead_time_days"].mean())
        surge = max(0.0, curr_lt - std_lt)
        rel = float(grp["reliability_score"].mean())
        
        # Events for this supplier
        sup_events = events[events["supplier_id"] == sup_id]
        event_items = [
            DisruptionEventItem(
                event_id=r["event_id"],
                event_date=pd.to_datetime(r["event_date"]).strftime("%Y-%m-%d"),
                event_type=r["event_type"],
                delay_days=int(r["delay_days"]),
                description=r["description"]
            )
            for _, r in sup_events.iterrows()
        ]
        
        # Delayed purchase orders count
        delayed_po_count = len(pos[(pos["supplier_id"] == sup_id) & (pos["status"] == "Delayed")])
        
        if delayed_only and surge == 0 and len(event_items) == 0 and delayed_po_count == 0:
            continue
            
        items.append(SupplierItem(
            supplier_id=sup_id,
            supplier_name=sup_name,
            medications_supplied_count=len(med_ids),
            medication_ids=med_ids,
            standard_lead_time_days=round(std_lt, 1),
            current_lead_time_days=round(curr_lt, 1),
            lead_time_surge_days=round(surge, 1),
            reliability_score=round(rel, 3),
            active_disruptions_count=len(event_items),
            total_delayed_orders_count=delayed_po_count,
            active_events=event_items
        ))
        
    # Sort by lead time surge descending, then reliability ascending
    items.sort(key=lambda x: (x.lead_time_surge_days, x.active_disruptions_count), reverse=True)
    
    return SupplierListResponse(total=len(items), items=items)
