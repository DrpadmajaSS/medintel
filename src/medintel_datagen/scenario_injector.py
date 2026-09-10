"""
Scenario Injector and Ground Truth Builder for MedIntel AI Evaluation.
"""

from typing import List
from .config import SCENARIO_DEFINITIONS
from .models import GroundTruth


class ScenarioInjector:
    @staticmethod
    def generate_ground_truth() -> List[GroundTruth]:
        """
        Builds the ground truth test scenario evaluation benchmarks.
        """
        ground_truth_records: List[GroundTruth] = []

        for scen in SCENARIO_DEFINITIONS:
            gt = GroundTruth(
                scenario_id=scen["scenario_id"],
                medication_id=scen["medication_id"],
                location_id=scen["location_id"],
                expected_issue=scen["expected_issue"],
                expected_severity=scen["expected_severity"],
                expected_stockout_window=scen["expected_stockout_window"],
                expected_recommendation=scen["expected_recommendation"],
            )
            ground_truth_records.append(gt)

        return ground_truth_records
