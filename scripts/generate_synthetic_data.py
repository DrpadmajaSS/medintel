#!/usr/bin/env python3
"""
CLI Script to generate reproducible synthetic healthcare medication & supply-chain datasets.

Usage:
    python scripts/generate_synthetic_data.py --seed 42 --output-dir data/raw
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from medintel_datagen.generator import MedIntelDataGenerator


def main():
    parser = argparse.ArgumentParser(
        description="MedIntel AI Synthetic Medication & Supply-Chain Dataset Generator"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/raw",
        help="Directory to save generated CSV files (default: data/raw)",
    )

    args = parser.parse_args()

    # Resolve relative output directory relative to project root
    output_path = Path(args.output_dir)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    generator = MedIntelDataGenerator(random_seed=args.seed, output_dir=str(output_path))
    generator.generate_all()

    print(f"\n✨ All synthetic datasets successfully generated in: {output_path}")


if __name__ == "__main__":
    main()
