# main.py
# Ce fichier expose les endpoints HTTP.
# On charge le modèle au démarrage (startup) pour éviter de le recharger à chaque requête.

from pathlib import Path
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from .inference import EmotionVideoInferer
from .schemas import InferenceResponse

app = FastAPI(title="MindVoice Emotion API", version="1.0")

# CORS: autorise le front Next.js (en dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en production, mets l'URL exacte du front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chemin modèle (à adapter)
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "best_model.pt"
inferer = None

@app.on_event("startup")
def load_model_once():
    global inferer
    inferer = EmotionVideoInferer(MODEL_PATH)

@app.post("/infer/video", response_model=InferenceResponse)
async def infer_video(
    file: UploadFile = File(...),
    sample_fps: int = Form(8),
    window_sec: float = Form(1.0),
    conf_thresh: float = Form(0.35),
):
    """
    Reçoit une vidéo via multipart/form-data, la sauvegarde temporairement,
    puis lance l'inférence et renvoie un JSON.
    """
    # Sauvegarde temporaire (important: UploadFile = stream)
    suffix = Path(file.filename).suffix if file.filename else ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Inference
    result = inferer.infer_video(
        tmp_path,
        sample_fps=sample_fps,
        window_sec=window_sec,
        conf_thresh=conf_thresh,
    )

    # Option: tu peux supprimer tmp_path si tu veux
    # tmp_path.unlink(missing_ok=True)

    return result
