"""
Unit tests for MedIntel RiskCalculator.
"""

from datetime import datetime
import pandas as pd
import pytest

from medintel_engine.config import RiskEngineConfig
from medintel_engine.risk_calculator import RiskCalculator


@pytest.fixture
def calculator():
    return RiskCalculator(config=RiskEngineConfig())


@pytest.fixture
def snapshot_dt():
    return datetime(2026, 8, 31)


def test_risk_calculator_critical_shortage(calculator, snapshot_dt):
    row = pd.Series({
        "medication_id": "MED001",
        "location_id": "LOC006",
        "quantity_on_hand": 0.0,
        "days_of_supply": 0.0,
        "adu_7d": 120.0,
        "adu_30d": 100.0,
        "trend_ratio": 1.20,
        "volatility_cv": 0.15,
        "criticality": "High",
        "unit_cost": 15.0,
        "primary_std_lt": 2.0,
        "primary_curr_lt": 5.0,
        "primary_lt_surge": 3.0,
        "active_delay_days": 12.0,
        "primary_reliability": 0.88,
        "has_delayed_po": True,
        "in_transit_ontime_qty": 0.0,
        "in_transit_nearest_days": 999.0,
        "near_lot_qty": 0.0,
        "min_days_to_expiry": 999.0,
        "other_locations_qoh": 50.0,
        "surplus_loc_name": None,
        "surplus_qoh": 0.0,
        "surplus_dos": 0.0,
        "alt_supplier_names": ["Vendor Beta"],
        "alt_min_lt": 4.0,
        "std_30d": 15.0
    })
    
    res = calculator.evaluate_sku(row, snapshot_dt)
    assert res["risk_level"] == "CRITICAL"
    assert res["risk_score"] >= 80.0
    assert "Acute low inventory buffer" in res["primary_risk_factors"]
    assert "Declare acute critical shortage" in res["recommended_review"]


def test_risk_calculator_false_alarm_mitigation(calculator, snapshot_dt):
    row = pd.Series({
        "medication_id": "MED021",
        "location_id": "LOC004",
        "quantity_on_hand": 0.0,
        "days_of_supply": 0.0,
        "adu_7d": 18.0,
        "adu_30d": 15.0,
        "trend_ratio": 1.20,
        "volatility_cv": 0.10,
        "criticality": "High",
        "unit_cost": 8.5,
        "primary_std_lt": 4.0,
        "primary_curr_lt": 4.0,
        "primary_lt_surge": 0.0,
        "active_delay_days": 0.0,
        "primary_reliability": 0.96,
        "has_delayed_po": False,
        "in_transit_ontime_qty": 500.0,
        "in_transit_nearest_days": 1.0,  # Arrives tomorrow!
        "near_lot_qty": 0.0,
        "min_days_to_expiry": 999.0,
        "other_locations_qoh": 4000.0,
        "surplus_loc_name": "Central AMC",
        "surplus_qoh": 2000.0,
        "surplus_dos": 40.0,
        "alt_supplier_names": ["Vendor Beta"],
        "alt_min_lt": 4.0,
        "std_30d": 3.0
    })
    
    res = calculator.evaluate_sku(row, snapshot_dt)
    assert res["risk_level"] == "LOW"
    assert res["risk_score"] <= 30.0
    assert "Confirmed inbound PO" in res["mitigating_factors"]
    assert "No escalation required" in res["recommended_review"]
