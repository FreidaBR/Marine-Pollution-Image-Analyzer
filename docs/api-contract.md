# Shared API Contract

## Analyze image

`POST /analyze` accepts a multipart form upload with the field name `file`.

Successful responses contain the original filename, the number of detections, and
each detection's class, confidence, and `[x1, y1, x2, y2]` bounding box:

```json
{
	"filename": "sample.jpg",
	"count": 1,
	"detections": [
		{
			"class_id": 0,
			"class_name": "plastic",
			"confidence": 0.91,
			"bbox": [12.5, 20.0, 140.25, 180.75]
		}
	]
}
```

`GET /health` returns `{ "status": "ok" }`.
