"""faster-whisper Wrapper mit Lazy Load und Model-Swap."""
from __future__ import annotations

import threading
from typing import Optional

import numpy as np

# CUDA DLLs muessen registriert sein, bevor faster_whisper importiert wird.
from .cuda_setup import ensure_cuda_dlls

try:
    ensure_cuda_dlls()
except RuntimeError:
    # Nicht fatal; CPU-Fallback funktioniert ggf. trotzdem.
    pass

from faster_whisper import WhisperModel  # noqa: E402


class Transcriber:
    def __init__(
        self,
        model: str,
        device: str = "cuda",
        compute_type: str = "float16",
        language: str = "de",
    ) -> None:
        self._model_name = model
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._model: Optional[WhisperModel] = None
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def language(self) -> str:
        return self._language

    def load(self) -> None:
        """Laedt das Modell. Beim ersten Aufruf wird es ggf. heruntergeladen."""
        with self._lock:
            if self._model is not None:
                return
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )

    def set_model(self, model: str) -> None:
        with self._lock:
            if model == self._model_name and self._model is not None:
                return
            self._model_name = model
            # Alten Modell-Handle freigeben; wird lazy neu geladen.
            self._model = None

    def set_language(self, language: str) -> None:
        self._language = language

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        # Sicherstellen: float32, mono, 16 kHz wird bereits beim Aufnehmen
        # festgelegt.
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        self.load()
        assert self._model is not None

        lang_param = None if self._language == "auto" else self._language

        with self._lock:
            segments, _info = self._model.transcribe(
                audio,
                language=lang_param,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
                beam_size=5,
            )
            parts = [seg.text for seg in segments]
        return "".join(parts).strip()
