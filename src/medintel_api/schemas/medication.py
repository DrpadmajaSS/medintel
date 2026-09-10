"""
Medication schemas for MedIntel API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MedicationItem(BaseModel):
    """Medication formulary record."""
    medication_id: str = Field(..., description="Unique medication identifier (e.g. MED001)")
    generic_name: str = Field(..., description="Generic clinical name of medication")
    strength: str = Field(..., description="Dosage strength (e.g. 4 mg/4 mL)")
    dosage_form: str = Field(..., description="Form (e.g. Injectable Solution, Tablet)")
    unit_of_measure: str = Field(..., description="Unit of dispensing (e.g. vial, ampule, tablet)")
    therapeutic_class: str = Field(..., description="Clinical therapeutic category")
    unit_cost: float = Field(..., description="Standard procurement unit cost in USD")
    criticality: str = Field(..., description="Clinical criticality level: High, Medium, Low")


class MedicationListResponse(BaseModel):
    """Response containing list of medications."""
    total: int = Field(..., description="Total count matching query")
    items: List[MedicationItem] = Field(..., description="List of medication items")
