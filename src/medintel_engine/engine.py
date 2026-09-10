"""
Master MedIntel AI Risk Intelligence Engine Orchestrator.
Coordinates dataset loading, feature signal extraction, stockout forecasting,
risk calculation, and generation of the structured production output schema.
"""

from datetime import datetime
from typing import Optional, Union
import pandas as pd

from medintel_engine.config import RiskEngineConfig
from medintel_engine.data_loader import DataLoader, MedIntelRawData
from medintel_engine.signals.utilization_signals import extract_utilization_signals
from medintel_engine.signals.supply_signals import extract_supply_signals
from medintel_engine.signals.pipeline_signals import extract_pipeline_signals
from medintel_engine.signals.inventory_signals import extract_inventory_signals
from medintel_engine.signals.expiry_signals import extract_expiry_signals
from medintel_engine.risk_calculator import RiskCalculator


class MedIntelRiskEngine:
    """End-to-end Risk Intelligence Engine for medication supply-chain and operational risk."""
    
    OUTPUT_COLUMNS = [
        "medication_id",
        "location_id",
        "risk_score",
        "risk_level",
        "predicted_stockout_date",
        "days_to_stockout",
        "primary_risk_factors",
        "contributing_factors",
        "mitigating_factors",
        "confidence",
        "recommended_review"
    ]
    
    def __init__(self, config: Optional[RiskEngineConfig] = None):
        self.config = config or RiskEngineConfig()
        self.calculator = RiskCalculator(self.config)
        
    def run_assessment(
        self,
        raw_data: Union[MedIntelRawData, str] = "data/raw",
        snapshot_date: Optional[Union[str, datetime]] = None
    ) -> pd.DataFrame:
        """
        Executes the full risk assessment pipeline across all medication-location pairs.
        
        Args:
          raw_data: MedIntelRawData instance or path string to raw data directory
          snapshot_date: Specific snapshot date (defaults to max date in inventory.csv)
          
        Returns:
          pd.DataFrame matching the production MedIntel output schema.
        """
        if isinstance(raw_data, str):
            loader = DataLoader(raw_data)
            data = loader.load_all()
        else:
            data = raw_data
            
        # Determine snapshot date
        if snapshot_date is None:
            snapshot_dt = pd.to_datetime(data.inventory["snapshot_date"].max())
        elif isinstance(snapshot_date, str):
            snapshot_dt = datetime.strptime(snapshot_date, "%Y-%m-%d")
        else:
            snapshot_dt = snapshot_date
            
        # 1. Extract Feature Signals
        util_signals = extract_utilization_signals(data.utilization_daily, snapshot_dt)
        primary_sups, alt_sups = extract_supply_signals(
            data.suppliers,
            data.supplier_events,
            snapshot_dt,
            recent_events_window_days=self.config.recent_events_window_days
        )
        pipeline_signals = extract_pipeline_signals(
            data.purchase_orders,
            snapshot_dt,
            recent_po_window_days=self.config.recent_po_window_days
        )
        inv_signals = extract_inventory_signals(
            data.inventory,
            snapshot_dt,
            surplus_dos_threshold=self.config.surplus_dos_threshold,
            surplus_qoh_threshold=self.config.surplus_qoh_threshold
        )
        expiry_signals = extract_expiry_signals(
            data.expiry_lots,
            snapshot_dt,
            expiry_horizon_days=self.config.expiry_horizon_days
        )
        
        # 2. Join into Master SKU Evaluation Matrix
        df_master = inv_signals.merge(data.medications, on="medication_id", how="left")
        df_master = df_master.merge(data.locations, on="location_id", how="left")
        df_master = df_master.merge(util_signals, on=["medication_id", "location_id"], how="left")
        df_master = df_master.merge(primary_sups, on="medication_id", how="left")
        df_master = df_master.merge(alt_sups, on="medication_id", how="left")
        df_master = df_master.merge(pipeline_signals, on=["medication_id", "location_id"], how="left")
        df_master = df_master.merge(expiry_signals, on=["medication_id", "location_id"], how="left")
        
        # Attach surplus location names (only for sister facilities)
        loc_names = data.locations.set_index("location_id")["location_name"].to_dict()
        df_master["surplus_loc_name"] = df_master.apply(
            lambda r: loc_names.get(r["surplus_loc_id"]) if (pd.notnull(r["surplus_loc_id"]) and r["surplus_loc_id"] != r["location_id"]) else None,
            axis=1
        )
        
        # 3. Compute Risk for all SKUs
        results = []
        for _, row in df_master.iterrows():
            eval_res = self.calculator.evaluate_sku(row, snapshot_dt)
            results.append(eval_res)
            
        df_results = pd.DataFrame(results)
        
        # 4. Clean and Order Production Schema
        df_results = df_results[self.OUTPUT_COLUMNS].copy()
        
        return df_results
