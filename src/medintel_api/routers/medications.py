"""
Medications master data router for MedIntel API.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from medintel_api.schemas.medication import MedicationItem, MedicationListResponse
from medintel_api.services.data_service import DataService, get_data_service

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.get("", response_model=MedicationListResponse, summary="Get Medications Master Formulary")
def get_medications(
    therapeutic_class: Optional[str] = Query(None, description="Filter by therapeutic class"),
    criticality: Optional[str] = Query(None, description="Filter by criticality: High, Medium, Low"),
    search: Optional[str] = Query(None, description="Search term for generic name or medication ID"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset index"),
    ds: DataService = Depends(get_data_service)
) -> MedicationListResponse:
    """Returns the medication master formulary with optional clinical filtering."""
    raw = ds.raw_data
    df = raw.medications.copy()
    
    if therapeutic_class:
        df = df[df["therapeutic_class"].str.lower().str.contains(therapeutic_class.lower())]
    if criticality:
        df = df[df["criticality"].str.lower() == criticality.lower()]
    if search:
        s = search.lower()
        df = df[df["generic_name"].str.lower().str.contains(s) | df["medication_id"].str.lower().str.contains(s)]
        
    total = len(df)
    df_page = df.iloc[offset:offset + limit]
    
    items = [
        MedicationItem(
            medication_id=row["medication_id"],
            generic_name=row["generic_name"],
            strength=row["strength"],
            dosage_form=row["dosage_form"],
            unit_of_measure=row["unit_of_measure"],
            therapeutic_class=row["therapeutic_class"],
            unit_cost=float(row["unit_cost"]),
            criticality=row["criticality"]
        )
        for _, row in df_page.iterrows()
    ]
    
    return MedicationListResponse(total=total, items=items)
