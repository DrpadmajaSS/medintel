"""
Unit tests for MedIntel StockoutPredictor.
"""

from datetime import datetime
import pytest
from medintel_engine.stockout_predictor import StockoutPredictor


def test_stockout_predictor_imminent_stockout():
    predictor = StockoutPredictor(simulation_horizon_days=60, trend_horizon_days=14)
    snapshot_dt = datetime(2026, 8, 31)
    
    # 50 units on hand, 25 units/day usage -> stockout in 2.0 days
    days, date_str = predictor.predict_trajectory(
        qoh=50.0,
        adu_7d=25.0,
        adu_30d=25.0,
        in_transit_qty=0.0,
        in_transit_days=999.0,
        snapshot_dt=snapshot_dt
    )
    assert days == 2.0
    assert date_str == "2026-09-02"


def test_stockout_predictor_in_transit_protection():
    predictor = StockoutPredictor(simulation_horizon_days=60, trend_horizon_days=14)
    snapshot_dt = datetime(2026, 8, 31)
    
    # 30 units on hand, 20 units/day usage, but 500 units arrive on day 1
    days, date_str = predictor.predict_trajectory(
        qoh=30.0,
        adu_7d=20.0,
        adu_30d=20.0,
        in_transit_qty=500.0,
        in_transit_days=1.0,
        snapshot_dt=snapshot_dt
    )
    # 30 - 20 + 500 = 510 -> stockout after 510 / 20 = 25.5 + 1 = 26.5 days
    assert days is not None
    assert days > 25.0


def test_stockout_predictor_healthy_buffer():
    predictor = StockoutPredictor(simulation_horizon_days=60, trend_horizon_days=14)
    snapshot_dt = datetime(2026, 8, 31)
    
    # 2000 units on hand, 10 units/day usage -> no stockout within 60 days
    days, date_str = predictor.predict_trajectory(
        qoh=2000.0,
        adu_7d=10.0,
        adu_30d=10.0,
        in_transit_qty=0.0,
        in_transit_days=999.0,
        snapshot_dt=snapshot_dt
    )
    assert days is None
    assert date_str is None
