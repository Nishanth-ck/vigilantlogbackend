# VigilantLog Monitor - Build Instructions

This folder contains everything needed to build standalone installers for VigilantLog File Monitor.

## 📦 What Gets Built

- **Windows**: `VigilantLog Monitor.exe` (standalone executable)
- **macOS**: `VigilantLog Monitor.app` (application bundle)
- **Linux**: `VigilantLog Monitor` (executable)

## 🔨 Build Instructions

### Windows

1. **Install Python 3.10+** from python.org
2. **Open Command Prompt** in this folder
3. **Run:**
   ```cmd
   build_installer.bat
   ```
4. **Find executable** in `dist/VigilantLog Monitor.exe`

### macOS / Linux

1. **Install Python 3.10+**
2. **Open Terminal** in this folder
3. **Make script executable:**
   ```bash
   chmod +x build_installer.sh
   ```
4. **Run:**
   ```bash
   ./build_installer.sh
   ```
5. **Find executable** in:
   - macOS: `dist/VigilantLog Monitor.app`
   - Linux: `dist/VigilantLog Monitor`

## 📤 Distribution

### Option 1: Direct Download (Simple)

1. Upload the built executable to your backend or file hosting
2. Add download link to your website
3. Users download and run

### Option 2: GitHub Releases (Recommended)

1. Create GitHub repository for your project
2. Upload built executables as release assets
3. Link from your website

### Option 3: Professional MSI Installer (Windows)

After building the .exe:

1. Download **WiX Toolset**: https://wixtoolset.org/
2. Create installer using WiX
3. Users get professional Windows installer

## 🚀 How It Works

1. **User downloads** the executable from your website
2. **User runs** the executable
3. **Executable runs in system tray** (background)
4. **Auto-syncs** configuration from your deployed backend
5. **User configures** folders via your website
6. **Monitor starts automatically** syncing files to cloud

## ⚙️ Configuration

The executable automatically:
- Creates config at: `~/.vigilantlog/config.json`
- Syncs settings from your backend every 60 seconds
- Starts/stops monitoring based on backend commands
- Stores backups in `~/VigilantLog_Backups/`

Users don't need to edit anything manually!

## 🔧 Before Building

**Update backend URL** in `vigilant_monitor.py`:

```python
DEFAULT_CONFIG = {
    "backend_url": "https://your-actual-backend.onrender.com",  # ← Change this!
    ...
}
```

## 📋 Requirements

The executable includes:
- Python runtime (bundled)
- All dependencies (bundled)
- File monitoring engine
- System tray interface
- Auto-update from backend

**No installation required for end users!**

## 🎯 File Size

Expected sizes:
- Windows .exe: ~15-20 MB
- macOS .app: ~20-25 MB
- Linux executable: ~15-20 MB

## 🔄 Updates

To update the monitor for users:
1. Modify `vigilant_monitor.py`
2. Rebuild executable
3. Upload new version
4. Users download and replace old version

## 🐛 Debugging

To test the executable:
1. Run it
2. Check system tray for icon
3. Right-click icon → see menu options
4. View logs at: `~/.vigilantlog/monitor.log`

## 📞 Support

For build issues, check:
- Python version (3.10+)
- All requirements installed
- Sufficient disk space
- Administrator/sudo permissions

