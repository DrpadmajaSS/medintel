"""
Data structures and schema definitions for MedIntel Synthetic Datasets.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Medication:
    medication_id: str
    generic_name: str
    strength: str
    dosage_form: str
    unit_of_measure: str
    therapeutic_class: str
    unit_cost: float
    criticality: str


@dataclass
class Location:
    location_id: str
    location_name: str
    location_type: str
    region: str


@dataclass
class Supplier:
    supplier_id: str
    supplier_name: str
    medication_id: str
    standard_lead_time_days: int
    current_lead_time_days: int
    reliability_score: float


@dataclass
class InventorySnapshot:
    inventory_id: str
    medication_id: str
    location_id: str
    snapshot_date: str
    quantity_on_hand: int
    reorder_level: int
    average_daily_usage: float
    days_of_supply: float


@dataclass
class UtilizationDaily:
    date: str
    medication_id: str
    location_id: str
    quantity_used: int
    patient_activity_index: float


@dataclass
class PurchaseOrder:
    po_id: str
    medication_id: str
    location_id: str
    supplier_id: str
    order_date: str
    expected_delivery_date: str
    actual_delivery_date: Optional[str]
    quantity_ordered: int
    quantity_received: int
    status: str


@dataclass
class SupplierEvent:
    event_id: str
    supplier_id: str
    medication_id: str
    event_date: str
    event_type: str
    delay_days: int
    description: str


@dataclass
class ExpiryLot:
    lot_id: str
    medication_id: str
    location_id: str
    quantity: int
    manufacture_date: str
    expiry_date: str


@dataclass
class GroundTruth:
    scenario_id: str
    medication_id: str
    location_id: str
    expected_issue: str
    expected_severity: str
    expected_stockout_window: str
    expected_recommendation: str
