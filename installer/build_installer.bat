@echo off
REM Build Windows Installer for VigilantLog
echo ====================================
echo Building VigilantLog Installer
echo ====================================

REM Install dependencies (use the same Python that runs this script)
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Build executable with PyInstaller
echo Building executable...
python -m PyInstaller --onefile ^
    --windowed ^
    --name "VigilantLogMonitor" ^
    --hidden-import=PIL ^
    --hidden-import=pystray ^
    vigilant_monitor.py

echo.
echo ====================================
echo Build complete!
echo ====================================
echo.
echo Executable created in: dist\VigilantLogMonitor.exe
echo.
echo To create MSI installer:
echo 1. Download WiX Toolset: https://wixtoolset.org/
echo 2. Run: build_msi.bat
echo.
pause


