"""
Medication risk intelligence router for MedIntel API.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Path
import pandas as pd

from medintel_api.schemas.risk import (
    RiskAssessmentItem,
    RiskListResponse,
    RiskDetailResponse,
    FacilityRiskDetail
)
from medintel_api.services.data_service import DataService, get_data_service

router = APIRouter(prefix="/risks", tags=["Risk Intelligence"])


@router.get("", response_model=RiskListResponse, summary="Get Ranked Medication Risk Assessments")
def get_risks(
    risk_level: Optional[str] = Query(None, description="Filter by risk tier: CRITICAL, HIGH, MEDIUM, LOW"),
    location_id: Optional[str] = Query(None, description="Filter by healthcare facility ID (e.g. LOC001)"),
    medication_id: Optional[str] = Query(None, description="Filter by medication ID (e.g. MED001)"),
    therapeutic_class: Optional[str] = Query(None, description="Filter by therapeutic category"),
    criticality: Optional[str] = Query(None, description="Filter by criticality: High, Medium, Low"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    search: Optional[str] = Query(None, description="Search term for drug or facility"),
    limit: int = Query(50, ge=1, le=525, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset index"),
    ds: DataService = Depends(get_data_service)
) -> RiskListResponse:
    """Returns current evaluated medication risk intelligence sorted by highest risk first."""
    
    items = list(ds.assessments_by_sku.values())
    
    # Filtering
    if risk_level:
        items = [i for i in items if i["risk_level"].upper() == risk_level.upper()]
    if location_id:
        items = [i for i in items if i["location_id"].upper() == location_id.upper()]
    if medication_id:
        items = [i for i in items if i["medication_id"].upper() == medication_id.upper()]
    if therapeutic_class:
        items = [i for i in items if i["therapeutic_class"].lower() == therapeutic_class.lower()]
    if criticality:
        items = [i for i in items if i["criticality"].lower() == criticality.lower()]
    if min_risk_score is not None:
        items = [i for i in items if i["risk_score"] >= min_risk_score]
    if search:
        s = search.lower()
        items = [
            i for i in items 
            if s in i["generic_name"].lower() or s in i["medication_id"].lower() or s in i["location_name"].lower()
        ]
        
    # Sort by risk score descending
    items.sort(key=lambda x: x["risk_score"], reverse=True)
    
    total = len(items)
    page_items = items[offset:offset + limit]
    
    return RiskListResponse(
        total=total,
        items=[RiskAssessmentItem(**item) for item in page_items]
    )


@router.get("/{medication_id}", response_model=RiskDetailResponse, summary="Get Detailed Medication Risk Intelligence")
def get_medication_risk_detail(
    medication_id: str = Path(..., description="Medication identifier (e.g. MED001)"),
    location_id: Optional[str] = Query(None, description="Optional facility ID to isolate single location"),
    ds: DataService = Depends(get_data_service)
) -> RiskDetailResponse:
    """Returns comprehensive diagnostic risk intelligence for a medication across facilities."""
    
    med_id_upper = medication_id.upper()
    if med_id_upper not in ds.medications_by_id:
        raise HTTPException(status_code=404, detail=f"Medication '{medication_id}' not found in active formulary.")
        
    med_meta = ds.medications_by_id[med_id_upper]
    raw = ds.raw_data
    snapshot_dt = ds.snapshot_dt
    
    # Facilities to evaluate
    facility_items = ds.assessments_by_med.get(med_id_upper, [])
    if location_id:
        loc_id_upper = location_id.upper()
        facility_items = [f for f in facility_items if f["location_id"] == loc_id_upper]
        if not facility_items:
            raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found for medication '{medication_id}'.")
            
    # Suppliers for this medication
    sups_df = raw.suppliers[raw.suppliers["medication_id"] == med_id_upper]
    events_df = raw.supplier_events[raw.supplier_events["medication_id"] == med_id_upper]
    
    primary_sup = None
    alt_sups = []
    if len(sups_df) > 0:
        sorted_sups = sups_df.sort_values(["standard_lead_time_days", "reliability_score"], ascending=[True, False])
        p_row = sorted_sups.iloc[0]
        
        # Check active disruptions on primary
        p_events = events_df[events_df["supplier_id"] == p_row["supplier_id"]]
        primary_sup = {
            "supplier_id": p_row["supplier_id"],
            "supplier_name": p_row["supplier_name"],
            "standard_lead_time_days": float(p_row["standard_lead_time_days"]),
            "current_lead_time_days": float(p_row["current_lead_time_days"]),
            "reliability_score": float(p_row["reliability_score"]),
            "active_disruptions": p_events.to_dict(orient="records") if len(p_events) > 0 else []
        }
        
        for _, alt_row in sorted_sups.iloc[1:].iterrows():
            alt_sups.append({
                "supplier_id": alt_row["supplier_id"],
                "supplier_name": alt_row["supplier_name"],
                "standard_lead_time_days": float(alt_row["standard_lead_time_days"]),
                "current_lead_time_days": float(alt_row["current_lead_time_days"]),
                "reliability_score": float(alt_row["reliability_score"])
            })
            
    # Assemble facility details
    facility_details = []
    latest_inv_df = raw.inventory[raw.inventory["snapshot_date"] == snapshot_dt]
    
    for f_item in facility_items:
        l_id = f_item["location_id"]
        
        # Raw inventory row
        inv_match = latest_inv_df[(latest_inv_df["medication_id"] == med_id_upper) & (latest_inv_df["location_id"] == l_id)]
        reorder_lvl = float(inv_match.iloc[0]["reorder_level"]) if len(inv_match) > 0 else 100.0
        
        # Open POs for this SKU
        pos_df = raw.purchase_orders[
            (raw.purchase_orders["medication_id"] == med_id_upper) &
            (raw.purchase_orders["location_id"] == l_id) &
            (raw.purchase_orders["status"].isin(["In Transit", "Delayed"])) &
            (raw.purchase_orders["order_date"] >= (snapshot_dt - pd.Timedelta(days=45)))
        ]
        open_pos_list = []
        for _, po_row in pos_df.iterrows():
            open_pos_list.append({
                "po_id": po_row["po_id"],
                "supplier_id": po_row["supplier_id"],
                "order_date": pd.to_datetime(po_row["order_date"]).strftime("%Y-%m-%d"),
                "expected_delivery_date": pd.to_datetime(po_row["expected_delivery_date"]).strftime("%Y-%m-%d"),
                "quantity_ordered": int(po_row["quantity_ordered"]),
                "status": po_row["status"],
                "days_until_arrival": int((pd.to_datetime(po_row["expected_delivery_date"]) - snapshot_dt).days)
            })
            
        # Expiry lots for this SKU
        lots_df = raw.expiry_lots[
            (raw.expiry_lots["medication_id"] == med_id_upper) &
            (raw.expiry_lots["location_id"] == l_id)
        ]
        lots_list = []
        for _, lot_row in lots_df.iterrows():
            dte = int((pd.to_datetime(lot_row["expiry_date"]) - snapshot_dt).days)
            lots_list.append({
                "lot_id": lot_row["lot_id"],
                "quantity": int(lot_row["quantity"]),
                "manufacture_date": pd.to_datetime(lot_row["manufacture_date"]).strftime("%Y-%m-%d"),
                "expiry_date": pd.to_datetime(lot_row["expiry_date"]).strftime("%Y-%m-%d"),
                "days_to_expiry": dte,
                "is_near_expiry": dte <= 60
            })
            
        # Regional surplus at sister locations
        surplus_list = []
        sister_inv = latest_inv_df[(latest_inv_df["medication_id"] == med_id_upper) & (latest_inv_df["location_id"] != l_id)]
        for _, s_row in sister_inv[sister_inv["days_of_supply"] >= 25.0].iterrows():
            surplus_list.append({
                "location_id": s_row["location_id"],
                "location_name": ds.locations_by_id.get(s_row["location_id"], {}).get("location_name", s_row["location_id"]),
                "quantity_on_hand": float(s_row["quantity_on_hand"]),
                "days_of_supply": float(s_row["days_of_supply"])
            })
            
        facility_details.append(FacilityRiskDetail(
            location_id=l_id,
            location_name=f_item["location_name"],
            location_type=ds.locations_by_id.get(l_id, {}).get("location_type", "General Hospital"),
            risk_score=f_item["risk_score"],
            risk_level=f_item["risk_level"],
            quantity_on_hand=f_item["quantity_on_hand"],
            reorder_level=reorder_lvl,
            average_daily_usage=f_item["average_daily_usage"],
            days_of_supply=f_item["days_of_supply"],
            trend_ratio=f_item["trend_ratio"],
            volatility_cv=0.15,
            predicted_stockout_date=f_item["predicted_stockout_date"],
            days_to_stockout=f_item["days_to_stockout"],
            primary_risk_factors=f_item["primary_risk_factors"],
            contributing_factors=f_item["contributing_factors"],
            mitigating_factors=f_item["mitigating_factors"],
            confidence=f_item["confidence"],
            recommended_review=f_item["recommended_review"],
            open_pos=open_pos_list,
            expiry_lots=lots_list,
            primary_supplier=primary_sup,
            alternate_suppliers=alt_sups,
            regional_surplus=surplus_list
        ))
        
    return RiskDetailResponse(
        medication_id=med_id_upper,
        generic_name=med_meta.get("generic_name", med_id_upper),
        strength=med_meta.get("strength", ""),
        dosage_form=med_meta.get("dosage_form", ""),
        unit_of_measure=med_meta.get("unit_of_measure", "unit"),
        therapeutic_class=med_meta.get("therapeutic_class", "General"),
        unit_cost=float(med_meta.get("unit_cost", 10.0)),
        criticality=med_meta.get("criticality", "Medium"),
        facilities=facility_details
    )
