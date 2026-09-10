"""
Historical daily utilization schemas for MedIntel API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class UtilizationPoint(BaseModel):
    """Daily dispensing data point."""
    date: str
    location_id: str
    location_name: str
    quantity_used: int
    patient_activity_index: float


class UtilizationHistoryResponse(BaseModel):
    """Historical time-series response for medication dispensing."""
    medication_id: str
    generic_name: str
    start_date: str
    end_date: str
    total_dispensed: int
    daily_average: float
    time_series: List[UtilizationPoint]
