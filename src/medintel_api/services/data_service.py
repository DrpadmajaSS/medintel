"""
Thread-safe, in-memory cached data service for MedIntel API.
Pre-loads synthetic datasets and pre-computes risk assessments for sub-10ms response times.
"""

import threading
from typing import Optional, Dict, Any, List
import pandas as pd

from medintel_engine.config import RiskEngineConfig
from medintel_engine.data_loader import DataLoader, MedIntelRawData
from medintel_engine.engine import MedIntelRiskEngine
from medintel_api.config import settings


class DataService:
    """Singleton service providing thread-safe, fast cached data access."""
    
    _instance: Optional["DataService"] = None
    _lock: threading.RLock = threading.RLock()
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or settings.data_dir
        self.raw_data: Optional[MedIntelRawData] = None
        self.risk_assessments_df: Optional[pd.DataFrame] = None
        self.snapshot_date_str: str = ""
        self.snapshot_dt: Optional[pd.Timestamp] = None
        
        # Fast lookup indexes
        self.medications_by_id: Dict[str, Dict[str, Any]] = {}
        self.locations_by_id: Dict[str, Dict[str, Any]] = {}
        self.assessments_by_sku: Dict[tuple, Dict[str, Any]] = {}
        self.assessments_by_med: Dict[str, List[Dict[str, Any]]] = {}
        self.assessments_by_loc: Dict[str, List[Dict[str, Any]]] = {}
        
        self.engine = MedIntelRiskEngine(config=RiskEngineConfig())
        self.reload()
        
    @classmethod
    def get_instance(cls, data_dir: Optional[str] = None) -> "DataService":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(data_dir=data_dir)
        return cls._instance
        
    def reload(self) -> None:
        """Reloads raw data and recalculates risk assessments in memory."""
        with self._lock:
            loader = DataLoader(self.data_dir)
            self.raw_data = loader.load_all()
            
            # Determine latest snapshot date
            self.snapshot_dt = self.raw_data.inventory["snapshot_date"].max()
            self.snapshot_date_str = self.snapshot_dt.strftime("%Y-%m-%d")
            
            # Run risk engine to get baseline assessments
            self.risk_assessments_df = self.engine.run_assessment(
                raw_data=self.raw_data,
                snapshot_date=self.snapshot_dt
            )
            
            # Enrich assessments with medication & location metadata for fast queries
            meds_dict = self.raw_data.medications.set_index("medication_id").to_dict(orient="index")
            locs_dict = self.raw_data.locations.set_index("location_id").to_dict(orient="index")
            
            self.medications_by_id = meds_dict
            self.locations_by_id = locs_dict
            
            # Get latest inventory by (med_id, loc_id)
            latest_inv = self.raw_data.inventory[
                self.raw_data.inventory["snapshot_date"] == self.snapshot_dt
            ].set_index(["medication_id", "location_id"]).to_dict(orient="index")
            
            # Utilization 7d/30d moving averages
            util = self.raw_data.utilization_daily
            c7 = self.snapshot_dt - pd.Timedelta(days=7)
            c30 = self.snapshot_dt - pd.Timedelta(days=30)
            u7 = util[util["date"] > c7].groupby(["medication_id", "location_id"])["quantity_used"].mean().to_dict()
            u30 = util[util["date"] > c30].groupby(["medication_id", "location_id"])["quantity_used"].mean().to_dict()
            
            self.assessments_by_sku.clear()
            self.assessments_by_med.clear()
            self.assessments_by_loc.clear()
            
            for _, row in self.risk_assessments_df.iterrows():
                m_id = str(row["medication_id"])
                l_id = str(row["location_id"])
                
                m_meta = meds_dict.get(m_id, {})
                l_meta = locs_dict.get(l_id, {})
                inv_meta = latest_inv.get((m_id, l_id), {})
                
                qoh = float(inv_meta.get("quantity_on_hand", 0.0))
                adu = float(u7.get((m_id, l_id), inv_meta.get("average_daily_usage", 1.0)))
                adu_30 = float(u30.get((m_id, l_id), adu))
                trend_ratio = round(adu / max(adu_30, 0.1), 2)
                
                item_dict = {
                    "medication_id": m_id,
                    "generic_name": m_meta.get("generic_name", m_id),
                    "location_id": l_id,
                    "location_name": l_meta.get("location_name", l_id),
                    "therapeutic_class": m_meta.get("therapeutic_class", "General"),
                    "criticality": m_meta.get("criticality", "Medium"),
                    "risk_score": float(row["risk_score"]),
                    "risk_level": str(row["risk_level"]),
                    "days_of_supply": float(inv_meta.get("days_of_supply", 0.0)),
                    "quantity_on_hand": qoh,
                    "average_daily_usage": round(adu, 1),
                    "trend_ratio": trend_ratio,
                    "predicted_stockout_date": row["predicted_stockout_date"] if pd.notnull(row["predicted_stockout_date"]) else None,
                    "days_to_stockout": float(row["days_to_stockout"]) if pd.notnull(row["days_to_stockout"]) else None,
                    "primary_risk_factors": str(row["primary_risk_factors"]),
                    "contributing_factors": str(row["contributing_factors"]),
                    "mitigating_factors": str(row["mitigating_factors"]),
                    "confidence": float(row["confidence"]),
                    "recommended_review": str(row["recommended_review"])
                }
                
                self.assessments_by_sku[(m_id, l_id)] = item_dict
                self.assessments_by_med.setdefault(m_id, []).append(item_dict)
                self.assessments_by_loc.setdefault(l_id, []).append(item_dict)


def get_data_service() -> DataService:
    """FastAPI dependency for accessing DataService."""
    return DataService.get_instance()
