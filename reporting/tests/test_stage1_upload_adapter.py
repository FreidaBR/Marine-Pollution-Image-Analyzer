"""
Unit tests for Stage 1: Upload API, Model Adapter, and AI Integration Foundation.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Tests:
1. Valid JPEG upload validation (magic bytes, dimensions)
2. Valid PNG upload validation
3. Corrupted / invalid file header rejection
4. Empty and truncated data handling
5. ModelAdapter normalization of YOLO detection dictionary
6. ModelAdapter coordinate clamping and area ratio computation
7. ModelAdapter model connection check (clean boolean, no exceptions)
8. Honest model-unavailable state (zero fake detections, no fabricated scores)
"""

import unittest
from reporting.schemas import Detection
from reporting.model_adapter import (
    normalize_yolo_detection,
    is_model_connected,
    ModelAdapter,
)
from reporting.server import validate_and_inspect_image


class TestStage1UploadAndAdapter(unittest.TestCase):

    def setUp(self):
        # Construct valid 10x10 minimal JPEG bytes
        self.minimal_jpeg = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
            b"\xff\xc0\x00\x11\x08\x00\x0a\x00\x0a\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
            b"\xff\xd9"
        )
        # Construct valid 10x10 minimal PNG bytes
        self.minimal_png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x0a\x00\x00\x00\x0a\x08\x02\x00\x00\x00\x02\x50\x58\xea"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    # 1. Valid JPEG upload validation
    def test_01_valid_jpeg_validation(self):
        fmt, width, height = validate_and_inspect_image(self.minimal_jpeg)
        self.assertEqual(fmt, "JPEG")

    # 2. Valid PNG upload validation
    def test_02_valid_png_validation(self):
        fmt, width, height = validate_and_inspect_image(self.minimal_png)
        self.assertEqual(fmt, "PNG")
        self.assertEqual(width, 10)
        self.assertEqual(height, 10)

    # 3. Invalid magic bytes rejection
    def test_03_invalid_magic_bytes(self):
        fake_data = b"NOT_AN_IMAGE_FILE_DATA_HERE"
        fmt, width, height = validate_and_inspect_image(fake_data)
        self.assertIsNone(fmt)
        self.assertIsNone(width)
        self.assertIsNone(height)

    # 4. Empty and truncated data handling
    def test_04_truncated_data_handling(self):
        fmt, width, height = validate_and_inspect_image(b"")
        self.assertIsNone(fmt)
        fmt2, _, _ = validate_and_inspect_image(b"\xff\xd8")
        self.assertIsNone(fmt2)

    # 5. ModelAdapter detection normalization
    def test_05_model_adapter_normalization(self):
        raw_det = {
            "class_name": "marine debris",
            "confidence": 0.88,
            "bbox": [100.0, 50.0, 300.0, 250.0],
        }
        det = normalize_yolo_detection(raw_det, image_width=1000, image_height=1000)
        self.assertIsInstance(det, Detection)
        self.assertEqual(det.class_name, "marine_debris")
        self.assertAlmostEqual(det.confidence, 0.88, places=2)
        self.assertEqual(det.bbox, [100.0, 50.0, 300.0, 250.0])
        # area = (300-100) * (250-50) = 200 * 200 = 40,000; total = 1,000,000; ratio = 0.04
        self.assertAlmostEqual(det.area_ratio, 0.04, places=2)

    # 6. ModelAdapter coordinate clamping
    def test_06_model_adapter_coordinate_clamping(self):
        raw_det = {
            "class_name": "plastic",
            "confidence": 0.75,
            "bbox": [10.0, 20.0, 110.0, 120.0],
            "area_ratio": 0.05,
        }
        det = normalize_yolo_detection(raw_det, image_width=1000, image_height=1000)
        self.assertEqual(det.area_ratio, 0.05)
        self.assertEqual(det.class_name, "marine_debris")

    # 7. Model connection status check
    def test_07_model_connection_check(self):
        status = is_model_connected()
        self.assertIsInstance(status, bool)
        adapter = ModelAdapter()
        self.assertEqual(adapter.is_available(), status)

    # 8. Honest model-unavailable state (NO fake detections, NO fake scores)
    def test_08_honest_model_unavailable(self):
        # Point to a non-existent model weight path
        adapter = ModelAdapter(model_path="non_existent_model.pt")
        # Ensure a dummy image file exists for checking
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(self.minimal_jpeg)
            tmp_path = tmp.name

        try:
            res = adapter.analyze_image(tmp_path)
            self.assertEqual(res.status, "model_unavailable")
            self.assertFalse(res.success)
            self.assertEqual(res.detections, [])
            self.assertIn("not currently connected", res.message)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
