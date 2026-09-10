"""
Data Loader for MedIntel AI Risk Intelligence Engine.
Loads, validates, and standardizes multi-table production datasets.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd


@dataclass
class MedIntelRawData:
    """Container holding loaded pandas DataFrames for all raw datasets."""
    medications: pd.DataFrame
    locations: pd.DataFrame
    suppliers: pd.DataFrame
    inventory: pd.DataFrame
    utilization_daily: pd.DataFrame
    purchase_orders: pd.DataFrame
    supplier_events: pd.DataFrame
    expiry_lots: pd.DataFrame


class DataLoader:
    """Handles dataset loading and basic type sanitization."""
    
    REQUIRED_FILES = [
        "medications.csv",
        "locations.csv",
        "suppliers.csv",
        "inventory.csv",
        "utilization_daily.csv",
        "purchase_orders.csv",
        "supplier_events.csv",
        "expiry_lots.csv"
    ]
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = data_dir
        self._validate_dir()
        
    def _validate_dir(self) -> None:
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"Data directory '{self.data_dir}' does not exist.")
        for fname in self.REQUIRED_FILES:
            fpath = os.path.join(self.data_dir, fname)
            if not os.path.exists(fpath):
                raise FileNotFoundError(f"Required dataset file '{fpath}' is missing.")
                
    def load_all(self) -> MedIntelRawData:
        """Loads all CSV datasets into memory with optimized dtypes."""
        meds = pd.read_csv(os.path.join(self.data_dir, "medications.csv"))
        locs = pd.read_csv(os.path.join(self.data_dir, "locations.csv"))
        sups = pd.read_csv(os.path.join(self.data_dir, "suppliers.csv"))
        inv = pd.read_csv(os.path.join(self.data_dir, "inventory.csv"))
        util = pd.read_csv(os.path.join(self.data_dir, "utilization_daily.csv"))
        pos = pd.read_csv(os.path.join(self.data_dir, "purchase_orders.csv"))
        events = pd.read_csv(os.path.join(self.data_dir, "supplier_events.csv"))
        lots = pd.read_csv(os.path.join(self.data_dir, "expiry_lots.csv"))
        
        # Standardize date types
        inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"])
        util["date"] = pd.to_datetime(util["date"])
        pos["order_date"] = pd.to_datetime(pos["order_date"])
        pos["expected_delivery_date"] = pd.to_datetime(pos["expected_delivery_date"])
        pos["actual_delivery_date"] = pd.to_datetime(pos["actual_delivery_date"])
        events["event_date"] = pd.to_datetime(events["event_date"])
        lots["manufacture_date"] = pd.to_datetime(lots["manufacture_date"])
        lots["expiry_date"] = pd.to_datetime(lots["expiry_date"])
        
        return MedIntelRawData(
            medications=meds,
            locations=locs,
            suppliers=sups,
            inventory=inv,
            utilization_daily=util,
            purchase_orders=pos,
            supplier_events=events,
            expiry_lots=lots
        )
