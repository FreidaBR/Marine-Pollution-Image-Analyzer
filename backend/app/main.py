from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_service.inference import detect_image


app = FastAPI(title="Marine Pollution Analyzer API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
	return {
		"message": "Marine Pollution Analyzer API is running",
		"docs": "/docs",
		"health": "/health",
		"analyze": "/analyze",
	}


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)) -> dict:
	"""Analyze an uploaded image with the plastic trash detector."""
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=415, detail="Please upload an image file")

	try:
		detections = detect_image(await file.read())
	except ValueError as error:
		raise HTTPException(status_code=400, detail=str(error)) from error
	except FileNotFoundError as error:
		raise HTTPException(status_code=503, detail=str(error)) from error
	except Exception as error:
		raise HTTPException(status_code=500, detail="Model inference failed") from error

	return {
		"filename": file.filename,
		"detections": detections,
		"count": len(detections),
	}
