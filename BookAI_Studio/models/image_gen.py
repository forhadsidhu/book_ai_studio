"""
Image Generator for BookAI Studio.

Requires stable package versions — run fix_packages.bat first if getting errors.

Backends (in priority order):
  1. local_sd      — Local Stable Diffusion via diffusers (no filter, no internet)
  2. automatic1111 — Local AUTOMATIC1111 WebUI API (no filter, no internet)
  3. pollinations  — Free internet API (has safety filter)
  4. openai        — DALL-E 3 (paid API key required)
"""

import os
import time
import urllib.parse
import requests
from io import BytesIO

try:
    from config import IMAGES_DIR
except ImportError:
    IMAGES_DIR = os.path.join(os.path.expanduser("~"), "BookAI_Exports", "images")

os.makedirs(IMAGES_DIR, exist_ok=True)

# Silence noisy warnings from transformers/diffusers
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("DIFFUSERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")


class ImageGenerator:

    def __init__(self, config: dict = None, use_api: bool = False,
                 api_url: str = "http://localhost:7860", model_path: str = ""):
        self._config = config or {}
        self.use_api = use_api
        self.api_url = api_url.rstrip("/")
        self.model_path = model_path
        self._pipeline = None

    # ── 1. Local diffusers (Stable Diffusion) ────────────────────────────────

    def _get_device(self):
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda", torch.float16
        except Exception:
            pass
        return "cpu", torch.float32

    def _load_pipeline(self):
        if self._pipeline is not None:
            return

        import torch
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

        device, dtype = self._get_device()
        model = self.model_path or "runwayml/stable-diffusion-v1-5"

        # Detect if model is a local single file (.safetensors / .ckpt)
        # vs a HuggingFace repo ID or local directory
        is_single_file = (
            os.path.isfile(model) and
            (model.endswith(".safetensors") or model.endswith(".ckpt"))
        )

        if is_single_file:
            # Load from a single .safetensors or .ckpt file (e.g. from civitai)
            self._pipeline = StableDiffusionPipeline.from_single_file(
                model,
                torch_dtype=dtype,
                safety_checker=None,
                requires_safety_checker=False,
            )
        else:
            # Load from HuggingFace repo ID or local model directory
            self._pipeline = StableDiffusionPipeline.from_pretrained(
                model,
                torch_dtype=dtype,
                safety_checker=None,
                requires_safety_checker=False,
            )

        self._pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self._pipeline.scheduler.config
        )
        self._pipeline = self._pipeline.to(device)

    def _generate_local(self, prompt, negative_prompt, width, height,
                        steps, guidance, seed, save_name):
        import torch
        self._load_pipeline()
        neg = negative_prompt or "blurry, deformed, ugly, watermark, low quality"
        device, _ = self._get_device()
        generator = torch.Generator(device=device).manual_seed(seed) if seed >= 0 else None
        result = self._pipeline(
            prompt=prompt,
            negative_prompt=neg,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator,
        )
        return self._save_image(result.images[0], save_name)

    # ── 2. AUTOMATIC1111 WebUI API ────────────────────────────────────────────

    def _a1111_available(self):
        try:
            r = requests.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _generate_via_a1111(self, prompt, negative_prompt, width, height,
                             steps, guidance, save_name):
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "blurry, bad quality, distorted",
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": guidance,
        }
        r = requests.post(f"{self.api_url}/sdapi/v1/txt2img", json=payload, timeout=180)
        r.raise_for_status()
        import base64
        from PIL import Image
        img_bytes = base64.b64decode(r.json()["images"][0])
        return self._save_image(Image.open(BytesIO(img_bytes)), save_name)

    # ── 3. Pollinations AI (free internet) ───────────────────────────────────

    def _generate_via_pollinations(self, prompt, width, height, save_name):
        from PIL import Image
        encoded = urllib.parse.quote(prompt[:800])
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={width}&height={height}&model=flux&nologo=true&enhance=true"
        )
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        return self._save_image(Image.open(BytesIO(r.content)).convert("RGB"), save_name)

    # ── 4. OpenAI DALL-E 3 ───────────────────────────────────────────────────

    def _openai_key(self):
        return self._config.get("openai_api_key", "").strip()

    def _generate_via_openai(self, prompt, save_name):
        import openai
        from PIL import Image
        client = openai.OpenAI(api_key=self._openai_key())
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt[:4000],
            size=self._config.get("openai_image_size", "1024x1024"),
            quality=self._config.get("openai_image_quality", "standard"),
            n=1,
        )
        r = requests.get(response.data[0].url, timeout=60)
        r.raise_for_status()
        return self._save_image(Image.open(BytesIO(r.content)).convert("RGB"), save_name)

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, prompt: str, negative_prompt: str = "",
                 width: int = 512, height: int = 512,
                 steps: int = 25, guidance: float = 7.5,
                 seed: int = -1, save_name: str = None) -> str:

        engine = self._config.get("image_engine", "local_sd")

        # Never use OpenAI if no key
        if engine == "openai" and not self._openai_key():
            engine = "local_sd"

        if engine == "local_sd":
            return self._generate_local(
                prompt, negative_prompt, width, height, steps, guidance, seed, save_name)

        if engine == "automatic1111":
            if self._a1111_available():
                return self._generate_via_a1111(
                    prompt, negative_prompt, width, height, steps, guidance, save_name)
            raise ConnectionError(
                "AUTOMATIC1111 is not running.\n"
                "Go to Settings → Images → switch engine to 'local_sd'."
            )

        if engine == "pollinations":
            return self._generate_via_pollinations(prompt, width, height, save_name)

        if engine == "openai":
            return self._generate_via_openai(prompt, save_name)

        # Fallback
        return self._generate_local(
            prompt, negative_prompt, width, height, steps, guidance, seed, save_name)

    def generate_character_avatar(self, character_name: str, description: str,
                                  style: str = "realistic portrait",
                                  save_name: str = None) -> str:
        prompt = (
            f"Portrait of {character_name}, {description}, {style}, "
            "detailed face, professional lighting, high quality"
        )
        sname = save_name or f"avatar_{character_name.lower().replace(' ', '_')}"
        return self.generate(prompt, width=512, height=512, save_name=sname)

    def generate_scene(self, scene_prompt: str, style: str = "cinematic",
                       save_name: str = None) -> str:
        prompt = f"{scene_prompt}, {style} style, dramatic lighting, detailed, high quality"
        return self.generate(prompt, width=512, height=512, save_name=save_name)

    def is_available(self) -> bool:
        engine = self._config.get("image_engine", "local_sd")
        if engine == "local_sd":
            try:
                import torch, diffusers  # noqa
                return True
            except ImportError:
                return False
        if engine == "automatic1111":
            return self._a1111_available()
        if engine == "pollinations":
            return True
        if engine == "openai":
            return bool(self._openai_key())
        return False

    def _save_image(self, image, save_name: str = None) -> str:
        if not save_name:
            save_name = f"image_{int(time.time())}"
        if not save_name.endswith(".png"):
            save_name += ".png"
        path = os.path.join(IMAGES_DIR, save_name)
        image.save(path, "PNG")
        return path
