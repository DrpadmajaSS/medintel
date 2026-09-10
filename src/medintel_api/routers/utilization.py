"""
Historical daily utilization time-series router for MedIntel API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Path
import pandas as pd

from medintel_api.schemas.utilization import UtilizationPoint, UtilizationHistoryResponse
from medintel_api.services.data_service import DataService, get_data_service

router = APIRouter(prefix="/utilization", tags=["Utilization Intelligence"])


@router.get("/{medication_id}", response_model=UtilizationHistoryResponse, summary="Get Historical Daily Utilization Time-Series")
def get_utilization_history(
    medication_id: str = Path(..., description="Medication ID (e.g. MED001)"),
    location_id: Optional[str] = Query(None, description="Optional facility ID to isolate single location"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    ds: DataService = Depends(get_data_service)
) -> UtilizationHistoryResponse:
    """Returns 365-day historical dispensing curves formatted for interactive frontend charting."""
    
    med_id_upper = medication_id.upper()
    if med_id_upper not in ds.medications_by_id:
        raise HTTPException(status_code=404, detail=f"Medication '{medication_id}' not found in active formulary.")
        
    med_meta = ds.medications_by_id[med_id_upper]
    locs_dict = ds.locations_by_id
    raw = ds.raw_data
    
    df = raw.utilization_daily[raw.utilization_daily["medication_id"] == med_id_upper].copy()
    
    if location_id:
        loc_id_upper = location_id.upper()
        df = df[df["location_id"] == loc_id_upper]
        if len(df) == 0:
            raise HTTPException(status_code=404, detail=f"No utilization found for location '{location_id}'.")
            
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]
        
    df = df.sort_values("date")
    
    time_series = [
        UtilizationPoint(
            date=pd.to_datetime(row["date"]).strftime("%Y-%m-%d"),
            location_id=row["location_id"],
            location_name=locs_dict.get(row["location_id"], {}).get("location_name", row["location_id"]),
            quantity_used=int(row["quantity_used"]),
            patient_activity_index=round(float(row["patient_activity_index"]), 3)
        )
        for _, row in df.iterrows()
    ]
    
    total_disp = sum(p.quantity_used for p in time_series)
    avg_disp = round(total_disp / max(len(time_series), 1), 2)
    s_date = time_series[0].date if time_series else ""
    e_date = time_series[-1].date if time_series else ""
    
    return UtilizationHistoryResponse(
        medication_id=med_id_upper,
        generic_name=med_meta.get("generic_name", med_id_upper),
        start_date=s_date,
        end_date=e_date,
        total_dispensed=total_disp,
        daily_average=avg_disp,
        time_series=time_series
    )
