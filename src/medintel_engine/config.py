"""
Configuration constants and parameters for the MedIntel Risk Intelligence Engine.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RiskEngineConfig:
    """Configuration class containing weights, thresholds, and simulation parameters."""
    
    # Simulation Horizon
    simulation_horizon_days: int = 60
    trend_horizon_days: int = 14
    
    # Utilization Signal Thresholds
    demand_surge_high_threshold: float = 1.50   # +50% acceleration
    demand_surge_med_threshold: float = 1.25    # +25% acceleration
    demand_surge_mild_threshold: float = 1.10   # +10% acceleration
    
    # Days of Supply Thresholds
    dos_critical_threshold: float = 2.0
    dos_depleted_threshold: float = 5.0
    dos_moderate_threshold: float = 10.0
    dos_adequate_threshold: float = 15.0
    dos_healthy_threshold: float = 25.0
    
    # Expiry Risk Thresholds
    expiry_horizon_days: int = 60
    expiry_waste_min_units: int = 10
    expiry_waste_min_dollars: float = 10000.0
    expiry_waste_high_dollars: float = 500000.0
    
    # Upstream Supply Thresholds
    lead_time_surge_threshold: int = 10
    recent_events_window_days: int = 30
    recent_po_window_days: int = 30
    
    # Mitigation / False Alarm Thresholds
    inbound_po_max_arrival_days: float = 2.0
    inbound_po_min_reliability: float = 0.90
    
    # Network Rebalancing Thresholds
    surplus_dos_threshold: float = 30.0
    surplus_qoh_threshold: float = 500.0
    
    # Signal Weights for Composite Scoring
    weight_dos: float = 0.40
    weight_supply: float = 0.35
    weight_trend: float = 0.20
    weight_volatility: float = 0.05
    
    # Criticality Multipliers
    criticality_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "High": 1.30,
        "Medium": 1.00,
        "Low": 0.75
    })
    
    # Score Cutoffs for Risk Categorization
    score_cutoff_critical: float = 80.0
    score_cutoff_high: float = 55.0
    score_cutoff_medium: float = 30.0
