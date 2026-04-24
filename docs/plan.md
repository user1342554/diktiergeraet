# Diktiergerät – Lokales Whisper-Diktat für Windows

## Ziel
Hintergrund-App: Shortcut drücken → ins aktive Textfeld diktieren → Whisper transkribiert lokal auf RTX 4070 Ti → Text wird automatisch ins Textfeld eingefügt.

## Kern-Entscheidungen
- **Hardware:** RTX 4070 Ti, 12 GB VRAM, CUDA 13 Treiber (kompatibel mit CUDA 12 Runtime).
- **Backend:** `faster-whisper` (ctranslate2) auf CUDA, float16. Schnell, bewährt.
- **Recording:** Toggle-Modus (Hotkey startet, Hotkey stoppt).
- **Injection:** Clipboard-Paste (Clipboard sichern → Text setzen → Strg+V senden → Clipboard wiederherstellen). Robust mit Umlauten, funktioniert überall.
- **Default-Shortcut:** `Ctrl+Alt+Space` (global, Windows-weit).
- **Default-Modell:** `large-v3` (12 GB VRAM reichen easy). Medium + Large-v3 im Tray auswählbar.
- **Default-Sprache:** `de`. Im Tray umschaltbar: `de`, `en`, `auto`.
- **Autostart:** Verknüpfung im Shell:Startup-Ordner (optional per Skript).

## Architektur

```
main.py          Entry point – Config laden, App starten, Tk-Mainloop
  │
  └─ app.py      Orchestrator – State Machine: IDLE/RECORDING/TRANSCRIBING/INJECTING
        │
        ├─ config.py            Persistentes JSON-Config in %APPDATA%\Diktiergeraet\
        ├─ audio_recorder.py    sounddevice, 16 kHz mono float32
        ├─ transcriber.py       faster-whisper Wrapper, lazy load, Model-Swap
        ├─ text_injector.py     pyperclip + pynput keyboard controller (Strg+V)
        ├─ hotkey.py            pynput GlobalHotKeys
        ├─ overlay.py           tkinter always-on-top Status-Fenster
        └─ tray.py              pystray Icon + Menü (Modell, Sprache, Quit)
```

## State Machine (in app.py)

```
IDLE --hotkey--> RECORDING
RECORDING --hotkey--> TRANSCRIBING (background thread)
TRANSCRIBING --done--> INJECTING
INJECTING --done--> IDLE
```

## Threading-Modell
- **Main-Thread:** Tk-Mainloop (Overlay). Pflicht auf Windows.
- **Tray-Thread:** `pystray.Icon.run_detached()`.
- **Hotkey-Thread:** pynput startet eigenen Listener-Thread.
- **Audio-Thread:** sounddevice InputStream hat eigenen Callback-Thread.
- **Transcribe-Thread:** eigenständiger `threading.Thread` pro Transkription.
- UI-Updates aus anderen Threads via `overlay_root.after(0, fn)`.

## Modul-Interfaces

### config.py
```python
@dataclass
class Config:
    model: str = "large-v3"
    language: str = "de"
    hotkey: str = "<ctrl>+<alt>+<space>"
    device: str = "cuda"
    compute_type: str = "float16"

def load_config() -> Config
def save_config(cfg: Config) -> None
```
Location: `%APPDATA%\Diktiergeraet\config.json`

### audio_recorder.py
```python
class AudioRecorder:
    def __init__(self, sample_rate: int = 16000)
    def start(self) -> None
    def stop(self) -> np.ndarray  # float32, mono, 16 kHz
    @property
    def is_recording(self) -> bool
```

### transcriber.py
```python
class Transcriber:
    def __init__(self, model: str, device: str, compute_type: str, language: str)
    def load(self) -> None                # lädt Modell (first call downloads)
    def transcribe(self, audio: np.ndarray) -> str
    def set_model(self, model: str) -> None
    def set_language(self, language: str) -> None
```

### text_injector.py
```python
def inject_text(text: str) -> None        # Clipboard-Paste-Trick
```

### overlay.py
```python
class Overlay:
    def __init__(self)                    # Tk-Fenster, always-on-top, borderless
    @property
    def root(self) -> tk.Tk
    def show_recording(self) -> None
    def show_transcribing(self) -> None
    def show_error(self, msg: str) -> None
    def hide(self) -> None
```

### hotkey.py
```python
class HotkeyListener:
    def __init__(self, hotkey: str, callback: Callable[[], None])
    def start(self) -> None
    def stop(self) -> None
    def set_hotkey(self, hotkey: str) -> None
```

### tray.py
```python
class Tray:
    def __init__(
        self,
        config: Config,
        on_model_change: Callable[[str], None],
        on_language_change: Callable[[str], None],
        on_quit: Callable[[], None],
    )
    def start(self) -> None               # run_detached
    def stop(self) -> None
```

### app.py
```python
class App:
    def __init__(self, config: Config)
    def run(self) -> None                 # Startet Tray, Hotkey, Tk-Mainloop
    def shutdown(self) -> None
    # intern:
    def _on_hotkey(self)                  # Toggle
    def _start_recording(self)
    def _stop_and_transcribe(self)
    def _change_model(self, model: str)
    def _change_language(self, lang: str)
```

## Dependencies (requirements.txt)
```
faster-whisper>=1.0.3
sounddevice>=0.4.6
numpy>=1.26,<2.0
pynput>=1.7.7
pystray>=0.19.5
Pillow>=10.0
pyperclip>=1.8.2
# CUDA runtime libs – ctranslate2 braucht cuBLAS + cuDNN 9
nvidia-cublas-cu12
nvidia-cudnn-cu12==9.*
```

Hinweis: Unter Windows müssen die DLL-Pfade dieser Pip-Pakete beim Start via `os.add_dll_directory()` registriert werden, bevor `faster_whisper` importiert wird.

## Install-Skripte

- `install.bat` – erstellt `.venv`, `pip install -r requirements.txt`, testet CUDA.
- `run.bat` – startet `pythonw` (kein Konsolenfenster) mit `src\main.py`.
- `install_autostart.bat` – legt Verknüpfung in `shell:startup` an.

## Reihenfolge der Implementierung
1. `requirements.txt`, `install.bat`, `run.bat` – Setup-Basis.
2. `config.py` – trivial, keine Deps.
3. `audio_recorder.py` – sounddevice isoliert testbar.
4. `text_injector.py` – pyperclip + pynput, kein Model nötig.
5. `transcriber.py` – faster-whisper Wrapper.
6. `overlay.py` – Tk-Fenster.
7. `hotkey.py` – pynput GlobalHotKeys.
8. `tray.py` – pystray mit Menü.
9. `app.py`, `main.py` – Integration.
10. `install_autostart.bat`.
11. install.bat ausführen, Smoke-Test.

## Known Risks
- **cuDNN-DLLs nicht gefunden:** Via `os.add_dll_directory()` vor faster-whisper-Import explizit registrieren.
- **Tk + pystray Threading:** Tk auf Main-Thread, pystray detached. pynput eigene Threads.
- **Clipboard-Race bei Paste:** Nach `keyboard.press/release('v')` kurz warten (100 ms), dann altes Clipboard restaurieren.
- **Autostart mit Konsolenfenster:** `pythonw.exe` statt `python.exe` verwenden.
- **Recording während Transcribe:** State-Machine blockt neuen Record-Start, bis INJECTING fertig.
