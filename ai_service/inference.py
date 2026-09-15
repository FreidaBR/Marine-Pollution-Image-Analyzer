from functools import lru_cache
from pathlib import Path

import cv2
from ultralytics import YOLO


CLASS_NAME_MAP = {
    "marine debris": "plastic_debris",
    "plastic": "plastic_debris",
}


@lru_cache(maxsize=4)
def get_model(model_path: str) -> YOLO:
    """Load each configured detector once per worker process."""
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError("Configured model weights are unavailable")
    return YOLO(str(path))


def run_inference(
    image_path: str, model_path: str, confidence_threshold: float
) -> list[dict]:
    """Run YOLO and return detections in the backend's frozen contract shape."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("The uploaded file is not a readable image")

    image_height, image_width = image.shape[:2]
    image_area = image_width * image_height
    model = get_model(model_path)
    results = model.predict(source=image, conf=confidence_threshold, verbose=False)
    detections: list[dict] = []

    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
            detections.append(
                {
                    "class_name": CLASS_NAME_MAP.get(class_name, class_name),
                    "confidence": round(float(box.conf[0]), 4),
                    "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                    "area_ratio": round(box_area / image_area, 6),
                }
            )

    return detections
