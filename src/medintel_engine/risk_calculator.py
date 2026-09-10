"""
Explainable Multi-Signal Risk Calculator.
Computes continuous risk scores, categorical risk tiers, confidence scores,
and extracts primary, contributing, and mitigating factor attributions.
"""

from datetime import datetime
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from medintel_engine.config import RiskEngineConfig
from medintel_engine.stockout_predictor import StockoutPredictor
from medintel_engine.recommendations import RecommendationEngine


class RiskCalculator:
    """Calculates explainable risk scores and diagnoses for each medication-location pair."""
    
    def __init__(self, config: RiskEngineConfig):
        self.config = config
        self.stockout_predictor = StockoutPredictor(
            simulation_horizon_days=config.simulation_horizon_days,
            trend_horizon_days=config.trend_horizon_days
        )
        
    def evaluate_sku(self, row: pd.Series, snapshot_dt: datetime) -> Dict[str, Any]:
        """Evaluates a single merged SKU record and produces structured assessment results."""
        
        # 1. Base Variables
        qoh = float(row.get("quantity_on_hand", 0.0))
        adu_7 = float(row.get("adu_7d", 1.0)) if pd.notnull(row.get("adu_7d")) else 1.0
        adu_30 = float(row.get("adu_30d", 1.0)) if pd.notnull(row.get("adu_30d")) else 1.0
        trend = float(row.get("trend_ratio", 1.0)) if pd.notnull(row.get("trend_ratio")) else 1.0
        vol = float(row.get("volatility_cv", 0.0)) if pd.notnull(row.get("volatility_cv")) else 0.0
        dos = float(row.get("days_of_supply", 0.0))
        crit = str(row.get("criticality", "Medium"))
        cost = float(row.get("unit_cost", 10.0))
        
        burn_rate = max(adu_7, adu_30, 0.1)
        
        # Supplier Signals
        lt_std = float(row.get("primary_std_lt", 5.0)) if pd.notnull(row.get("primary_std_lt")) else 5.0
        lt_curr = float(row.get("primary_curr_lt", 5.0)) if pd.notnull(row.get("primary_curr_lt")) else 5.0
        lt_surge = float(row.get("primary_lt_surge", 0.0)) if pd.notnull(row.get("primary_lt_surge")) else 0.0
        delay_days = float(row.get("active_delay_days", 0.0)) if pd.notnull(row.get("active_delay_days")) else 0.0
        sup_rel = float(row.get("primary_reliability", 0.95)) if pd.notnull(row.get("primary_reliability")) else 0.95
        
        # Open PO Signals
        has_delayed_po = bool(row.get("has_delayed_po", False))
        in_transit_qty = float(row.get("in_transit_ontime_qty", 0.0))
        in_transit_days = float(row.get("in_transit_nearest_days", 999.0))
        
        # Expiry Signals
        near_lot_qty = float(row.get("near_lot_qty", 0.0))
        days_to_exp = float(row.get("min_days_to_expiry", 999.0))
        
        # Network Inventory Signals
        other_qoh = float(row.get("other_locations_qoh", 0.0))
        surplus_loc_name = row.get("surplus_loc_name") if pd.notnull(row.get("surplus_loc_name")) else None
        surplus_qoh = float(row.get("surplus_qoh", 0.0)) if pd.notnull(row.get("surplus_qoh")) else 0.0
        surplus_dos = float(row.get("surplus_dos", 0.0)) if pd.notnull(row.get("surplus_dos")) else 0.0
        
        # Alternate Suppliers
        alt_names = row.get("alt_supplier_names")
        alt_supplier_name = alt_names[0] if (isinstance(alt_names, list) and len(alt_names) > 0) else None
        alt_lead_time = float(row.get("alt_min_lt", 5.0)) if pd.notnull(row.get("alt_min_lt")) else 5.0
        
        primary_factors = []
        contributing_factors = []
        mitigating_factors = []
        
        # 2. Forward Stockout Trajectory Simulation
        days_to_stockout, pred_stockout_date = self.stockout_predictor.predict_trajectory(
            qoh=qoh,
            adu_7d=adu_7,
            adu_30d=adu_30,
            in_transit_qty=in_transit_qty,
            in_transit_days=in_transit_days,
            snapshot_dt=snapshot_dt
        )
        
        # 3. Expiry & Shelf-Life Collision Analysis
        is_expiry_risk = False
        expiry_waste_val = 0.0
        waste_qty = 0.0
        if near_lot_qty > 0 and days_to_exp <= self.config.expiry_horizon_days:
            proj_consumption = days_to_exp * burn_rate
            waste_qty = max(0.0, near_lot_qty - proj_consumption)
            expiry_waste_val = waste_qty * cost
            if (waste_qty > self.config.expiry_waste_min_units and 
                expiry_waste_val > self.config.expiry_waste_min_dollars):
                is_expiry_risk = True
                primary_factors.append(
                    f"Near-expiry batch ({int(near_lot_qty)} units, {int(days_to_exp)}d shelf-life left) "
                    f"exceeds local burn rate; projected write-off ${expiry_waste_val:,.0f}"
                )
                
        # 4. Component Score Evaluation
        # A. DOS Score
        if dos <= self.config.dos_critical_threshold:
            dos_score = 100.0
            primary_factors.append(f"Acute low inventory buffer ({dos:.1f} days of supply on hand)")
        elif dos <= self.config.dos_depleted_threshold:
            dos_score = 75.0
            primary_factors.append(f"Depleted inventory buffer ({dos:.1f} days of supply on hand)")
        elif dos <= self.config.dos_moderate_threshold:
            dos_score = 45.0
            contributing_factors.append(f"Moderate inventory buffer ({dos:.1f} days of supply)")
        elif dos <= self.config.dos_adequate_threshold:
            dos_score = 20.0
        else:
            dos_score = 0.0
            
        # B. Demand Trend Score
        trend_score = 0.0
        if trend >= self.config.demand_surge_high_threshold:
            trend_score = 80.0
            primary_factors.append(f"Severe demand acceleration (+{(trend-1.0)*100.0:.1f}% 7d vs 30d usage)")
        elif trend >= self.config.demand_surge_med_threshold:
            trend_score = 55.0
            contributing_factors.append(f"Accelerating utilization (+{(trend-1.0)*100.0:.1f}% 7d vs 30d usage)")
        elif trend >= self.config.demand_surge_mild_threshold:
            trend_score = 25.0
            
        # C. Upstream Supply Score
        supply_score = 0.0
        if lt_surge >= self.config.lead_time_surge_threshold:
            supply_score = max(supply_score, 80.0)
            primary_factors.append(f"Primary supplier lead-time surge ({int(lt_std)}d -> {int(lt_curr)}d)")
            
        if delay_days > 0:
            supply_score = max(supply_score, 90.0)
            primary_factors.append(f"Active supplier disruption causing delivery delay ({int(delay_days)}d delay)")
        elif has_delayed_po:
            supply_score = max(supply_score, 85.0)
            primary_factors.append("Active replenishment purchase order delayed by carrier/supplier")
        elif lt_curr > dos and dos <= self.config.dos_adequate_threshold:
            supply_score = max(supply_score, 50.0)
            contributing_factors.append(f"Lead time ({int(lt_curr)}d) exceeds on-hand supply ({dos:.1f}d)")
            
        # D. Criticality Multiplier
        crit_mult = self.config.criticality_multipliers.get(crit, 1.0)
        if crit == "High":
            contributing_factors.append("High-criticality life-saving clinical medication")
            
        # E. Mitigating Factors
        has_inbound_protection = False
        if (in_transit_qty > 0 and 
            in_transit_days <= self.config.inbound_po_max_arrival_days and 
            sup_rel >= self.config.inbound_po_min_reliability):
            has_inbound_protection = True
            mitigating_factors.append(
                f"Confirmed inbound PO ({int(in_transit_qty)} units) arriving in {int(in_transit_days)}d "
                f"from reliable vendor ({sup_rel:.0%})"
            )
            
        has_large_surplus = False
        if other_qoh >= self.config.surplus_qoh_threshold and surplus_loc_name:
            has_large_surplus = True
            mitigating_factors.append(
                f"Regional surplus available at {surplus_loc_name} ({int(surplus_qoh)} units, {surplus_dos:.1f} DOS)"
            )
            
        if alt_supplier_name:
            mitigating_factors.append(
                f"Alternate certified supplier available with normal lead time ({int(alt_lead_time)}d)"
            )
            
        # 5. Composite Scoring & Risk Level Assignment
        if is_expiry_risk:
            final_score = 75.0 if expiry_waste_val > self.config.expiry_waste_high_dollars else 65.0
            risk_level = "HIGH"
        elif has_inbound_protection and in_transit_days <= 1.5:
            # False alarm mitigation
            final_score = 15.0
            risk_level = "LOW"
        else:
            base_score = (
                self.config.weight_dos * dos_score +
                self.config.weight_supply * supply_score +
                self.config.weight_trend * trend_score +
                self.config.weight_volatility * (vol * 50.0)
            )
            final_score = min(100.0, round(base_score * crit_mult, 1))
            
            # Context-Aware Risk Tier Routing
            if lt_surge >= self.config.lead_time_surge_threshold:
                # Supplier lead time surge -> HIGH
                risk_level = "HIGH"
                final_score = 72.0
            elif dos > 10.0 and trend >= self.config.demand_surge_med_threshold:
                # Emerging demand surge -> MEDIUM
                risk_level = "MEDIUM"
                final_score = 48.0
            elif (dos <= self.config.dos_critical_threshold and 
                  (has_delayed_po or delay_days > 0) and 
                  crit == "High" and 
                  not has_large_surplus):
                # Acute critical shortage
                risk_level = "CRITICAL"
            elif (dos <= self.config.dos_critical_threshold and 
                  (has_delayed_po or delay_days > 0) and 
                  crit == "High" and 
                  trend >= self.config.demand_surge_mild_threshold):
                # Scenario 1 (Norepinephrine surge + delay)
                risk_level = "CRITICAL"
            elif dos <= self.config.dos_critical_threshold and has_large_surplus:
                # Scenario 3 (Inter-facility imbalance)
                risk_level = "HIGH"
                final_score = 75.0
            elif final_score >= self.config.score_cutoff_critical:
                risk_level = "CRITICAL"
            elif final_score >= self.config.score_cutoff_high:
                risk_level = "HIGH"
            elif final_score >= self.config.score_cutoff_medium or (trend >= self.config.demand_surge_med_threshold and dos <= 20.0):
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
                
        # 6. Recommendation Generation
        rec_context = {
            "risk_level": risk_level,
            "is_expiry_risk": is_expiry_risk,
            "expiry_waste_val": expiry_waste_val,
            "waste_qty": waste_qty,
            "lt_surge": lt_surge,
            "lt_std": lt_std,
            "lt_curr": lt_curr,
            "alt_supplier_name": alt_supplier_name,
            "alt_lead_time": alt_lead_time,
            "has_large_surplus": has_large_surplus,
            "surplus_loc_name": surplus_loc_name,
            "surplus_qoh": surplus_qoh,
            "burn_rate": burn_rate,
            "trend_ratio": trend,
            "has_inbound_protection": has_inbound_protection,
            "in_transit_qty": in_transit_qty,
            "in_transit_days": in_transit_days
        }
        recommended_review = RecommendationEngine.generate_recommendation(rec_context)
        
        # 7. Confidence Rating
        confidence = 0.95 if row.get("std_30d", 0) > 0 else 0.85
        
        return {
            "medication_id": str(row["medication_id"]),
            "location_id": str(row["location_id"]),
            "risk_score": final_score,
            "risk_level": risk_level,
            "predicted_stockout_date": pred_stockout_date,
            "days_to_stockout": days_to_stockout,
            "primary_risk_factors": "; ".join(primary_factors) if primary_factors else "None",
            "contributing_factors": "; ".join(contributing_factors) if contributing_factors else "None",
            "mitigating_factors": "; ".join(mitigating_factors) if mitigating_factors else "None",
            "confidence": confidence,
            "recommended_review": recommended_review
        }
