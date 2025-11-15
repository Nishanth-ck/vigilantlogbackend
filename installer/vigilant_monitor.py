"""
VigilantLog File Monitor - Desktop Agent
Standalone executable that monitors files and syncs with cloud
No Python installation required for end users
"""
import time
import shutil
import os
import socket
import sys
import json
import threading
from pathlib import Path
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import requests
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "watchdog", "requests", "pystray", "pillow"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import requests
    import pystray
    from PIL import Image, ImageDraw

# Configuration
CONFIG_DIR = Path.home() / ".vigilantlog"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "monitor.log"

DEFAULT_CONFIG = {
    "backend_url": "https://vigilantlog-backend.onrender.com",
    # Use a shared default ID when the web app does not provide a device name.
    # This keeps things working even when users skip the device-name step.
    "device_id": "default",
    "monitor_folders": [],
    "backup_folder": str(Path.home() / "VigilantLog_Backups"),
    "auto_start": True,
    "monitoring_enabled": False,
    "sync_interval": 60
}

# Global state
monitoring_active = False
observers = []
tray_icon = None


def log_message(message):
    """Log message to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    
    print(log_entry.strip())


def load_config():
    """Load configuration from file."""
    CONFIG_DIR.mkdir(exist_ok=True)
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return {**DEFAULT_CONFIG, **config}
        except Exception as e:
            log_message(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def is_connected():
    """Check internet connection."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


class FileMonitorHandler(FileSystemEventHandler):
    """Handles file system events."""
    
    def __init__(self, backup_folder):
        self.backup_folder = backup_folder
        os.makedirs(backup_folder, exist_ok=True)

    def on_modified(self, event):
        if not event.is_directory:
            self.backup_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            time.sleep(0.2)
            if os.path.exists(event.src_path):
                self.backup_file(event.src_path)

    def backup_file(self, file_path):
        """Backup a file (keeps only latest version)."""
        try:
            filename = os.path.basename(file_path)
            
            # Skip temp files
            if filename.startswith('~') or filename.startswith('.tmp'):
                return
            
            if not os.path.exists(file_path):
                return
            
            # Delete old backups
            for backup_name in os.listdir(self.backup_folder):
                if backup_name.startswith(filename + '_'):
                    try:
                        os.remove(os.path.join(self.backup_folder, backup_name))
                    except:
                        pass
            
            # Create new backup
            backup_name = f"{filename}_BACKUP"
            dest_path = os.path.join(self.backup_folder, backup_name)
            shutil.copy2(file_path, dest_path)
            log_message(f"Backed up: {filename}")
                
        except Exception as e:
            log_message(f"Backup error: {e}")


def sync_with_backend():
    """Sync configuration with backend."""
    config = load_config()
    
    if not is_connected():
        log_message("No internet connection. Using local config.")
        return config
    
    try:
        backend_url = config.get("backend_url", DEFAULT_CONFIG["backend_url"])
        device_id = config.get("device_id") or "default"
        
        response = requests.get(
            f"{backend_url}/api/file-monitor/state",
            params={"deviceId": device_id},
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            remote_state = data.get("state", {})
            
            # Update local config from remote
            if remote_state.get("monitor_folders"):
                config["monitor_folders"] = remote_state["monitor_folders"]
                log_message(f"Updated monitor folders: {len(remote_state['monitor_folders'])} folders")
            
            if remote_state.get("backup_folder"):
                config["backup_folder"] = remote_state["backup_folder"]
                log_message(f"Updated backup folder: {remote_state['backup_folder']}")
            
            if "startMonitoring" in remote_state:
                config["monitoring_enabled"] = remote_state["startMonitoring"]
                log_message(f"Monitoring enabled: {remote_state['startMonitoring']}")
            
            save_config(config)
            log_message("✓ Synced with backend")
        else:
            log_message(f"Backend returned {response.status_code}")
        
    except Exception as e:
        log_message(f"Sync error: {e}")
    
    return config


def start_monitoring():
    """Start file monitoring."""
    global monitoring_active, observers
    
    if monitoring_active:
        return
    
    config = load_config()
    monitor_folders = config.get("monitor_folders", [])
    backup_folder = config.get("backup_folder")
    
    if not monitor_folders:
        log_message("No folders configured")
        return
    
    os.makedirs(backup_folder, exist_ok=True)
    
    event_handler = FileMonitorHandler(backup_folder)
    observers = []
    
    for folder in monitor_folders:
        if os.path.exists(folder):
            observer = Observer()
            observer.schedule(event_handler, folder, recursive=True)
            observer.start()
            observers.append(observer)
            log_message(f"Monitoring: {folder}")
    
    if observers:
        monitoring_active = True
        log_message("Monitoring started")
        update_tray_icon()


def upload_backups_to_cloud():
    """Upload local backup files to the backend's cloud storage endpoint."""
    config = load_config()
    backup_folder = config.get("backup_folder")
    backend_url = config.get("backend_url", DEFAULT_CONFIG["backend_url"])

    if not backup_folder or not os.path.exists(backup_folder):
        log_message("Cloud upload skipped: backup folder not found")
        return

    if not is_connected():
        log_message("Cloud upload skipped: no internet connection")
        return

    try:
        for filename in os.listdir(backup_folder):
            file_path = os.path.join(backup_folder, filename)
            if not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, "rb") as f:
                    files = {"file": (filename, f, "application/octet-stream")}
                    resp = requests.post(
                        f"{backend_url}/api/file-monitor/upload",
                        files=files,
                        timeout=30,
                    )

                if resp.ok:
                    log_message(f"Uploaded {filename} to cloud")
                else:
                    log_message(
                        f"Cloud upload failed for {filename}: "
                        f"{resp.status_code} {resp.text[:200]}"
                    )
            except Exception as e:
                log_message(f"Cloud upload error for {filename}: {e}")
    except Exception as e:
        log_message(f"Cloud upload batch error: {e}")


def stop_monitoring():
    """Stop file monitoring."""
    global monitoring_active, observers
    
    for observer in observers:
        observer.stop()
        observer.join()
    
    observers = []
    monitoring_active = False
    log_message("Monitoring stopped")
    update_tray_icon()


def sync_loop():
    """Background sync loop."""
    while True:
        try:
            config = sync_with_backend()

            # Auto-start/stop based on backend config
            should_monitor = config.get("monitoring_enabled", False)

            if should_monitor and not monitoring_active:
                start_monitoring()
            elif not should_monitor and monitoring_active:
                stop_monitoring()

            # When monitoring is active, periodically push backups to cloud
            if monitoring_active:
                upload_backups_to_cloud()

        except Exception as e:
            log_message(f"Sync loop error: {e}")

        time.sleep(60)  # Sync every minute


def create_icon_image():
    """Create system tray icon."""
    # Create a simple icon
    width = 64
    height = 64
    color1 = (0, 123, 255) if monitoring_active else (128, 128, 128)
    color2 = (0, 86, 179) if monitoring_active else (96, 96, 96)
    
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=color2)
    
    return image


def update_tray_icon():
    """Update tray icon status."""
    global tray_icon
    if tray_icon:
        tray_icon.icon = create_icon_image()
        tray_icon.title = f"VigilantLog - {'Active' if monitoring_active else 'Stopped'}"


def on_start_click(icon, item):
    """Start monitoring from tray menu."""
    start_monitoring()


def on_stop_click(icon, item):
    """Stop monitoring from tray menu."""
    stop_monitoring()


def on_sync_click(icon, item):
    """Manual sync from tray menu."""
    sync_with_backend()
    log_message("Manual sync triggered")


def on_quit_click(icon, item):
    """Quit application."""
    stop_monitoring()
    icon.stop()


def setup_tray_icon():
    """Setup system tray icon."""
    global tray_icon
    
    menu = pystray.Menu(
        pystray.MenuItem("Start Monitoring", on_start_click),
        pystray.MenuItem("Stop Monitoring", on_stop_click),
        pystray.MenuItem("Sync Now", on_sync_click),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit_click)
    )
    
    tray_icon = pystray.Icon(
        "vigilantlog",
        create_icon_image(),
        "VigilantLog - Stopped",
        menu
    )
    
    return tray_icon


def main():
    """Main application entry point."""
    log_message("=" * 60)
    log_message("VigilantLog File Monitor Started")
    log_message("=" * 60)
    
    # First-time setup
    config = load_config()
    
    if config["backend_url"] == "https://your-backend.onrender.com":
        log_message("⚠️  Please configure backend URL")
        log_message(f"Edit: {CONFIG_FILE}")
        # Don't exit - user can configure via web interface
    
    log_message(f"Device ID: {config['device_id']}")
    log_message(f"Config: {CONFIG_FILE}")
    log_message(f"Logs: {LOG_FILE}")
    
    # Start sync thread
    sync_thread = threading.Thread(target=sync_loop, daemon=True)
    sync_thread.start()
    
    # Initial sync
    sync_with_backend()
    
    # Setup and run system tray icon
    icon = setup_tray_icon()
    log_message("Running in system tray...")
    icon.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("Shutting down...")
        stop_monitoring()
        sys.exit(0)
    except Exception as e:
        log_message(f"Fatal error: {e}")
        sys.exit(1)




