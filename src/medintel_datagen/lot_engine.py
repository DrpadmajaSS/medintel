"""
Lot Engine: Simulates medication lot numbers, manufacture dates,
expiry dates, and batch quantities.
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from .config import (
    LOCATIONS_CATALOG,
    MEDICATIONS_CATALOG,
    SIMULATION_END_DATE,
)
from .models import ExpiryLot, InventorySnapshot


class LotEngine:
    def __init__(self, random_seed: int = 42):
        self.rng = np.random.default_rng(random_seed)

    def generate_expiry_lots(
        self,
        final_snapshots: List[InventorySnapshot]
    ) -> List[ExpiryLot]:
        """
        Generates realistic expiry lots for active on-hand inventory
        as of the final snapshot date (SIMULATION_END_DATE = 2026-08-31).
        Reconciles lot quantities with quantity_on_hand.
        """
        lots: List[ExpiryLot] = []
        lot_seq = 1000

        # Map (med_id, loc_id) -> snapshot
        snap_map = {(s.medication_id, s.location_id): s for s in final_snapshots}

        for med in MEDICATIONS_CATALOG:
            med_id = med["medication_id"]

            for loc in LOCATIONS_CATALOG:
                loc_id = loc["location_id"]
                snap = snap_map.get((med_id, loc_id))
                qoh = snap.quantity_on_hand if snap else 0

                if qoh <= 0:
                    continue

                # Check Scenario 4: Alteplase at South Ambulatory (LOC007)
                if med_id == "MED039" and loc_id == "LOC007":
                    mfg_date = date(2024, 9, 15).isoformat()
                    # Expiring in 35 days (2026-10-05)
                    exp_date = (SIMULATION_END_DATE + timedelta(days=35)).isoformat()
                    lots.append(
                        ExpiryLot(
                            lot_id=f"LOT-202409-TPA4",
                            medication_id=med_id,
                            location_id=loc_id,
                            quantity=qoh,
                            manufacture_date=mfg_date,
                            expiry_date=exp_date,
                        )
                    )
                    continue

                # Standard distribution: 1 to 2 lots per location
                if qoh <= 40:
                    num_lots = 1
                else:
                    num_lots = 2 if self.rng.random() < 0.65 else 1

                if num_lots == 1:
                    lot_qtys = [qoh]
                else:
                    split_ratio = float(self.rng.uniform(0.4, 0.7))
                    qty1 = int(round(qoh * split_ratio))
                    qty2 = qoh - qty1
                    lot_qtys = [qty1, qty2] if qty2 > 0 else [qoh]

                for l_idx, l_qty in enumerate(lot_qtys):
                    if l_qty <= 0:
                        continue

                    # Manufacture date: 6 to 18 months in the past
                    mfg_days_ago = int(self.rng.integers(120, 540))
                    mfg_d = SIMULATION_END_DATE - timedelta(days=mfg_days_ago)

                    # Shelf life: 18 to 36 months total (expiring 6 to 24 months in the future)
                    shelf_life_days = int(self.rng.integers(540, 1080))
                    exp_d = mfg_d + timedelta(days=shelf_life_days)

                    # Guarantee expiry is well after simulation end date (at least 90 days out)
                    if exp_d <= SIMULATION_END_DATE + timedelta(days=90):
                        exp_d = SIMULATION_END_DATE + timedelta(days=int(self.rng.integers(120, 480)))

                    lot_code = f"LOT-{mfg_d.strftime('%Y%m')}-{lot_seq:04d}"
                    lot_seq += 1

                    lots.append(
                        ExpiryLot(
                            lot_id=lot_code,
                            medication_id=med_id,
                            location_id=loc_id,
                            quantity=l_qty,
                            manufacture_date=mfg_d.isoformat(),
                            expiry_date=exp_d.isoformat(),
                        )
                    )

        # Sort lots by lot_id
        lots.sort(key=lambda x: (x.medication_id, x.location_id, x.expiry_date))
        return lots
