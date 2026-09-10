"""
Stockout Forward Predictor.
Simulates daily closed-loop inventory trajectories over a configurable horizon (e.g. 60 days),
incorporating trend-adjusted daily burn rates and scheduled in-transit PO deliveries.
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
import pandas as pd
import numpy as np


class StockoutPredictor:
    """Predicts stockout date and days to stockout using discrete-event daily simulation."""
    
    def __init__(self, simulation_horizon_days: int = 60, trend_horizon_days: int = 14):
        self.horizon_days = simulation_horizon_days
        self.trend_days = trend_horizon_days
        
    def predict_trajectory(
        self,
        qoh: float,
        adu_7d: float,
        adu_30d: float,
        in_transit_qty: float,
        in_transit_days: float,
        snapshot_dt: datetime
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Simulates forward daily inventory progression.
        
        Returns:
          - days_to_stockout: float estimate of days until stock is exhausted, or None if safe
          - predicted_stockout_date: ISO date string 'YYYY-MM-DD', or None if safe
        """
        sim_inv = float(qoh)
        
        for d in range(1, self.horizon_days + 1):
            # Dynamic daily burn: use recent 7-day rate for initial window, reverting to 30-day baseline
            daily_usage = float(adu_7d) if d <= self.trend_days else float(adu_30d)
            sim_inv -= daily_usage
            
            # Add inbound in-transit PO arrival if it lands on day d
            if in_transit_qty > 0 and d == max(1, int(in_transit_days)):
                sim_inv += in_transit_qty
                
            if sim_inv <= 0:
                fractional_day = (sim_inv + daily_usage) / max(daily_usage, 0.1)
                days_to_stockout = round(d - 1 + fractional_day, 1)
                days_to_stockout = max(0.0, days_to_stockout)
                
                pred_dt = snapshot_dt + timedelta(days=int(days_to_stockout))
                pred_date_str = pred_dt.strftime("%Y-%m-%d")
                return days_to_stockout, pred_date_str
                
        return None, None
