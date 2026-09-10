"""
Health check and metadata router for MedIntel API.
"""

from fastapi import APIRouter, Depends
from medintel_api.schemas.common import HealthResponse, MetadataResponse
from medintel_api.services.data_service import DataService, get_data_service

router = APIRouter(tags=["Health & System"])


@router.get("/health", response_model=HealthResponse, summary="Application Health Check")
def get_health(ds: DataService = Depends(get_data_service)) -> HealthResponse:
    """Returns application status, API version, dataset readiness, and monitored SKU counts."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        data_status="loaded",
        snapshot_date=ds.snapshot_date_str,
        medications_count=len(ds.medications_by_id),
        locations_count=len(ds.locations_by_id),
        assessed_skus_count=len(ds.assessments_by_sku)
    )


@router.get("/metadata", response_model=MetadataResponse, summary="System Metadata")
def get_metadata(ds: DataService = Depends(get_data_service)) -> MetadataResponse:
    """Returns lists of available facilities, therapeutic classes, criticality tiers, and risk levels."""
    raw = ds.raw_data
    facilities = [
        {"id": row["location_id"], "name": row["location_name"], "type": row["location_type"], "region": row["region"]}
        for _, row in raw.locations.iterrows()
    ]
    classes = sorted(raw.medications["therapeutic_class"].unique().tolist())
    
    return MetadataResponse(
        facilities=facilities,
        therapeutic_classes=classes,
        criticality_levels=["High", "Medium", "Low"],
        risk_levels=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        snapshot_date=ds.snapshot_date_str
    )


@router.post("/reload-data", summary="Refresh In-Memory Cache")
def reload_data(ds: DataService = Depends(get_data_service)):
    """Forces in-memory reload and re-assessment of datasets."""
    ds.reload()
    return {
        "status": "success",
        "message": f"Successfully reloaded {len(ds.assessments_by_sku)} SKUs on snapshot {ds.snapshot_date_str}"
    }
