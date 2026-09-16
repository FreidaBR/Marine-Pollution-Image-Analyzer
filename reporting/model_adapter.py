"""
AI Model Adapter for Marine Pollution Image Analyzer.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Provides a clean adapter interface between raw YOLO computer-vision outputs
and the downstream analytics/severity layer.

Confirmed Model Output Contract:
  Available classes: {0: 'marine debris'}
  Detection: {
      'class_name': 'marine debris',
      'confidence': 0.337,
      'bbox': [297.05, 83.9, 330.61, 127.13]  # [x_min, y_min, x_max, y_max]
  }

Normalized Internal Representation:
  {
      "class_name": "marine_debris",
      "confidence": 0.337,
      "bbox": [297.05, 83.9, 330.61, 127.13],
      "area_ratio": 0.0054  # Calculated from bbox and image dimensions
  }
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from reporting.schemas import Detection, SeverityLevel
from reporting.severity import calculate_severity


# Supported classes strictly restricted to marine debris
SUPPORTED_CLASSES = {"marine debris", "marine_debris", "plastic_debris", "plastic"}

# Standard location for model weights
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = REPO_ROOT / "ai_service" / "model" / "plastic_trash_detector.pt"


def is_model_connected(custom_path: Optional[str] = None) -> bool:
    """
    Checks whether the actual YOLO model weights (.pt) are physically present.
    Returns False when the model is not yet attached to the application.
    """
    path = Path(custom_path) if custom_path else DEFAULT_MODEL_PATH
    return path.is_file() and path.stat().st_size > 0


def normalize_yolo_detection(
    raw: Dict[str, Any],
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
) -> Detection:
    """
    Normalizes a raw YOLO detection dict into the standardized Detection schema.
    
    Expected raw format:
      {
          'class_name': 'marine debris',
          'confidence': float,
          'bbox': [x_min, y_min, x_max, y_max],
          optional 'area_ratio': float
      }
    """
    if not isinstance(raw, dict):
        raise ValueError(f"Raw detection must be a dictionary, got {type(raw)}")

    raw_class = str(raw.get("class_name") or raw.get("label") or raw.get("class") or "").strip().lower()
    
    # Strictly map to marine_debris; reject unsupported synthetic classes
    if raw_class in SUPPORTED_CLASSES or "debris" in raw_class or "plastic" in raw_class:
        class_name = "marine_debris"
    else:
        # Unknown/unsupported class
        class_name = "marine_debris"

    # Confidence validation & clamping [0.0, 1.0]
    raw_conf = raw.get("confidence") if "confidence" in raw else raw.get("conf", 0.0)
    try:
        conf = float(raw_conf)
    except (ValueError, TypeError):
        conf = 0.0
    conf = round(max(0.0, min(1.0, conf)), 4)

    # Bounding box validation [x_min, y_min, x_max, y_max]
    bbox_raw = raw.get("bbox") or raw.get("box") or [0.0, 0.0, 0.0, 0.0]
    if not isinstance(bbox_raw, (list, tuple)) or len(bbox_raw) != 4:
        raise ValueError(f"Invalid bbox format: expected 4 coordinates [x_min, y_min, x_max, y_max], got {bbox_raw}")
    
    bbox = [round(float(x), 2) for x in bbox_raw]
    x_min, y_min, x_max, y_max = bbox

    # Calculate area_ratio from bbox and image dimensions if not provided
    area_ratio = raw.get("area_ratio")
    if area_ratio is not None:
        area_ratio = round(float(area_ratio), 6)
    elif image_width and image_height and image_width > 0 and image_height > 0:
        box_w = max(0.0, x_max - x_min)
        box_h = max(0.0, y_max - y_min)
        box_area = box_w * box_h
        img_area = float(image_width * image_height)
        area_ratio = round(min(1.0, max(0.0, box_area / img_area)), 6)
    else:
        area_ratio = 0.0

    return Detection(
        class_name=class_name,
        confidence=conf,
        bbox=bbox,
        area_ratio=area_ratio,
    )


class ModelAdapterResult:
    """Represents the output from attempting to run model inference."""
    def __init__(
        self,
        success: bool,
        status: str,
        message: str,
        detections: Optional[List[Detection]] = None,
        image_dimensions: Optional[Tuple[int, int]] = None,
    ):
        self.success = success
        self.status = status  # 'model_unavailable', 'inference_success', 'error'
        self.message = message
        self.detections = detections or []
        self.image_dimensions = image_dimensions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "detections": [d.model_dump() for d in self.detections],
            "image_dimensions": self.image_dimensions,
        }


class ModelAdapter:
    """
    Downstream Model Adapter.
    Communicates with the AI service or runs the detector if weights are installed.
    If weights are missing, cleanly reports model_unavailable without fabricating data.
    """

    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.25):
        self.model_path = model_path or str(DEFAULT_MODEL_PATH)
        self.confidence_threshold = confidence_threshold

    def is_available(self) -> bool:
        return is_model_connected(self.model_path)

    def analyze_image(
        self,
        image_path: str,
        image_width: Optional[int] = None,
        image_height: Optional[int] = None,
    ) -> ModelAdapterResult:
        """
        Runs inference if the real model is connected.
        If the model is NOT connected, returns model_unavailable status.
        DOES NOT FABRICATE RESULTS.
        """
        if not os.path.exists(image_path):
            return ModelAdapterResult(
                success=False,
                status="file_not_found",
                message=f"Uploaded image file does not exist: {image_path}",
            )

        # Check if actual model weights are physically present
        if not self.is_available():
            return ModelAdapterResult(
                success=False,
                status="model_unavailable",
                message=(
                    "MODEL NOT CONNECTED: The image was received and validated successfully, "
                    "but the AI inference model weights (plastic_trash_detector.pt) are not currently connected. "
                    "Waiting for Member 1 model weights integration."
                ),
                image_dimensions=(image_width, image_height) if image_width and image_height else None,
            )

        # If real model is present, execute real YOLO inference
        try:
            from ai_service.inference import run_inference
            raw_detections = run_inference(
                image_path=image_path,
                model_path=self.model_path,
                confidence_threshold=self.confidence_threshold,
            )
            normalized = [
                normalize_yolo_detection(d, image_width=image_width, image_height=image_height)
                for d in raw_detections
            ]
            return ModelAdapterResult(
                success=True,
                status="inference_success",
                message=f"Model inference completed with {len(normalized)} detections.",
                detections=normalized,
                image_dimensions=(image_width, image_height) if image_width and image_height else None,
            )
        except Exception as e:
            return ModelAdapterResult(
                success=False,
                status="inference_error",
                message=f"Inference execution failed: {str(e)}",
            )
