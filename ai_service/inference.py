from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


MODEL_PATH = Path(__file__).resolve().parent / "model" / "plastic_trash_detector.pt"


@lru_cache(maxsize=1)
def get_model() -> YOLO:
	"""Load the detector once per worker process."""
	if not MODEL_PATH.exists():
		raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
	return YOLO(str(MODEL_PATH))


def detect_image(image_bytes: bytes, confidence: float = 0.25) -> list[dict]:
	"""Run plastic detection on an uploaded image and return JSON-safe results."""
	image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
	if image is None:
		raise ValueError("The uploaded file is not a readable image")

	model = get_model()
	results = model.predict(source=image, conf=confidence, verbose=False)
	detections = []

	for result in results:
		if result.boxes is None:
			continue

		for box in result.boxes:
			class_id = int(box.cls[0])
			detections.append(
				{
					"class_id": class_id,
					"class_name": model.names[class_id],
					"confidence": round(float(box.conf[0]), 4),
					"bbox": [round(float(value), 2) for value in box.xyxy[0].tolist()],
				}
			)

	return detections
