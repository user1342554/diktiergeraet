"""Sanity check: CUDA runtime libs via pip packages sind auffindbar und
faster-whisper kann ein kleines Modell auf CUDA laden."""
from __future__ import annotations

import sys
from pathlib import Path

# Src-Verzeichnis in den Pfad legen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cuda_setup import ensure_cuda_dlls  # noqa: E402

print("[1/3] Registriere CUDA-DLL-Pfade...")
try:
    ensure_cuda_dlls()
    print("      OK")
except Exception as e:
    print(f"      WARNUNG: {e}")

print("[2/3] Importiere faster_whisper...")
try:
    from faster_whisper import WhisperModel  # noqa: E402
    print("      OK")
except Exception as e:
    print(f"      FEHLER: {e}")
    sys.exit(1)

print("[3/3] Lade tiny-Modell auf CUDA (Smoke-Test)...")
try:
    model = WhisperModel("tiny", device="cuda", compute_type="float16")
    print("      OK - CUDA funktioniert.")
except Exception as e:
    print(f"      FEHLER beim CUDA-Load: {e}")
    print("      Versuche CPU-Fallback...")
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("      CPU funktioniert (aber CUDA ist empfohlen).")
    except Exception as e2:
        print(f"      FEHLER auch auf CPU: {e2}")
        sys.exit(1)

print("\nAlles gut. Diktiergeraet ist einsatzbereit.")
