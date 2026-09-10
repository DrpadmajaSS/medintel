"""
Utilization Signal Extractor.
Calculates 7-day, 14-day, and 30-day moving average daily usage, demand velocity trend ratios,
and coefficient of variation (volatility) per (medication_id, location_id).
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np


def extract_utilization_signals(utilization_df: pd.DataFrame, snapshot_dt: datetime) -> pd.DataFrame:
    """
    Extracts multi-window utilization metrics from daily utilization records.
    
    Returns DataFrame indexed by (medication_id, location_id) with columns:
      - adu_7d: 7-day rolling average daily usage
      - adu_14d: 14-day rolling average daily usage
      - adu_30d: 30-day rolling average daily usage
      - std_30d: 30-day standard deviation
      - trend_ratio: adu_7d / max(adu_30d, 0.1)
      - volatility_cv: std_30d / max(adu_30d, 0.1)
    """
    df = utilization_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])
        
    c7 = snapshot_dt - timedelta(days=7)
    c14 = snapshot_dt - timedelta(days=14)
    c30 = snapshot_dt - timedelta(days=30)
    
    # Filter by time windows up to snapshot_dt
    df_window = df[df["date"] <= snapshot_dt]
    
    u7 = df_window[df_window["date"] > c7].groupby(["medication_id", "location_id"])["quantity_used"].mean().rename("adu_7d")
    u14 = df_window[df_window["date"] > c14].groupby(["medication_id", "location_id"])["quantity_used"].mean().rename("adu_14d")
    u30_agg = df_window[df_window["date"] > c30].groupby(["medication_id", "location_id"])["quantity_used"].agg(["mean", "std"]).rename(
        columns={"mean": "adu_30d", "std": "std_30d"}
    )
    
    util_metrics = pd.concat([u7, u14, u30_agg], axis=1).reset_index()
    util_metrics["trend_ratio"] = (util_metrics["adu_7d"] / util_metrics["adu_30d"].clip(lower=0.1)).round(3)
    util_metrics["volatility_cv"] = ((util_metrics["std_30d"] / util_metrics["adu_30d"].clip(lower=0.1)).fillna(0)).round(3)
    
    return util_metrics
