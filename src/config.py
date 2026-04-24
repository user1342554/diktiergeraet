"""Persistente Konfiguration in %APPDATA%\\Diktiergeraet\\config.json."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Optional


AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
AVAILABLE_LANGUAGES = ["de", "en", "auto"]


def _config_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata)
    else:
        base = Path.home() / "AppData" / "Roaming"
    d = base / "Diktiergeraet"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return _config_dir() / "config.json"


@dataclass
class Config:
    model: str = "large-v3"
    language: str = "de"
    hotkey: str = "<ctrl>+<alt>+<space>"
    settings_hotkey: str = "<ctrl>+<alt>+<shift>+<space>"
    device: str = "cuda"
    compute_type: str = "float16"
    # Injection-Verhalten
    paste_restore_delay_ms: int = 150
    # Mikrofon-Index (None = System-Default)
    input_device: Optional[int] = None


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        cfg = Config()
        save_config(cfg)
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Config()
    known = {f.name for f in fields(Config)}
    clean = {k: v for k, v in data.items() if k in known}
    return Config(**clean)


def save_config(cfg: Config) -> None:
    path = config_path()
    path.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
