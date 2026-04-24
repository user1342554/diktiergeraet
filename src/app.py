"""Orchestrator: verdrahtet Hotkey, Audio, Whisper, Tray und Overlay."""
from __future__ import annotations

import threading
import traceback
from enum import Enum, auto

from .audio_recorder import AudioRecorder
from .config import Config, save_config
from .hotkey import HotkeyListener
from .overlay import Overlay
from .settings_window import SettingsWindow
from .text_injector import inject_text
from .transcriber import Transcriber
from .tray import Tray


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


class App:
    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._state = State.IDLE
        self._state_lock = threading.Lock()

        self._overlay = Overlay()
        self._recorder = AudioRecorder(
            device=config.input_device,
            audio_callback=self._on_audio_block,
        )
        self._transcriber = Transcriber(
            model=config.model,
            device=config.device,
            compute_type=config.compute_type,
            language=config.language,
        )
        self._hotkey = HotkeyListener(
            hotkey=config.hotkey,
            callback=self._on_hotkey,
            settings_hotkey=config.settings_hotkey,
            settings_callback=self._open_settings,
        )
        self._tray = Tray(
            config=config,
            on_model_change=self._change_model,
            on_language_change=self._change_language,
            on_open_settings=self._open_settings,
            on_quit=self._request_shutdown,
        )

        self._settings_win = None  # Referenz halten, damit nicht gc'd
        self._shutdown_requested = False

    # ----- Lifecycle --------------------------------------------------

    def run(self) -> None:
        threading.Thread(target=self._preload_model, daemon=True).start()
        self._tray.start()
        self._hotkey.start()
        # Kurze Willkommens-Anzeige, damit man die Hotkeys sieht
        self._overlay.root.after(400, self._show_welcome)
        self._overlay.root.mainloop()

    def _show_welcome(self) -> None:
        self._overlay.show_info(
            "Diktiergerät ist bereit",
            f"Diktieren: {self._cfg.hotkey}   •   Einstellungen: {self._cfg.settings_hotkey}",
            duration_ms=4500,
        )

    def _preload_model(self) -> None:
        try:
            self._transcriber.load()
        except Exception as e:  # noqa: BLE001
            msg = f"Modell-Load fehlgeschlagen: {e}"
            print(f"[app] {msg}")
            traceback.print_exc()
            self._overlay.root.after(0, lambda: self._overlay.show_error(str(e)))

    def _request_shutdown(self) -> None:
        self._shutdown_requested = True
        self._overlay.root.after(0, self._shutdown)

    def _shutdown(self) -> None:
        try:
            self._hotkey.stop()
        except Exception:
            pass
        try:
            self._tray.stop()
        except Exception:
            pass
        try:
            self._overlay.root.quit()
            self._overlay.root.destroy()
        except Exception:
            pass

    # ----- Audio-Samples -> Overlay ----------------------------------

    def _on_audio_block(self, samples) -> None:
        # Aus Audio-Callback-Thread: Samples zum Overlay dispatchen.
        self._overlay.update_audio(samples)

    # ----- Hotkey -> State-Machine ------------------------------------

    def _on_hotkey(self) -> None:
        with self._state_lock:
            state = self._state

        if state == State.IDLE:
            self._start_recording()
        elif state == State.RECORDING:
            self._stop_and_transcribe()

    def _start_recording(self) -> None:
        try:
            self._recorder.start()
        except Exception as e:  # noqa: BLE001
            msg = f"Audio-Start fehlgeschlagen: {e}"
            print(f"[app] {msg}")
            self._overlay.root.after(0, lambda: self._overlay.show_error(str(e)))
            return
        with self._state_lock:
            self._state = State.RECORDING
        self._overlay.root.after(0, self._overlay.show_recording)

    def _stop_and_transcribe(self) -> None:
        with self._state_lock:
            self._state = State.TRANSCRIBING
        self._overlay.root.after(0, self._overlay.show_transcribing)
        threading.Thread(target=self._do_transcribe, daemon=True).start()

    def _do_transcribe(self) -> None:
        try:
            audio = self._recorder.stop()
            text = self._transcriber.transcribe(audio)
            if text:
                inject_text(text, restore_delay_ms=self._cfg.paste_restore_delay_ms)
        except Exception as e:  # noqa: BLE001
            msg = f"Transkription fehlgeschlagen: {e}"
            print(f"[app] {msg}")
            traceback.print_exc()
            self._overlay.root.after(0, lambda: self._overlay.show_error(str(e)))
        finally:
            with self._state_lock:
                self._state = State.IDLE
            self._overlay.root.after(0, self._overlay.hide)

    # ----- Tray-Callbacks ---------------------------------------------

    def _change_model(self, model: str) -> None:
        print(f"[app] Wechsle Modell zu {model}")
        self._cfg.model = model
        save_config(self._cfg)
        self._transcriber.set_model(model)
        threading.Thread(target=self._preload_model, daemon=True).start()

    def _change_language(self, lang: str) -> None:
        print(f"[app] Wechsle Sprache zu {lang}")
        self._cfg.language = lang
        save_config(self._cfg)
        self._transcriber.set_language(lang)

    def _open_settings(self) -> None:
        # pystray ruft aus Tray-Thread; ins Tk dispatchen.
        self._overlay.root.after(0, self._open_settings_main_thread)

    def _open_settings_main_thread(self) -> None:
        if self._settings_win is not None:
            try:
                self._settings_win._win.lift()   # type: ignore[attr-defined]
                return
            except Exception:
                self._settings_win = None
        self._settings_win = SettingsWindow(
            parent=self._overlay.root,
            config=self._cfg,
            on_save=self._apply_settings,
        )
        # Wenn geschlossen, Referenz freigeben
        self._settings_win._win.bind(  # type: ignore[attr-defined]
            "<Destroy>", lambda e: self._clear_settings_ref(),
        )

    def _clear_settings_ref(self) -> None:
        self._settings_win = None

    def _apply_settings(self, cfg: Config) -> None:
        """Einstellungen aus dem Settings-Fenster uebernehmen."""
        print(f"[app] Einstellungen uebernommen: {cfg}")
        self._cfg = cfg
        save_config(cfg)
        # Mikrofon
        self._recorder.set_device(cfg.input_device)
        # Modell
        self._transcriber.set_model(cfg.model)
        self._transcriber.set_language(cfg.language)
        threading.Thread(target=self._preload_model, daemon=True).start()
        # Hotkey neu binden
        try:
            self._hotkey.set_hotkey(cfg.hotkey)
        except Exception as e:  # noqa: BLE001
            print(f"[app] Hotkey-Fehler: {e}")
            self._overlay.show_error(f"Hotkey ungueltig: {e}")
        # Tray aktualisieren
        self._tray.refresh()
