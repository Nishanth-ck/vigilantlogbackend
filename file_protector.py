import time
import shutil
import os
import socket
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from state import load_state, save_state
from datetime import datetime
from pymongo import MongoClient
import gridfs

# ====== MongoDB Connection ======
MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME = os.environ.get("DB_NAME", "vigilantlog")

# Global monitoring state
monitoring_active = False
observer_instances = []

def is_connected():
    """Check internet connection."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def upload_to_mongo():
    """Upload all files from backup folder to MongoDB."""
    if not MONGO_URI:
        print("[UPLOAD] No MONGO_URI configured, skipping upload.")
        return
        
    state = load_state()
    backup_folder = state.get("backup_folder", "")

    if not backup_folder or not os.path.exists(backup_folder):
        print("[UPLOAD] Backup folder not found.")
        return

    if not is_connected():
        print("[UPLOAD] No internet connection. Skipping upload.")
        return

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        fs = gridfs.GridFS(db)

        uploaded = 0
        for filename in os.listdir(backup_folder):
            file_path = os.path.join(backup_folder, filename)

            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    # Delete old version if exists
                    old_file = db.fs.files.find_one({"filename": filename})
                    if old_file:
                        fs.delete(old_file["_id"])

                    fs.put(
                        f.read(),
                        filename=filename,
                        uploadDate=datetime.utcnow()
                    )
                    uploaded += 1
                    print(f"[UPLOAD] Sent {filename} to MongoDB")

        client.close()
        print(f"[UPLOAD] Completed: {uploaded} files uploaded at {datetime.now()}")
    except Exception as e:
        print(f"[UPLOAD ERROR] {e}")


class ProtectHandler(FileSystemEventHandler):
    """Handles file system events and creates backups."""
    
    def __init__(self):
        self.last_seen_files = {}
        self.recent_files = {}

    def on_modified(self, event):
        if not event.is_directory:
            self.backup_file(event.src_path, "modified")
            self.last_seen_files[event.src_path] = True

    def on_deleted(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            
            # Skip temp files
            if filename.startswith('~') or filename.startswith('.tmp') or filename.endswith('.tmp'):
                return
            
            time.sleep(0.1)
            
            if not os.path.exists(event.src_path):
                self.backup_file(event.src_path, "deleted")
                if event.src_path in self.last_seen_files:
                    del self.last_seen_files[event.src_path]

    def on_created(self, event):
        if not event.is_directory:
            time.sleep(0.2)
            if os.path.exists(event.src_path):
                self.backup_file(event.src_path, "created")
                self.last_seen_files[event.src_path] = True

    def on_moved(self, event):
        if not event.is_directory:
            if event.dest_path and os.path.exists(event.dest_path):
                self.backup_file(event.dest_path, "moved")
                self.last_seen_files[event.dest_path] = True

    def backup_file(self, file_path, action):
        """Backup a file when it's modified, deleted, created, or moved. Keeps only the latest backup."""
        try:
            filename = os.path.basename(file_path)
            state = load_state()
            backup_folder = state.get("backup_folder", "")
            
            if not backup_folder:
                return

            os.makedirs(backup_folder, exist_ok=True)

            # Delete old backups of this file first (keep only latest)
            self.delete_old_backups(backup_folder, filename)

            if action == "deleted":
                time.sleep(0.3)
                
                if os.path.exists(file_path):
                    print(f"[SAVE_DETECTED] File was saved (not deleted): {filename}")
                    self.backup_file(file_path, "modified")
                    return
                
                # For deleted files, use simple naming without timestamp
                backup_name = f"{filename}_BACKUP"
                dest_path = os.path.join(backup_folder, backup_name)
                
                last_backup = self.find_last_backup(backup_folder, filename)
                if last_backup:
                    shutil.copy2(last_backup, dest_path)
                    print(f"[DELETED] Preserved backup: {filename}")
                else:
                    with open(dest_path, 'w') as f:
                        f.write(f"File was deleted: {file_path}\n")
                        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    print(f"[DELETED] Created marker: {filename}")
                    
            elif os.path.exists(file_path):
                # Use simple naming without timestamp - always overwrites previous backup
                backup_name = f"{filename}_BACKUP"
                dest_path = os.path.join(backup_folder, backup_name)
                shutil.copy2(file_path, dest_path)
                print(f"[{action.upper()}] Backed up: {filename} (latest version)")
                
        except Exception as e:
            print(f"Error backing up {file_path}: {e}")

    def delete_old_backups(self, backup_folder, filename):
        """Delete all existing backups of a file to keep only the latest."""
        if not os.path.exists(backup_folder):
            return
        
        try:
            for backup_name in os.listdir(backup_folder):
                # Match both old format (with timestamp) and new format (_BACKUP)
                if backup_name.startswith(filename + '_'):
                    old_backup_path = os.path.join(backup_folder, backup_name)
                    try:
                        os.remove(old_backup_path)
                        print(f"[CLEANUP] Removed old backup: {backup_name}")
                    except Exception as e:
                        print(f"[CLEANUP] Failed to remove {backup_name}: {e}")
        except Exception as e:
            print(f"[CLEANUP] Error cleaning old backups: {e}")

    def find_last_backup(self, backup_folder, filename):
        """Find the most recent backup of a file."""
        if not os.path.exists(backup_folder):
            return None
        
        for backup_name in os.listdir(backup_folder):
            if backup_name.startswith(filename + '_'):
                return os.path.join(backup_folder, backup_name)
        return None


def start_file_monitoring():
    """Start file monitoring in a background thread."""
    global monitoring_active, observer_instances
    
    state = load_state()
    monitor_folders = state.get("monitor_folders", [])
    backup_folder = state.get("backup_folder", "")
    
    if not monitor_folders or not backup_folder:
        print("[FILE_MONITOR] No folders configured to monitor")
        return False
    
    if monitoring_active:
        print("[FILE_MONITOR] Already active")
        return False
    
    os.makedirs(backup_folder, exist_ok=True)
    
    event_handler = ProtectHandler()
    observer_instances = []
    
    for folder in monitor_folders:
        if os.path.exists(folder):
            observer = Observer()
            observer.schedule(event_handler, folder, recursive=True)
            observer.start()
            observer_instances.append(observer)
            print(f"[FILE_MONITOR] Started monitoring: {folder}")
        else:
            print(f"[FILE_MONITOR] Folder does not exist: {folder}")
    
    if observer_instances:
        monitoring_active = True
        print(f"[FILE_MONITOR] Backups will be saved to: {backup_folder}")
        return True
    else:
        print("[FILE_MONITOR] No valid folders to monitor")
        return False


def stop_file_monitoring():
    """Stop file monitoring."""
    global monitoring_active, observer_instances
    
    for observer in observer_instances:
        observer.stop()
        observer.join()
    
    observer_instances = []
    monitoring_active = False
    print("[FILE_MONITOR] Stopped")
    return True


def get_monitoring_status():
    """Get current monitoring status."""
    return monitoring_active

