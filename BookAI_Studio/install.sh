#!/bin/bash
echo "============================================"
echo "  BookAI Studio - Linux/macOS Setup"
echo "============================================"
echo ""
echo "Installing Python dependencies..."
pip install PyQt6 openai PyMuPDF ebooklib pyttsx3 gTTS moviepy Pillow requests python-docx

echo "Installing PyTorch (NVIDIA GPU)..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

echo "Installing Stable Diffusion..."
pip install diffusers transformers accelerate safetensors

echo "============================================"
echo "  Done! Run: python main.py"
echo "============================================"
