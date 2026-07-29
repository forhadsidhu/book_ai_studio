@echo off
echo ============================================
echo   BookAI Studio - Build .exe
echo ============================================
echo.

echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building BookAI_Studio.exe...
echo This will take 2-5 minutes. Please wait.
echo.

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

echo.
if exist "dist\BookAI_Studio.exe" (
    echo ============================================
    echo   SUCCESS! Your .exe is ready:
    echo   dist\BookAI_Studio.exe
    echo ============================================
) else (
    echo ============================================
    echo   Build failed. Check errors above.
    echo ============================================
)
echo.
pause
