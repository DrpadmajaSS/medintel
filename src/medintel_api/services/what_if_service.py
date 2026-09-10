"""
Interactive What-If Scenario Simulation Service for MedIntel API.
Performs non-destructive parameter perturbation and dynamic stockout / risk recalculation.
"""

import uuid
from typing import Dict, Any, Optional, List
import pandas as pd

from medintel_engine.config import RiskEngineConfig
from medintel_engine.risk_calculator import RiskCalculator
from medintel_engine.stockout_predictor import StockoutPredictor
from medintel_api.services.data_service import DataService
from medintel_api.schemas.what_if import (
    WhatIfRequest,
    WhatIfBaseline,
    WhatIfScenario,
    WhatIfImpact,
    WhatIfResponse
)


class WhatIfService:
    """Simulates operational perturbations on demand, inventory, and supplier lead times."""
    
    def __init__(self, data_service: DataService):
        self.ds = data_service
        self.config = RiskEngineConfig()
        self.calculator = RiskCalculator(self.config)
        self.predictor = StockoutPredictor(
            simulation_horizon_days=self.config.simulation_horizon_days,
            trend_horizon_days=self.config.trend_horizon_days
        )
        
    def simulate(self, request: WhatIfRequest) -> WhatIfResponse:
        """Executes a non-destructive What-If scenario simulation."""
        
        m_id = request.medication_id
        l_id = request.location_id
        
        # 1. Retrieve baseline state from cache
        sku_key = (m_id, l_id)
        if sku_key not in self.ds.assessments_by_sku:
            raise KeyError(f"Medication '{m_id}' at location '{l_id}' was not found in active formulary.")
            
        base_item = self.ds.assessments_by_sku[sku_key]
        m_meta = self.ds.medications_by_id.get(m_id, {})
        l_meta = self.ds.locations_by_id.get(l_id, {})
        
        raw = self.ds.raw_data
        snapshot_dt = self.ds.snapshot_dt
        
        # Raw inventory row
        inv_row = raw.inventory[
            (raw.inventory["medication_id"] == m_id) & 
            (raw.inventory["location_id"] == l_id) & 
            (raw.inventory["snapshot_date"] == snapshot_dt)
        ]
        qoh_base = float(inv_row.iloc[0]["quantity_on_hand"]) if len(inv_row) > 0 else float(base_item["quantity_on_hand"])
        reorder_lvl = float(inv_row.iloc[0]["reorder_level"]) if len(inv_row) > 0 else 100.0
        
        # Raw utilization metrics
        util = raw.utilization_daily
        c7 = snapshot_dt - pd.Timedelta(days=7)
        c30 = snapshot_dt - pd.Timedelta(days=30)
        u_sku = util[(util["medication_id"] == m_id) & (util["location_id"] == l_id)]
        u7_base = float(u_sku[u_sku["date"] > c7]["quantity_used"].mean()) if len(u_sku) > 0 else 1.0
        u30_base = float(u_sku[u_sku["date"] > c30]["quantity_used"].mean()) if len(u_sku) > 0 else 1.0
        u30_std = float(u_sku[u_sku["date"] > c30]["quantity_used"].std()) if len(u_sku) > 0 else 0.0
        
        # Primary supplier & events
        sups = raw.suppliers[raw.suppliers["medication_id"] == m_id]
        if len(sups) > 0:
            top_sup = sups.sort_values(["standard_lead_time_days", "reliability_score"], ascending=[True, False]).iloc[0]
            sup_std_lt = float(top_sup["standard_lead_time_days"])
            sup_curr_lt = float(top_sup["current_lead_time_days"])
            sup_rel = float(top_sup["reliability_score"])
        else:
            sup_std_lt, sup_curr_lt, sup_rel = 5.0, 5.0, 0.95
            
        # Active open POs
        pos = raw.purchase_orders[
            (raw.purchase_orders["medication_id"] == m_id) &
            (raw.purchase_orders["location_id"] == l_id) &
            (raw.purchase_orders["status"].isin(["In Transit", "Delayed"])) &
            (raw.purchase_orders["order_date"] >= (snapshot_dt - pd.Timedelta(days=30)))
        ]
        in_transit_qty = float(pos[pos["status"] == "In Transit"]["quantity_ordered"].sum()) if len(pos) > 0 else 0.0
        in_transit_days = (
            float((pos[pos["status"] == "In Transit"]["expected_delivery_date"].min() - snapshot_dt).days)
            if len(pos[pos["status"] == "In Transit"]) > 0 else 999.0
        )
        has_delayed_po = (pos["status"] == "Delayed").any() if len(pos) > 0 else False
        
        # Expiry lots
        lots = raw.expiry_lots[
            (raw.expiry_lots["medication_id"] == m_id) &
            (raw.expiry_lots["location_id"] == l_id)
        ].copy()
        lots["days_to_expiry"] = (pd.to_datetime(lots["expiry_date"]) - snapshot_dt).dt.days
        near_lots = lots[lots["days_to_expiry"] <= 60]
        near_lot_qty = float(near_lots["quantity"].sum()) if len(near_lots) > 0 else 0.0
        min_days_to_exp = float(near_lots["days_to_expiry"].min()) if len(near_lots) > 0 else 999.0
        
        # 2. Compute Baseline Model Signals
        base_signals = [
            f"Inventory: {qoh_base:.0f} units ({base_item['days_of_supply']:.1f} DOS)",
            f"Daily Demand: {u7_base:.1f} units/day (Trend: {base_item['trend_ratio']:.2f}x)",
            f"Supplier Lead Time: {sup_curr_lt:.0f} days (Std: {sup_std_lt:.0f}d)"
        ]
        if base_item["primary_risk_factors"] != "None":
            base_signals.append(f"Risk Factors: {base_item['primary_risk_factors']}")
            
        baseline = WhatIfBaseline(
            medication_id=m_id,
            generic_name=base_item["generic_name"],
            location_id=l_id,
            location_name=base_item["location_name"],
            quantity_on_hand=qoh_base,
            average_daily_usage=round(u7_base, 1),
            days_of_supply=base_item["days_of_supply"],
            risk_score=base_item["risk_score"],
            risk_level=base_item["risk_level"],
            days_to_stockout=base_item["days_to_stockout"],
            predicted_stockout_date=base_item["predicted_stockout_date"],
            supplier_lead_time_days=sup_curr_lt,
            key_signals=base_signals
        )
        
        # 3. Apply Perturbations (Non-Destructive In-Memory Simulation)
        d_pct = request.demand_change_percent
        s_delay = max(0.0, request.supplier_delay_days)
        i_pct = request.inventory_change_percent
        transfer_units = request.inventory_transfer_units
        
        # Perturbed values
        qoh_sim = max(0.0, qoh_base * (1.0 + i_pct / 100.0) + transfer_units)
        u7_sim = max(0.1, u7_base * (1.0 + d_pct / 100.0))
        u30_sim = max(0.1, u30_base * (1.0 + d_pct / 100.0))
        dos_sim = round(qoh_sim / max(u7_sim, u30_sim, 0.1), 1)
        
        sup_curr_lt_sim = sup_curr_lt + s_delay
        delay_days_sim = s_delay
        in_transit_days_sim = in_transit_days + s_delay if in_transit_qty > 0 else 999.0
        
        # Simulate stockout with perturbed values
        dts_sim, date_sim = self.predictor.predict_trajectory(
            qoh=qoh_sim,
            adu_7d=u7_sim,
            adu_30d=u30_sim,
            in_transit_qty=in_transit_qty,
            in_transit_days=in_transit_days_sim,
            snapshot_dt=snapshot_dt
        )
        
        # Re-score perturbed SKU with RiskCalculator
        sim_row = pd.Series({
            "medication_id": m_id,
            "location_id": l_id,
            "quantity_on_hand": qoh_sim,
            "days_of_supply": dos_sim,
            "adu_7d": u7_sim,
            "adu_30d": u30_sim,
            "trend_ratio": round(u7_sim / max(u30_sim, 0.1), 2),
            "volatility_cv": round(u30_std / max(u30_sim, 0.1), 2),
            "criticality": m_meta.get("criticality", "Medium"),
            "unit_cost": float(m_meta.get("unit_cost", 10.0)),
            "primary_std_lt": sup_std_lt,
            "primary_curr_lt": sup_curr_lt_sim,
            "primary_lt_surge": max(0.0, sup_curr_lt_sim - sup_std_lt),
            "active_delay_days": delay_days_sim,
            "primary_reliability": sup_rel,
            "has_delayed_po": has_delayed_po or (s_delay > 0),
            "in_transit_ontime_qty": in_transit_qty,
            "in_transit_nearest_days": in_transit_days_sim,
            "near_lot_qty": near_lot_qty,
            "min_days_to_expiry": min_days_to_exp,
            "other_locations_qoh": float(base_item["quantity_on_hand"]) * 2,
            "surplus_loc_name": None,
            "surplus_qoh": 0.0,
            "surplus_dos": 0.0,
            "alt_supplier_names": [],
            "alt_min_lt": sup_std_lt,
            "std_30d": u30_std
        })
        
        sim_eval = self.calculator.evaluate_sku(sim_row, snapshot_dt)
        
        sim_signals = [
            f"Simulated Inventory: {qoh_sim:.0f} units ({dos_sim:.1f} DOS)",
            f"Simulated Daily Demand: {u7_sim:.1f} units/day ({d_pct:+.1f}%)",
            f"Simulated Lead Time: {sup_curr_lt_sim:.0f} days (+{s_delay:.0f}d delay)"
        ]
        if sim_eval["primary_risk_factors"] != "None":
            sim_signals.append(f"Diagnosed Signals: {sim_eval['primary_risk_factors']}")
            
        scenario = WhatIfScenario(
            projected_quantity_on_hand=round(qoh_sim, 1),
            projected_daily_usage=round(u7_sim, 1),
            projected_days_of_supply=dos_sim,
            projected_risk_score=sim_eval["risk_score"],
            projected_risk_level=sim_eval["risk_level"],
            projected_days_to_stockout=dts_sim,
            projected_stockout_date=date_sim,
            projected_supplier_lead_time_days=sup_curr_lt_sim,
            simulated_signals=sim_signals
        )
        
        # 4. Impact Analysis
        delta_dos = round(dos_sim - base_item["days_of_supply"], 1)
        
        if dts_sim is not None and base_item["days_to_stockout"] is not None:
            delta_dts = round(dts_sim - base_item["days_to_stockout"], 1)
        elif dts_sim is not None and base_item["days_to_stockout"] is None:
            delta_dts = round(dts_sim - 60.0, 1)
        elif dts_sim is None and base_item["days_to_stockout"] is not None:
            delta_dts = 999.0  # Stockout prevented!
        else:
            delta_dts = None
            
        delta_score = round(sim_eval["risk_score"] - base_item["risk_score"], 1)
        transition_str = f"{base_item['risk_level']} → {sim_eval['risk_level']}"
        
        # Stockout change description
        if base_item["days_to_stockout"] is not None and dts_sim is None:
            stockout_change = f"Stockout PREVENTED (Previously projected in {base_item['days_to_stockout']:.1f} days)"
        elif base_item["days_to_stockout"] is None and dts_sim is not None:
            stockout_change = f"NEW Stockout Projected in {dts_sim:.1f} days ({date_sim})"
        elif base_item["days_to_stockout"] is not None and dts_sim is not None:
            diff = dts_sim - base_item["days_to_stockout"]
            if diff < 0:
                stockout_change = f"Stockout Accelerated by {abs(diff):.1f} days (Now {dts_sim:.1f}d on {date_sim})"
            elif diff > 0:
                stockout_change = f"Stockout Delayed by {diff:.1f} days (Extended to {dts_sim:.1f}d on {date_sim})"
            else:
                stockout_change = "No change in stockout horizon"
        else:
            stockout_change = "Safe: No stockout projected within 60 days"
            
        # Explanations
        explanation_parts = []
        if d_pct != 0:
            explanation_parts.append(f"Demand change of {d_pct:+.1f}% shifts burn rate from {u7_base:.1f} to {u7_sim:.1f} units/day.")
        if s_delay != 0:
            explanation_parts.append(f"Supplier delivery delay of +{s_delay:.0f} days increases procurement lead time to {sup_curr_lt_sim:.0f} days.")
        if i_pct != 0 or transfer_units != 0:
            explanation_parts.append(f"Inventory adjustments shift on-hand stock by {qoh_sim - qoh_base:+.0f} units.")
        explanation_parts.append(f"Days of Supply changes by {delta_dos:+.1f} days, moving risk score by {delta_score:+.1f} points ({transition_str}).")
        
        explanation = " ".join(explanation_parts)
        
        # Clinical implication
        if sim_eval["risk_level"] in ["CRITICAL", "HIGH"] and base_item["risk_level"] not in ["CRITICAL", "HIGH"]:
            clinical_implication = "URGENT WARNING: Simulated perturbations elevate this medication into high-priority shortage territory requiring advance procurement or lateral transfer."
        elif sim_eval["risk_level"] == "LOW" and base_item["risk_level"] in ["CRITICAL", "HIGH"]:
            clinical_implication = "SUCCESSFUL MITIGATION: Simulated lateral transfer / inventory buffer successfully eliminates critical stockout risk."
        else:
            clinical_implication = sim_eval["recommended_review"]
            
        # Affected locations if transfer source is specified
        affected = []
        if request.transfer_source_location_id and transfer_units > 0:
            src_loc_id = request.transfer_source_location_id
            src_name = self.ds.locations_by_id.get(src_loc_id, {}).get("location_name", src_loc_id)
            affected.append({
                "location_id": src_loc_id,
                "location_name": src_name,
                "impact_type": "Surplus Deduction",
                "units_transferred": transfer_units,
                "note": f"Source facility transfers {transfer_units:.0f} units to {base_item['location_name']}."
            })
            
        impact = WhatIfImpact(
            delta_days_of_supply=delta_dos,
            delta_days_to_stockout=delta_dts,
            delta_risk_score=delta_score,
            risk_level_transition=transition_str,
            stockout_status_change=stockout_change,
            affected_locations=affected,
            explanation=explanation,
            clinical_implication=clinical_implication
        )
        
        return WhatIfResponse(
            simulation_id=f"SIM-{uuid.uuid4().hex[:8].upper()}",
            medication_id=m_id,
            location_id=l_id,
            parameters_applied={
                "demand_change_percent": d_pct,
                "supplier_delay_days": s_delay,
                "inventory_change_percent": i_pct,
                "inventory_transfer_units": transfer_units,
                "transfer_source_location_id": request.transfer_source_location_id
            },
            baseline=baseline,
            scenario=scenario,
            impact=impact
        )
