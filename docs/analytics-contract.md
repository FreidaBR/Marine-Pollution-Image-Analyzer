# Marine Pollution Image Analyzer — Analytics & Intelligence Layer Contract
**Role**: Member 4 (Report, Analytics & Intelligence Engineer)  
**Status**: Frozen for Hackathon Integration  
**Architecture Alignment**: PS-3Y-14 | SDG 14: Life Below Water  

---

## 1. Pipeline Overview & Ownership Boundaries
The product operates on **Single-Image Observations**:
$$\text{ONE OBSERVATION} = \text{ONE IMAGE} + \text{LOCATION (Separate)} + \text{OBSERVATION DATE} + \text{YOLO MODEL DETECTIONS}$$

### Flow Diagram:
```
[ 1. USER UPLOADS SINGLE IMAGE ]
        ↓
[ 2. USER ENTERS SEPARATE LOCATION & DATE ] (location_name, latitude, longitude, date)
        ↓
[ 3. YOLO COMPUTER VISION INFERENCE ] (Member 1 - AI/ML)
        ↓  (Outputs: class_name="marine_debris", confidence [0-1], bbox [x_min, y_min, x_max, y_max])
[ 4. ANALYTICS & INTELLIGENCE LAYER ] (Member 4 - This module)
        ↓  (Calculates: severity score 0-100, why-score-calculated breakdown, recommendations)
[ 5. PERSISTENCE & HISTORY REGISTRY ] (Saved to chronological observation store)
        ↓
[ 6. DASHBOARD / TRENDS / MAP / REPORT ] (Dynamically aggregated for user inspection)
```

---

## 2. Standard Input Contract (YOLO Predictions)
The computer vision model output for a single image must conform to:

```json
{
  "image_url": "/uploads/OBS-2026-0001.jpg",
  "observation_date": "2026-09-15T10:30:00Z",
  "location": {
    "name": "Karwar Coast - Port Jetty Hotspot",
    "latitude": 14.8142,
    "longitude": 74.1351,
    "observation_date": "2026-09-15T10:30:00Z"
  },
  "detections": [
    {
      "class_name": "marine_debris",
      "confidence": 0.96,
      "bbox": [30.0, 40.0, 360.0, 380.0],
      "area_ratio": 0.16
    },
    {
      "class_name": "marine_debris",
      "confidence": 0.93,
      "bbox": [380.0, 70.0, 600.0, 340.0],
      "area_ratio": 0.12
    }
  ]
}
```

### Contract Rules
1. **Field Naming**: Strict `snake_case`.
2. **Bounding Box**: Exactly 4 numbers `[x_min, y_min, x_max, y_max]` in pixel coordinates.
3. **Confidence**: Float strictly bounded in `[0.0, 1.0]`.
4. **Primary Class**: `marine_debris` (Visible floating waste / plastic debris).
5. **Area Ratio**: Optional float `[0.0, 1.0]`. If omitted, density fallback is automatically applied.
6. **Location Independence**: Location is **not encoded in the image**; it is supplied separately via user input.
7. **Scientific Language**: "Visible Pollution Indicators", "Estimated Pollution Severity". Never claim laboratory-confirmed chemical pollution.

---

## 3. Visual Pollution Severity Engine (`reporting/severity.py`)

### Mathematical Model
The composite **Image-Based Visual Pollution Indicator Score** ($S \in [0, 100]$):
$$S = \min\left(100, \max\left(1, S_{\text{count}} + S_{\text{avg\_conf}} + S_{\text{max\_conf}} + S_{\text{coverage}}\right)\right)$$
*(If total detections $= 0$, then $S = 0$, mapped to `Clean`)*

### Component Points Breakdown
- **Count Component** ($S_{\text{count}}$, max 35 pts): $35 \times \min\left(1.0, \frac{\ln(1 + N)}{\ln(1 + 12)}\right)$
- **Mean Confidence** ($S_{\text{avg\_conf}}$, max 20 pts): $20 \times \bar{c}$
- **Peak Confidence** ($S_{\text{max\_conf}}$, max 15 pts): $15 \times c_{\max}$
- **Visible Coverage / Density** ($S_{\text{coverage}}$, max 30 pts):
  - When `area_ratio` provided: $30 \times \min\left(1.0, \frac{\sum a_i}{0.25}\right)$
  - Fallback density: $30 \times \min\left(1.0, \frac{N}{8} \times (0.5 + 0.5 \bar{c})\right)$

### Qualitative Severity Tiers
| Score Range | Severity Tier | Accent Color | Operational Field Directive |
| :--- | :--- | :--- | :--- |
| **0** | `Clean` | Mint (`#34d399`) | Baseline reference; continue routine surveillance |
| **1 – 29** | `Low` | Cyan (`#38bdf8`) | Isolated debris; log observation and continue monitoring |
| **30 – 59** | `Moderate` | Amber (`#fbbf24`) | Several indicators; schedule targeted shoreline inspection |
| **60 – 84** | `High` | Orange (`#fb923c`) | Dense waste; prioritize cleanup unit deployment |
| **85 – 100** | `Critical` | Coral Red (`#f87171`) | Heavy accumulation; notify responsible environmental authority |

---

## 4. REST API Specifications (`reporting/server.py`)

A lightweight Python service is included that exposes the following integration endpoints:

### 1. `POST /api/v1/analyze`
Submits a single image analysis for evaluation.
- **Request Body**:
  ```json
  {
    "image_url": "https://example.com/coastal.jpg",
    "location_name": "Karwar Coast - Port Jetty Hotspot",
    "latitude": 14.8142,
    "longitude": 74.1351,
    "observation_date": "2026-09-15T10:30:00Z",
    "detections": [
      { "class_name": "marine_debris", "confidence": 0.94, "bbox": [50, 60, 320, 340], "area_ratio": 0.09 }
    ]
  }
  ```
- **Response Body**:
  ```json
  {
    "analysis_id": "OBS-2026-0009",
    "status": "completed",
    "image_url": "https://example.com/coastal.jpg",
    "summary": {
      "dominant_category": "marine_debris",
      "total_detections": 1,
      "severity": "Moderate",
      "severity_score": 48,
      "average_confidence": 0.94,
      "max_confidence": 0.94,
      "estimated_coverage": 0.09
    },
    "breakdown": {
      "count_score": 8.7,
      "conf_score": 18.8,
      "peak_score": 14.1,
      "cov_score": 10.8
    }
  }
  ```

### 2. `GET /api/v1/observations`
Returns all verified single-image observations stored in history.

### 3. `POST /api/v1/compare`
Calculates dynamic delta comparison between two observations.
- **Request Body**:
  ```json
  { "previous_id": "OBS-2026-09-001", "current_id": "OBS-2026-09-008" }
  ```
- **Response**: Score delta, percentage change, debris count delta, severity transition (`Moderate → Critical`), and summary text.

### 4. `GET /api/v1/reports/{id}?format=html`
Returns an executive printable observation report.

---

## 5. Team Integration Guide

### AI / ML Engineer (Member 1)
When your model runs inference on an uploaded image, simply pass the resulting list of `{ class_name, confidence, bbox, area_ratio }` to `POST /api/v1/analyze` or `reporting.analyze_single_result()`.

### Backend Engineer (Member 3)
Import functions directly from `reporting`:
```python
from reporting import analyze_single_result, compare_historical_points, calculate_dataset_statistics
```

### Frontend Engineer (Member 2 & 5)
Consume the REST endpoints or mount `reporting/dashboard.html` as the interactive monitoring dashboard.
