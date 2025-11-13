#!/bin/bash
# Build macOS/Linux Installer for VigilantLog

echo "===================================="
echo "Building VigilantLog Installer"
echo "===================================="

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Build executable with PyInstaller
echo "Building executable..."
pyinstaller --onefile \
    --windowed \
    --name "VigilantLog Monitor" \
    --add-data "icon.ico:." \
    --hidden-import=PIL \
    --hidden-import=pystray \
    vigilant_monitor.py

echo ""
echo "===================================="
echo "Build complete!"
echo "===================================="
echo ""
echo "Executable created in: dist/VigilantLog Monitor"
echo ""

# Make executable
chmod +x "dist/VigilantLog Monitor"

# For macOS, create .app bundle
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Creating macOS .app bundle..."
    mkdir -p "dist/VigilantLog Monitor.app/Contents/MacOS"
    mkdir -p "dist/VigilantLog Monitor.app/Contents/Resources"
    
    mv "dist/VigilantLog Monitor" "dist/VigilantLog Monitor.app/Contents/MacOS/"
    
    cat > "dist/VigilantLog Monitor.app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>VigilantLog Monitor</string>
    <key>CFBundleIdentifier</key>
    <string>com.vigilantlog.monitor</string>
    <key>CFBundleName</key>
    <string>VigilantLog Monitor</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF
    
    echo "macOS app created: dist/VigilantLog Monitor.app"
fi

echo "Done!"

