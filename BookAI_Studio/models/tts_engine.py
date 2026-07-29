"""
Text-to-Speech engine for BookAI Studio.

Priority order:
  1. OpenAI TTS (tts-1-hd) — best quality, human-like voices, requires API key
  2. gTTS              — decent quality, requires internet
  3. pyttsx3           — offline fallback, robotic but always available
"""

import os
import threading
import tempfile
import time

try:
    from config import AUDIO_DIR
except ImportError:
    AUDIO_DIR = os.path.join(os.path.expanduser("~"), "BookAI_Exports", "audio")

OPENAI_VOICES = ["nova", "shimmer", "alloy", "echo", "fable", "onyx"]


class TTSEngine:

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._pyttsx3_engine = None
        self._stop_flag = False
        self._lock = threading.Lock()
        self._current_temp_file = None

        self.engine_name = self._config.get("tts_engine", "openai")
        self.voice = self._config.get("tts_voice", "nova")
        self._openai_speed = max(0.25, min(4.0, float(self._config.get("tts_rate", 1.0))))
        self._pyttsx3_rate = int(self._config.get("tts_pyttsx3_rate", 150))

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str):
        """Speak text. Run this in a background thread — it blocks until done."""
        self._stop_flag = False
        if self.engine_name == "openai" and self._openai_available():
            ok = self._speak_openai(text)
            if ok:
                return
        if self._gtts_available():
            ok = self._speak_gtts(text)
            if ok:
                return
        self._speak_pyttsx3(text)

    def save_to_file(self, text: str, filename: str = None) -> str:
        """Save speech to file. Returns the path."""
        if not filename:
            filename = f"audio_{int(time.time())}.mp3"
        out_path = os.path.join(AUDIO_DIR, filename)

        if self.engine_name == "openai" and self._openai_available():
            if self._save_openai(text, out_path):
                return out_path

        # gTTS fallback
        if self._save_gtts(text, out_path):
            return out_path

        # pyttsx3 last resort
        wav_path = out_path.replace(".mp3", ".wav")
        if self._save_pyttsx3(text, wav_path):
            if os.path.exists(wav_path):
                os.rename(wav_path, out_path)
                return out_path

        raise RuntimeError(
            "No TTS engine could export audio.\n\n"
            "Solutions:\n"
            "• Set an OpenAI API key in Settings for human-like voices\n"
            "• pip install gTTS  (requires internet)\n"
            "• pip install pyttsx3  (offline, robotic)"
        )

    def stop(self):
        self._stop_flag = True
        with self._lock:
            if self._pyttsx3_engine:
                try:
                    self._pyttsx3_engine.stop()
                except Exception:
                    pass
        self._cleanup_temp()

    def set_rate(self, value):
        """Accept either openai speed (0.25-4.0 float) or pyttsx3 rate (int 80-300)."""
        try:
            f = float(value)
            if f <= 10.0:
                # openai-style speed multiplier
                self._openai_speed = max(0.25, min(4.0, f))
            else:
                # pyttsx3 words-per-minute
                self._pyttsx3_rate = max(80, min(300, int(f)))
                self._apply_pyttsx3_rate()
        except Exception:
            pass

    def set_openai_speed(self, speed: float):
        self._openai_speed = max(0.25, min(4.0, float(speed)))

    def set_pyttsx3_rate(self, rate: int):
        self._pyttsx3_rate = max(80, min(300, int(rate)))
        self._apply_pyttsx3_rate()

    def _apply_pyttsx3_rate(self):
        with self._lock:
            if self._pyttsx3_engine:
                try:
                    self._pyttsx3_engine.setProperty("rate", self._pyttsx3_rate)
                except Exception:
                    pass

    def set_voice(self, voice: str):
        self.voice = voice

    def set_engine(self, engine_name: str):
        self.engine_name = engine_name

    def is_available(self) -> bool:
        return True

    def get_voices(self) -> list:
        """Return pyttsx3 system voices for backward compatibility."""
        try:
            eng = self._get_pyttsx3_engine()
            if eng:
                voices = eng.getProperty("voices")
                return [{"id": v.id, "name": v.name} for v in voices]
        except Exception:
            pass
        return []

    # ── OpenAI TTS ────────────────────────────────────────────────────────────

    def _openai_available(self) -> bool:
        try:
            import openai  # noqa
            return bool(self._config.get("openai_api_key", "").strip())
        except ImportError:
            return False

    def _get_openai_client(self):
        import openai
        key = self._config.get("openai_api_key", "").strip()
        if not key:
            raise ValueError(
                "OpenAI API key not set.\n\nGo to Settings → OpenAI API Key."
            )
        return openai.OpenAI(api_key=key)

    def _save_openai(self, text: str, output_path: str) -> bool:
        try:
            client = self._get_openai_client()
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=self.voice,
                input=text[:4096],
                speed=self._openai_speed,
            )
            response.stream_to_file(output_path)
            return True
        except Exception as e:
            print(f"OpenAI TTS error: {e}")
            return False

    def _speak_openai(self, text: str) -> bool:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=AUDIO_DIR)
        tmp.close()
        self._current_temp_file = tmp.name
        if self._save_openai(text, tmp.name):
            self._play_audio_file(tmp.name)
            return True
        self._cleanup_temp()
        return False

    # ── gTTS ──────────────────────────────────────────────────────────────────

    def _gtts_available(self) -> bool:
        try:
            import gtts  # noqa
            return True
        except ImportError:
            return False

    def _save_gtts(self, text: str, output_path: str) -> bool:
        try:
            from gtts import gTTS
            gTTS(text=text[:5000], lang="en", slow=False).save(output_path)
            return True
        except Exception as e:
            print(f"gTTS error: {e}")
            return False

    def _speak_gtts(self, text: str) -> bool:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=AUDIO_DIR)
        tmp.close()
        self._current_temp_file = tmp.name
        if self._save_gtts(text, tmp.name):
            self._play_audio_file(tmp.name)
            return True
        self._cleanup_temp()
        return False

    # ── pyttsx3 ──────────────────────────────────────────────────────────────

    def _pyttsx3_available(self) -> bool:
        try:
            import pyttsx3  # noqa
            return True
        except ImportError:
            return False

    def _get_pyttsx3_engine(self):
        with self._lock:
            if self._pyttsx3_engine is None:
                try:
                    import pyttsx3
                    self._pyttsx3_engine = pyttsx3.init()
                    self._pyttsx3_engine.setProperty("rate", self._pyttsx3_rate)
                    voices = self._pyttsx3_engine.getProperty("voices")
                    if voices:
                        self._pyttsx3_engine.setProperty("voice", voices[0].id)
                except Exception as e:
                    print(f"pyttsx3 init error: {e}")
            return self._pyttsx3_engine

    def _speak_pyttsx3(self, text: str) -> bool:
        try:
            eng = self._get_pyttsx3_engine()
            if not eng:
                return False
            eng.setProperty("rate", self._pyttsx3_rate)
            eng.say(text)
            eng.runAndWait()
            return True
        except Exception as e:
            print(f"pyttsx3 speak error: {e}")
            return False

    def _save_pyttsx3(self, text: str, output_path: str) -> bool:
        try:
            eng = self._get_pyttsx3_engine()
            if not eng:
                return False
            eng.setProperty("rate", self._pyttsx3_rate)
            eng.save_to_file(text, output_path)
            eng.runAndWait()
            return os.path.exists(output_path)
        except Exception as e:
            print(f"pyttsx3 save error: {e}")
            return False

    # ── Playback ──────────────────────────────────────────────────────────────

    def _play_audio_file(self, path: str):
        """Play an audio file. Blocks until done or _stop_flag is set."""
        if self._stop_flag:
            return
        # pygame — best cross-platform control
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._stop_flag:
                time.sleep(0.1)
            pygame.mixer.music.stop()
            return
        except ImportError:
            pass
        # Platform fallback
        import subprocess, sys
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["afplay", path])
            else:
                for player in ["mpg123", "mpg321", "aplay"]:
                    try:
                        proc = subprocess.Popen(
                            [player, path], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
                        )
                        while proc.poll() is None and not self._stop_flag:
                            time.sleep(0.1)
                        return
                    except FileNotFoundError:
                        continue
        except Exception as e:
            print(f"Audio playback error: {e}")

    def _cleanup_temp(self):
        if self._current_temp_file:
            try:
                if os.path.exists(self._current_temp_file):
                    os.remove(self._current_temp_file)
            except Exception:
                pass
            self._current_temp_file = None
