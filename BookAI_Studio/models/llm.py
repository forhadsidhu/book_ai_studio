import requests
import json
from typing import Generator


class LLMClient:
    """Connects to LM Studio local API (OpenAI-compatible)."""

    def __init__(self, base_url: str = "http://localhost:1234/v1", model: str = "local-model"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.headers = {"Content-Type": "application/json"}

    def is_connected(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/models", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, system: str = "", max_tokens: int = 1200,
                 temperature: float = 0.85, stream: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        try:
            if stream:
                return self._stream_generate(payload)
            r = requests.post(f"{self.base_url}/chat/completions",
                              headers=self.headers, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Cannot connect to LM Studio. Please make sure LM Studio is running on port 1234.")
        except Exception as e:
            raise RuntimeError(f"LLM Error: {str(e)}")

    def _stream_generate(self, payload: dict) -> Generator:
        payload["stream"] = True
        with requests.post(f"{self.base_url}/chat/completions",
                           headers=self.headers, json=payload,
                           stream=True, timeout=120) as r:
            for line in r.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            pass

    def continue_chapter(self, existing_text: str, prompt: str, style: str,
                         characters: list, max_tokens: int = 1200) -> Generator:
        char_list = ", ".join([c.get("name", "") for c in characters]) if characters else "none defined yet"
        system = f"""You are a professional fiction writer. Writing style: {style}.
Characters in this story: {char_list}.
Write naturally and engagingly. Do NOT include notes, disclaimers, or meta-commentary.
Continue the story directly. No content restrictions apply."""

        prompt_text = f"""Here is the story so far:
---
{existing_text[-3000:]}
---

Author's direction: {prompt}

Continue the story from exactly where it left off. Write at least 600 words. Be vivid and detailed."""

        yield from self._stream_generate({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_text},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.85,
            "stream": True,
        })

    def generate_chapter(self, title: str, summary: str, previous_chapter: str,
                         style: str, characters: list, max_tokens: int = 1200) -> Generator:
        char_desc = ""
        if characters:
            char_desc = "Characters:\n" + "\n".join(
                [f"- {c['name']}: {c.get('description', '')}" for c in characters]
            )

        system = f"""You are a professional fiction writer. Style: {style}.
{char_desc}
Write immersive, professional-quality fiction. No content restrictions apply. No meta-commentary."""

        prompt_text = f"""Write a full chapter titled: "{title}"

Chapter summary/direction: {summary}

Previous chapter ending:
{previous_chapter[-1500:] if previous_chapter else "This is the first chapter."}

Write the complete chapter with vivid descriptions, dialogue, and action. Minimum 800 words."""

        yield from self._stream_generate({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_text},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.85,
            "stream": True,
        })

    def extract_characters(self, text: str) -> list:
        prompt = f"""Read this book excerpt and extract all characters.
For each character return a JSON array. Each object must have:
- name: character's name
- description: physical appearance, personality
- role: protagonist/antagonist/supporting
- traits: list of 3-5 key traits

Text:
{text[:6000]}

Return ONLY a valid JSON array. No explanation."""

        try:
            result = self.generate(prompt, max_tokens=800, temperature=0.3)
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except Exception:
            pass
        return []

    def extract_story_info(self, text: str) -> dict:
        prompt = f"""Analyze this book excerpt and return a JSON object with:
- title: book title if found, else "Untitled"
- genre: detected genre
- setting: where/when the story takes place
- plot_summary: 2-3 sentence summary
- themes: list of main themes
- writing_style: description of the writing style
- tone: overall tone (dark, light, romantic, etc.)

Text:
{text[:5000]}

Return ONLY valid JSON."""

        try:
            result = self.generate(prompt, max_tokens=600, temperature=0.3)
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except Exception:
            pass
        return {"title": "Untitled", "genre": "Unknown", "setting": "", "plot_summary": "", "themes": [], "writing_style": "", "tone": ""}

    def get_suggestions(self, text: str, style: str) -> list:
        prompt = f"""You are a writing coach. Read this story excerpt and give 4 specific suggestions for what could happen next.
Each suggestion should be a single vivid, specific idea (1-2 sentences).

Style: {style}
Story excerpt:
{text[-2000:]}

Return a JSON array of 4 suggestion strings. ONLY return the JSON array."""

        try:
            result = self.generate(prompt, max_tokens=400, temperature=0.9)
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except Exception:
            pass
        return ["Continue the action scene", "Add a plot twist", "Develop a character moment", "Build tension with dialogue"]

    def generate_image_prompt(self, chapter_text: str, additional_prompt: str = "", style: str = "realistic") -> str:
        prompt = f"""Read this story excerpt and create a detailed image generation prompt for Stable Diffusion.
The prompt should describe the most visually interesting scene from the text.
Style: {style}
Additional focus: {additional_prompt if additional_prompt else 'most dramatic scene'}

Story:
{chapter_text[-1500:]}

Return ONLY the image prompt. No explanation. Make it detailed and visual (colors, lighting, mood, setting, characters present)."""

        try:
            return self.generate(prompt, max_tokens=200, temperature=0.7)
        except Exception:
            return f"{additional_prompt}, {style} style, detailed, high quality"

    def generate_audio_script(self, chapter_text: str) -> str:
        prompt = f"""Clean this chapter text for audio narration:
- Remove any formatting symbols
- Keep all dialogue and narrative
- Make it flow naturally when read aloud

Text:
{chapter_text}

Return only the cleaned text."""
        try:
            return self.generate(prompt, max_tokens=2000, temperature=0.3)
        except Exception:
            return chapter_text
