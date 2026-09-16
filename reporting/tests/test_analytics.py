"""
Comprehensive Unit Tests for Environmental Analytics & Intelligence Layer.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Tests all 14 mandatory conditions:
 1. Zero detections
 2. Single low-confidence detection
 3. Multiple detections
 4. High-confidence detections
 5. Missing area_ratio fallback
 6. Multi-image survey aggregation
 7. Empty survey handling
 8. Historical comparison calculation
 9. Location aggregation
10. Hotspot detection and ranking
11. Trend analysis & trajectory calculation
12. Severity score boundary conditions
13. Invalid / out-of-bound confidence handling
14. Malformed detection input resilience
"""

import unittest
from reporting.schemas import SeverityLevel, Detection, Location
from reporting.severity import (
    calculate_severity,
    normalize_detection,
    score_to_severity_level,
    SEVERITY_CONFIG,
)
from reporting.analytics import (
    analyze_single_result,
    calculate_dataset_statistics,
    identify_dominant_category,
    calculate_severity_distribution,
)
from reporting.survey import (
    aggregate_survey,
    calculate_survey_severity,
    calculate_survey_statistics,
)
from reporting.history import compare_historical_points
from reporting.hotspots import aggregate_location_intelligence, haversine_distance_km
from reporting.trends import calculate_trends
from reporting.recommendations import get_recommendations
from reporting.report_builder import build_analysis_report, build_survey_report, render_html_report


class TestAnalyticsIntelligenceLayer(unittest.TestCase):

    # 1. Zero detections
    def test_01_zero_detections(self):
        sev, score, breakdown = calculate_severity([])
        self.assertEqual(sev, SeverityLevel.CLEAN)
        self.assertEqual(score, 0)
        self.assertEqual(breakdown["total_detections"], 0)

    # 2. One low-confidence detection
    def test_02_single_low_confidence_detection(self):
        det = Detection(class_name="marine_debris", confidence=0.25, bbox=[10, 10, 50, 50])
        sev, score, breakdown = calculate_severity([det])
        self.assertEqual(sev, SeverityLevel.LOW)
        self.assertTrue(1 <= score < 30)
        self.assertEqual(breakdown["total_detections"], 1)

    # 3. Multiple detections
    def test_03_multiple_detections_scaling(self):
        low_count_dets = [
            Detection(class_name="marine_debris", confidence=0.85, bbox=[0, 0, 50, 50])
        ]
        high_count_dets = [
            Detection(class_name="marine_debris", confidence=0.85, bbox=[i * 10, 0, i * 10 + 50, 50])
            for i in range(8)
        ]
        _, score_low, _ = calculate_severity(low_count_dets)
        _, score_high, _ = calculate_severity(high_count_dets)
        self.assertGreater(score_high, score_low)

    # 4. High-confidence detections vs low-confidence detections
    def test_04_confidence_scaling(self):
        low_conf = [Detection(class_name="marine_debris", confidence=0.30, bbox=[0, 0, 100, 100])]
        high_conf = [Detection(class_name="marine_debris", confidence=0.98, bbox=[0, 0, 100, 100])]
        _, score_low, _ = calculate_severity(low_conf)
        _, score_high, _ = calculate_severity(high_conf)
        self.assertGreater(score_high, score_low)

    # 5. Missing area_ratio fallback
    def test_05_missing_area_ratio_fallback(self):
        det_without_area = Detection(class_name="marine_debris", confidence=0.85, bbox=[10, 10, 80, 80], area_ratio=None)
        sev, score, breakdown = calculate_severity([det_without_area])
        self.assertFalse(breakdown["used_area_ratio"])
        self.assertIsNone(breakdown["estimated_coverage"])
        self.assertGreater(score, 0)

    # 6. Multi-image survey aggregation
    def test_06_multi_image_survey_aggregation(self):
        img1 = analyze_single_result("IMG-01", [Detection(class_name="marine_debris", confidence=0.9, bbox=[0, 0, 50, 50])])
        img2 = analyze_single_result("IMG-02", [])
        survey = aggregate_survey("SRV-TEST", "Test Coastal Survey", [img1, img2], date="2026-09-15")
        self.assertEqual(survey.total_images, 2)
        self.assertEqual(survey.affected_images, 1)
        self.assertEqual(survey.clean_images, 1)
        self.assertEqual(survey.total_detections, 1)
        self.assertIn("Clean", survey.severity_distribution)
        self.assertEqual(survey.severity_distribution["Clean"], 1)

    # 7. Empty survey handling
    def test_07_empty_survey_handling(self):
        survey = aggregate_survey("SRV-EMPTY", "Empty Survey", [])
        self.assertEqual(survey.total_images, 0)
        self.assertEqual(survey.total_detections, 0)
        self.assertEqual(survey.average_score, 0)
        self.assertEqual(survey.overall_severity, SeverityLevel.CLEAN)

    # 8. Historical comparison calculation
    def test_08_historical_comparison(self):
        prev = {"id": "S1", "score": 40, "detections": 10, "severity": "Moderate"}
        curr = {"id": "S2", "score": 68, "detections": 25, "severity": "High"}
        delta = compare_historical_points(prev, curr)
        self.assertEqual(delta.score_change, 28)
        self.assertEqual(delta.score_percent_change, 70.0)
        self.assertEqual(delta.detection_count_change, 15)
        self.assertTrue(delta.severity_changed)
        self.assertEqual(delta.trend_direction, "deteriorating")
        self.assertIn("Pollution score increased", delta.summary_text)

    # 9. Location aggregation
    def test_09_location_aggregation(self):
        records = [
            {"location": {"name": "Karwar Point", "latitude": 14.80, "longitude": 74.13}, "summary": {"severity_score": 40, "total_detections": 3}},
            {"location": {"name": "Karwar Point", "latitude": 14.805, "longitude": 74.132}, "summary": {"severity_score": 60, "total_detections": 5}},
            {"location": {"name": "Malpe Beach", "latitude": 13.35, "longitude": 74.70}, "summary": {"severity_score": 20, "total_detections": 1}},
        ]
        clusters = aggregate_location_intelligence(records, cluster_distance_km=5.0)
        self.assertEqual(len(clusters), 2)
        karwar = next(c for c in clusters if "Karwar" in c.location)
        self.assertEqual(karwar.analysis_count, 2)
        self.assertEqual(karwar.total_detections, 8)
        self.assertEqual(karwar.average_score, 50)

    # 10. Hotspot calculation & ranking
    def test_10_hotspot_calculation(self):
        records = [
            {"location": {"name": "Clean Zone", "latitude": 12.0, "longitude": 75.0}, "summary": {"severity_score": 15, "total_detections": 1}},
            {"location": {"name": "Critical Zone", "latitude": 14.8, "longitude": 74.1}, "summary": {"severity_score": 88, "total_detections": 20}},
        ]
        clusters = aggregate_location_intelligence(records, hotspot_score_threshold=60)
        hotspots = [c for c in clusters if c.is_hotspot]
        self.assertEqual(len(hotspots), 1)
        self.assertEqual(hotspots[0].location, "Critical Zone")
        self.assertEqual(clusters[0].risk_rank, 1)

    # 11. Trend calculation
    def test_11_trend_calculation(self):
        points = [
            {"date": "2026-09-01", "score": 30, "detections": 5, "severity": "Moderate"},
            {"date": "2026-09-05", "score": 45, "detections": 12, "severity": "Moderate"},
            {"date": "2026-09-10", "score": 75, "detections": 22, "severity": "High"},
        ]
        trends = calculate_trends(points)
        self.assertEqual(len(trends.dates), 3)
        self.assertEqual(trends.trend_direction, "deteriorating")
        self.assertEqual(trends.highest_risk_period, "2026-09-10")
        self.assertGreater(trends.percentage_change, 0)

    # 12. Severity score boundary conditions
    def test_12_severity_boundaries(self):
        self.assertEqual(score_to_severity_level(0), SeverityLevel.CLEAN)
        self.assertEqual(score_to_severity_level(1), SeverityLevel.LOW)
        self.assertEqual(score_to_severity_level(29), SeverityLevel.LOW)
        self.assertEqual(score_to_severity_level(30), SeverityLevel.MODERATE)
        self.assertEqual(score_to_severity_level(59), SeverityLevel.MODERATE)
        self.assertEqual(score_to_severity_level(60), SeverityLevel.HIGH)
        self.assertEqual(score_to_severity_level(84), SeverityLevel.HIGH)
        self.assertEqual(score_to_severity_level(85), SeverityLevel.CRITICAL)
        self.assertEqual(score_to_severity_level(100), SeverityLevel.CRITICAL)

    # 13. Invalid confidence bounds handling
    def test_13_invalid_confidence_values(self):
        # Clamped via validator
        det_over = Detection(class_name="marine_debris", confidence=1.5, bbox=[0, 0, 10, 10])
        det_under = Detection(class_name="marine_debris", confidence=-0.5, bbox=[0, 0, 10, 10])
        self.assertEqual(det_over.confidence, 1.0)
        self.assertEqual(det_under.confidence, 0.0)

    # 14. Malformed detection data resilience
    def test_14_malformed_detection_data(self):
        raw_dets = [
            {"class_name": "marine_debris", "confidence": 0.85, "bbox": [10, 10, 100, 100]},
            "totally_invalid_string",
            None,
            {"broken": "keys_without_bbox"},
            ("marine_debris", 0.90, [20, 20, 80, 80]),
        ]
        sev, score, breakdown = calculate_severity(raw_dets)
        # Should gracefully ignore corrupted items and score valid ones
        self.assertEqual(breakdown["total_detections"], 2)
        self.assertGreater(score, 0)

    # Bonus: Report generation & HTML render
    def test_15_report_generation(self):
        analysis = analyze_single_result(
            "TEST-ANL",
            [Detection(class_name="marine_debris", confidence=0.88, bbox=[10, 10, 100, 100])],
            location=Location(name="Karwar", latitude=14.8, longitude=74.1),
        )
        report_data = build_analysis_report(analysis)
        html_out = render_html_report(report_data)
        self.assertIn("<!DOCTYPE html>", html_out)
        self.assertIn("MARINEGUARD AI", html_out)
        self.assertIn("TEST-ANL", html_out)


if __name__ == "__main__":
    unittest.main()
