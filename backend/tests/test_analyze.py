import io

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _fake_image_file():
    return {"image": ("test.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")}


def test_analyze_returns_mock_detections_and_persists(client):
    response = client.post(
        "/api/v1/analyze",
        files=_fake_image_file(),
        data={"location_name": "Karwar Coast", "latitude": "14.80", "longitude": "74.13"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["analysis_id"].startswith("ANL-")
    assert body["status"] == "completed"
    assert body["image_url"] == f"/uploads/{body['analysis_id']}.jpg"
    assert body["location"] == {"name": "Karwar Coast", "latitude": 14.80, "longitude": 74.13}
    assert body["report_url"] == f"/api/v1/reports/{body['analysis_id']}"

    assert len(body["detections"]) >= 1
    for detection in body["detections"]:
        assert "class_name" in detection
        assert 0.0 <= detection["confidence"] <= 1.0
        assert len(detection["bbox"]) == 4
        assert 0.0 <= detection["area_ratio"] <= 1.0

    summary = body["summary"]
    assert summary["severity"] in {"Low", "Moderate", "High", "Critical"}
    assert 0 <= summary["severity_score"] <= 100
    assert summary["total_detections"] == len(body["detections"])

    # The analysis should now be retrievable individually...
    analysis_id = body["analysis_id"]
    get_response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert get_response.status_code == 200
    assert get_response.json()["analysis_id"] == analysis_id

    # ...and appear in the list endpoint.
    list_response = client.get("/api/v1/analyses")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    assert any(item["analysis_id"] == analysis_id for item in list_body["items"])

    # ...and its report should be buildable.
    report_response = client.get(f"/api/v1/reports/{analysis_id}")
    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["analysis_id"] == analysis_id
    assert len(report_body["recommendations"]) >= 1


def test_analyze_without_location_omits_it(client):
    response = client.post("/api/v1/analyze", files=_fake_image_file())
    assert response.status_code == 200
    assert response.json()["location"] is None


def test_get_analysis_404_for_unknown_id(client):
    response = client.get("/api/v1/analyses/ANL-9999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_report_404_for_unknown_id(client):
    response = client.get("/api/v1/reports/not-a-real-id")
    assert response.status_code == 404


def test_analyze_rejects_non_image_file(client):
    response = client.post(
        "/api/v1/analyze",
        files={"image": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "invalid_file_type"


def test_analyze_ids_are_unique_per_upload(client):
    first = client.post("/api/v1/analyze", files=_fake_image_file()).json()
    second = client.post("/api/v1/analyze", files=_fake_image_file()).json()
    assert first["analysis_id"] != second["analysis_id"]
