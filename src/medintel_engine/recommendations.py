"""
Clinical & Operational Action Recommendation Engine.
Synthesizes multi-signal risk diagnoses into specific, actionable clinical,
procurement, and lateral inventory rebalancing recommendations.
"""

from typing import Dict, Any, Optional


class RecommendationEngine:
    """Generates context-aware clinical and supply chain recommendations."""
    
    @staticmethod
    def generate_recommendation(context: Dict[str, Any]) -> str:
        """
        Generates actionable review text based on diagnosed risk profile.
        
        Context parameters:
          - risk_level: str ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
          - is_expiry_risk: bool
          - expiry_waste_val: float
          - waste_qty: float
          - lt_surge: float
          - lt_std: float
          - lt_curr: float
          - alt_supplier_name: Optional[str]
          - alt_lead_time: Optional[float]
          - has_large_surplus: bool
          - surplus_loc_name: Optional[str]
          - surplus_qoh: float
          - burn_rate: float
          - trend_ratio: float
          - has_inbound_protection: bool
          - in_transit_qty: float
          - in_transit_days: float
        """
        risk_level = context.get("risk_level", "LOW")
        is_expiry_risk = context.get("is_expiry_risk", False)
        expiry_waste_val = context.get("expiry_waste_val", 0.0)
        waste_qty = context.get("waste_qty", 0.0)
        lt_surge = context.get("lt_surge", 0.0)
        alt_supplier_name = context.get("alt_supplier_name")
        alt_lead_time = context.get("alt_lead_time", 5.0)
        has_large_surplus = context.get("has_large_surplus", False)
        surplus_loc_name = context.get("surplus_loc_name")
        surplus_qoh = context.get("surplus_qoh", 0.0)
        burn_rate = max(context.get("burn_rate", 1.0), 0.1)
        trend_ratio = context.get("trend_ratio", 1.0)
        has_inbound_protection = context.get("has_inbound_protection", False)
        in_transit_qty = context.get("in_transit_qty", 0.0)
        in_transit_days = context.get("in_transit_days", 1.0)
        
        if risk_level == "CRITICAL":
            if has_large_surplus and surplus_loc_name:
                transfer_qty = int(min(surplus_qoh * 0.30, burn_rate * 7.0))
                transfer_qty = max(10, transfer_qty)
                return (
                    f"Declare acute critical shortage, expedite secondary supplier emergency PO, and "
                    f"execute urgent stock transfer of {transfer_qty} units from {surplus_loc_name}."
                )
            else:
                return (
                    "Declare acute critical shortage, expedite secondary supplier emergency PO, and "
                    "implement strict clinical conservation protocols immediately."
                )
                
        elif risk_level == "HIGH":
            if is_expiry_risk:
                return (
                    f"Prevent high-cost drug write-off (${expiry_waste_val:,.0f}): transfer {int(waste_qty)} expiring "
                    f"units to high-volume comprehensive facility for prioritized FIFO utilization."
                )
            elif lt_surge >= 10:
                vendor_text = alt_supplier_name if alt_supplier_name else "certified alternate supplier"
                return (
                    f"Reroute purchase order allocation to {vendor_text} with {int(alt_lead_time)}-day lead time to avoid stockout."
                )
            elif has_large_surplus and surplus_loc_name:
                rebalance_qty = int(min(surplus_qoh * 0.20, burn_rate * 10.0))
                rebalance_qty = max(10, rebalance_qty)
                return (
                    f"Rebalance regional network: initiate lateral transfer of {rebalance_qty} units from {surplus_loc_name} immediately."
                )
            else:
                return "Place expedited replenishment purchase order and monitor daily burn rate closely."
                
        elif risk_level == "MEDIUM":
            if trend_ratio >= 1.25:
                pct = (trend_ratio - 1.0) * 100.0
                return (
                    f"Classify as emerging risk (+{pct:.1f}% demand surge); dynamically adjust safety stock baseline upwards "
                    f"and trigger automated replenishment PO 5 days ahead of schedule."
                )
            else:
                return "Emerging supply vulnerability. Review reorder thresholds and schedule early replenishment order."
                
        else:  # LOW
            if has_inbound_protection:
                return (
                    f"No escalation required; inbound shipment ({int(in_transit_qty)} units) confirmed on schedule "
                    f"arriving in {int(in_transit_days)}d. Maintain standard monitoring."
                )
            else:
                return "Inventory and supply chain parameters within normal operating thresholds. Maintain standard replenishment cycle."
