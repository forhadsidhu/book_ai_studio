@echo off
echo ============================================
echo   BookAI Studio - Windows Setup
echo ============================================
echo.
echo Installing Python dependencies...
pip install PyQt6 openai PyMuPDF ebooklib pyttsx3 gTTS moviepy Pillow requests python-docx
echo.
echo Installing PyTorch (NVIDIA GPU)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
echo.
echo Installing Stable Diffusion...
pip install diffusers transformers accelerate safetensors
echo.
echo ============================================
echo   Done! Run: python main.py
echo ============================================
pause
