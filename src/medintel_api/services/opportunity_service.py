"""
Opportunity Service for MedIntel API.
Identifies regional network inventory imbalances, lateral rebalancing pairs (deficit vs surplus),
and near-expiry batch salvage opportunities.
"""

from typing import Optional, List, Dict, Any
import pandas as pd

from medintel_api.services.data_service import DataService
from medintel_api.schemas.opportunities import (
    RedistributionOpportunity,
    ExpiryOpportunity,
    OpportunitiesResponse
)


class OpportunityService:
    """Computes network redistribution pairs and expiry salvage opportunities."""
    
    def __init__(self, data_service: DataService):
        self.ds = data_service
        
    def get_opportunities(self, location_id: Optional[str] = None) -> OpportunitiesResponse:
        """Finds all lateral rebalancing and expiry salvage opportunities across the network."""
        
        redistribution_list: List[RedistributionOpportunity] = []
        expiry_list: List[ExpiryOpportunity] = []
        
        raw = self.ds.raw_data
        meds_dict = self.ds.medications_by_id
        locs_dict = self.ds.locations_by_id
        latest_date = self.ds.snapshot_dt
        
        # 1. Lateral Rebalancing Pairs
        # Look for medications where one facility has low DOS (<= 5.0) and another has surplus DOS (>= 25.0 and QOH >= 200)
        latest_inv = raw.inventory[raw.inventory["snapshot_date"] == latest_date].copy()
        
        # Group by medication_id
        for med_id, grp in latest_inv.groupby("medication_id"):
            med_meta = meds_dict.get(med_id, {})
            cost = float(med_meta.get("unit_cost", 10.0))
            
            deficits = grp[grp["days_of_supply"] <= 5.0]
            surpluses = grp[(grp["days_of_supply"] >= 25.0) & (grp["quantity_on_hand"] >= 100.0)]
            
            if len(deficits) > 0 and len(surpluses) > 0:
                for _, def_row in deficits.iterrows():
                    def_loc_id = def_row["location_id"]
                    if location_id and def_loc_id != location_id:
                        continue
                        
                    # Pick best surplus location (highest QOH)
                    top_surplus = surpluses.sort_values("quantity_on_hand", ascending=False).iloc[0]
                    sur_loc_id = top_surplus["location_id"]
                    
                    if def_loc_id == sur_loc_id:
                        continue
                        
                    def_loc_name = locs_dict.get(def_loc_id, {}).get("location_name", def_loc_id)
                    sur_loc_name = locs_dict.get(sur_loc_id, {}).get("location_name", sur_loc_id)
                    
                    # Calculate recommended transfer quantity: 7-14 days of deficit usage, capped at 30% of surplus
                    def_adu = max(float(def_row["average_daily_usage"]), 1.0)
                    rec_transfer = int(min(float(top_surplus["quantity_on_hand"]) * 0.30, def_adu * 10.0))
                    rec_transfer = max(10, rec_transfer)
                    
                    cost_avoidance = rec_transfer * cost
                    urgency = "HIGH" if def_row["days_of_supply"] <= 2.0 else "MEDIUM"
                    
                    redistribution_list.append(RedistributionOpportunity(
                        medication_id=med_id,
                        generic_name=med_meta.get("generic_name", med_id),
                        therapeutic_class=med_meta.get("therapeutic_class", "General"),
                        unit_cost=cost,
                        deficit_location_id=def_loc_id,
                        deficit_location_name=def_loc_name,
                        deficit_days_of_supply=float(def_row["days_of_supply"]),
                        deficit_quantity_on_hand=float(def_row["quantity_on_hand"]),
                        surplus_location_id=sur_loc_id,
                        surplus_location_name=sur_loc_name,
                        surplus_days_of_supply=float(top_surplus["days_of_supply"]),
                        surplus_quantity_on_hand=float(top_surplus["quantity_on_hand"]),
                        recommended_transfer_units=rec_transfer,
                        estimated_cost_avoidance_usd=round(cost_avoidance, 2),
                        urgency=urgency,
                        action_directive=(
                            f"Initiate urgent intra-network stock transfer of {rec_transfer} units from "
                            f"{sur_loc_name} to {def_loc_name}."
                        )
                    ))
                    
        # 2. Expiry Salvage Opportunities
        lots = raw.expiry_lots.copy()
        lots["days_to_expiry"] = (pd.to_datetime(lots["expiry_date"]) - latest_date).dt.days
        near_lots = lots[lots["days_to_expiry"] <= 90].sort_values("days_to_expiry")
        
        for _, lot_row in near_lots.iterrows():
            m_id = lot_row["medication_id"]
            l_id = lot_row["location_id"]
            if location_id and l_id != location_id:
                continue
                
            m_meta = meds_dict.get(m_id, {})
            l_meta = locs_dict.get(l_id, {})
            cost = float(m_meta.get("unit_cost", 10.0))
            
            # Estimate local consumption velocity
            sku_inv = latest_inv[(latest_inv["medication_id"] == m_id) & (latest_inv["location_id"] == l_id)]
            local_adu = float(sku_inv.iloc[0]["average_daily_usage"]) if len(sku_inv) > 0 else 1.0
            
            dte = int(lot_row["days_to_expiry"])
            qty = int(lot_row["quantity"])
            proj_consumption = dte * max(local_adu, 0.1)
            unconsumed = max(0, int(qty - proj_consumption))
            waste_val = round(unconsumed * cost, 2)
            
            if unconsumed > 5 and waste_val >= 5000.0:
                # Find high-volume sister facility for transfer
                other_inv = latest_inv[(latest_inv["medication_id"] == m_id) & (latest_inv["location_id"] != l_id)]
                if len(other_inv) > 0:
                    top_consumer = other_inv.sort_values("average_daily_usage", ascending=False).iloc[0]
                    target_loc_id = top_consumer["location_id"]
                    target_loc_name = locs_dict.get(target_loc_id, {}).get("location_name", target_loc_id)
                else:
                    target_loc_id = None
                    target_loc_name = None
                    
                expiry_list.append(ExpiryOpportunity(
                    lot_id=lot_row["lot_id"],
                    medication_id=m_id,
                    generic_name=m_meta.get("generic_name", m_id),
                    location_id=l_id,
                    location_name=l_meta.get("location_name", l_id),
                    days_to_expiry=dte,
                    expiry_date=pd.to_datetime(lot_row["expiry_date"]).strftime("%Y-%m-%d"),
                    lot_quantity=qty,
                    projected_unconsumed_units=unconsumed,
                    unit_cost=cost,
                    projected_financial_waste_usd=waste_val,
                    suggested_target_location_id=target_loc_id,
                    suggested_target_location_name=target_loc_name,
                    action_directive=(
                        f"Transfer {unconsumed} expiring units to {target_loc_name or 'regional hospital'} "
                        f"for prioritized FIFO administration within {dte} days."
                    )
                ))
                
        # Total value at stake
        total_rebalance_val = sum(r.estimated_cost_avoidance_usd for r in redistribution_list)
        total_expiry_val = sum(e.projected_financial_waste_usd for e in expiry_list)
        total_val = round(total_rebalance_val + total_expiry_val, 2)
        
        return OpportunitiesResponse(
            total_opportunities_count=len(redistribution_list) + len(expiry_list),
            total_value_at_stake_usd=total_val,
            redistribution_opportunities=redistribution_list,
            expiry_salvage_opportunities=expiry_list
        )
