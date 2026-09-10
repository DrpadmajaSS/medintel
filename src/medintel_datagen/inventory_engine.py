"""
Inventory Engine: Closed-loop daily inventory balance simulation,
reorder trigger execution, snapshot persistence, and mathematical consistency.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from .config import (
    LOCATIONS_CATALOG,
    MEDICATIONS_CATALOG,
    SIMULATION_DAYS,
    SIMULATION_END_DATE,
    SIMULATION_START_DATE,
)
from .models import InventorySnapshot, PurchaseOrder, Supplier, SupplierEvent


class InventoryEngine:
    def __init__(self, random_seed: int = 42):
        self.rng = np.random.default_rng(random_seed)
        self.dates = [
            SIMULATION_START_DATE + timedelta(days=i)
            for i in range(SIMULATION_DAYS)
        ]
        self.date_strs = [d.isoformat() for d in self.dates]

    def simulate_inventory_and_orders(
        self,
        utilization_df: pd.DataFrame,
        suppliers: List[Supplier],
        supplier_events: List[SupplierEvent],
    ) -> Tuple[List[InventorySnapshot], List[PurchaseOrder]]:
        """
        Runs the daily closed-loop inventory simulation across 365 days.
        Generates daily inventory snapshots and purchase orders.
        """
        # Map (med_id, sup_id) -> Supplier object
        supplier_map: Dict[Tuple[str, str], Supplier] = {
            (s.medication_id, s.supplier_id): s for s in suppliers
        }

        # Map med_id -> list of supplier objects
        med_to_sups: Dict[str, List[Supplier]] = {}
        for s in suppliers:
            med_to_sups.setdefault(s.medication_id, []).append(s)

        # Index supplier events by (supplier_id, medication_id)
        event_map: Dict[Tuple[str, str], List[SupplierEvent]] = {}
        for evt in supplier_events:
            event_map.setdefault((evt.supplier_id, evt.medication_id), []).append(evt)

        # Pre-pivot daily utilization into a fast lookup table
        util_dict = (
            utilization_df.set_index(["medication_id", "location_id", "date"])["quantity_used"]
            .to_dict()
        )

        all_inventory_snapshots: List[InventorySnapshot] = []
        all_purchase_orders: List[PurchaseOrder] = []
        po_counter = 10001

        # Track scheduled future deliveries: delivery_date -> list of (med_id, loc_id, qty)
        scheduled_deliveries: Dict[str, List[Tuple[str, str, int]]] = {}

        # Track pending PO per (med_id, loc_id)
        has_pending_order: Dict[Tuple[str, str], bool] = {}

        # Initialize base state for each (med, loc)
        current_inventory: Dict[Tuple[str, str], int] = {}
        historical_usage: Dict[Tuple[str, str], List[int]] = {}

        # Set initial inventory balances
        for med in MEDICATIONS_CATALOG:
            med_id = med["medication_id"]
            base_usage = med["base_daily_usage_mean"]

            for loc in LOCATIONS_CATALOG:
                loc_id = loc["location_id"]
                size_mult = loc["size_multiplier"]

                # Base starting inventory: ~22 to 30 days of initial demand
                initial_qoh = int(max(15, base_usage * size_mult * self.rng.integers(22, 32)))

                # Scenario 4 initialization (Alteplase at LOC007): Outpatient center starts with 280 units batch
                if med_id == "MED039" and loc_id == "LOC007":
                    initial_qoh = 280

                # Scenario 3 initialization (Dexmedetomidine at LOC001): High volume center
                elif med_id == "MED008" and loc_id == "LOC001":
                    initial_qoh = 800

                # Scenario 1 initialization (Norepinephrine at LOC006): Trauma center
                elif med_id == "MED001" and loc_id == "LOC006":
                    initial_qoh = 400

                # Scenario 6 initialization (Vancomycin at LOC004)
                elif med_id == "MED021" and loc_id == "LOC004":
                    initial_qoh = 250

                current_inventory[(med_id, loc_id)] = initial_qoh
                historical_usage[(med_id, loc_id)] = []
                has_pending_order[(med_id, loc_id)] = False

        # Run day-by-day simulation
        for day_idx, cur_date in enumerate(self.dates):
            date_str = cur_date.isoformat()

            # 1. Ingest arriving shipments scheduled for today
            if date_str in scheduled_deliveries:
                for med_id, loc_id, qty_recv in scheduled_deliveries[date_str]:
                    current_inventory[(med_id, loc_id)] += qty_recv
                    has_pending_order[(med_id, loc_id)] = False

            # Process each medication & location
            for med in MEDICATIONS_CATALOG:
                med_id = med["medication_id"]
                for loc in LOCATIONS_CATALOG:
                    loc_id = loc["location_id"]

                    # 2. Ingest daily consumption
                    daily_used = util_dict.get((med_id, loc_id, date_str), 0)
                    historical_usage[(med_id, loc_id)].append(daily_used)

                    # Update on-hand inventory (floor at 0)
                    qoh = current_inventory[(med_id, loc_id)]
                    qoh = max(0, qoh - daily_used)
                    current_inventory[(med_id, loc_id)] = qoh

                    # 3. Compute rolling average daily usage (trailing 14 days)
                    past_usage = historical_usage[(med_id, loc_id)][-14:]
                    avg_daily_usage = float(np.mean(past_usage))
                    avg_daily_usage = max(0.1, round(avg_daily_usage, 2))

                    # 4. Compute days of supply (mathematically exact)
                    days_of_supply = round(qoh / avg_daily_usage, 1)

                    # 5. Determine reorder level
                    sups = med_to_sups.get(med_id, [])
                    primary_sup = sups[0] if sups else None
                    std_lead_time = primary_sup.standard_lead_time_days if primary_sup else 5

                    safety_days = 8
                    reorder_level = int(np.ceil(avg_daily_usage * (std_lead_time + safety_days)))
                    reorder_level = max(5, reorder_level)

                    # Create daily snapshot
                    inv_id = f"INV-{cur_date.strftime('%Y%m%d')}-{med_id}-{loc_id}"
                    snapshot = InventorySnapshot(
                        inventory_id=inv_id,
                        medication_id=med_id,
                        location_id=loc_id,
                        snapshot_date=date_str,
                        quantity_on_hand=qoh,
                        reorder_level=reorder_level,
                        average_daily_usage=avg_daily_usage,
                        days_of_supply=days_of_supply,
                    )
                    all_inventory_snapshots.append(snapshot)

                    # 6. Reorder evaluation logic
                    should_reorder = False

                    # Check standard reorder condition
                    if qoh <= reorder_level and not has_pending_order[(med_id, loc_id)]:
                        should_reorder = True

                    # Handle scenario constraints to create exact ground-truth states on Day 365
                    if med_id == "MED001" and loc_id == "LOC006":
                        # Scenario 1: Suppress orders before day 350 to allow natural burn, place order on day 350 that is delayed
                        if day_idx < (SIMULATION_DAYS - 35):
                            pass  # normal
                        elif day_idx == (SIMULATION_DAYS - 15):
                            should_reorder = True
                        elif day_idx >= (SIMULATION_DAYS - 35):
                            should_reorder = False

                    elif med_id == "MED022" and loc_id == "LOC002":
                        # Scenario 2: Regular order delivered at day 348 to establish 14-16 days DOS
                        if day_idx == (SIMULATION_DAYS - 18):
                            should_reorder = True

                    elif med_id == "MED008" and loc_id == "LOC005":
                        # Scenario 3 (LOC005 deficit): suppress replenishment in last 25 days to reach ~1.8 days of supply
                        if day_idx >= (SIMULATION_DAYS - 25):
                            should_reorder = False

                    elif med_id == "MED008" and loc_id == "LOC001":
                        # Scenario 3 (LOC001 surplus): inject a bulk stock arrival around day 335
                        if day_idx == (SIMULATION_DAYS - 30):
                            should_reorder = True

                    elif med_id == "MED039" and loc_id == "LOC007":
                        # Scenario 4: No reorders at low-velocity site holding near-expiry lot
                        should_reorder = False

                    elif med_id == "MED021" and loc_id == "LOC004":
                        # Scenario 6: Suppress reorders from day 335, order on day 361 arriving on 2026-09-01
                        if day_idx < (SIMULATION_DAYS - 30):
                            pass  # normal
                        elif day_idx == (SIMULATION_DAYS - 4):
                            should_reorder = True
                        elif day_idx >= (SIMULATION_DAYS - 30):
                            should_reorder = False

                    if should_reorder and primary_sup is not None:
                        has_pending_order[(med_id, loc_id)] = True

                        # Target stock is ~28 days of supply
                        target_stock = int(np.ceil(avg_daily_usage * 28))
                        qty_to_order = max(50, target_stock - qoh)
                        # Round to nearest batch of 10 or 25
                        qty_to_order = int(np.ceil(qty_to_order / 10.0) * 10)

                        if med_id == "MED008" and loc_id == "LOC001" and day_idx == (SIMULATION_DAYS - 30):
                            qty_to_order = 1800  # Scenario 3 surplus batch

                        if med_id == "MED001" and loc_id == "LOC006" and day_idx == (SIMULATION_DAYS - 15):
                            qty_to_order = 600   # Scenario 1 order

                        if med_id == "MED021" and loc_id == "LOC004" and day_idx == (SIMULATION_DAYS - 4):
                            qty_to_order = 500   # Scenario 6 order

                        exp_deliv_date = cur_date + timedelta(days=std_lead_time)

                        # Determine actual lead time and disruptions
                        act_lead_time = std_lead_time

                        # Check for active supplier events
                        events = event_map.get((primary_sup.supplier_id, med_id), [])
                        active_delay = 0
                        for evt in events:
                            evt_d = date.fromisoformat(evt.event_date)
                            # If event occurred within 30 days prior to order
                            if 0 <= (cur_date - evt_d).days <= 35:
                                active_delay = max(active_delay, evt.delay_days)

                        if active_delay > 0:
                            act_lead_time += active_delay
                        else:
                            # Random supplier variation
                            if self.rng.random() > primary_sup.reliability_score:
                                act_lead_time += int(self.rng.integers(1, 4))

                        act_deliv_date = cur_date + timedelta(days=act_lead_time)

                        # Check if delivery falls within the 365-day simulation
                        if act_deliv_date <= SIMULATION_END_DATE:
                            # Delivered during simulation
                            # Small chance of partial delivery (e.g. 5%)
                            if self.rng.random() < 0.05 and active_delay > 0:
                                qty_received = int(qty_to_order * 0.75)
                                po_status = "Partially Delivered"
                            elif act_lead_time > std_lead_time:
                                qty_received = qty_to_order
                                po_status = "Delayed"
                            else:
                                qty_received = qty_to_order
                                po_status = "Delivered"

                            act_deliv_str = act_deliv_date.isoformat()
                            # Schedule delivery into inventory pipeline
                            scheduled_deliveries.setdefault(act_deliv_str, []).append(
                                (med_id, loc_id, qty_received)
                            )
                        else:
                            # Not yet delivered as of simulation end date
                            qty_received = 0
                            act_deliv_str = None

                            if exp_deliv_date < SIMULATION_END_DATE:
                                po_status = "Delayed"
                            else:
                                po_status = "In Transit"

                        po = PurchaseOrder(
                            po_id=f"PO-{po_counter}",
                            medication_id=med_id,
                            location_id=loc_id,
                            supplier_id=primary_sup.supplier_id,
                            order_date=date_str,
                            expected_delivery_date=exp_deliv_date.isoformat(),
                            actual_delivery_date=act_deliv_str,
                            quantity_ordered=qty_to_order,
                            quantity_received=qty_received,
                            status=po_status,
                        )
                        all_purchase_orders.append(po)
                        po_counter += 1

        return all_inventory_snapshots, all_purchase_orders
