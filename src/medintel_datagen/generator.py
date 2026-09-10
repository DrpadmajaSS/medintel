"""
Main Orchestrator for MedIntel Synthetic Healthcare Dataset Generation.
"""

import os
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd

from .config import (
    LOCATIONS_CATALOG,
    MEDICATIONS_CATALOG,
    SIMULATION_END_DATE,
)
from .inventory_engine import InventoryEngine
from .lot_engine import LotEngine
from .models import Location, Medication
from .scenario_injector import ScenarioInjector
from .supply_engine import SupplyEngine
from .utilization_engine import UtilizationEngine


class MedIntelDataGenerator:
    def __init__(self, random_seed: int = 42, output_dir: str = "data/raw"):
        self.random_seed = random_seed
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.util_engine = UtilizationEngine(random_seed=self.random_seed)
        self.supply_engine = SupplyEngine(random_seed=self.random_seed)
        self.inv_engine = InventoryEngine(random_seed=self.random_seed)
        self.lot_engine = LotEngine(random_seed=self.random_seed)

    def generate_all(self) -> Dict[str, pd.DataFrame]:
        """
        Executes the entire generation pipeline and saves all CSVs to output_dir.
        Returns a dictionary of generated DataFrames.
        """
        print(f"🚀 Initializing MedIntel Data Generator (Seed: {self.random_seed})...")

        # 1. Medications Master
        print("  [1/9] Generating medications master catalog...")
        medications_data = [
            Medication(
                medication_id=m["medication_id"],
                generic_name=m["generic_name"],
                strength=m["strength"],
                dosage_form=m["dosage_form"],
                unit_of_measure=m["unit_of_measure"],
                therapeutic_class=m["therapeutic_class"],
                unit_cost=m["unit_cost"],
                criticality=m["criticality"],
            ).__dict__
            for m in MEDICATIONS_CATALOG
        ]
        medications_df = pd.DataFrame(medications_data)

        # 2. Locations Master
        print("  [2/9] Generating locations master catalog...")
        locations_data = [
            Location(
                location_id=l["location_id"],
                location_name=l["location_name"],
                location_type=l["location_type"],
                region=l["region"],
            ).__dict__
            for l in LOCATIONS_CATALOG
        ]
        locations_df = pd.DataFrame(locations_data)

        # 3. Suppliers Catalog & Disruption Events
        print("  [3/9] Generating suppliers catalog & disruption events...")
        suppliers_list, med_to_suppliers = self.supply_engine.generate_suppliers_catalog()
        suppliers_df = pd.DataFrame([s.__dict__ for s in suppliers_list])

        supplier_events_list = self.supply_engine.generate_supplier_events()
        supplier_events_df = pd.DataFrame([e.__dict__ for e in supplier_events_list])

        # 4. Daily Utilization Time Series (12 months)
        print("  [4/9] Simulating daily medication utilization (365 days x 75 meds x 7 locs)...")
        activity_map = self.util_engine.generate_patient_activity_indices()
        _, utilization_df = self.util_engine.generate_daily_utilization(activity_map)

        # 5. Closed-Loop Daily Inventory & Purchase Orders Simulation
        print("  [5/9] Simulating closed-loop inventory snapshots & purchase orders...")
        inventory_snapshots, purchase_orders = self.inv_engine.simulate_inventory_and_orders(
            utilization_df=utilization_df,
            suppliers=suppliers_list,
            supplier_events=supplier_events_list,
        )
        inventory_df = pd.DataFrame([s.__dict__ for s in inventory_snapshots])
        purchase_orders_df = pd.DataFrame([p.__dict__ for p in purchase_orders])

        # 6. Expiry Lots Generation
        print("  [6/9] Generating active expiry lots and batch reconciliation...")
        final_date_str = SIMULATION_END_DATE.isoformat()
        final_snapshots = [s for s in inventory_snapshots if s.snapshot_date == final_date_str]
        expiry_lots = self.lot_engine.generate_expiry_lots(final_snapshots)
        expiry_lots_df = pd.DataFrame([l.__dict__ for l in expiry_lots])

        # 7. Ground Truth Benchmark Scenarios
        print("  [7/9] Injecting ground truth evaluation scenarios...")
        ground_truth = ScenarioInjector.generate_ground_truth()
        ground_truth_df = pd.DataFrame([g.__dict__ for g in ground_truth])

        # Export all to CSV
        print("  [8/9] Exporting CSV artifacts...")
        dfs = {
            "medications.csv": medications_df,
            "locations.csv": locations_df,
            "suppliers.csv": suppliers_df,
            "inventory.csv": inventory_df,
            "utilization_daily.csv": utilization_df,
            "purchase_orders.csv": purchase_orders_df,
            "supplier_events.csv": supplier_events_df,
            "expiry_lots.csv": expiry_lots_df,
            "ground_truth.csv": ground_truth_df,
        }

        for filename, df in dfs.items():
            csv_path = self.output_dir / filename
            df.to_csv(csv_path, index=False)
            print(f"    ✓ Wrote {filename} ({len(df):,} rows)")

        print("  [9/9] Generation complete! All datasets persisted.")
        return dfs
