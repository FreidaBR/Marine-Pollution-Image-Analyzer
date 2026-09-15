# Shared API Contract

**Frozen.** This mirrors the contract in the team's project-context document
(`Marine_Pollution_Image_Analyzer_Agent_Project_Context.docx`, section 8) and
is implemented end-to-end in `backend/` today (mock inference mode). Do not
rename fields, routes, or data formats without telling the whole team.

Base URL (local dev): `http://localhost:8000` (`VITE_API_BASE_URL` in `.env`).

## Contract rules

- snake_case for all JSON fields.
- Bounding boxes: `[x_min, y_min, x_max, y_max]`.
- Confidence values: `0.0`–`1.0`.
- Class names come from a shared enum/list (see
  `backend/app/core/pollution_classes.py` / `ai_service/labels.py`):
  `plastic_debris`, `oil_slick`, `algal_bloom`, `other_contamination`,
  `clean_reference`.
- Severity: `"Low" | "Moderate" | "High" | "Critical"`, plus a `severity_score`
  (0–100) for finer-grained comparison — see the severity table below.
- Timestamps: ISO 8601.
- Errors: `{"error": {"code": "...", "message": "..."}}`.
- The frontend must use one centralized API client.

## Endpoints

### `GET /health`

`{"status": "ok"}` — basic connectivity check.

### `POST /api/v1/analyze`

Multipart form-data:

- `image` (required, file) — jpeg/png/webp, ≤ `MAX_UPLOAD_SIZE_MB` (default 10MB)
- `location_name` (optional, string)
- `latitude` (optional, number)
- `longitude` (optional, number)
- `observation_date` (optional, ISO date/datetime string)

Response `200`:

```json
{
  "analysis_id": "ANL-0001",
  "status": "completed",
  "image_url": "/uploads/ANL-0001.jpg",
  "location": { "name": "Karwar Coast", "latitude": 14.8, "longitude": 74.13 },
  "detections": [
    {
      "class_name": "plastic_debris",
      "confidence": 0.91,
      "bbox": [120, 80, 340, 260],
      "area_ratio": 0.04
    }
  ],
  "summary": {
    "dominant_category": "plastic_debris",
    "total_detections": 1,
    "severity": "Moderate",
    "severity_score": 58
  },
  "report_url": "/api/v1/reports/ANL-0001"
}
```

`location` is `null` when none of the location fields were provided.
Response `400` (invalid file type/size/empty) uses the standard error envelope.

### `GET /api/v1/analyses?limit=20&offset=0`

```json
{
  "total": 1,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "analysis_id": "ANL-0001",
      "image_url": "/uploads/ANL-0001.jpg",
      "created_at": "...",
      "summary": { "...": "same shape as above" }
    }
  ]
}
```

### `GET /api/v1/analyses/{analysis_id}`

Same shape as the `POST /api/v1/analyze` response. `404` (standard error
envelope) if the id doesn't exist.

### `GET /api/v1/reports/{analysis_id}`

```json
{
  "analysis_id": "ANL-0001",
  "generated_at": "...",
  "image_name": "beach.jpg",
  "location": { "...": "or null" },
  "detections": ["..."],
  "severity": "Moderate",
  "severity_score": 58,
  "recommendations": ["Inspect the area in person and consider a cleanup effort."],
  "disclaimer": "This report reflects visible-indicator estimates from image analysis, not laboratory-confirmed contamination."
}
```

`404` if the analysis id doesn't exist.

### `GET /uploads/{filename}`

Static file serving for the uploaded images referenced by `image_url`.

## Severity table (project brief, section on severity logic)

| Level    | Example rule                                                  | Action                         |
| -------- | ------------------------------------------------------------- | ------------------------------ |
| Low      | Few low-confidence or isolated indicators                     | Monitor and document           |
| Moderate | Several visible indicators or medium confidence               | Inspect area, consider cleanup |
| High     | Multiple clear indicators, oil-like pattern, or dense waste   | Prioritize field verification  |
| Critical | Extensive visible contamination or multiple severe indicators | Notify responsible authority   |

## Contract between backend and the model (`ai_service`)

The backend calls `ai_service` **in-process** (a direct Python import — no
HTTP), via `backend/app/services/inference_service.py`. To plug in the real
model, implement:

```python
# ai_service/inference.py
def run_inference(
    image_path: str, model_path: str, confidence_threshold: float
) -> list[dict]:
    """Each dict: {"class_name": str, "confidence": float,
    "bbox": [x_min, y_min, x_max, y_max], "area_ratio": float}.

    Maps directly onto Ultralytics YOLO `Results.boxes` output
    (xyxy for bbox, conf for confidence, cls -> class_name via labels.py) —
    see https://github.com/venkataramaraoguttikonda/marine-debris-detection-yolov8
    (single class: "marine debris" in that base repo; map/extend to the
    shared class list above as the model supports).
    """
```

Optional:

```python
# ai_service/labels.py
LABELS: list[str] = [...]  # shared class-name list; used by the mock
                            # provider too, so mock output matches the real
                            # model's vocabulary
```

Switch the backend to use it by setting in `.env`:

```
AI_MODE=real
MODEL_PATH=/path/to/weights.pt
```

No other backend or frontend code changes needed.

## Contract between backend and reporting (`reporting`)

Optional hooks — the backend already computes a documented severity
heuristic and a basic JSON report, and will prefer real implementations once
available:

```python
# reporting/severity.py
def calculate_severity(detections: list[dict]) -> dict:
    """detections: [{"class_name": str, "confidence": float,
    "bbox": [...], "area_ratio": float}]
    Returns {"severity": "Low"|"Moderate"|"High"|"Critical",
    "severity_score": int (0-100)}."""

# reporting/report_builder.py
def build_report(analysis: dict) -> dict:
    """analysis: {"analysis_id", "image_name", "location", "detections",
    "severity", "severity_score", "created_at"}.
    Returns a dict with at least "recommendations": list[str] — add
    HTML/PDF export fields here as that work is built out."""
```

## Not yet implemented (flagged, not silently skipped)

- PDF/HTML report rendering — `GET /api/v1/reports/{id}` currently returns
  JSON only; Member 4's `reporting/report_builder.py` is expected to add the
  HTML/PDF path.
- Auth — none yet; not required for the hackathon MVP.
