"""
Dashboard metrics and executive KPI router for MedIntel API.
"""

from typing import Optional, Dict
from fastapi import APIRouter, Depends, Query
import pandas as pd

from medintel_api.schemas.metrics import DashboardMetricsResponse
from medintel_api.services.data_service import DataService, get_data_service
from medintel_api.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/metrics", tags=["Dashboard Metrics & KPIs"])


@router.get("", response_model=DashboardMetricsResponse, summary="Get Executive Dashboard Metrics & KPIs")
def get_metrics(
    location_id: Optional[str] = Query(None, description="Optional facility ID to isolate single location"),
    ds: DataService = Depends(get_data_service)
) -> DashboardMetricsResponse:
    """Returns top-level executive KPIs for the MedIntel dashboard."""
    
    items = list(ds.assessments_by_sku.values())
    if location_id:
        items = [i for i in items if i["location_id"].upper() == location_id.upper()]
        
    raw = ds.raw_data
    snapshot_dt = ds.snapshot_dt
    meds_dict = ds.medications_by_id
    
    # Counts by risk level
    breakdown = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for i in items:
        lvl = i["risk_level"]
        breakdown[lvl] = breakdown.get(lvl, 0) + 1
        
    critical_count = breakdown.get("CRITICAL", 0)
    
    # Emerging risks: MEDIUM items with trend_ratio >= 1.25
    emerging_count = len([i for i in items if i["risk_level"] == "MEDIUM" and i["trend_ratio"] >= 1.25])
    
    # Potential stockouts: stockout in <= 14 days
    potential_stockouts = len([i for i in items if i["days_to_stockout"] is not None and i["days_to_stockout"] <= 14.0])
    
    # Expiry risks: Lots expiring within 60 days
    lots = raw.expiry_lots.copy()
    lots["days_to_expiry"] = (pd.to_datetime(lots["expiry_date"]) - snapshot_dt).dt.days
    near_lots = lots[lots["days_to_expiry"] <= 60]
    if location_id:
        near_lots = near_lots[near_lots["location_id"].str.upper() == location_id.upper()]
        
    expiry_count = len(near_lots)
    expiry_exposure_val = sum(float(r["quantity"]) * float(meds_dict.get(r["medication_id"], {}).get("unit_cost", 10.0)) for _, r in near_lots.iterrows())
    
    # Supplier risks: Active delays or lead time surges
    sups = raw.suppliers
    events = raw.supplier_events
    surging_sups = len(sups[sups["current_lead_time_days"] > sups["standard_lead_time_days"]]["supplier_id"].unique())
    delayed_sups = len(events[events["event_date"] > (snapshot_dt - pd.Timedelta(days=30))]["supplier_id"].unique())
    supplier_risks = max(surging_sups, delayed_sups)
    
    # Opportunities
    opp_service = OpportunityService(ds)
    opps = opp_service.get_opportunities(location_id=location_id)
    
    return DashboardMetricsResponse(
        medications_monitored=len(ds.medications_by_id) if not location_id else len(set(i["medication_id"] for i in items)),
        locations_monitored=len(ds.locations_by_id) if not location_id else 1,
        critical_risks=critical_count,
        emerging_risks=emerging_count,
        potential_stockouts=potential_stockouts,
        expiry_risks=expiry_count,
        total_expiry_exposure_usd=round(expiry_exposure_val, 2),
        supplier_risks=supplier_risks,
        potential_redistribution_opportunities=len(opps.redistribution_opportunities),
        estimated_rebalance_savings_usd=round(sum(r.estimated_cost_avoidance_usd for r in opps.redistribution_opportunities), 2),
        risk_level_breakdown=breakdown
    )
