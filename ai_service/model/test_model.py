from pathlib import Path
from ultralytics import YOLO

# Get the folder where this script is located
BASE_DIR = Path(__file__).resolve().parent

# The model and image are in the same folder as this script
MODEL_PATH = BASE_DIR / "plastic_trash_detector.pt"
IMAGE_PATH = BASE_DIR / "test1.jpg"

print("Checking files...")
print("Model path:", MODEL_PATH)
print("Image path:", IMAGE_PATH)

# Check that the model exists
if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found at:\n{MODEL_PATH}"
    )

# Check that the test image exists
if not IMAGE_PATH.exists():
    raise FileNotFoundError(
        f"Test image not found at:\n{IMAGE_PATH}"
    )

# Load the model
print("\nLoading model...")
model = YOLO(str(MODEL_PATH))

print("\nModel loaded successfully!")
print("Available classes:")
print(model.names)

# Run prediction
print("\nRunning prediction...")

results = model.predict(
    source=str(IMAGE_PATH),
    conf=0.25,
    save=True,
    project=str(BASE_DIR / "results"),
    name="plastic_test",
    exist_ok=True
)

# Print detected objects
print("\nDetections:")

for result in results:
    if result.boxes is None or len(result.boxes) == 0:
        print("No objects detected.")
        continue

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        bbox = [
            round(value, 2)
            for value in box.xyxy[0].tolist()
        ]

        print({
            "class_name": model.names[class_id],
            "confidence": round(confidence, 3),
            "bbox": bbox
        })

print("\nPrediction completed!")
print("Annotated image saved at:")
print(BASE_DIR / "results" / "plastic_test")