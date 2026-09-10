"""
Inventory & Regional Network Surplus Signal Extractor.
Extracts on-hand quantities, days of supply, and detects surplus inventory
at sister facilities across the healthcare network available for lateral rebalancing.
"""

from datetime import datetime
import pandas as pd
import numpy as np


def extract_inventory_signals(
    inventory_df: pd.DataFrame,
    snapshot_dt: datetime,
    surplus_dos_threshold: float = 30.0,
    surplus_qoh_threshold: float = 500.0
) -> pd.DataFrame:
    """
    Extracts latest inventory snapshots and computes network-wide lateral surplus inventory.
    
    Returns:
      - latest_inv: DataFrame with latest snapshot per SKU plus surplus location metadata
    """
    inv = inventory_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(inv["snapshot_date"]):
        inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"])
        
    latest_inv = inv[inv["snapshot_date"] == snapshot_dt].copy()
    
    # Calculate network total QOH and other locations QOH
    net_totals = latest_inv.groupby("medication_id")["quantity_on_hand"].transform("sum")
    latest_inv["network_total_qoh"] = net_totals
    latest_inv["other_locations_qoh"] = latest_inv["network_total_qoh"] - latest_inv["quantity_on_hand"]
    
    # Identify top surplus facility per medication
    surplus_candidates = latest_inv[
        (latest_inv["days_of_supply"] >= surplus_dos_threshold)
        | (latest_inv["quantity_on_hand"] >= surplus_qoh_threshold)
    ].copy()
    
    if len(surplus_candidates) > 0:
        surplus_locs = (
            surplus_candidates.sort_values(
                ["medication_id", "days_of_supply", "quantity_on_hand"],
                ascending=[True, False, False]
            )
            .groupby("medication_id")
            .first()
            .reset_index()
        )
        surplus_locs = surplus_locs[[
            "medication_id",
            "location_id",
            "quantity_on_hand",
            "days_of_supply"
        ]].rename(columns={
            "location_id": "surplus_loc_id",
            "quantity_on_hand": "surplus_qoh",
            "days_of_supply": "surplus_dos"
        })
        latest_inv = latest_inv.merge(surplus_locs, on="medication_id", how="left")
    else:
        latest_inv["surplus_loc_id"] = None
        latest_inv["surplus_qoh"] = 0.0
        latest_inv["surplus_dos"] = 0.0
        
    latest_inv["surplus_qoh"] = latest_inv["surplus_qoh"].fillna(0.0)
    latest_inv["surplus_dos"] = latest_inv["surplus_dos"].fillna(0.0)
    
    return latest_inv
