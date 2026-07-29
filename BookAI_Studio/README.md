# BookAI Studio

A fully offline AI-powered desktop app for writing books, generating character portraits, creating audio narrations, and producing video trailers — all on your own machine with no cloud and no content restrictions.

---

## Features

### Writing
- AI chapter generation and continuation (real-time streaming output)
- Story direction prompts ("what happens next")
- 4 AI-generated plot suggestions based on current text
- Writing style selector (Dark Fantasy, Romance, Thriller, Erotica, etc.)

### Book Import
- Import PDF, EPUB, TXT, DOCX files
- Auto-extract all chapters, characters, and story details

### Characters
- Character profile manager (name, role, description, traits, appearance)
- AI-generated character avatar portraits (Stable Diffusion)

### Images & Video
- AI scene image generation from chapter text (auto-prompt creation)
- Multiple art styles: Cinematic, Dark Fantasy, Realistic, Oil Painting, Anime, Watercolor
- Book trailer video generator (images + audio + animated title)

### Audio
- Read chapters aloud (pyttsx3 offline or gTTS online)
- Export chapters as MP3

### Privacy
- 100% offline — nothing leaves your machine
- No content filters on text or images
- All data stored locally

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 64-bit | Windows 11 |
| Python | 3.10 | 3.11 |
| RAM | 16 GB | 32 GB |
| Storage | 20 GB | 50 GB |
| GPU | Not required | NVIDIA 8GB+ VRAM (for images) |

---

## Installation (Running from Source)

### Step 1 — Install Python packages

**Windows (double-click):**
```
install.bat
```

**Manual:**
```bash
pip install PyQt6 openai PyMuPDF ebooklib pyttsx3 gTTS moviepy Pillow requests python-docx numpy scipy
```

**If you have no GPU (Windows):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**If you have an NVIDIA GPU:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install diffusers transformers accelerate safetensors
```

---

### Step 2 — Set up LM Studio (required for writing)

LM Studio runs a local AI model that BookAI Studio connects to for text generation.

1. Download LM Studio from **https://lmstudio.ai** and install it
2. Open LM Studio → click the **Search** icon (magnifying glass) in the left sidebar
3. Search for one of these recommended models:

| Model | Size | Quality |
|-------|------|---------|
| `dolphin-2.6-mistral-7b` Q4_K_M | ~4 GB | ⭐⭐⭐⭐ Fast, recommended |
| `dolphin-llama3-8b` Q4_K_M | ~5 GB | ⭐⭐⭐⭐⭐ Best quality |
| `nous-hermes-2-mistral-7b` Q4_K_M | ~4 GB | ⭐⭐⭐⭐ Good balance |

4. Click **Download** on the Q4_K_M version
5. Click the **`<>`** (Developer) icon in the left sidebar
6. Select your downloaded model from the dropdown at the top
7. Click the green **Start Server** button
8. You should see: `Server running on http://localhost:1234`
9. **Keep LM Studio open** while using BookAI Studio

---

### Step 3 — Set up image generation (optional, GPU recommended)

**Option A — Automatic (diffusers, downloads model on first use):**

No setup needed. On first image generation, it downloads Stable Diffusion automatically (~2 GB). Requires internet on first run only.

To use an unrestricted model, go to Settings → Images → enter model path:
```
SG161222/Realistic_Vision_V5.1_noVAE
```

**Option B — AUTOMATIC1111 WebUI (more control, better quality):**

```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
cd stable-diffusion-webui
./webui.bat --api --listen   # Windows
```

Then in BookAI Studio → Settings → enable **"Use SD API"** → URL: `http://localhost:7860`

Download models from [civitai.com](https://civitai.com) and place in `stable-diffusion-webui/models/Stable-diffusion/`

---

### Step 4 — Run the app

```bash
python main.py
```

The status bar will show **"LM Studio: Connected"** when the AI is ready.

---

## Building the Windows .exe

Run `build.bat` (double-click) or run this manually in the `bookAI` folder:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "BookAI_Studio" ^
  --add-data "ui;ui" ^
  --add-data "models;models" ^
  --add-data "utils;utils" ^
  --hidden-import "PyQt6.QtCore" ^
  --hidden-import "PyQt6.QtWidgets" ^
  --hidden-import "PyQt6.QtGui" ^
  --hidden-import "fitz" ^
  --hidden-import "ebooklib" ^
  --hidden-import "docx" ^
  --hidden-import "gtts" ^
  --hidden-import "pyttsx3" ^
  main.py
```

Your `.exe` will be in the `dist/` folder. **No Python required** to run it.

---

## End User Guide (Running the .exe)

### What end users need
1. **LM Studio** — free, from https://lmstudio.ai
2. **A model file** — recommended: `dolphin-2.6-mistral-7b Q4_K_M` (~4 GB download)
3. **BookAI_Studio.exe** — the app

### First-time setup for end users
1. Install LM Studio
2. Open LM Studio → Search icon → search `dolphin-2.6-mistral-7b` → download Q4_K_M
3. LM Studio → `<>` icon → select the model → click **Start Server**
4. Double-click `BookAI_Studio.exe`
5. Status bar shows **"LM Studio: Connected"** — ready to write

### Writing workflow
1. **File → New Project** — create a project
2. **Edit → Add Chapter** — add a chapter
3. Select the chapter → type a direction in the prompt box → click **Generate Chapter**
4. Click **Continue Writing** to extend existing text
5. Use **Get Suggestions** (right panel) for 4 AI plot ideas
6. **Ctrl+S** to save

### Importing an existing book
1. **File → Import Book** (or toolbar button)
2. Select PDF, EPUB, TXT, or DOCX
3. Chapters are extracted automatically
4. Characters and story info are auto-detected by the AI

### Audio
1. Select a chapter → **Audio** tab
2. Click **Read Aloud** (uses system voice, fully offline)
3. Click **Export MP3** to save as audio file

### Images (GPU required for best results)
1. Select a chapter → **Images** tab
2. Click **Generate Scene Image** (AI creates the prompt from your text automatically)
3. Saved to `~/BookAI_Exports/images/`

### Video
1. **Video** tab → **Create Book Trailer**
2. Combines your generated images + audio into an MP4

---

## Running on Paperspace (Cloud GPU)

Use this if you don't have a local GPU.

### Recommended machine
**A4000** (16 GB VRAM) — handles both LLM + Stable Diffusion comfortably (~$0.76/hr)

### Setup
1. Create a **Core** machine with **ML-in-a-Box** template on Paperspace
2. Select **A4000**, 100 GB storage
3. Open the machine → **Open in Browser** (gives desktop in browser)
4. Open terminal inside the browser desktop
5. Upload and extract `bookAI_studio.zip`
6. Install dependencies:

```bash
pip install PyQt6 openai PyMuPDF ebooklib pyttsx3 gTTS moviepy Pillow requests python-docx
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install diffusers transformers accelerate safetensors

# Install llama.cpp as LM Studio replacement (Linux)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python

# Download a model
wget "https://huggingface.co/TheBloke/dolphin-2.6-mistral-7B-GGUF/resolve/main/dolphin-2.6-mistral-7b.Q4_K_M.gguf"

# Start LLM server (keep this terminal open)
python -m llama_cpp.server --model dolphin-2.6-mistral-7b.Q4_K_M.gguf --port 1234 --n_gpu_layers 35
```

7. In a second terminal:
```bash
cd bookAI
python main.py
```

**Important:** Stop your Paperspace machine when not in use — billing is per hour.

---

## Settings Reference

Open via **Tools → Settings** or the ⚙ toolbar button.

| Setting | Default | Description |
|---------|---------|-------------|
| LM Studio URL | `http://localhost:1234/v1` | Local AI server address |
| Model name | `local-model` | Model name (any string works with LM Studio) |
| Max tokens | 1200 | Words per generation — increase for longer chapters |
| Temperature | 0.85 | Creativity. Higher = more varied output |
| TTS Engine | pyttsx3 | `pyttsx3` = offline system voice, `gTTS` = Google online |
| Use SD API | Off | Enable to use AUTOMATIC1111 instead of local diffusers |
| SD API URL | `http://localhost:7860` | AUTOMATIC1111 API address |

---

## Project Structure

```
bookAI/
├── main.py              Entry point
├── config.py            Config and default settings
├── requirements.txt     Python dependencies
├── build.bat            Windows .exe build script
├── install.bat          Windows dependency installer
├── install.sh           Linux dependency installer
├── README.md            This file
├── SETUP_GUIDE.txt      Quick reference card
├── ui/
│   ├── main_window.py   Main window and all UI logic
│   └── styles.py        Dark theme stylesheet
├── models/
│   ├── llm.py           LM Studio API client
│   ├── image_gen.py     Stable Diffusion image generation
│   ├── tts_engine.py    Text-to-speech
│   ├── video_gen.py     Video export
│   └── book_parser.py   PDF/EPUB/TXT/DOCX parser
└── utils/
    └── storage.py       Project save/load (JSON)
```

---

## Troubleshooting

**"LM Studio: Disconnected" in status bar**
- Make sure LM Studio is open, a model is loaded, and the server is running on port 1234
- Go to LM Studio → `<>` icon → confirm server shows `Running`

**torch DLL error on Windows (no GPU)**
```bash
pip uninstall torch torchvision torchaudio -y
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**"No stable diffusion model available"**
- You have no GPU or torch failed to load — image generation won't work locally
- Use AUTOMATIC1111 API mode: Settings → enable "Use SD API" → URL: `http://localhost:7860`
- Or skip images entirely — writing/audio features work without it

**Menu error on startup (TypeError addAction)**
- Upgrade PyQt6: `pip install --upgrade PyQt6`

**PDF import not working**
```bash
pip install --upgrade PyMuPDF
```

**App window doesn't open on Linux**
```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0
export DISPLAY=:0
python main.py
```

**Video creation fails**
```bash
pip install moviepy
# Linux also needs:
sudo apt install ffmpeg
```

---

## Changelog

### Current Version (Milestone 1 + 2 — Merged)
- All Milestone 1 features: writing, characters, audio, book import
- All Milestone 2 features: images, video
- Fixed: PyQt6 menu `addAction` compatibility with newer versions
- Fixed: QProgressBar crash when generating chapters
- Fixed: QThread destroyed while running (multiple background workers)
- Fixed: torch DLL crash on Windows machines without GPU
- Fixed: image_gen gracefully returns unavailable when torch/GPU missing
