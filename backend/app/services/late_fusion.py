"""
Late Fusion Audio + Video Inference Service

This module provides multimodal emotion inference by combining:
- Vision model (ResNet-18): 8 emotions from facial expressions
- Audio model (Wav2Vec2): 8 emotions from speech

Late fusion at logits level produces 9 final emotion probabilities:
anger, calm, contempt, disgust, fear, happy, neutral, sad, surprise
"""

from pathlib import Path
import subprocess
import tempfile
import shutil
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2

# Default device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ImageNet normalization constants
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406])
IMAGENET_STD = np.array([0.229, 0.224, 0.225])


def strip_prefix(state_dict, prefixes=("module.", "model.")):
    """Remove prefixes from state_dict keys (e.g., from DataParallel training)."""
    clean_sd = {}
    for k, v in state_dict.items():
        for p in prefixes:
            if k.startswith(p):
                k = k[len(p):]
        clean_sd[k] = v
    return clean_sd


def ordered_labels(idx_to_emotion):
    """Get labels in order from checkpoint mapping."""
    if isinstance(idx_to_emotion, dict):
        return [idx_to_emotion.get(i, idx_to_emotion.get(str(i)))
                for i in range(len(idx_to_emotion))]
    return list(idx_to_emotion)


# ============================================================
# Video Preprocessing
# ============================================================

def preprocess_frame(frame_bgr, img_size):
    """Prepare a BGR frame for ResNet18 inference."""
    frame = cv2.resize(frame_bgr, (img_size, img_size))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = frame / 255.0
    frame = (frame - IMAGENET_MEAN) / IMAGENET_STD
    frame = np.transpose(frame, (2, 0, 1))  # HWC -> CHW
    return torch.tensor(frame, dtype=torch.float32)


def sample_frames(video_path, num_frames=16):
    """Uniformly sample frames from a video."""
    video_path = Path(video_path)

    # Try direct OpenCV first
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # If OpenCV can't read frame count (common with webm), convert via ffmpeg
    if total <= 0:
        cap.release()
        ffmpeg = _guess_ffmpeg()
        if ffmpeg:
            # Convert to mp4 which OpenCV handles better
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                subprocess.run(
                    [ffmpeg, "-y", "-i", str(video_path), "-c:v", "libx264",
                     "-preset", "ultrafast", "-crf", "23", tmp_path],
                    capture_output=True, check=True
                )
                cap = cv2.VideoCapture(tmp_path)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                if total <= 0:
                    cap.release()
                    Path(tmp_path).unlink(missing_ok=True)
                    return []

                frames = _extract_frames(cap, total, num_frames)
                cap.release()
                Path(tmp_path).unlink(missing_ok=True)
                return frames
            except subprocess.CalledProcessError:
                Path(tmp_path).unlink(missing_ok=True)
                return []
        return []

    frames = _extract_frames(cap, total, num_frames)
    cap.release()
    return frames


def _extract_frames(cap, total, num_frames):
    """Extract uniformly spaced frames from an open VideoCapture."""
    idxs = np.linspace(0, total - 1, num_frames).astype(int)
    frames = []

    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, frame = cap.read()
        if ok:
            frames.append(frame)

    return frames


# ============================================================
# Audio Extraction
# ============================================================

def _guess_ffmpeg():
    """Find ffmpeg executable."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    # Windows fallback paths
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def extract_audio(video_path, wav_path, sr=16000, ffmpeg_path=None):
    """Extract mono audio from video using ffmpeg."""
    ffmpeg = ffmpeg_path or _guess_ffmpeg()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg not found. Please install ffmpeg.")

    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sr),
        str(wav_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def load_audio(wav_path):
    """Load wav file as numpy array using soundfile."""
    import soundfile as sf

    audio, sr = sf.read(str(wav_path), dtype="float32")

    # Stereo to mono
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    wav = torch.from_numpy(np.asarray(audio, dtype=np.float32))
    return wav, sr


# ============================================================
# Audio Model (Wav2Vec2)
# ============================================================

# Lazy import to avoid import errors when transformers is not installed
_Wav2Vec2Model = None


def _get_wav2vec2_model():
    """Lazy load Wav2Vec2Model to provide better error messages."""
    global _Wav2Vec2Model
    if _Wav2Vec2Model is None:
        try:
            from transformers import Wav2Vec2Model
            _Wav2Vec2Model = Wav2Vec2Model
        except ImportError as e:
            raise ImportError(
                "transformers package not installed or Wav2Vec2Model not available. "
                "Install with: pip install transformers torch torchaudio"
            ) from e
    return _Wav2Vec2Model


class AudioWav2Vec2Classifier(nn.Module):
    """Audio emotion classifier using Wav2Vec2 backbone."""

    def __init__(self, model_name: str, pooling="mean", projector=None, classifier_in=768):
        super().__init__()
        Wav2Vec2Model = _get_wav2vec2_model()
        self.encoder = Wav2Vec2Model.from_pretrained(model_name)
        self.pooling = pooling
        self.projector = projector
        self.classifier = nn.Linear(classifier_in, 8)

    def forward(self, wav):
        out = self.encoder(wav).last_hidden_state  # (B, T, H)

        if self.pooling == "mean":
            pooled = out.mean(dim=1)
        else:
            pooled = out.max(dim=1).values

        if self.projector is not None:
            pooled = self.projector(pooled)

        return self.classifier(pooled)  # logits


# ============================================================
# Model Building
# ============================================================

def build_video_model(video_ckpt, device):
    """Reconstruct ResNet18 video model from checkpoint."""
    from torchvision.models import resnet18

    sd = strip_prefix(video_ckpt["model_state"])
    model = resnet18(num_classes=8)
    model.load_state_dict(sd, strict=True)
    model.to(device).eval()

    labels = ordered_labels(video_ckpt["idx_to_emotion"])
    img_size = int(video_ckpt.get("img_size", 224))

    return model, labels, img_size


def build_audio_model(audio_ckpt, device):
    """Reconstruct Wav2Vec2 audio model from checkpoint."""
    sd = strip_prefix(audio_ckpt["model_state"])

    model_name = audio_ckpt.get("model_name", "facebook/wav2vec2-base")
    pooling = audio_ckpt.get("pooling", "mean")
    sr = int(audio_ckpt.get("sample_rate", 16000))
    max_len = int(audio_ckpt.get("max_length", 0))

    classifier_in = sd["classifier.weight"].shape[1]

    # Projector (if present in checkpoint)
    projector = None
    if "projector.0.weight" in sd:
        w = sd["projector.0.weight"]
        out_f, in_f = w.shape
        projector = nn.Sequential(nn.Linear(in_f, out_f))

    model = AudioWav2Vec2Classifier(
        model_name=model_name,
        pooling=pooling,
        projector=projector,
        classifier_in=classifier_in
    )

    model.load_state_dict(sd, strict=True)
    model.to(device).eval()

    labels = ordered_labels(audio_ckpt["idx_to_emotion"])
    return model, labels, sr, max_len


# ============================================================
# Late Fusion
# ============================================================

def project_to_9(z8, mapping):
    """Project 8-class logits to 9-class space."""
    B = z8.shape[0]
    z9 = torch.full((B, 9), -1e9, device=z8.device)
    for j, k in enumerate(mapping):
        z9[:, k] = z8[:, j]
    return z9


def fuse_logits(z_audio, z_video, a2f, v2f, wa=0.5, wv=0.5):
    """Late fusion of audio and video logits."""
    za9 = project_to_9(z_audio, a2f)
    zv9 = project_to_9(z_video, v2f)

    z = wa * za9 + wv * zv9
    p = F.softmax(z, dim=1)

    return p


# ============================================================
# Main Inference Function
# ============================================================

@torch.no_grad()
def late_fusion_from_video(
    video_file: Path,
    audio_pt: Path,
    video_pt: Path,
    wa: float = 0.5,
    wv: float = 0.5,
    num_frames: int = 16,
    device: Optional[str] = None,
    ffmpeg_path: Optional[str] = None,
) -> dict:
    """
    Run late fusion inference on a video file.

    Args:
        video_file: Path to input video
        audio_pt: Path to audio model checkpoint
        video_pt: Path to video model checkpoint
        wa: Weight for audio modality (default 0.5)
        wv: Weight for video modality (default 0.5)
        num_frames: Number of frames to sample from video
        device: Device to run on (auto-detected if None)
        ffmpeg_path: Optional path to ffmpeg executable

    Returns:
        dict with:
            - labels_9: List of 9 emotion labels
            - probs_9: List of 9 probabilities
            - pred_label: Predicted emotion label
            - pred_confidence: Confidence of prediction
    """
    _device = device or DEVICE

    # Load checkpoints
    video_ckpt = torch.load(video_pt, map_location="cpu")
    audio_ckpt = torch.load(audio_pt, map_location="cpu")

    # Build models
    video_model, video_labels, img_size = build_video_model(video_ckpt, _device)
    audio_model, audio_labels, sr, max_len = build_audio_model(audio_ckpt, _device)

    # Compute unified 9-label space
    final_labels = sorted(set(video_labels) | set(audio_labels))
    a2f = [final_labels.index(l) for l in audio_labels]
    v2f = [final_labels.index(l) for l in video_labels]

    # Video inference
    frames = sample_frames(video_file, num_frames=num_frames)
    if not frames:
        raise ValueError(f"Could not extract frames from video: {video_file}")

    x_video = torch.stack([preprocess_frame(f, img_size) for f in frames]).to(_device)
    z_video = video_model(x_video).mean(dim=0, keepdim=True)  # (1, 8)

    # Audio inference
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "audio.wav"
        extract_audio(video_file, wav_path, sr, ffmpeg_path)
        wav, _ = load_audio(str(wav_path))

    if max_len > 0:
        wav = wav[:max_len]
    wav = wav.unsqueeze(0).to(_device)
    z_audio = audio_model(wav)  # (1, 8)

    # Late fusion
    probs = fuse_logits(z_audio, z_video, a2f, v2f, wa=wa, wv=wv)  # (1, 9)
    probs = probs.squeeze(0).detach().cpu().tolist()
    pred_idx = int(np.argmax(probs))

    return {
        "labels_9": final_labels,
        "probs_9": probs,
        "pred_label": final_labels[pred_idx],
        "pred_confidence": probs[pred_idx],
        "emotion_probabilities": {label: prob for label, prob in zip(final_labels, probs)},
    }


# Singleton model cache to avoid reloading on every request
_model_cache = {}


def get_inference_engine(
    audio_pt: Path,
    video_pt: Path,
    device: Optional[str] = None,
):
    """
    Get or create cached inference models.
    Returns a function that runs inference without reloading models.
    """
    cache_key = (str(audio_pt), str(video_pt), device or DEVICE)

    if cache_key not in _model_cache:
        _device = device or DEVICE

        video_ckpt = torch.load(video_pt, map_location="cpu")
        audio_ckpt = torch.load(audio_pt, map_location="cpu")

        video_model, video_labels, img_size = build_video_model(video_ckpt, _device)
        audio_model, audio_labels, sr, max_len = build_audio_model(audio_ckpt, _device)

        final_labels = sorted(set(video_labels) | set(audio_labels))
        a2f = [final_labels.index(l) for l in audio_labels]
        v2f = [final_labels.index(l) for l in video_labels]

        _model_cache[cache_key] = {
            "video_model": video_model,
            "audio_model": audio_model,
            "video_labels": video_labels,
            "audio_labels": audio_labels,
            "final_labels": final_labels,
            "img_size": img_size,
            "sr": sr,
            "max_len": max_len,
            "a2f": a2f,
            "v2f": v2f,
            "device": _device,
        }

    return _model_cache[cache_key]


@torch.no_grad()
def run_inference_cached(
    video_file: Path,
    audio_pt: Path,
    video_pt: Path,
    wa: float = 0.5,
    wv: float = 0.5,
    num_frames: int = 16,
    device: Optional[str] = None,
    ffmpeg_path: Optional[str] = None,
) -> dict:
    """
    Run inference using cached models (faster for repeated calls).
    """
    cache = get_inference_engine(audio_pt, video_pt, device)
    _device = cache["device"]

    # Video inference
    frames = sample_frames(video_file, num_frames=num_frames)
    if not frames:
        raise ValueError(f"Could not extract frames from video: {video_file}")

    x_video = torch.stack([preprocess_frame(f, cache["img_size"]) for f in frames]).to(_device)
    z_video = cache["video_model"](x_video).mean(dim=0, keepdim=True)

    # Audio inference
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "audio.wav"
        extract_audio(video_file, wav_path, cache["sr"], ffmpeg_path)
        wav, _ = load_audio(str(wav_path))

    if cache["max_len"] > 0:
        wav = wav[:cache["max_len"]]
    wav = wav.unsqueeze(0).to(_device)
    z_audio = cache["audio_model"](wav)

    # Late fusion
    probs = fuse_logits(z_audio, z_video, cache["a2f"], cache["v2f"], wa=wa, wv=wv)
    probs = probs.squeeze(0).detach().cpu().tolist()
    pred_idx = int(np.argmax(probs))

    final_labels = cache["final_labels"]

    return {
        "labels_9": final_labels,
        "probs_9": probs,
        "pred_label": final_labels[pred_idx],
        "pred_confidence": probs[pred_idx],
        "emotion_probabilities": {label: prob for label, prob in zip(final_labels, probs)},
    }
