#!/usr/bin/env python3
"""
CLI Execution Script for MedIntel AI Risk Intelligence Engine.

Usage:
  python scripts/run_risk_engine.py --data-dir data/raw --output-path data/processed/risk_assessments.csv
"""

import os
import sys
import argparse
from datetime import datetime
import pandas as pd

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from medintel_engine.engine import MedIntelRiskEngine
from medintel_engine.config import RiskEngineConfig


def main():
    parser = argparse.ArgumentParser(description="Run MedIntel Medication Risk Intelligence Engine.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/raw",
        help="Path to raw CSV dataset directory (default: data/raw)"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="data/processed/risk_assessments.csv",
        help="Path to output CSV assessment file (default: data/processed/risk_assessments.csv)"
    )
    parser.add_argument(
        "--snapshot-date",
        type=str,
        default=None,
        help="Optional ISO date (YYYY-MM-DD) for inventory snapshot (defaults to latest available)"
    )
    parser.add_argument(
        "--min-risk-level",
        type=str,
        default=None,
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        help="Optional filter to show only records at or above given risk level"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Initializing MedIntel Risk Intelligence Engine (Data: {args.data_dir})...")
    engine = MedIntelRiskEngine(config=RiskEngineConfig())
    
    print("⏳ Executing multi-signal feature extraction and risk simulation...")
    df_assessments = engine.run_assessment(raw_data=args.data_dir, snapshot_date=args.snapshot_date)
    
    # Ensure parent output directory exists
    out_dir = os.path.dirname(args.output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
    df_assessments.to_csv(args.output_path, index=False)
    print(f"✅ Successfully wrote {len(df_assessments)} risk assessments to '{args.output_path}'!")
    
    print("\n📊 Risk Level Breakdown:")
    counts = df_assessments["risk_level"].value_counts()
    for lvl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if lvl in counts:
            print(f"   • {lvl:<8}: {counts[lvl]:>3d} SKUs ({counts[lvl] / len(df_assessments):.1%})")
            
    # Display high-priority alerts
    high_priority = df_assessments[df_assessments["risk_level"].isin(["CRITICAL", "HIGH"])]
    print(f"\n🚨 High-Priority Clinical & Supply-Chain Alerts ({len(high_priority)} SKUs):")
    for _, row in high_priority.head(10).iterrows():
        print(f"   [{row['risk_level']}] {row['medication_id']} @ {row['location_id']} | Score: {row['risk_score']:.1f} | Stockout: {row['days_to_stockout']}d")
        print(f"     Primary: {row['primary_risk_factors']}")
        print(f"     Action : {row['recommended_review']}")
        print()


if __name__ == "__main__":
    main()
