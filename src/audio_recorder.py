"""Audio-Aufnahme ueber sounddevice in einen Puffer, mit Level-Callback."""
from __future__ import annotations

import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


AudioCallback = Callable[[np.ndarray], None]  # Roh-Samples pro Block (float32, mono)


class AudioRecorder:
    """Nimmt mono 16 kHz float32 auf. start() -> stop() liefert np.ndarray.

    Optional: device (Index aus sd.query_devices()); None = Default.
    Optional: level_callback – bekommt RMS-Level pro Audioblock.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        device: Optional[int] = None,
        audio_callback: Optional[AudioCallback] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self._device = device
        self._audio_cb = audio_callback
        self._stream: Optional[sd.InputStream] = None
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def set_device(self, device: Optional[int]) -> None:
        """Nur im IDLE-Zustand aendern."""
        self._device = device

    def set_audio_callback(self, cb: Optional[AudioCallback]) -> None:
        self._audio_cb = cb

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        if status:
            pass
        # indata shape: (frames, 1) float32
        flat = indata.reshape(-1).copy()
        with self._lock:
            self._chunks.append(flat)
        if self._audio_cb is not None:
            try:
                self._audio_cb(flat)
            except Exception:
                pass

    def start(self) -> None:
        if self._recording:
            return
        with self._lock:
            self._chunks = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
            blocksize=0,
            device=self._device,
        )
        self._stream.start()
        self._recording = True

    def stop(self) -> np.ndarray:
        if not self._recording:
            return np.zeros(0, dtype=np.float32)
        assert self._stream is not None
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None
            self._recording = False
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._chunks, axis=0).astype(np.float32)
            self._chunks = []
        return audio
