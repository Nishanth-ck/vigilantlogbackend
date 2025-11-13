@echo off
REM Build Windows Installer for VigilantLog
echo ====================================
echo Building VigilantLog Installer
echo ====================================

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Build executable with PyInstaller
echo Building executable...
pyinstaller --onefile ^
    --windowed ^
    --name "VigilantLog Monitor" ^
    --icon=icon.ico ^
    --add-data "icon.ico;." ^
    --hidden-import=PIL ^
    --hidden-import=pystray ^
    vigilant_monitor.py

echo.
echo ====================================
echo Build complete!
echo ====================================
echo.
echo Executable created in: dist\VigilantLog Monitor.exe
echo.
echo To create MSI installer:
echo 1. Download WiX Toolset: https://wixtoolset.org/
echo 2. Run: build_msi.bat
echo.
pause

