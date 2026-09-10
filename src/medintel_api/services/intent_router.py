"""
Structured Conversational Intent Classifier and Entity Resolution Router for MedIntel.
Enforces explicit multi-stage query routing:
1. Intent Classification (Priority over previous context)
2. Entity Resolution (Medications, facilities, suppliers, metrics, pronouns)
3. Context Resolution (Resolves pronouns without overriding new intents)
4. Confidence Thresholding & Clarification Generation
"""

import re
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from medintel_api.services.data_service import DataService
from medintel_api.schemas.chat import ChatRequest


class IntentEnum(str, Enum):
    DAILY_BRIEF = "DAILY_BRIEF"
    EMERGING_RISK = "EMERGING_RISK"
    ACTION_RECOMMENDATION = "ACTION_RECOMMENDATION"
    TRANSFER_ANALYSIS = "TRANSFER_ANALYSIS"
    OPPORTUNITY_ANALYSIS = "OPPORTUNITY_ANALYSIS"
    WHAT_IF_SIMULATION = "WHAT_IF_SIMULATION"
    SUPPLIER_ANALYSIS = "SUPPLIER_ANALYSIS"
    UTILIZATION_ANALYSIS = "UTILIZATION_ANALYSIS"
    RECENT_CHANGES = "RECENT_CHANGES"
    RISK_INVESTIGATION = "RISK_INVESTIGATION"
    INVENTORY_ANALYSIS = "INVENTORY_ANALYSIS"
    GENERAL_EXPLORATION = "GENERAL_EXPLORATION"


@dataclass
class StructuredIntent:
    intent: IntentEnum
    medication_id: Optional[str] = None
    medication_name: Optional[str] = None
    location_id: Optional[str] = None
    location_name: Optional[str] = None
    supplier_id: Optional[str] = None
    percentage_change: Optional[float] = None
    supplier_delay_days: Optional[float] = None
    transfer_units: Optional[float] = None
    confidence: float = 1.0
    context_reference: Optional[str] = None
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None
    raw_prompt: str = ""


class ConversationalIntentRouter:
    """Classifies user intent and resolves entities with strict context-override boundaries."""

    def __init__(self, data_service: DataService):
        self.ds = data_service

    def route(self, request: ChatRequest) -> StructuredIntent:
        p_raw = request.prompt.strip()
        p = p_raw.lower()

        # Step 1: Extract Entities and Parameters from Current Text
        med_id_explicit, med_name_explicit = self._find_medication(p_raw)
        loc_id_explicit, loc_name_explicit = self._find_location(p_raw)
        pronoun_ref = self._find_pronoun_reference(p)
        sim_params = self._parse_simulation_params(p_raw)

        # -------------------------------------------------------------
        # Stage 1: ACTION_RECOMMENDATION (Global Scope)
        # Priority: "Tell me what to do first", "What should I prioritize?"
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "what to do first", "what should i do first", "what should we do first",
            "most important thing i should act on", "most important thing to act on",
            "what should i prioritize", "what to prioritize", "highest priority action",
            "tell me what to do", "first action", "recommended priority", "priority action"
        ]):
            return StructuredIntent(
                intent=IntentEnum.ACTION_RECOMMENDATION,
                confidence=0.98,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 2: TRANSFER_ANALYSIS (Targeted Stock Movement)
        # Priority: "Can I transfer this from somewhere else?", "Where can we transfer stock from?"
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "transfer this", "transfer from", "transfer stock", "move stock", "rebalance this",
            "donor facility", "donor hospital", "sister facility", "sister hospital",
            "somewhere else", "another facility", "another hospital", "lateral transfer",
            "transfer it", "can we transfer", "can i transfer"
        ]) and any(w in p for w in ["transfer", "move", "rebalance", "donor", "shift", "source", "relocate"]):
            target_med = med_id_explicit or (request.context_medication_id if pronoun_ref else None)
            target_name = med_name_explicit or (self.ds.medications_by_id.get(target_med, {}).get("generic_name") if target_med else None)
            
            if not target_med and pronoun_ref:
                for msg in reversed(request.conversation_history):
                    h_id, h_name = self._find_medication(msg.content)
                    if h_id:
                        target_med, target_name = h_id, h_name
                        break
                        
            if not target_med:
                target_med, target_name = "MED001", "Norepinephrine Bitartrate"

            return StructuredIntent(
                intent=IntentEnum.TRANSFER_ANALYSIS,
                medication_id=target_med,
                medication_name=target_name,
                location_id=loc_id_explicit,
                location_name=loc_name_explicit,
                context_reference=pronoun_ref,
                confidence=0.96,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 3: EMERGING_RISK (Global Network Scope)
        # Priority: "Which risks are emerging?", "What are emerging risks?"
        # Rule: Must NOT inherit previous medication context!
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "which risks are emerging", "what risks are emerging", "emerging risk", "emerging risks",
            "emerging surges", "emerging demand", "acceleration risks", "demand surges", "emerging alerts"
        ]) and not med_id_explicit:
            return StructuredIntent(
                intent=IntentEnum.EMERGING_RISK,
                confidence=0.97,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 4: WHAT_IF_SIMULATION
        # Priority: "What happens if demand increases 20%?", "Simulate 50% surge on Meropenem"
        # Rule: If no medication is explicit and no unambiguous pronoun exists, ASK CLARIFICATION!
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "what happens if", "what if", "simulate", "if demand increases", "if demand surges",
            "if supplier is delayed", "if we transfer", "demand increases", "demand surges"
        ]) and (sim_params["percentage_change"] != 0.0 or sim_params["supplier_delay_days"] != 0.0 or sim_params["transfer_units"] != 0.0 or "what if" in p or "simulate" in p):
            target_med = med_id_explicit
            target_name = med_name_explicit
            
            if not target_med and pronoun_ref and request.context_medication_id:
                target_med = request.context_medication_id
                target_name = self.ds.medications_by_id.get(target_med, {}).get("generic_name")
                
            # If no medication was specified and no explicit pronoun was used:
            # DO NOT GUESS! DO NOT DEFAULT! Ask for clarification!
            if not target_med:
                return StructuredIntent(
                    intent=IntentEnum.WHAT_IF_SIMULATION,
                    needs_clarification=True,
                    clarification_prompt=(
                        f"Which medication would you like me to simulate a {sim_params.get('percentage_change', 20):+.0f}% change for?\n\n"
                        "Here are the highest-priority candidates across our hospital network today:\n"
                        "1. **Norepinephrine Bitartrate (`MED001`)** @ Valley Regional Trauma Center (Critical Shortage • 0.0 DOS)\n"
                        "2. **Meropenem (`MED022`)** @ North Suburban General Hospital (Emerging Sepsis Surge • +76% Velocity)\n"
                        "3. **Dexmedetomidine (`MED008`)** @ Westside Community Hospital (Regional Network Imbalance • 0.0 DOS)\n"
                        "4. **Insulin Glargine (`MED057`)** @ Metro Memorial Health (Supplier Lead-Time Surge • 25d Delay)\n\n"
                        "Please specify which medication (or reply *'simulate Meropenem'* or *'simulate Norepinephrine'*)."
                    ),
                    percentage_change=sim_params.get("percentage_change"),
                    supplier_delay_days=sim_params.get("supplier_delay_days"),
                    transfer_units=sim_params.get("transfer_units"),
                    confidence=0.94,
                    raw_prompt=p_raw
                )

            return StructuredIntent(
                intent=IntentEnum.WHAT_IF_SIMULATION,
                medication_id=target_med,
                medication_name=target_name,
                location_id=loc_id_explicit or (self._get_default_location_for_med(target_med)),
                location_name=loc_name_explicit,
                percentage_change=sim_params.get("percentage_change", 0.0),
                supplier_delay_days=sim_params.get("supplier_delay_days", 0.0),
                transfer_units=sim_params.get("transfer_units", 0.0),
                context_reference=pronoun_ref,
                confidence=0.96,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 5: OPPORTUNITY_ANALYSIS (Global Network Scope)
        # Priority: "Where do we have excess inventory?", "What are the biggest cost-saving opportunities?"
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "excess inventory", "excess stock", "surplus inventory", "surplus stock",
            "cost-saving", "cost saving", "savings opportunities", "cost avoidance",
            "rebalancing opportunities", "redistribution opportunities", "expiry salvage",
            "near-expiry", "near expiry", "waste avoidance", "where do we have excess"
        ]):
            return StructuredIntent(
                intent=IntentEnum.OPPORTUNITY_ANALYSIS,
                medication_id=med_id_explicit,
                medication_name=med_name_explicit,
                confidence=0.96,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 6: SUPPLIER_ANALYSIS (Network or Vendor Scope)
        # Priority: "Which suppliers have disruptions?", "Show supplier lead-time surges"
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "supplier", "distributor", "vendor", "delayed order", "lead time", "lead-time",
            "packaging line", "supply chain hold", "carrier delay", "delayed shipments"
        ]):
            return StructuredIntent(
                intent=IntentEnum.SUPPLIER_ANALYSIS,
                medication_id=med_id_explicit,
                medication_name=med_name_explicit,
                confidence=0.95,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 7: UTILIZATION_ANALYSIS (Velocity & Burn Rate Trends)
        # Priority: "Which medications have accelerating demand?", "Show highest burn rate drugs"
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "accelerating demand", "demand acceleration", "burn rate", "velocity",
            "usage spike", "highest burn", "fastest demand", "trend ratio", "consumption acceleration"
        ]):
            return StructuredIntent(
                intent=IntentEnum.UTILIZATION_ANALYSIS,
                medication_id=med_id_explicit,
                medication_name=med_name_explicit,
                confidence=0.95,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 8: RECENT_CHANGES (Network Delta)
        # Priority: "What changed recently across our supply network?"
        # -------------------------------------------------------------
        if any(phrase in p for phrase in [
            "what changed", "changes across", "network shifts", "recent changes",
            "latest developments", "what's new", "new risks today"
        ]):
            return StructuredIntent(
                intent=IntentEnum.RECENT_CHANGES,
                confidence=0.95,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 9: RISK_INVESTIGATION (Medication-Specific Diagnostic)
        # Priority: "Why is Norepinephrine at risk?", "Why is that medication at risk?"
        # -------------------------------------------------------------
        if any(phrase in p for phrase in ["why is", "at risk", "shortage", "risk factors", "root cause", "explain the risk", "risk score"]):
            target_med = med_id_explicit or (request.context_medication_id if pronoun_ref else None)
            target_name = med_name_explicit or (self.ds.medications_by_id.get(target_med, {}).get("generic_name") if target_med else None)
            
            if not target_med and pronoun_ref:
                for msg in reversed(request.conversation_history):
                    h_id, h_name = self._find_medication(msg.content)
                    if h_id:
                        target_med, target_name = h_id, h_name
                        break
                        
            if not target_med:
                target_med, target_name = "MED001", "Norepinephrine Bitartrate"

            return StructuredIntent(
                intent=IntentEnum.RISK_INVESTIGATION,
                medication_id=target_med,
                medication_name=target_name,
                location_id=loc_id_explicit,
                location_name=loc_name_explicit,
                context_reference=pronoun_ref,
                confidence=0.95,
                raw_prompt=p_raw
            )

        # -------------------------------------------------------------
        # Stage 10: INVENTORY_ANALYSIS (Catalog Stock Queries)
        # Priority: "What is our current stock of Propofol?", "Show inventory breakdown for Ketamine"
        # -------------------------------------------------------------
        if med_id_explicit or any(phrase in p for phrase in ["inventory", "stock level", "on hand", "qoh", "how much", "how many units"]):
            target_med = med_id_explicit or (request.context_medication_id if pronoun_ref else None)
            target_name = med_name_explicit or (self.ds.medications_by_id.get(target_med, {}).get("generic_name") if target_med else None)
            
            if target_med:
                return StructuredIntent(
                    intent=IntentEnum.INVENTORY_ANALYSIS,
                    medication_id=target_med,
                    medication_name=target_name,
                    location_id=loc_id_explicit,
                    location_name=loc_name_explicit,
                    confidence=0.92,
                    raw_prompt=p_raw
                )

        # -------------------------------------------------------------
        # Stage 11: DAILY_BRIEF (Default Overview & Morning Rounds)
        # Priority: "What should I worry about today?", "Morning summary", "Daily brief"
        # -------------------------------------------------------------
        return StructuredIntent(
            intent=IntentEnum.DAILY_BRIEF,
            confidence=0.90,
            raw_prompt=p_raw
        )

    def _find_medication(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        t_lower = text.lower()
        for m_id, m_data in self.ds.medications_by_id.items():
            g_name = m_data.get("generic_name", "").lower()
            if m_id.lower() in t_lower or g_name in t_lower:
                return m_id, m_data.get("generic_name")
            short_name = g_name.split()[0]
            if len(short_name) > 4 and short_name in t_lower:
                return m_id, m_data.get("generic_name")
        return None, None

    def _find_location(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        t_lower = text.lower()
        for l_id, l_data in self.ds.locations_by_id.items():
            l_name = l_data.get("location_name", "").lower()
            if l_id.lower() in t_lower or l_name in t_lower:
                return l_id, l_data.get("location_name")
        if "trauma" in t_lower or "valley" in t_lower:
            return "LOC006", "Valley Regional Trauma Center"
        if "north" in t_lower or "suburban" in t_lower:
            return "LOC002", "North Suburban General Hospital"
        if "central" in t_lower or "amc" in t_lower:
            return "LOC001", "Central Academic Medical Center"
        if "westside" in t_lower:
            return "LOC005", "Westside Community Hospital"
        if "metro" in t_lower:
            return "LOC003", "Metro Memorial Health - Main"
        if "jude" in t_lower:
            return "LOC004", "St. Jude Children's Pavilion"
        if "ambulatory" in t_lower or "south" in t_lower:
            return "LOC007", "South Ambulatory & Surgical Center"
        return None, None

    def _find_pronoun_reference(self, p: str) -> Optional[str]:
        for pron in [
            "this medication", "that medication", "this drug", "that drug", "the medication", "the drug",
            "this", "that", "it", "somewhere else", "another facility", "another hospital"
        ]:
            if re.search(r'\b' + re.escape(pron) + r'\b', p):
                return pron
        return None

    def _parse_simulation_params(self, text: str) -> Dict[str, float]:
        params = {"percentage_change": 0.0, "supplier_delay_days": 0.0, "transfer_units": 0.0}
        pct_match = re.search(r'([+-]?\d+(?:\.\d+)?)\s*%', text)
        if pct_match:
            val = float(pct_match.group(1))
            if "decreas" in text.lower() and val > 0:
                val = -val
            params["percentage_change"] = val
        elif "increase" in text.lower() or "surge" in text.lower():
            params["percentage_change"] = 20.0
            
        days_match = re.search(r'(\d+)\s*(?:days?|d)\s*(?:delay|late|supplier)?', text.lower())
        if days_match and ("delay" in text.lower() or "supplier" in text.lower() or "late" in text.lower()):
            params["supplier_delay_days"] = float(days_match.group(1))
            
        units_match = re.search(r'transfer\s*(\d+)', text.lower()) or re.search(r'(\d+)\s*(?:units?|vials?|doses?)', text.lower())
        if units_match and "transfer" in text.lower():
            params["transfer_units"] = float(units_match.group(1))
            
        return params

    def _get_default_location_for_med(self, med_id: str) -> str:
        items = self.ds.assessments_by_med.get(med_id, [])
        if items:
            top = max(items, key=lambda x: x["risk_score"])
            return top["location_id"]
        return "LOC001"
