"""Laden/Prüfen der faster-whisper Modelle von HuggingFace
mit Fortschritts-Callback, der sich in eine Tk-Progressbar einspeisen lässt.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Optional

from huggingface_hub import snapshot_download
from huggingface_hub.utils import tqdm as hf_tqdm_module  # noqa: F401


REPO_MAP: dict[str, str] = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}


def _hf_cache_root() -> Path:
    import os
    hf_home = os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if hf_home:
        return Path(hf_home) / "hub" if Path(hf_home).name != "hub" else Path(hf_home)
    return Path.home() / ".cache" / "huggingface" / "hub"


def is_downloaded(model_name: str) -> bool:
    """Grobe Heuristik: mindestens ein Snapshot mit einer model.bin-Datei
    ueber 10 MB und ohne '.incomplete'-Marker."""
    repo = REPO_MAP.get(model_name)
    if not repo:
        return False
    repo_dir = _hf_cache_root() / ("models--" + repo.replace("/", "--"))
    snapshots = repo_dir / "snapshots"
    if not snapshots.is_dir():
        return False
    for snap in snapshots.iterdir():
        model_bin = snap / "model.bin"
        if model_bin.exists() and model_bin.stat().st_size > 10 * 1024 * 1024:
            # Kein .incomplete im Blobs-Ordner?
            blobs = repo_dir / "blobs"
            if blobs.is_dir():
                has_incomplete = any(b.name.endswith(".incomplete") for b in blobs.iterdir())
                if not has_incomplete:
                    return True
            else:
                return True
    return False


ProgressCallback = Callable[[int, int, str], None]
# args: bytes_done, bytes_total, status_text


def _make_tqdm_class(progress_cb: Optional[ProgressCallback]):
    """Baut eine tqdm-Subklasse, die in den Progress-Callback pusht.
    Aggregiert ueber alle gleichzeitig laufenden tqdm-Instanzen."""
    from tqdm import tqdm as base_tqdm

    lock = threading.Lock()
    active: dict[int, tuple[int, int, str]] = {}
    counter = [0]

    class _Tqdm(base_tqdm):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("disable", False)
            super().__init__(*args, **kwargs)
            with lock:
                counter[0] += 1
                self._cb_id = counter[0]
                active[self._cb_id] = (0, self.total or 0, str(self.desc or ""))
            self._emit()

        def update(self, n=1):
            super().update(n)
            with lock:
                active[self._cb_id] = (self.n, self.total or self.n, str(self.desc or ""))
            self._emit()

        def close(self):
            super().close()
            with lock:
                active.pop(self._cb_id, None)
            self._emit()

        def _emit(self):
            if progress_cb is None:
                return
            with lock:
                if not active:
                    progress_cb(0, 0, "")
                    return
                total = sum(t for _, t, _ in active.values())
                done = sum(d for d, _, _ in active.values())
                # Neuste Desc als Status
                desc = next(iter(active.values()))[2]
            try:
                progress_cb(done, total, desc)
            except Exception:
                pass

    return _Tqdm


def download_model(
    model_name: str,
    progress_cb: Optional[ProgressCallback] = None,
) -> Path:
    """Synchroner Download. Wenn schon vorhanden, resumed HF automatisch."""
    repo = REPO_MAP.get(model_name)
    if not repo:
        raise ValueError(f"Unbekanntes Modell: {model_name}")
    tqdm_class = _make_tqdm_class(progress_cb)
    path = snapshot_download(repo_id=repo, tqdm_class=tqdm_class)
    return Path(path)


def download_model_async(
    model_name: str,
    progress_cb: Optional[ProgressCallback] = None,
    on_done: Optional[Callable[[Optional[Exception]], None]] = None,
) -> threading.Thread:
    def worker():
        err: Optional[Exception] = None
        try:
            download_model(model_name, progress_cb)
        except Exception as e:  # noqa: BLE001
            err = e
        if on_done is not None:
            try:
                on_done(err)
            except Exception:
                pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
