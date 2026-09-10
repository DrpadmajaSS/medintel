"""
Expiry & Clinical Waste Risk Signal Extractor.
Analyzes active medication batches, shelf-life horizons, and projects
unconsumed physical waste and financial write-off risks per SKU.
"""

from datetime import datetime
import pandas as pd
import numpy as np


def extract_expiry_signals(
    expiry_lots_df: pd.DataFrame,
    snapshot_dt: datetime,
    expiry_horizon_days: int = 60
) -> pd.DataFrame:
    """
    Extracts near-expiry batch risk metrics.
    
    Returns DataFrame indexed by (medication_id, location_id) with:
      - near_lot_id: identifier of nearest expiring lot
      - near_lot_qty: total quantity across near-expiry lots
      - min_days_to_expiry: shortest remaining shelf-life in days
      - nearest_expiry_date: expiration date string
    """
    lots = expiry_lots_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(lots["expiry_date"]):
        lots["expiry_date"] = pd.to_datetime(lots["expiry_date"])
        
    lots["days_to_expiry"] = (lots["expiry_date"] - snapshot_dt).dt.days
    
    # Filter lots expiring within the horizon window
    near_lots = lots[lots["days_to_expiry"] <= expiry_horizon_days].copy()
    
    if len(near_lots) > 0:
        lot_agg = (
            near_lots.sort_values("days_to_expiry")
            .groupby(["medication_id", "location_id"])
            .agg({
                "lot_id": "first",
                "quantity": "sum",
                "days_to_expiry": "min",
                "expiry_date": lambda d: d.iloc[0].strftime("%Y-%m-%d")
            })
            .reset_index()
            .rename(columns={
                "lot_id": "near_lot_id",
                "quantity": "near_lot_qty",
                "days_to_expiry": "min_days_to_expiry",
                "expiry_date": "nearest_expiry_date"
            })
        )
    else:
        lot_agg = pd.DataFrame(columns=[
            "medication_id",
            "location_id",
            "near_lot_id",
            "near_lot_qty",
            "min_days_to_expiry",
            "nearest_expiry_date"
        ])
        
    return lot_agg
