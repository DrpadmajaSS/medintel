"""
Supply Chain & Supplier Disruption Signal Extractor.
Analyzes supplier lead times, lead time surges, recent disruption events,
reliability scores, and alternate supplier availability.
"""

from datetime import datetime, timedelta
from typing import Tuple
import pandas as pd
import numpy as np


def extract_supply_signals(
    suppliers_df: pd.DataFrame,
    supplier_events_df: pd.DataFrame,
    snapshot_dt: datetime,
    recent_events_window_days: int = 30
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts primary and alternate supplier risk metrics per medication.
    
    Returns:
      - primary_sups: DataFrame with primary vendor metrics, lead time surges, and active disruption delays
      - alt_sups: DataFrame with alternate certified vendors maintaining standard lead times
    """
    sups = suppliers_df.copy()
    events = supplier_events_df.copy()
    
    if not pd.api.types.is_datetime64_any_dtype(events["event_date"]):
        events["event_date"] = pd.to_datetime(events["event_date"])
        
    sups["lead_time_surge"] = (sups["current_lead_time_days"] - sups["standard_lead_time_days"]).clip(lower=0)
    
    # Primary supplier per medication: lowest standard lead time, break ties with reliability
    primary_sups = (
        sups.sort_values(["medication_id", "standard_lead_time_days", "reliability_score"], ascending=[True, True, False])
        .groupby("medication_id")
        .first()
        .reset_index()
    )
    primary_sups = primary_sups.rename(columns={
        "supplier_id": "primary_supplier_id",
        "supplier_name": "primary_supplier_name",
        "standard_lead_time_days": "primary_std_lt",
        "current_lead_time_days": "primary_curr_lt",
        "reliability_score": "primary_reliability",
        "lead_time_surge": "primary_lt_surge"
    })
    
    # Alternate suppliers with normal lead time
    alt_sups = (
        sups[sups["lead_time_surge"] == 0]
        .groupby("medication_id")
        .agg({
            "supplier_id": lambda x: list(x),
            "supplier_name": lambda x: list(x),
            "current_lead_time_days": "min"
        })
        .reset_index()
        .rename(columns={
            "supplier_id": "alt_supplier_ids",
            "supplier_name": "alt_supplier_names",
            "current_lead_time_days": "alt_min_lt"
        })
    )
    
    # Filter recent active events within window
    recent_events = events[events["event_date"] > (snapshot_dt - timedelta(days=recent_events_window_days))]
    if len(recent_events) > 0:
        event_summary = (
            recent_events.groupby(["supplier_id", "medication_id"])
            .agg({
                "delay_days": "sum",
                "event_type": lambda x: "; ".join(x.unique()),
                "description": lambda x: "; ".join(x.iloc[-1:])
            })
            .reset_index()
            .rename(columns={
                "delay_days": "active_delay_days",
                "event_type": "disruption_type",
                "description": "disruption_desc"
            })
        )
        primary_sups = primary_sups.merge(
            event_summary.rename(columns={"supplier_id": "primary_supplier_id"}),
            on=["primary_supplier_id", "medication_id"],
            how="left"
        )
    else:
        primary_sups["active_delay_days"] = 0.0
        primary_sups["disruption_type"] = None
        primary_sups["disruption_desc"] = None
        
    primary_sups["active_delay_days"] = primary_sups["active_delay_days"].fillna(0.0)
    
    return primary_sups, alt_sups
