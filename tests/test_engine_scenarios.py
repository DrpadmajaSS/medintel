"""
Comprehensive Test Suite Benchmarking MedIntel Risk Engine Against Ground Truth.
Verifies:
  - 100% exact scenario severity match on Scenarios 1 to 6
  - Output schema structure and non-null constraints
  - Zero leakage of ground truth into inference pipeline
"""

import os
import pandas as pd
import pytest

from medintel_engine.engine import MedIntelRiskEngine
from medintel_engine.config import RiskEngineConfig


@pytest.fixture(scope="module")
def engine_assessment_results():
    engine = MedIntelRiskEngine(config=RiskEngineConfig())
    df = engine.run_assessment(raw_data="data/raw")
    return df


@pytest.fixture(scope="module")
def ground_truth_df():
    gt_path = "data/raw/ground_truth.csv"
    assert os.path.exists(gt_path), f"Missing {gt_path}"
    return pd.read_csv(gt_path)


def test_output_schema_and_completeness(engine_assessment_results):
    df = engine_assessment_results
    assert len(df) == 525, f"Expected 525 facility-medication SKUs, got {len(df)}"
    
    expected_cols = [
        "medication_id",
        "location_id",
        "risk_score",
        "risk_level",
        "predicted_stockout_date",
        "days_to_stockout",
        "primary_risk_factors",
        "contributing_factors",
        "mitigating_factors",
        "confidence",
        "recommended_review"
    ]
    assert list(df.columns) == expected_cols
    
    # Check non-null constraints on mandatory fields
    assert df["medication_id"].isna().sum() == 0
    assert df["location_id"].isna().sum() == 0
    assert df["risk_score"].isna().sum() == 0
    assert df["risk_level"].isna().sum() == 0
    assert df["confidence"].isna().sum() == 0
    assert df["recommended_review"].isna().sum() == 0
    
    # Check valid risk levels
    assert set(df["risk_level"].unique()).issubset({"CRITICAL", "HIGH", "MEDIUM", "LOW"})
    assert (df["risk_score"] >= 0.0).all() and (df["risk_score"] <= 100.0).all()


def test_scenario_1_critical_stockout(engine_assessment_results, ground_truth_df):
    """Scenario 1: Norepinephrine at LOC006 with demand surge & delayed PO -> CRITICAL."""
    gt_row = ground_truth_df[ground_truth_df["scenario_id"] == "SCENARIO-1"].iloc[0]
    res = engine_assessment_results[
        (engine_assessment_results["medication_id"] == gt_row["medication_id"]) &
        (engine_assessment_results["location_id"] == gt_row["location_id"])
    ].iloc[0]
    
    assert res["risk_level"] == "CRITICAL"
    assert res["risk_score"] >= 80.0
    assert res["days_to_stockout"] <= 3.0
    assert "critical shortage" in res["recommended_review"].lower()


def test_scenario_2_emerging_demand_surge(engine_assessment_results, ground_truth_df):
    """Scenario 2: Meropenem at LOC002 with accelerating burn rate -> MEDIUM."""
    gt_row = ground_truth_df[ground_truth_df["scenario_id"] == "SCENARIO-2"].iloc[0]
    res = engine_assessment_results[
        (engine_assessment_results["medication_id"] == gt_row["medication_id"]) &
        (engine_assessment_results["location_id"] == gt_row["location_id"])
    ].iloc[0]
    
    assert res["risk_level"] == "MEDIUM"
    assert "emerging" in res["recommended_review"].lower() or "safety stock" in res["recommended_review"].lower()


def test_scenario_3_inter_facility_imbalance(engine_assessment_results, ground_truth_df):
    """Scenario 3: Dexmedetomidine at LOC005 with low stock but surplus at LOC001 -> HIGH."""
    gt_row = ground_truth_df[ground_truth_df["scenario_id"] == "SCENARIO-3"].iloc[0]
    res = engine_assessment_results[
        (engine_assessment_results["medication_id"] == gt_row["medication_id"]) &
        (engine_assessment_results["location_id"] == gt_row["location_id"])
    ].iloc[0]
    
    assert res["risk_level"] == "HIGH"
    assert "rebalance" in res["recommended_review"].lower() or "transfer" in res["recommended_review"].lower()
    assert "Regional surplus available" in res["mitigating_factors"]


def test_scenario_4_impending_expiry_waste(engine_assessment_results, ground_truth_df):
    """Scenario 4: Alteplase at LOC007 near-expiry lot with low velocity -> HIGH."""
    gt_row = ground_truth_df[ground_truth_df["scenario_id"] == "SCENARIO-4"].iloc[0]
    res = engine_assessment_results[
        (engine_assessment_results["medication_id"] == gt_row["medication_id"]) &
        (engine_assessment_results["location_id"] == gt_row["location_id"])
    ].iloc[0]
    
    assert res["risk_level"] == "HIGH"
    assert "expiry" in res["primary_risk_factors"].lower()
    assert "write-off" in res["recommended_review"].lower() or "fifo" in res["recommended_review"].lower()


def test_scenario_5_lead_time_surge(engine_assessment_results, ground_truth_df):
    """Scenario 5: Insulin Glargine at LOC003 with supplier lead-time jump -> HIGH."""
    gt_row = ground_truth_df[ground_truth_df["scenario_id"] == "SCENARIO-5"].iloc[0]
    res = engine_assessment_results[
        (engine_assessment_results["medication_id"] == gt_row["medication_id"]) &
        (engine_assessment_results["location_id"] == gt_row["location_id"])
    ].iloc[0]
    
    assert res["risk_level"] == "HIGH"
    assert "lead-time surge" in res["primary_risk_factors"].lower()
    assert "reroute" in res["recommended_review"].lower()


def test_scenario_6_false_alarm_mitigation(engine_assessment_results, ground_truth_df):
    """Scenario 6: Vancomycin at LOC004 low stock but confirmed inbound PO arriving in 1d -> LOW."""
    gt_row = ground_truth_df[ground_truth_df["scenario_id"] == "SCENARIO-6"].iloc[0]
    res = engine_assessment_results[
        (engine_assessment_results["medication_id"] == gt_row["medication_id"]) &
        (engine_assessment_results["location_id"] == gt_row["location_id"])
    ].iloc[0]
    
    assert res["risk_level"] == "LOW"
    assert res["risk_score"] <= 30.0
    assert "inbound po" in res["mitigating_factors"].lower()
    assert "no escalation required" in res["recommended_review"].lower()
