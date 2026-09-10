"""
Pipeline Purchase Order Signal Extractor.
Extracts active, unfulfilled purchase orders, delivery timelines,
in-transit arrival dates, and delayed order status per SKU.
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np


def extract_pipeline_signals(
    purchase_orders_df: pd.DataFrame,
    snapshot_dt: datetime,
    recent_po_window_days: int = 30
) -> pd.DataFrame:
    """
    Extracts open purchase orders currently in the supply chain pipeline.
    
    Filters out obsolete delayed POs if a newer order was already fulfilled.
    
    Returns DataFrame indexed by (medication_id, location_id) with:
      - active_po_count: number of active open orders
      - active_po_qty: sum of ordered units in flight
      - nearest_po_days: days until nearest expected delivery
      - nearest_po_id: PO identifier of nearest order
      - nearest_po_status: status of nearest order
      - has_delayed_po: boolean indicator of delayed shipment
      - in_transit_ontime_qty: quantity of verified in-transit orders
      - in_transit_nearest_days: days to nearest in-transit delivery
    """
    pos = purchase_orders_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(pos["order_date"]):
        pos["order_date"] = pd.to_datetime(pos["order_date"])
    if not pd.api.types.is_datetime64_any_dtype(pos["expected_delivery_date"]):
        pos["expected_delivery_date"] = pd.to_datetime(pos["expected_delivery_date"])
        
    # Latest delivered PO date per SKU
    delivered_pos = pos[pos["status"] == "Delivered"]
    if len(delivered_pos) > 0:
        latest_delivered = (
            delivered_pos.groupby(["medication_id", "location_id"])["order_date"]
            .max()
            .rename("latest_delivered_date")
        )
    else:
        latest_delivered = pd.Series(name="latest_delivered_date", dtype="datetime64[ns]")
        
    # Active open POs within recent operational window
    open_pos = pos[
        pos["status"].isin(["In Transit", "Delayed"])
        & (pos["order_date"] >= (snapshot_dt - timedelta(days=recent_po_window_days)))
    ].copy()
    
    open_pos = open_pos.merge(latest_delivered, on=["medication_id", "location_id"], how="left")
    # Only keep open POs that have not been superseded by a subsequent delivered order
    open_pos = open_pos[
        open_pos["latest_delivered_date"].isna()
        | (open_pos["order_date"] >= open_pos["latest_delivered_date"])
    ].copy()
    
    open_pos["days_to_deliv"] = (open_pos["expected_delivery_date"] - snapshot_dt).dt.days
    
    if len(open_pos) > 0:
        po_agg = open_pos.groupby(["medication_id", "location_id"]).apply(
            lambda g: pd.Series({
                "active_po_count": len(g),
                "active_po_qty": g["quantity_ordered"].sum(),
                "nearest_po_days": g["days_to_deliv"].min(),
                "nearest_po_id": g.sort_values("days_to_deliv").iloc[0]["po_id"],
                "nearest_po_status": g.sort_values("days_to_deliv").iloc[0]["status"],
                "has_delayed_po": (g["status"] == "Delayed").any(),
                "in_transit_ontime_qty": g[g["status"] == "In Transit"]["quantity_ordered"].sum(),
                "in_transit_nearest_days": (
                    g[g["status"] == "In Transit"]["days_to_deliv"].min()
                    if (g["status"] == "In Transit").any()
                    else 999
                )
            }),
            include_groups=False
        ).reset_index()
    else:
        po_agg = pd.DataFrame(columns=[
            "medication_id",
            "location_id",
            "active_po_count",
            "active_po_qty",
            "nearest_po_days",
            "nearest_po_id",
            "nearest_po_status",
            "has_delayed_po",
            "in_transit_ontime_qty",
            "in_transit_nearest_days"
        ])
        
    return po_agg
