"""
Unit tests for MedIntel Risk Engine Signal Extractors.
"""

from datetime import datetime
import pandas as pd
import numpy as np
import pytest

from medintel_engine.signals.utilization_signals import extract_utilization_signals
from medintel_engine.signals.supply_signals import extract_supply_signals
from medintel_engine.signals.pipeline_signals import extract_pipeline_signals
from medintel_engine.signals.inventory_signals import extract_inventory_signals
from medintel_engine.signals.expiry_signals import extract_expiry_signals


@pytest.fixture
def sample_snapshot_dt():
    return datetime(2026, 8, 31)


def test_extract_utilization_signals(sample_snapshot_dt):
    dates = pd.date_range("2026-08-01", "2026-08-31", freq="D")
    df_util = pd.DataFrame({
        "date": list(dates) * 2,
        "medication_id": ["MED001"] * len(dates) + ["MED002"] * len(dates),
        "location_id": ["LOC001"] * len(dates) + ["LOC001"] * len(dates),
        "quantity_used": [50] * len(dates) + [10 + i for i in range(len(dates))],
        "patient_activity_index": [1.0] * (len(dates) * 2)
    })
    
    signals = extract_utilization_signals(df_util, sample_snapshot_dt)
    assert len(signals) == 2
    assert "adu_7d" in signals.columns
    assert "trend_ratio" in signals.columns
    assert "volatility_cv" in signals.columns
    
    med1 = signals[signals["medication_id"] == "MED001"].iloc[0]
    assert pytest.approx(med1["adu_7d"], 0.1) == 50.0
    assert pytest.approx(med1["trend_ratio"], 0.1) == 1.0


def test_extract_supply_signals(sample_snapshot_dt):
    df_sups = pd.DataFrame({
        "supplier_id": ["SUP001", "SUP002"],
        "supplier_name": ["Vendor Alpha", "Vendor Beta"],
        "medication_id": ["MED001", "MED001"],
        "standard_lead_time_days": [4, 7],
        "current_lead_time_days": [14, 7],
        "reliability_score": [0.95, 0.98]
    })
    df_events = pd.DataFrame({
        "event_id": ["EVT001"],
        "supplier_id": ["SUP001"],
        "medication_id": ["MED001"],
        "event_date": [datetime(2026, 8, 15)],
        "event_type": ["Logistics Delay"],
        "delay_days": [10],
        "description": ["Port congestion"]
    })
    
    primary_sups, alt_sups = extract_supply_signals(df_sups, df_events, sample_snapshot_dt)
    assert len(primary_sups) == 1
    assert primary_sups.iloc[0]["primary_supplier_id"] == "SUP001"
    assert primary_sups.iloc[0]["primary_lt_surge"] == 10
    assert primary_sups.iloc[0]["active_delay_days"] == 10
    
    assert len(alt_sups) == 1
    assert "SUP002" in alt_sups.iloc[0]["alt_supplier_ids"]


def test_extract_pipeline_signals(sample_snapshot_dt):
    df_pos = pd.DataFrame({
        "po_id": ["PO-101", "PO-102"],
        "medication_id": ["MED001", "MED001"],
        "location_id": ["LOC001", "LOC001"],
        "supplier_id": ["SUP001", "SUP001"],
        "order_date": [datetime(2026, 8, 20), datetime(2026, 8, 25)],
        "expected_delivery_date": [datetime(2026, 8, 24), datetime(2026, 9, 2)],
        "actual_delivery_date": [datetime(2026, 8, 24), pd.NaT],
        "quantity_ordered": [500, 300],
        "quantity_received": [500, 0],
        "status": ["Delivered", "In Transit"]
    })
    
    pipe = extract_pipeline_signals(df_pos, sample_snapshot_dt)
    assert len(pipe) == 1
    assert pipe.iloc[0]["in_transit_ontime_qty"] == 300
    assert pipe.iloc[0]["in_transit_nearest_days"] == 2


def test_extract_inventory_signals(sample_snapshot_dt):
    df_inv = pd.DataFrame({
        "inventory_id": ["INV1", "INV2"],
        "medication_id": ["MED001", "MED001"],
        "location_id": ["LOC001", "LOC002"],
        "snapshot_date": [sample_snapshot_dt, sample_snapshot_dt],
        "quantity_on_hand": [50, 1500],
        "reorder_level": [100, 200],
        "average_daily_usage": [25.0, 30.0],
        "days_of_supply": [2.0, 50.0]
    })
    
    inv_res = extract_inventory_signals(df_inv, sample_snapshot_dt)
    assert len(inv_res) == 2
    assert inv_res[inv_res["location_id"] == "LOC001"]["other_locations_qoh"].iloc[0] == 1500
    assert inv_res[inv_res["location_id"] == "LOC001"]["surplus_loc_id"].iloc[0] == "LOC002"


def test_extract_expiry_signals(sample_snapshot_dt):
    df_lots = pd.DataFrame({
        "lot_id": ["LOT01", "LOT02"],
        "medication_id": ["MED001", "MED002"],
        "location_id": ["LOC001", "LOC001"],
        "quantity": [200, 500],
        "manufacture_date": [datetime(2025, 1, 1), datetime(2025, 1, 1)],
        "expiry_date": [datetime(2026, 9, 20), datetime(2028, 1, 1)]
    })
    
    exp_res = extract_expiry_signals(df_lots, sample_snapshot_dt, expiry_horizon_days=60)
    assert len(exp_res) == 1
    assert exp_res.iloc[0]["near_lot_id"] == "LOT01"
    assert exp_res.iloc[0]["min_days_to_expiry"] == 20
