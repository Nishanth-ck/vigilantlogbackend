@echo off
echo ====================================
echo Building VigilantLog File Monitor
echo ====================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
python -m pip install --upgrade pip
pip install watchdog==4.0.0 requests==2.31.0 pystray==0.19.5 pillow==10.4.0 pyinstaller==6.3.0

echo.
echo [2/4] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

echo.
echo [3/4] Building executable with PyInstaller...
python -m PyInstaller --name "VigilantLog File Monitor" ^
    --onefile ^
    --windowed ^
    --icon=NONE ^
    --add-data "vigilant_monitor.py;." ^
    vigilant_monitor.py

echo.
echo [4/4] Checking build output...
if exist "dist\VigilantLog File Monitor.exe" (
    echo ====================================
    echo Build Successful!
    echo ====================================
    echo.
    echo Executable location:
    echo %cd%\dist\VigilantLog File Monitor.exe
    echo.
    echo File size:
    dir "dist\VigilantLog File Monitor.exe" | findstr "VigilantLog"
    echo.
    echo ====================================
    echo Next Steps:
    echo ====================================
    echo 1. Test the executable:
    echo    - Run: "dist\VigilantLog File Monitor.exe"
    echo    - Check system tray for icon
    echo.
    echo 2. Upload to GitHub Releases:
    echo    - Go to: https://github.com/Nishanth-ck/vigilant-log-frontend/releases
    echo    - Create new release or edit existing
    echo    - Upload: dist\VigilantLog File Monitor.exe
    echo.
    echo 3. Update the download link in your website
    echo ====================================
) else (
    echo ====================================
    echo Build Failed!
    echo ====================================
    echo Please check the error messages above
)

echo.
pause

