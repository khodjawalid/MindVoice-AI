#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
========================================================
LATE FUSION AUDIO + VIDEO (INFERENCE SCRIPT)
========================================================

Ce script :
1) charge deux modèles entraînés séparément :
   - un modèle vidéo (ResNet18 -> 8 émotions)
   - un modèle audio (Wav2Vec2 -> 8 émotions)
2) extrait l'audio et des frames depuis une vidéo
3) infère des LOGITS pour chaque modalité
4) projette les sorties vers un espace commun de 9 émotions
5) effectue une late fusion au niveau des logits
6) applique un softmax final pour obtenir des probabilités

IMPORTANT :
- Les modèles retournent des LOGITS (pas des probabilités)
- Le softmax est appliqué UNE SEULE FOIS à la fin
========================================================
"""

# ======================================================
# IMPORTS
# ======================================================
from pathlib import Path
import subprocess
import tempfile
import json
import argparse

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import cv2  # lecture vidéo

# ======================================================
# DEVICE (CPU / GPU)
# ======================================================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ======================================================
# UTILS
# ======================================================
def strip_prefix(state_dict, prefixes=("module.", "model.")):
    """
    Supprime des préfixes inutiles dans les clés du state_dict
    (ex: entraînement en DataParallel)
    """
    clean_sd = {}
    for k, v in state_dict.items():
        for p in prefixes:
            if k.startswith(p):
                k = k[len(p):]
        clean_sd[k] = v
    return clean_sd


def ordered_labels(idx_to_emotion):
    """
    Récupère les labels dans le bon ordre à partir du checkpoint
    """
    if isinstance(idx_to_emotion, dict):
        return [idx_to_emotion.get(i, idx_to_emotion.get(str(i)))
                for i in range(len(idx_to_emotion))]
    return list(idx_to_emotion)


# ======================================================
# VIDEO PREPROCESSING
# ======================================================
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406])
IMAGENET_STD  = np.array([0.229, 0.224, 0.225])


def preprocess_frame(frame_bgr, img_size):
    """
    Prépare une frame pour ResNet18
    """
    frame = cv2.resize(frame_bgr, (img_size, img_size))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = frame / 255.0
    frame = (frame - IMAGENET_MEAN) / IMAGENET_STD
    frame = np.transpose(frame, (2, 0, 1))  # HWC -> CHW
    return torch.tensor(frame, dtype=torch.float32)


def sample_frames(video_path, num_frames=16):
    """
    Échantillonne uniformément des frames dans la vidéo
    """
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    idxs = np.linspace(0, total - 1, num_frames).astype(int)
    frames = []

    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, frame = cap.read()
        if ok:
            frames.append(frame)

    cap.release()
    return frames




# ======================================================
# AUDIO EXTRACTION
# ======================================================

import shutil
import subprocess
from pathlib import Path

def _guess_ffmpeg_windows():
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None

def extract_audio(video_path, wav_path, sr=16000, ffmpeg_path=None):
    """
    Extrait l'audio mono depuis une vidéo avec ffmpeg.
    """
    ffmpeg = ffmpeg_path or shutil.which("ffmpeg") or _guess_ffmpeg_windows()
    if not ffmpeg:
        raise FileNotFoundError(
            "ffmpeg introuvable depuis ce kernel Python.\n"
            "➡️ Fais un restart du kernel Jupyter / relance VS Code.\n"
            "Sinon passe ffmpeg_path='C:/.../ffmpeg.exe'."
        )

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
    """
    Charge un wav en numpy avec soundfile (pas besoin de torchaudio/torchcodec).
    Retour: (wav_tensor_1d, sample_rate)
    """
    import soundfile as sf
    import numpy as np
    import torch

    audio, sr = sf.read(str(wav_path), dtype="float32")  # audio: (T,) ou (T,C)

    # Si stéréo -> mono
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    # Conversion torch
    wav = torch.from_numpy(np.asarray(audio, dtype=np.float32))
    return wav, sr



# ======================================================
# AUDIO MODEL
# ======================================================
from transformers import Wav2Vec2Model

class AudioWav2Vec2Classifier(nn.Module):
    """
    Modèle audio IDENTIQUE à celui utilisé à l'entraînement (HF Wav2Vec2)
    """
    def __init__(self, model_name: str, pooling="mean", projector=None, classifier_in=768):
        super().__init__()
        self.encoder = Wav2Vec2Model.from_pretrained(model_name)
        self.pooling = pooling
        self.projector = projector
        self.classifier = nn.Linear(classifier_in, 8)

    def forward(self, wav):
        out = self.encoder(wav).last_hidden_state  # (B,T,H)

        if self.pooling == "mean":
            pooled = out.mean(dim=1)
        else:
            pooled = out.max(dim=1).values

        if self.projector is not None:
            pooled = self.projector(pooled)

        return self.classifier(pooled)  # logits


# ======================================================
# BUILD MODELS
# ======================================================
def build_video_model(video_ckpt):
    """
    Reconstruit ResNet18 exactement comme à l'entraînement
    """
    from torchvision.models import resnet18

    sd = strip_prefix(video_ckpt["model_state"])
    model = resnet18(num_classes=8)
    model.load_state_dict(sd, strict=True)
    model.to(DEVICE).eval()

    labels = ordered_labels(video_ckpt["idx_to_emotion"])
    img_size = int(video_ckpt.get("img_size", 224))

    return model, labels, img_size


def build_audio_model(audio_ckpt):
    """
    Reconstruction STRICTEMENT compatible avec un checkpoint
    entraîné avec transformers.Wav2Vec2Model
    """
    from transformers import Wav2Vec2Model

    sd = strip_prefix(audio_ckpt["model_state"])

    model_name = audio_ckpt.get("model_name", "facebook/wav2vec2-base")
    pooling = audio_ckpt.get("pooling", "mean")
    sr = int(audio_ckpt.get("sample_rate", 16000))
    max_len = int(audio_ckpt.get("max_length", 0))

    # classifier input dim
    classifier_in = sd["classifier.weight"].shape[1]

    # projector (si présent)
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

    # 🔥 MAINTENANT les clés MATCHENT
    model.load_state_dict(sd, strict=True)
    model.to(DEVICE).eval()

    labels = ordered_labels(audio_ckpt["idx_to_emotion"])
    return model, labels, sr, max_len




# ======================================================
# FUSION
# ======================================================
def project_to_9(z8, mapping):
    """
    Projette un vecteur (B,8) vers (B,9)
    """
    B = z8.shape[0]
    z9 = torch.full((B, 9), -1e9, device=z8.device)
    for j, k in enumerate(mapping):
        z9[:, k] = z8[:, j]
    return z9


def fuse_logits(z_audio, z_video, a2f, v2f, wa=0.5, wv=0.5):
    """
    Late fusion AU NIVEAU DES LOGITS
    """
    za9 = project_to_9(z_audio, a2f)
    zv9 = project_to_9(z_video, v2f)

    z = wa * za9 + wv * zv9
    p = F.softmax(z, dim=1)

    return p


# ======================================================
# MAIN INFERENCE FUNCTION
# ======================================================
@torch.no_grad()
def infer(video_path, audio_pt, video_pt):
    """
    Pipeline complet d'inférence
    """
    video_ckpt = torch.load(video_pt, map_location="cpu")
    audio_ckpt = torch.load(audio_pt, map_location="cpu")

    video_model, video_labels, img_size = build_video_model(video_ckpt)
    audio_model, audio_labels, sr, max_len = build_audio_model(audio_ckpt)

    # Labels finaux (9)
    final_labels = sorted(set(video_labels) | set(audio_labels))
    a2f = [final_labels.index(l) for l in audio_labels]
    v2f = [final_labels.index(l) for l in video_labels]

    # ----- VIDEO INFERENCE -----
    frames = sample_frames(video_path)
    x_video = torch.stack(
        [preprocess_frame(f, img_size) for f in frames]
    ).to(DEVICE)

    z_video = video_model(x_video).mean(dim=0, keepdim=True)  # (1,8)

    # ----- AUDIO INFERENCE -----
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "audio.wav"
        extract_audio(video_path, wav_path, sr)
        wav, _ = load_audio(wav_path)

    wav = wav[:max_len].unsqueeze(0).to(DEVICE)
    z_audio = audio_model(wav)  # (1,8)

    # ----- FUSION -----
    probs = fuse_logits(z_audio, z_video, a2f, v2f)

    return {
        "labels": final_labels,
        "probs": probs.squeeze(0).cpu().tolist(),
        "prediction": final_labels[int(probs.argmax())]
    }


# ======================================================
# CLI
# ======================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio-pt", required=True)
    parser.add_argument("--video-pt", required=True)
    args = parser.parse_args()

    out = infer(
        Path(args.video),
        Path(args.audio_pt),
        Path(args.video_pt)
    )

    print(json.dumps(out, indent=2, ensure_ascii=False))


def late_fusion_from_video(
    video_file: Path,
    audio_pt: Path,
    video_pt: Path,
    wa: float = 0.5,
    wv: float = 0.5,
    num_frames: int = 16,
    device: str | None = None,
    ffmpeg_path: str | None = None,
) -> dict:
    """
    Wrapper "app-ready":
    - vidéo en entrée
    - renvoie probs(9), labels(9), label prédit
    - configurable (wa,wv,num_frames,device)
    """
    global DEVICE
    if device is not None:
        DEVICE = device

    # on réutilise ton pipeline mais en rendant wa/wv/num_frames paramétrables
    video_ckpt = torch.load(video_pt, map_location="cpu")
    audio_ckpt = torch.load(audio_pt, map_location="cpu")

    video_model, video_labels, img_size = build_video_model(video_ckpt)
    audio_model, audio_labels, sr, max_len = build_audio_model(audio_ckpt)

    final_labels = sorted(set(video_labels) | set(audio_labels))
    if len(final_labels) != 9:
        raise RuntimeError(f"Expected 9 unique emotions, got {len(final_labels)}: {final_labels}")

    a2f = [final_labels.index(l) for l in audio_labels]
    v2f = [final_labels.index(l) for l in video_labels]

    # VIDEO
    frames = sample_frames(video_file, num_frames=num_frames)
    x_video = torch.stack([preprocess_frame(f, img_size) for f in frames]).to(DEVICE)
    z_video = video_model(x_video).mean(dim=0, keepdim=True)  # (1,8)

    # AUDIO
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "audio.wav"
        extract_audio(video_file, wav_path, sr)
        wav, _ = load_audio(str(wav_path))

    wav = wav[:max_len].unsqueeze(0).to(DEVICE)
    z_audio = audio_model(wav)  # (1,8)

    # FUSION logits -> probs
    probs = fuse_logits(z_audio, z_video, a2f, v2f, wa=wa, wv=wv)  # (1,9)
    probs = probs.squeeze(0).detach().cpu().tolist()
    pred_idx = int(np.argmax(probs))

    return {
        "video_file": str(video_file),
        "labels_9": final_labels,
        "probs_9": probs,
        "pred_label": final_labels[pred_idx],
        "weights": {"wa": wa, "wv": wv},
        "debug": {
            "audio_labels_8": audio_labels,
            "video_labels_8": video_labels,
            "num_frames": num_frames,
            "device": DEVICE,
        }
    }
