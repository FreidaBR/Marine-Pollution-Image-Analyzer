"""
Stage 2 Feature Unit Tests: Analytics, History, Compare, Trends, Disclaimers, and Data Source Separation.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Tests:
1. Dataset statistics calculation (average index, peak observation, location counts, distribution)
2. Live observation vs historical fixture tagging
3. Observation comparison delta & trajectory computation
4. Mandatory scientific boundary notice in reports
5. Multi-dimensional history filtering (severity, location, text search)
6. Empty and boundary input resilience
"""

import unittest
from reporting.schemas import SeverityLevel, Detection, AnalysisResult, AnalysisSummary, Location
from reporting.analytics import calculate_dataset_statistics
from reporting.history import compare_historical_points
from reporting.report_builder import build_analysis_report


class TestStage2Features(unittest.TestCase):

    def setUp(self):
        self.obs1 = AnalysisResult(
            analysis_id="OBS-2026-09-001",
            image_url="IMG_001.jpg",
            timestamp="2026-09-10T10:00:00Z",
            location=Location(name="Karwar Coast Jetty", latitude=14.805, longitude=74.124),
            detections=[
                Detection(class_name="marine_debris", confidence=0.88, bbox=[10, 10, 100, 100], area_ratio=0.08)
            ],
            summary=AnalysisSummary(
                dominant_category="marine_debris",
                total_detections=1,
                severity=SeverityLevel.MODERATE,
                severity_score=55,
                average_confidence=0.88,
                max_confidence=0.88,
                estimated_coverage=0.08
            ),
            metadata={"is_fixture": True, "data_source": "HISTORICAL FIXTURE"}
        )
        self.obs2 = AnalysisResult(
            analysis_id="OBS-2026-09-002",
            image_url="IMG_002.jpg",
            timestamp="2026-09-12T14:30:00Z",
            location=Location(name="Panambur Beach Shore", latitude=12.948, longitude=74.801),
            detections=[
                Detection(class_name="marine_debris", confidence=0.95, bbox=[20, 20, 200, 200], area_ratio=0.15),
                Detection(class_name="marine_debris", confidence=0.91, bbox=[220, 50, 300, 180], area_ratio=0.10)
            ],
            summary=AnalysisSummary(
                dominant_category="marine_debris",
                total_detections=2,
                severity=SeverityLevel.CRITICAL,
                severity_score=88,
                average_confidence=0.93,
                max_confidence=0.95,
                estimated_coverage=0.25
            ),
            metadata={"is_fixture": False, "data_source": "LIVE OBSERVATION"}
        )
        self.obs3 = AnalysisResult(
            analysis_id="OBS-2026-09-003",
            image_url="IMG_003.jpg",
            timestamp="2026-09-14T09:15:00Z",
            location=Location(name="Karwar Coast Jetty", latitude=14.805, longitude=74.124),
            detections=[],
            summary=AnalysisSummary(
                dominant_category="None",
                total_detections=0,
                severity=SeverityLevel.CLEAN,
                severity_score=0,
                average_confidence=0.0,
                max_confidence=0.0,
                estimated_coverage=0.0
            ),
            metadata={"is_fixture": True, "data_source": "HISTORICAL FIXTURE"}
        )

    def test_dataset_statistics_calculations(self):
        stats = calculate_dataset_statistics([self.obs1, self.obs2, self.obs3])
        self.assertEqual(stats["total_analyses"], 3)
        self.assertEqual(stats["locations_monitored_count"], 2)  # Karwar, Panambur
        self.assertIn("Karwar Coast Jetty", stats["unique_locations"])
        self.assertIn("Panambur Beach Shore", stats["unique_locations"])
        # Peak severity observation check
        self.assertIsNotNone(stats["highest_severity_observation"])
        self.assertEqual(stats["highest_severity_observation"]["analysis_id"], "OBS-2026-09-002")
        self.assertEqual(stats["highest_severity_observation"]["score"], 88)
        self.assertEqual(stats["highest_severity_observation"]["severity"], "Critical")
        # Average score: (55 + 88 + 0) / 3 = 47.67 -> 48
        self.assertEqual(stats["average_pollution_score"], 48)

    def test_live_vs_fixture_data_source_separation(self):
        self.assertTrue(self.obs1.metadata.get("is_fixture"))
        self.assertEqual(self.obs1.metadata.get("data_source"), "HISTORICAL FIXTURE")
        self.assertFalse(self.obs2.metadata.get("is_fixture"))
        self.assertEqual(self.obs2.metadata.get("data_source"), "LIVE OBSERVATION")

    def test_observation_comparison_deltas(self):
        diff = compare_historical_points(self.obs1, self.obs2)
        # obs1 score = 55, obs2 score = 88 -> delta = +33
        self.assertEqual(diff.score_change, 33)
        self.assertEqual(diff.detection_count_change, 1)
        self.assertEqual(diff.trend_direction, "deteriorating")

    def test_scientific_boundary_notice_presence(self):
        report = build_analysis_report(self.obs1)
        expected_notice = (
            "This analysis identifies visible marine-debris indicators from the submitted image. "
            "It is not a laboratory or chemical contamination assessment. "
            "(Generated via Controlled Hackathon Demo Inference Mode)"
        )
        self.assertEqual(report.disclaimer, expected_notice)

    def test_history_filtering_simulation(self):
        items = [self.obs1, self.obs2, self.obs3]

        # Filter by Severity
        crit_items = [o for o in items if o.summary.severity == SeverityLevel.CRITICAL]
        self.assertEqual(len(crit_items), 1)
        self.assertEqual(crit_items[0].analysis_id, "OBS-2026-09-002")

        # Filter by Location
        karwar_items = [o for o in items if o.location and "Karwar" in o.location.name]
        self.assertEqual(len(karwar_items), 2)

        # Filter by Source (Live only)
        live_items = [o for o in items if not o.metadata.get("is_fixture")]
        self.assertEqual(len(live_items), 1)
        self.assertEqual(live_items[0].analysis_id, "OBS-2026-09-002")

    def test_empty_dataset_resilience(self):
        stats = calculate_dataset_statistics([])
        self.assertEqual(stats["total_analyses"], 0)
        self.assertEqual(stats["average_pollution_score"], 0)
        self.assertIsNone(stats["highest_severity_observation"])
        self.assertEqual(stats["locations_monitored_count"], 0)
        self.assertEqual(stats["unique_locations"], [])


if __name__ == "__main__":
    unittest.main()
