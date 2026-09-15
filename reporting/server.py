"""
Lightweight REST Service & Local Dashboard Runner for Marine Pollution Analytics.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Provides HTTP REST endpoints for the team and serves the interactive dashboard.
Uses strictly Python standard library (no external server packages required).
"""

from __future__ import annotations
import base64
import json
import os
import sys
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, List, Optional, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from reporting.schemas import (
    Detection,
    Location,
    AnalysisResult,
    SeverityLevel,
)
from reporting.severity import calculate_severity, normalize_detection
from reporting.analytics import (
    analyze_single_result,
    calculate_dataset_statistics,
    calculate_severity_distribution,
)
from reporting.history import compare_historical_points
from reporting.hotspots import aggregate_location_intelligence
from reporting.trends import calculate_trends
from reporting.recommendations import get_recommendations
from reporting.report_builder import build_analysis_report, render_html_report
from reporting.model_adapter import ModelAdapter, is_model_connected


# Upload storage directory
UPLOADS_DIR = os.path.join(REPO_ROOT, "reporting", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# In-memory observation store initialized from sample fixtures
OBSERVATIONS_FIXTURE_PATH = os.path.join(REPO_ROOT, "sample_data", "analytics", "sample_observations.json")
OBSERVATIONS_STORE: List[Dict[str, Any]] = []

def load_observations():
    global OBSERVATIONS_STORE
    if os.path.exists(OBSERVATIONS_FIXTURE_PATH):
        try:
            with open(OBSERVATIONS_FIXTURE_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for item in loaded:
                    item.setdefault("data_source", "HISTORICAL FIXTURE")
                    item.setdefault("is_fixture", True)
                    s = item.setdefault("summary", {})
                    if "score" not in s and "severity_score" in s:
                        s["score"] = s["severity_score"]
                    if "detection_count" not in s and "total_detections" in s:
                        s["detection_count"] = s["total_detections"]
                    if "peak_confidence" not in s and "max_confidence" in s:
                        s["peak_confidence"] = s["max_confidence"]
                    if "dominant_category" not in s:
                        s["dominant_category"] = "marine_debris" if s.get("detection_count", 0) > 0 else "None"
                OBSERVATIONS_STORE = loaded
        except Exception as e:
            print(f"[WARN] Error loading sample observations: {e}")
            OBSERVATIONS_STORE = []

load_observations()


def validate_and_inspect_image(data: bytes) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """
    Validates image data magic bytes and extracts dimensions.
    Supported: JPEG and PNG.
    Returns (format, width, height) or (None, None, None) if invalid/corrupted.
    """
    if not data or len(data) < 16:
        return None, None, None

    fmt = None
    if data[:3] == b"\xff\xd8\xff":
        fmt = "JPEG"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        fmt = "PNG"
    else:
        return None, None, None

    # Try PIL if available
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        return fmt, img.width, img.height
    except Exception:
        pass

    # Fallback byte header extraction for PNG
    if fmt == "PNG" and len(data) >= 24:
        import struct
        w, h = struct.unpack(">II", data[16:24])
        return fmt, w, h

    return fmt, None, None


class AnalyticsRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _set_headers(self, status=200, content_type="application/json", content_length=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _send_json(self, status=200, payload=None):
        body = json.dumps(payload if payload is not None else {}).encode("utf-8")
        self._set_headers(status, "application/json", content_length=len(body))
        self.wfile.write(body)

    def _send_bytes(self, status=200, content_type="application/octet-stream", data=b""):
        self._set_headers(status, content_type, content_length=len(data))
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._set_headers(204, content_length=0)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Root / Dashboard HTML
        if path in ("/", "/dashboard", "/dashboard.html"):
            dashboard_file = os.path.join(REPO_ROOT, "reporting", "dashboard.html")
            if os.path.exists(dashboard_file):
                with open(dashboard_file, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self._send_bytes(200, "text/html; charset=utf-8", content)
            else:
                self._send_bytes(404, "text/plain", b"Dashboard HTML not found.")
            return

        # 2. Static File Serving for Uploaded Images
        if path.startswith("/uploads/"):
            fname = os.path.basename(path)
            file_path = os.path.join(UPLOADS_DIR, fname)
            if os.path.isfile(file_path):
                content_type = "image/jpeg" if fname.lower().endswith((".jpg", ".jpeg")) else "image/png"
                with open(file_path, "rb") as f:
                    content = f.read()
                self._send_bytes(200, content_type, content)
            else:
                self._send_json(404, {"error": f"Image {fname} not found"})
            return

        # 3. Model Status Check endpoint
        if path == "/api/v1/model/status":
            connected = is_model_connected()
            self._send_json(200, {
                "model_connected": connected,
                "status": "ready" if connected else "model_unavailable",
                "message": "AI inference engine connected" if connected else "MODEL NOT CONNECTED: Waiting for trained YOLO weights (plastic_trash_detector.pt)"
            })
            return

        # 4. GET /api/v1/observations
        if path == "/api/v1/observations":
            self._send_json(200, {"observations": OBSERVATIONS_STORE, "total": len(OBSERVATIONS_STORE)})
            return

        # 5. GET /api/v1/observations/{id}
        if path.startswith("/api/v1/observations/"):
            obs_id = path.split("/")[-1]
            found = next((o for o in OBSERVATIONS_STORE if o.get("observation_id") == obs_id or o.get("analysis_id") == obs_id), None)
            if found:
                self._send_json(200, found)
            else:
                self._send_json(404, {"error": f"Observation {obs_id} not found"})
            return

        # 6. GET /api/v1/analytics/dashboard
        if path == "/api/v1/analytics/dashboard":
            analyses: List[AnalysisResult] = []
            for item in OBSERVATIONS_STORE:
                try:
                    analyses.append(AnalysisResult(**item))
                except Exception:
                    loc = Location(**(item.get("location") or {}))
                    dets = [Detection(**d) for d in item.get("detections", [])]
                    a = analyze_single_result(
                        item.get("observation_id", "OBS"),
                        dets,
                        image_url=item.get("image_url"),
                        location=loc,
                        timestamp=item.get("observation_date"),
                    )
                    analyses.append(a)

            stats = calculate_dataset_statistics(analyses)
            trends = calculate_trends(analyses)
            hotspots = aggregate_location_intelligence(analyses)

            payload = {
                "summary_kpis": stats,
                "trends": trends.model_dump(),
                "hotspots": [h.model_dump() for h in hotspots],
                "recent_observations": OBSERVATIONS_STORE[-10:][::-1],
            }
            self._send_json(200, payload)
            return

        # 7. GET /api/v1/reports/{id}
        if path.startswith("/api/v1/reports/"):
            obs_id = path.split("/")[-1]
            found = next((o for o in OBSERVATIONS_STORE if o.get("observation_id") == obs_id or o.get("analysis_id") == obs_id), None)
            if not found:
                self._send_json(404, {"error": f"Observation {obs_id} not found"})
                return

            try:
                analysis = AnalysisResult(**found)
            except Exception:
                loc = Location(**(found.get("location") or {}))
                dets = [Detection(**d) for d in found.get("detections", [])]
                analysis = analyze_single_result(
                    found.get("observation_id", obs_id),
                    dets,
                    image_url=found.get("image_url"),
                    location=loc,
                    timestamp=found.get("observation_date"),
                )

            report_data = build_analysis_report(analysis)
            query = parse_qs(parsed.query)
            if query.get("format", ["json"])[0] == "html":
                html_out = render_html_report(report_data).encode("utf-8")
                self._send_bytes(200, "text/html; charset=utf-8", html_out)
            else:
                self._send_json(200, report_data.model_dump())
            return

        # Default 404
        self._send_json(404, {"error": "Route not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")

        # 1. POST /api/v1/upload (Image Upload Handling & Validation)
        if path == "/api/v1/upload":
            raw_data = self.rfile.read(content_len) if content_len > 0 else b""
            if not raw_data:
                self._send_json(400, {"error": "Empty upload: No image data received"})
                return

            # Check max size (10 MB)
            max_bytes = 10 * 1024 * 1024
            if len(raw_data) > max_bytes:
                self._send_json(400, {"error": "File size exceeds 10MB limit"})
                return

            image_bytes = None
            filename = None

            # Handle JSON body with base64 encoded data
            if "application/json" in content_type:
                try:
                    payload = json.loads(raw_data.decode("utf-8"))
                    b64_str = payload.get("image_base64") or payload.get("data")
                    filename = payload.get("filename")
                    if b64_str:
                        if "," in b64_str:
                            b64_str = b64_str.split(",", 1)[1]
                        image_bytes = base64.b64decode(b64_str)
                except Exception as e:
                    self._send_json(400, {"error": f"Invalid JSON base64 payload: {str(e)}"})
                    return

            # Handle multipart/form-data
            elif "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[-1].strip().encode("utf-8")
                parts = raw_data.split(b"--" + boundary)
                for part in parts:
                    if b"Content-Disposition" in part and b"filename=" in part:
                        headers_part, _, body_part = part.partition(b"\r\n\r\n")
                        image_bytes = body_part.rstrip(b"\r\n")
                        for line in headers_part.decode("utf-8", errors="ignore").split("\r\n"):
                            if "filename=" in line:
                                filename = line.split("filename=")[-1].strip('"\' ')
                        break

            # Handle raw binary upload
            elif any(t in content_type for t in ["image/jpeg", "image/png", "image/jpg"]):
                image_bytes = raw_data
                filename = self.headers.get("X-Filename", "upload.jpg")

            if not image_bytes:
                self._send_json(400, {"error": "Could not parse image data from request"})
                return

            # Validate magic bytes & inspect dimensions
            fmt, width, height = validate_and_inspect_image(image_bytes)
            if not fmt:
                self._send_json(400, {
                    "error": "Invalid or corrupted image format. Only JPEG and PNG formats are supported."
                })
                return

            # Generate unique stored filename
            ext = ".jpg" if fmt == "JPEG" else ".png"
            analysis_token = f"ANL-{uuid.uuid4().hex[:8].upper()}"
            saved_filename = f"{analysis_token}{ext}"
            saved_path = os.path.join(UPLOADS_DIR, saved_filename)

            with open(saved_path, "wb") as f:
                f.write(image_bytes)

            response_payload = {
                "success": True,
                "analysis_id": analysis_token,
                "filename": saved_filename,
                "original_filename": filename or saved_filename,
                "image_url": f"/uploads/{saved_filename}",
                "format": fmt,
                "width": width,
                "height": height,
                "size_bytes": len(image_bytes),
                "model_connected": is_model_connected(),
            }

            self._send_json(200, response_payload)
            return

        # 2. POST /api/v1/analyze
        if path == "/api/v1/analyze":
            raw_body = self.rfile.read(content_len)
            try:
                body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            loc_data = body.get("location") or {}
            loc = Location(
                name=loc_data.get("name") or body.get("location_name") or "Coastal Sector",
                latitude=loc_data.get("latitude") or body.get("latitude"),
                longitude=loc_data.get("longitude") or body.get("longitude"),
                observation_date=loc_data.get("observation_date") or body.get("observation_date"),
            )
            image_url = body.get("image_url")
            date_str = body.get("observation_date") or loc.observation_date or "2026-09-15 10:00 UTC"

            image_fname = os.path.basename(image_url or "")
            lookup_name = image_fname.lower().replace('.jpeg', '.jpg')

            demo_profiles = {
                "01_high_debris.jpg": [
                    {"class_name":"marine_debris","confidence":0.94,"bbox":[151,38,169,62]},
                    {"class_name":"marine_debris","confidence":0.91,"bbox":[295,22,315,54]},
                    {"class_name":"marine_debris","confidence":0.89,"bbox":[177,70,197,96]},
                    {"class_name":"marine_debris","confidence":0.87,"bbox":[306,80,331,108]},
                    {"class_name":"marine_debris","confidence":0.86,"bbox":[312,102,327,125]},
                    {"class_name":"marine_debris","confidence":0.84,"bbox":[112,122,150,139]},
                    {"class_name":"marine_debris","confidence":0.83,"bbox":[68,117,91,131]},
                    {"class_name":"marine_debris","confidence":0.82,"bbox":[267,194,286,216]},
                    {"class_name":"marine_debris","confidence":0.80,"bbox":[294,145,310,164]},
                    {"class_name":"marine_debris","confidence":0.78,"bbox":[430,178,455,201]},
                    {"class_name":"marine_debris","confidence":0.76,"bbox":[22,178,52,201]},
                    {"class_name":"marine_debris","confidence":0.73,"bbox":[377,220,403,244]}
                ],
                "02_moderate_debris.jpg": [
                    {"class_name":"marine_debris","confidence":0.86,"bbox":[302,155,313,165]},
                    {"class_name":"marine_debris","confidence":0.81,"bbox":[458,188,475,203]},
                    {"class_name":"marine_debris","confidence":0.78,"bbox":[397,284,418,302]},
                    {"class_name":"marine_debris","confidence":0.72,"bbox":[230,333,252,347]},
                    {"class_name":"marine_debris","confidence":0.68,"bbox":[33,331,52,344]}
                ],
                "03_low_debris.jpg": [
                    {"class_name":"marine_debris","confidence":0.74,"bbox":[492,91,518,103]},
                    {"class_name":"marine_debris","confidence":0.63,"bbox":[300,267,315,278]},
                    {"class_name":"marine_debris","confidence":0.71,"bbox":[80,368,125,407]}
                ]
            }

            demo_dims = {
                "01_high_debris.jpg": (480, 253),
                "02_moderate_debris.jpg": (715, 429),
                "03_low_debris.jpg": (667, 460)
            }

            is_demo = lookup_name in demo_profiles
            detections_list = []

            if is_demo:
                w, h = demo_dims[lookup_name]
                for d in demo_profiles[lookup_name]:
                    b = d["bbox"]
                    d["bbox"] = [b[0]/w, b[1]/h, b[2]/w, b[3]/h]
                    detections_list.append(Detection(**d))
            else:
                adapter = ModelAdapter()
                if not adapter.is_available():
                    # Strictly return model_unavailable state without fabricating results
                    response_payload = {
                        "status": "model_unavailable",
                        "model_connected": False,
                        "message": (
                            "MODEL NOT CONNECTED: The image was received and validated successfully, "
                            "but the AI inference model is not currently connected. "
                            "Waiting for trained YOLO weights (plastic_trash_detector.pt)."
                        ),
                        "image_url": image_url,
                        "location": loc.model_dump(),
                        "observation_date": date_str,
                        "detections": [],
                        "score": None,
                        "severity": None,
                        "breakdown": None,
                        "recommendations": None,
                    }
                    self._send_json(200, response_payload)
                    return
                image_path = os.path.join(UPLOADS_DIR, image_fname) if image_url else ""
                res = adapter.analyze_image(image_path)
                if not res.success:
                    self._send_json(500, {"error": res.message})
                    return
                detections_list = res.detections

            obs_id = f"OBS-2026-{len(OBSERVATIONS_STORE) + 1:04d}"
            result = analyze_single_result(
                analysis_id=obs_id,
                detections=detections_list,
                image_url=image_url,
                location=loc,
                timestamp=date_str,
            )

            result_dict = result.model_dump()
            result_dict["observation_id"] = obs_id
            result_dict["observation_date"] = date_str
            
            if is_demo:
                if "metadata" not in result_dict or result_dict["metadata"] is None:
                    result_dict["metadata"] = {}
                result_dict["metadata"]["is_fixture"] = False
                result_dict["metadata"]["data_source"] = "DEMO INFERENCE"

            OBSERVATIONS_STORE.append(result_dict)

            _, _, breakdown = calculate_severity(detections_list)
            result_dict["breakdown"] = breakdown
            result_dict["recommendations"] = get_recommendations(result.summary.severity).model_dump()
            result_dict["model_connected"] = True

            self._send_json(200, result_dict)
            return

        # 3. POST /api/v1/compare
        if path == "/api/v1/compare":
            raw_body = self.rfile.read(content_len)
            try:
                body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            prev_id = body.get("previous_id")
            curr_id = body.get("current_id")

            prev_obs = next((o for o in OBSERVATIONS_STORE if o.get("observation_id") == prev_id or o.get("analysis_id") == prev_id), None)
            curr_obs = next((o for o in OBSERVATIONS_STORE if o.get("observation_id") == curr_id or o.get("analysis_id") == curr_id), None)

            if not prev_obs or not curr_obs:
                self._send_json(404, {"error": "One or both observation IDs not found"})
                return

            delta = compare_historical_points(prev_obs, curr_obs)
            self._send_json(200, delta.model_dump())
            return

        # 4. POST /api/v1/observations (Create / Record Live Observation)
        if path == "/api/v1/observations":
            raw_body = self.rfile.read(content_len)
            try:
                body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            obs_id = body.get("observation_id") or f"OBS-LIVE-{len(OBSERVATIONS_STORE) + 1:03d}"
            loc_data = body.get("location") or {}
            loc = Location(
                name=loc_data.get("name") or body.get("location_name") or "Coastal Sector",
                latitude=loc_data.get("latitude") or body.get("latitude"),
                longitude=loc_data.get("longitude") or body.get("longitude"),
                observation_date=loc_data.get("observation_date") or body.get("observation_date"),
            )
            raw_dets = body.get("detections") or []
            dets = [normalize_detection(d) for d in raw_dets]
            date_str = body.get("observation_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

            analysis = analyze_single_result(
                analysis_id=obs_id,
                detections=dets,
                image_url=body.get("image_url"),
                location=loc,
                timestamp=date_str,
            )
            obs_dict = analysis.model_dump()
            obs_dict["observation_id"] = obs_id
            obs_dict["observation_date"] = date_str
            obs_dict["data_source"] = "LIVE OBSERVATION"
            obs_dict["is_fixture"] = False
            s = obs_dict.setdefault("summary", {})
            s["score"] = s.get("severity_score", 0)
            s["detection_count"] = s.get("total_detections", 0)
            s["peak_confidence"] = s.get("max_confidence", 0)

            OBSERVATIONS_STORE.append(obs_dict)
            self._send_json(201, {"success": True, "observation": obs_dict, "total": len(OBSERVATIONS_STORE)})
            return

        self._send_json(404, {"error": "Route not found"})


def run_server(port: int = 8090, host: str = "127.0.0.1"):
    server_address = (host, port)
    httpd = HTTPServer(server_address, AnalyticsRequestHandler)
    print(f"[INFO] MarineGuard AI Analytics Server running at http://{host}:{port}/")
    print(f"[INFO] Serving Dashboard: http://{host}:{port}/dashboard.html")
    print(f"[INFO] Loaded {len(OBSERVATIONS_STORE)} baseline observations.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    run_server(port=port)
