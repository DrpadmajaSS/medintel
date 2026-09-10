"""
Supply Engine: Simulates suppliers catalog, supplier disruption events,
lead times, and purchase order lifecycles.
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from .config import (
    LOCATIONS_CATALOG,
    MEDICATIONS_CATALOG,
    SCENARIO_DEFINITIONS,
    SIMULATION_DAYS,
    SIMULATION_END_DATE,
    SIMULATION_START_DATE,
    SUPPLIERS_MASTER,
)
from .models import PurchaseOrder, Supplier, SupplierEvent


class SupplyEngine:
    def __init__(self, random_seed: int = 42):
        self.rng = np.random.default_rng(random_seed)

    def generate_suppliers_catalog(self) -> Tuple[List[Supplier], Dict[str, List[str]]]:
        """
        Generate supplier-to-medication mappings.
        Returns:
            - List of Supplier dataclass instances (table: suppliers.csv)
            - Mapping of medication_id -> list of supplier_ids (primary and backup)
        """
        suppliers_list: List[Supplier] = []
        med_to_suppliers: Dict[str, List[str]] = {}

        # Index suppliers by specialty
        specialty_to_suppliers: Dict[str, List[dict]] = {}
        for s in SUPPLIERS_MASTER:
            for spec in s["specialties"]:
                specialty_to_suppliers.setdefault(spec, []).append(s)

        general_suppliers = [s for s in SUPPLIERS_MASTER if "General Hospital Formulary" in s["specialties"] or "Intravenous Fluids" in s["specialties"]]
        if not general_suppliers:
            general_suppliers = SUPPLIERS_MASTER

        for med in MEDICATIONS_CATALOG:
            med_id = med["medication_id"]
            med_class = med["therapeutic_class"]

            # Match suppliers with matching specialty or fall back to general
            matching = specialty_to_suppliers.get(med_class, general_suppliers)
            if not matching:
                matching = SUPPLIERS_MASTER

            # Choose primary and secondary suppliers
            if med_id == "MED001":
                primary_sup = next(s for s in SUPPLIERS_MASTER if s["supplier_id"] == "SUP001")
            elif med_id == "MED057":
                primary_sup = next(s for s in SUPPLIERS_MASTER if s["supplier_id"] == "SUP008")
            elif med_id == "MED021":
                primary_sup = next(s for s in SUPPLIERS_MASTER if s["supplier_id"] == "SUP002")
            else:
                primary_idx = int(self.rng.choice(len(matching)))
                primary_sup = matching[primary_idx]

            # Choose secondary supplier if available
            secondary_candidates = [s for s in SUPPLIERS_MASTER if s["supplier_id"] != primary_sup["supplier_id"]]
            if med_id == "MED057":
                secondary_sup = next(s for s in SUPPLIERS_MASTER if s["supplier_id"] == "SUP005")
            else:
                sec_idx = int(self.rng.integers(0, len(secondary_candidates)))
                secondary_sup = secondary_candidates[sec_idx]

            assigned_suppliers = [primary_sup]
            if med_id == "MED057" or self.rng.random() < 0.70:  # 70% of medications have a secondary supplier contract
                assigned_suppliers.append(secondary_sup)

            med_to_suppliers[med_id] = [s["supplier_id"] for s in assigned_suppliers]

            for s in assigned_suppliers:
                std_lt = s["base_lead_time"] + int(self.rng.choice([-1, 0, 1]))
                std_lt = max(2, min(14, std_lt))
                cur_lt = std_lt

                # Scenario 5 specific override: SUP008 with MED057 has current lead time surged to 25 days
                if s["supplier_id"] == "SUP008" and med_id == "MED057":
                    cur_lt = 25

                rel_score = round(float(s["base_reliability"] + self.rng.normal(0, 0.01)), 2)
                rel_score = max(0.70, min(0.99, rel_score))

                sup_obj = Supplier(
                    supplier_id=s["supplier_id"],
                    supplier_name=s["supplier_name"],
                    medication_id=med_id,
                    standard_lead_time_days=std_lt,
                    current_lead_time_days=cur_lt,
                    reliability_score=rel_score,
                )
                suppliers_list.append(sup_obj)

        return suppliers_list, med_to_suppliers

    def generate_supplier_events(self) -> List[SupplierEvent]:
        """
        Generate realistic historical and active supply chain disruption events.
        """
        events: List[SupplierEvent] = []
        event_counter = 1001

        # Scenario 1 Event: Norepinephrine delay from SUP001
        # Event date: 2026-08-16 (15 days before simulation end)
        s1_date = date(2026, 8, 16).isoformat()
        events.append(
            SupplierEvent(
                event_id=f"EVT-{event_counter}",
                supplier_id="SUP001",
                medication_id="MED001",
                event_date=s1_date,
                event_type="Transportation Delay",
                delay_days=12,
                description="Regional freight hub cryogenic storage disruption and carrier line-haul delay affecting Norepinephrine distribution.",
            )
        )
        event_counter += 1

        # Scenario 5 Event: Insulin Glargine packaging disruption from SUP008
        # Event date: 2026-08-10 (21 days before simulation end)
        s5_date = date(2026, 8, 10).isoformat()
        events.append(
            SupplierEvent(
                event_id=f"EVT-{event_counter}",
                supplier_id="SUP008",
                medication_id="MED057",
                event_date=s5_date,
                event_type="Packaging Line Disruption",
                delay_days=20,
                description="Critical automated secondary packaging machinery failure at central production facility resulting in 20-day shipment delay.",
            )
        )
        event_counter += 1

        # General historical / background events across the 365 days
        event_types = [
            ("Raw Material Shortage", "Active Pharmaceutical Ingredient (API) synthesis yield shortfall delayed batch release.", 8, 20),
            ("Regulatory Inspection Hold", "Routine cGMP inspection follow-up audit paused fill-finish lot releases.", 10, 25),
            ("Port Congestion", "Intermodal maritime container congestion delayed imported precursor chemicals.", 5, 14),
            ("Quality Recall Hold", "Precautionary quarantine for particulate matter verification cleared after secondary testing.", 7, 18),
            ("Demand Surge Allocation", "National regional surge triggered distributor allocation caps of 70% order fulfillment.", 4, 12),
            ("Facility Maintenance", "Scheduled HVAC and cleanroom annual re-certification temporarily suspended dispatch.", 3, 7),
        ]

        # Generate ~25-35 background historical events spread over the year
        num_bg_events = int(self.rng.integers(25, 36))
        for _ in range(num_bg_events):
            random_day_offset = int(self.rng.integers(15, SIMULATION_DAYS - 20))
            evt_date = (SIMULATION_START_DATE + timedelta(days=random_day_offset)).isoformat()

            # Random supplier and medication
            med_idx = int(self.rng.integers(0, len(MEDICATIONS_CATALOG)))
            med = MEDICATIONS_CATALOG[med_idx]
            med_id = med["medication_id"]

            sup_idx = int(self.rng.integers(0, len(SUPPLIERS_MASTER)))
            sup = SUPPLIERS_MASTER[sup_idx]
            sup_id = sup["supplier_id"]

            etype_idx = int(self.rng.integers(0, len(event_types)))
            etype, edesc, min_d, max_d = event_types[etype_idx]
            delay = int(self.rng.integers(min_d, max_d + 1))

            events.append(
                SupplierEvent(
                    event_id=f"EVT-{event_counter}",
                    supplier_id=sup_id,
                    medication_id=med_id,
                    event_date=evt_date,
                    event_type=etype,
                    delay_days=delay,
                    description=f"{edesc} Impacting {med['generic_name']}.",
                )
            )
            event_counter += 1

        # Sort chronologically
        events.sort(key=lambda x: x.event_date)
        return events
