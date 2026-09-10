"""
Daily Intelligence Briefing Service for MedIntel API.
Synthesizes multi-signal risk data into prioritized ACT, WATCH, OPPORTUNITY, and LEARN sections.
"""

from typing import Optional, List, Dict, Any
import pandas as pd

from medintel_api.services.data_service import DataService
from medintel_api.schemas.intelligence import DailyIntelligenceBrief, BriefItem


class IntelligenceService:
    """Generates the prioritized Daily Intelligence Brief."""
    
    def __init__(self, data_service: DataService):
        self.ds = data_service
        
    def generate_brief(self, location_id: Optional[str] = None) -> DailyIntelligenceBrief:
        """Generates prioritized daily briefing categorized into ACT, WATCH, OPPORTUNITY, and LEARN."""
        
        all_assessments = list(self.ds.assessments_by_sku.values())
        if location_id:
            all_assessments = [a for a in all_assessments if a["location_id"] == location_id]
            
        # Sort by risk score descending
        all_assessments.sort(key=lambda x: x["risk_score"], reverse=True)
        
        act_items: List[BriefItem] = []
        watch_items: List[BriefItem] = []
        opportunity_items: List[BriefItem] = []
        learn_items: List[BriefItem] = []
        
        # 1. Populate ACT (Top Critical & High Actionable Items)
        critical_high = [a for a in all_assessments if a["risk_level"] in ["CRITICAL", "HIGH"]]
        for idx, item in enumerate(critical_high[:5]):
            metric_text = (
                f"{item['days_of_supply']:.1f} DOS"
                if item["days_to_stockout"] is None or item["days_to_stockout"] == 0
                else f"Stockout in {item['days_to_stockout']:.1f}d"
            )
            act_items.append(BriefItem(
                id=f"ACT-{idx+1}",
                category="ACT",
                title=f"Critical Supply Shortage: {item['generic_name']} at {item['location_name']}",
                medication_id=item["medication_id"],
                medication_name=item["generic_name"],
                location_id=item["location_id"],
                location_name=item["location_name"],
                severity=item["risk_level"],
                metric_highlight=metric_text,
                detail=f"Primary drivers: {item['primary_risk_factors']}. Mitigations: {item['mitigating_factors']}.",
                recommended_action=item["recommended_review"]
            ))
            
        # 2. Populate WATCH (Emerging Demand Surges & Buffer Deterioration)
        emerging_items = [
            a for a in all_assessments 
            if a["risk_level"] == "MEDIUM" and (a["trend_ratio"] >= 1.20 or a["days_of_supply"] <= 15.0)
        ]
        emerging_items.sort(key=lambda x: x["trend_ratio"], reverse=True)
        
        for idx, item in enumerate(emerging_items[:5]):
            pct_surge = (item["trend_ratio"] - 1.0) * 100.0
            watch_items.append(BriefItem(
                id=f"WATCH-{idx+1}",
                category="WATCH",
                title=f"Emerging Demand Acceleration: {item['generic_name']} at {item['location_name']}",
                medication_id=item["medication_id"],
                medication_name=item["generic_name"],
                location_id=item["location_id"],
                location_name=item["location_name"],
                severity="MEDIUM",
                metric_highlight=f"+{pct_surge:.1f}% Surge (7d vs 30d)",
                detail=(
                    f"Consumption velocity is accelerating ({item['average_daily_usage']:.1f} units/day). "
                    f"Current on-hand buffer ({item['days_of_supply']:.1f} DOS) is safe today but will breach static reorder baseline."
                ),
                recommended_action=item["recommended_review"]
            ))
            
        # 3. Populate OPPORTUNITY (Redistribution & Expiry Salvage)
        raw = self.ds.raw_data
        lots = raw.expiry_lots
        snapshot_dt = self.ds.snapshot_dt
        
        # Check near-expiry lots (<= 60 days)
        lots_copy = lots.copy()
        lots_copy["days_to_expiry"] = (pd.to_datetime(lots_copy["expiry_date"]) - snapshot_dt).dt.days
        near_lots = lots_copy[lots_copy["days_to_expiry"] <= 60]
        
        opp_count = 1
        # Expiry salvage opportunities
        for _, lot_row in near_lots.iterrows():
            m_id = lot_row["medication_id"]
            l_id = lot_row["location_id"]
            if location_id and l_id != location_id:
                continue
                
            m_meta = self.ds.medications_by_id.get(m_id, {})
            l_meta = self.ds.locations_by_id.get(l_id, {})
            cost = float(m_meta.get("unit_cost", 10.0))
            waste_val = float(lot_row["quantity"]) * cost
            
            if waste_val >= 25000.0:
                opportunity_items.append(BriefItem(
                    id=f"OPP-{opp_count}",
                    category="OPPORTUNITY",
                    title=f"Near-Expiry Salvage: {m_meta.get('generic_name')} at {l_meta.get('location_name')}",
                    medication_id=m_id,
                    medication_name=m_meta.get("generic_name"),
                    location_id=l_id,
                    location_name=l_meta.get("location_name"),
                    severity="HIGH",
                    metric_highlight=f"${waste_val:,.0f} Value ({lot_row['days_to_expiry']}d left)",
                    detail=(
                        f"Lot {lot_row['lot_id']} holds {lot_row['quantity']} units expiring on "
                        f"{pd.to_datetime(lot_row['expiry_date']).strftime('%Y-%m-%d')}. "
                        f"Local consumption velocity is insufficient to exhaust batch prior to expiration."
                    ),
                    recommended_action=(
                        f"Transfer expiring units to high-volume regional comprehensive facility for "
                        f"prioritized FIFO utilization to avoid financial write-off."
                    )
                ))
                opp_count += 1
                
        # Lateral transfer opportunities
        for item in critical_high:
            if "lateral transfer" in item["recommended_review"].lower() or "rebalance regional network" in item["recommended_review"].lower():
                opportunity_items.append(BriefItem(
                    id=f"OPP-{opp_count}",
                    category="OPPORTUNITY",
                    title=f"Lateral Network Rebalancing: {item['generic_name']}",
                    medication_id=item["medication_id"],
                    medication_name=item["generic_name"],
                    location_id=item["location_id"],
                    location_name=item["location_name"],
                    severity="MEDIUM",
                    metric_highlight=f"Sister Surplus Available",
                    detail=(
                        f"{item['location_name']} has depleted stock ({item['days_of_supply']:.1f} DOS) "
                        f"while sister facilities in the health network maintain surplus inventory."
                    ),
                    recommended_action=item["recommended_review"]
                ))
                opp_count += 1
                if opp_count > 6:
                    break
                    
        # 4. Populate LEARN (Clinical & Operational Knowledge Nuggets)
        learn_items = [
            BriefItem(
                id="LEARN-1",
                category="LEARN",
                title="Early Demand Velocity vs Static Reorder Thresholds",
                metric_highlight="Early Warning",
                detail=(
                    "Static hospital reorder rules evaluate 14 days of supply as 'healthy'. However, a +50% velocity acceleration "
                    "will breach safe buffers 5-7 days before scheduled reorders. MedIntel uses 7d/30d moving average ratios to catch emerging risks."
                ),
                recommended_action="Always configure dynamic safety stock baseline adjustment when trailing 7-day velocity exceeds 30-day baseline by >25%."
            ),
            BriefItem(
                id="LEARN-2",
                category="LEARN",
                title="Mitigating Supply False Alarms with Inbound Pipeline Intelligence",
                metric_highlight="Cost Avoidance",
                detail=(
                    "Naive inventory dashboards flag low on-hand stock (< 2 days) as critical red alerts, frequently prompting expensive emergency spot orders. "
                    "MedIntel cross-references verified carrier tracking and supplier reliability scores to downgrade protected in-transit shipments."
                ),
                recommended_action="Confirm in-transit purchase order delivery schedule before placing secondary expedited orders."
            ),
            BriefItem(
                id="LEARN-3",
                category="LEARN",
                title="Inter-Facility Lateral Stock Rebalancing",
                metric_highlight="Network Optimization",
                detail=(
                    "Stockouts frequently occur at smaller community hospitals while academic medical centers in the same health system hold 45+ days of surplus inventory. "
                    "Lateral network transfers resolve local shortages within hours at zero incremental procurement cost."
                ),
                recommended_action="Prioritize intra-network transfers from high-surplus sister facilities before placing spot-market manufacturer orders."
            ),
            BriefItem(
                id="LEARN-4",
                category="LEARN",
                title="Proactive Expiry Mitigation for High-Cost Biologics",
                metric_highlight="Waste Reduction",
                detail=(
                    "Specialty emergency drugs (e.g. Thrombolytics / Alteplase) stored at low-volume ambulatory surgery centers risk expiring before usage. "
                    "Proactive transfer to high-volume comprehensive stroke centers ensures 100% batch consumption."
                ),
                recommended_action="Conduct weekly shelf-life collision audits across specialty drugs with unit costs exceeding $1,000."
            )
        ]
        
        # Executive Headline
        critical_count = len([a for a in all_assessments if a["risk_level"] == "CRITICAL"])
        high_count = len([a for a in all_assessments if a["risk_level"] == "HIGH"])
        emerging_count = len([a for a in all_assessments if a["risk_level"] == "MEDIUM" and a["trend_ratio"] >= 1.25])
        
        headline = (
            f"MedIntel Daily Brief: {critical_count} critical shortage requiring immediate action, "
            f"{high_count} high-priority network rebalancing opportunities, and {emerging_count} emerging demand surges detected."
        )
        
        return DailyIntelligenceBrief(
            date=self.ds.snapshot_date_str,
            headline=headline,
            act=act_items,
            watch=watch_items,
            opportunity=opportunity_items[:5],
            learn=learn_items
        )
