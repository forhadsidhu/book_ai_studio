import os
import json

APP_NAME = "BookAI Studio"
APP_VERSION = "1.1.0"

# Default paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(os.path.expanduser("~"), "BookAI_Projects")
MODELS_DIR = os.path.join(os.path.expanduser("~"), "BookAI_Models")
EXPORTS_DIR = os.path.join(os.path.expanduser("~"), "BookAI_Exports")
IMAGES_DIR = os.path.join(EXPORTS_DIR, "images")
AUDIO_DIR = os.path.join(EXPORTS_DIR, "audio")
VIDEO_DIR = os.path.join(EXPORTS_DIR, "videos")

for d in [PROJECTS_DIR, MODELS_DIR, EXPORTS_DIR, IMAGES_DIR, AUDIO_DIR, VIDEO_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".bookAI_config.json")

DEFAULT_CONFIG = {
    "lm_studio_url": "http://localhost:1234/v1",
    "lm_studio_model": "local-model",
    "sd_api_url": "http://localhost:7860",
    "use_sd_api": False,
    "sd_model_path": "",
    # Image engine: automatic1111 | local_sd | pollinations | openai
    "image_engine": "automatic1111",   # default: local AUTOMATIC1111 (no filter)
    "pollinations_model": "flux",
    "pollinations_seed": -1,
    # OpenAI settings (optional)
    "openai_api_key": "",
    "use_openai_images": False,
    "openai_image_size": "1024x1024",
    "openai_image_quality": "standard",
    # TTS settings
    "tts_engine": "gtts",     # gtts | pyttsx3 | openai
    "tts_voice": "nova",       # openai voices: nova shimmer alloy echo fable onyx
    "tts_rate": 1.0,           # float speed multiplier for openai (0.25–4.0)
    "tts_pyttsx3_rate": 150,   # words-per-minute for pyttsx3 fallback
    # General
    "theme": "dark",
    "auto_save": True,
    "chunk_size": 800,
    "max_tokens": 1200,
    "temperature": 0.85,
    "writing_style": "Dark Fantasy",
    "last_project": "",
    "editor_font_size": 14,
    "editor_line_height": 1.8,
    "editor_paragraph_spacing": 12,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                merged.update(data)

                # ── Migration: fix old configs that still point to OpenAI ──
                # If no API key is set, never use OpenAI for images or TTS
                if not merged.get("openai_api_key", "").strip():
                    merged["use_openai_images"] = False
                    if merged.get("image_engine", "") == "openai":
                        merged["image_engine"] = "local_sd"
                    if merged.get("tts_engine", "") == "openai":
                        merged["tts_engine"] = "gtts"

                # If image_engine key is missing entirely (very old config),
                # default to local_sd instead of anything cloud-based
                if "image_engine" not in data:
                    merged["image_engine"] = "local_sd"

                return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
