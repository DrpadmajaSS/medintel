"""
Utilization Engine: Simulates realistic daily medication utilization patterns
across all medications, locations, and time horizons.
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from .config import (
    LOCATIONS_CATALOG,
    MEDICATIONS_CATALOG,
    SIMULATION_DAYS,
    SIMULATION_START_DATE,
)
from .models import UtilizationDaily


class UtilizationEngine:
    def __init__(self, random_seed: int = 42):
        self.rng = np.random.default_rng(random_seed)
        self.dates = [
            SIMULATION_START_DATE + timedelta(days=i)
            for i in range(SIMULATION_DAYS)
        ]
        self.date_strs = [d.isoformat() for d in self.dates]

    def generate_patient_activity_indices(self) -> Dict[Tuple[str, str], float]:
        """
        Generate daily patient activity index (census, acuity, volume factor)
        for each location across the 365 days.
        """
        activity_map: Dict[Tuple[str, str], float] = {}

        for loc in LOCATIONS_CATALOG:
            loc_id = loc["location_id"]
            base_mean = loc["base_activity_mean"]

            for day_idx, d in enumerate(self.dates):
                # Day of week effect (e.g. Sunday=6, Saturday=5)
                # Elective & ambulatory drops on weekends, trauma stays steady
                weekday = d.weekday()
                is_weekend = weekday >= 5

                if loc["location_type"] == "Ambulatory Surgical Center":
                    dow_factor = 0.35 if is_weekend else 1.15
                elif loc["location_type"] == "Trauma Center":
                    dow_factor = 1.12 if is_weekend else 0.98  # Higher trauma on weekends
                elif loc["location_type"] == "Children's Hospital":
                    dow_factor = 0.85 if is_weekend else 1.05
                else:
                    dow_factor = 0.82 if is_weekend else 1.06

                # Seasonal holiday dip in late December (Dec 22-Jan 2)
                holiday_dip = 1.0
                if (d.month == 12 and d.day >= 22) or (d.month == 1 and d.day <= 2):
                    holiday_dip = 0.82

                # Moderate random fluctuation
                noise = self.rng.normal(0, 0.04)

                # Combine factors
                activity_val = max(0.40, round(base_mean * dow_factor * holiday_dip + noise, 3))
                activity_map[(loc_id, d.isoformat())] = activity_val

        return activity_map

    def generate_daily_utilization(
        self,
        activity_map: Dict[Tuple[str, str], float]
    ) -> Tuple[List[UtilizationDaily], pd.DataFrame]:
        """
        Simulate the daily utilization for all (medication, location, day) combinations.
        Returns both a list of dataclass objects and a pandas DataFrame.
        """
        records: List[UtilizationDaily] = []
        raw_rows = []

        # Precompute season factors for dates
        # Winter months: Nov (11), Dec (12), Jan (1), Feb (2)
        # Summer months: Jun (6), Jul (7), Aug (8)
        season_factors = []
        for d in self.dates:
            month = d.month
            if month in [11, 12, 1, 2]:
                season_factors.append(1.45)  # Respiratory/infection surge
            elif month in [6, 7, 8]:
                season_factors.append(0.80)
            else:
                season_factors.append(1.00)

        for med in MEDICATIONS_CATALOG:
            med_id = med["medication_id"]
            base_usage = med["base_daily_usage_mean"]
            pattern = med["demand_pattern"]

            for loc in LOCATIONS_CATALOG:
                loc_id = loc["location_id"]
                size_mult = loc["size_multiplier"]

                # Facility-specific adjustment based on clinical fit
                # e.g., Children's Hospital uses less adult meds, Trauma uses more resuscitation
                specialty_mult = 1.0
                if loc["location_type"] == "Children's Hospital":
                    if med["therapeutic_class"] in ["Obstetric / Labor Induction", "Plasma Volume Expander"]:
                        specialty_mult = 0.15
                    elif med["therapeutic_class"] in ["Bronchodilator", "Antidiabetic / Insulin"]:
                        specialty_mult = 1.30
                    else:
                        specialty_mult = 0.50
                elif loc["location_type"] == "Ambulatory Surgical Center":
                    if med["therapeutic_class"] in ["Vasopressor / Inotrope", "Plasma Volume Expander", "Thrombolytic"]:
                        specialty_mult = 0.10
                    elif med["therapeutic_class"] in ["Local Anesthetic", "General Anesthetic / Sedative", "NSAID"]:
                        specialty_mult = 1.40
                    else:
                        specialty_mult = 0.35
                elif loc["location_type"] == "Trauma Center":
                    if med["therapeutic_class"] in ["Vasopressor / Inotrope", "Emergency / Resuscitation", "Intravenous Fluids", "Thrombolytic"]:
                        specialty_mult = 1.50

                base_loc_demand = max(0.5, base_usage * size_mult * specialty_mult)

                for day_idx, d in enumerate(self.dates):
                    date_str = d.isoformat()
                    activity_idx = activity_map[(loc_id, date_str)]

                    # Compute baseline adjusted demand
                    current_mean = base_loc_demand * activity_idx

                    # Apply specialized pattern trajectories
                    if pattern == "stable":
                        pass  # Standard variation around mean

                    elif pattern == "gradual_increase":
                        # Increases +35% over the 365 days
                        trend_factor = 0.85 + 0.35 * (day_idx / SIMULATION_DAYS)
                        current_mean *= trend_factor

                    elif pattern == "gradual_decrease":
                        # Decreases -30% over the 365 days
                        trend_factor = 1.15 - 0.30 * (day_idx / SIMULATION_DAYS)
                        current_mean *= trend_factor

                    elif pattern == "seasonal_winter":
                        current_mean *= season_factors[day_idx]

                    elif pattern == "surge_scenario" and med_id == "MED001" and loc_id == "LOC006":
                        # Scenario 1: Valley Regional Trauma Center has massive surge in last 30 days
                        if day_idx >= (SIMULATION_DAYS - 30):
                            days_into_surge = day_idx - (SIMULATION_DAYS - 30)
                            surge_mult = 1.0 + 0.85 * min(1.0, (days_into_surge / 18))
                            current_mean *= surge_mult

                    elif pattern == "emerging_risk_scenario" and med_id == "MED022" and loc_id == "LOC002":
                        # Scenario 2: Meropenem at North Suburban ramps up over final 21 days
                        if day_idx >= (SIMULATION_DAYS - 21):
                            days_into_ramp = day_idx - (SIMULATION_DAYS - 21)
                            ramp_mult = 1.0 + 0.95 * (days_into_ramp / 21)
                            current_mean *= ramp_mult

                    elif pattern == "expiry_scenario" and med_id == "MED039" and loc_id == "LOC007":
                        # Scenario 4: Alteplase at Ambulatory Center has very low velocity (~1-2 per week)
                        current_mean = 0.18

                    # Generate daily integer quantity using Poisson distribution with random noise
                    # for realistic clinical variation
                    sampled_qty = int(self.rng.poisson(max(0.01, current_mean)))

                    # Ensure non-negative
                    sampled_qty = max(0, sampled_qty)

                    rec = UtilizationDaily(
                        date=date_str,
                        medication_id=med_id,
                        location_id=loc_id,
                        quantity_used=sampled_qty,
                        patient_activity_index=round(activity_idx, 3),
                    )
                    records.append(rec)
                    raw_rows.append({
                        "date": date_str,
                        "medication_id": med_id,
                        "location_id": loc_id,
                        "quantity_used": sampled_qty,
                        "patient_activity_index": round(activity_idx, 3),
                    })

        df = pd.DataFrame(raw_rows)
        return records, df
