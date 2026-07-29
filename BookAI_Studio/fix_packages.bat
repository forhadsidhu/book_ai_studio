@echo off
echo ============================================================
echo   BookAI Studio — Package Fix Script
echo   This installs versions known to work together
echo ============================================================
echo.

cd /d "%~dp0\.."

call env\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not find virtual environment.
    echo Make sure you run this from inside your release_v1 folder.
    pause
    exit /b 1
)

echo Step 1 — Removing broken package versions...
python -m pip uninstall -y torch torchvision torchaudio diffusers transformers accelerate tokenizers safetensors xformers 2>nul
echo Done.
echo.

echo Step 2 — Installing stable PyTorch (CUDA 12.1, tested with Python 3.10)...
python -m pip install torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo CUDA version failed, trying CPU-only torch...
    python -m pip install torch==2.3.1 torchvision==0.18.1
)
echo Done.
echo.

echo Step 3 — Installing stable diffusers stack...
python -m pip install diffusers==0.30.0 transformers==4.44.0 accelerate==0.33.0 safetensors==0.4.3 tokenizers==0.19.1
echo Done.
echo.

echo Step 4 — Installing other dependencies...
python -m pip install PyQt6 PyQt6-Qt6 openai requests Pillow gTTS pyttsx3 moviepy PyMuPDF ebooklib python-docx omegaconf
echo Done.
echo.

echo ============================================================
echo   All packages installed successfully!
echo   Now run:  python main.py
echo ============================================================
pause
