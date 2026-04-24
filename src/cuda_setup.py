"""Registriert die DLL-Verzeichnisse der nvidia-*-cu12-Pip-Pakete,
damit ctranslate2 (faster-whisper) cuBLAS und cuDNN findet.

MUSS vor dem Import von faster_whisper aufgerufen werden.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_cuda_dlls() -> None:
    """Fuegt die bin-Verzeichnisse von nvidia-cublas-cu12 und
    nvidia-cudnn-cu12 zur DLL-Suche hinzu."""
    if sys.platform != "win32":
        return

    # Finde site-packages/nvidia/
    import importlib.util

    try:
        spec = importlib.util.find_spec("nvidia")
    except ModuleNotFoundError:
        spec = None

    nvidia_roots: list[Path] = []
    if spec is not None and spec.submodule_search_locations:
        for p in spec.submodule_search_locations:
            nvidia_roots.append(Path(p))

    # Fallback: venv/Lib/site-packages/nvidia
    for sp in sys.path:
        cand = Path(sp) / "nvidia"
        if cand.is_dir() and cand not in nvidia_roots:
            nvidia_roots.append(cand)

    added: list[str] = []
    for root in nvidia_roots:
        # Gesuchte Unterordner
        for sub in ("cublas", "cudnn", "cuda_nvrtc", "cuda_runtime"):
            bin_dir = root / sub / "bin"
            if bin_dir.is_dir():
                try:
                    os.add_dll_directory(str(bin_dir))
                except (FileNotFoundError, OSError):
                    pass
                # Zusaetzlich in PATH prependen, damit indirekt geladene
                # DLLs (z.B. cublas via cudnn) aufgefunden werden.
                current = os.environ.get("PATH", "")
                path_str = str(bin_dir)
                if path_str not in current.split(os.pathsep):
                    os.environ["PATH"] = path_str + os.pathsep + current
                added.append(path_str)

    if not added:
        raise RuntimeError(
            "Keine CUDA-DLL-Verzeichnisse gefunden. Pruefe, ob "
            "nvidia-cublas-cu12 und nvidia-cudnn-cu12==9.* installiert sind."
        )
