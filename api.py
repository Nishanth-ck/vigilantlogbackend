from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime
import os
from pymongo import MongoClient
import gridfs
from state import load_state, save_state
import file_protector

app = Flask(__name__)
CORS(app)

# Environment
MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME = os.environ.get("DB_NAME", "vigilantlog")

client = MongoClient(MONGO_URI) if MONGO_URI else None
db = client[DB_NAME] if client else None


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"ok": True, "time": now_iso()})


# ====== FILE MONITORING ENDPOINTS ======

@app.route("/api/file-monitor/state", methods=["GET"])
def get_file_monitor_state():
    """Get file monitoring configuration state."""
    state = load_state()
    return jsonify({
        "success": True,
        "state": state,
        "monitoring_active": file_protector.get_monitoring_status()
    })


@app.route("/api/file-monitor/state", methods=["POST"])
def update_file_monitor_state():
    """Update file monitoring configuration."""
    try:
        data = request.json
        state = load_state()
        
        if "monitor_folders" in data:
            state["monitor_folders"] = data["monitor_folders"]
        if "backup_folder" in data:
            state["backup_folder"] = data["backup_folder"]
        if "startMonitoring" in data:
            state["startMonitoring"] = data["startMonitoring"]
        
        save_state(state)
        return jsonify({"success": True, "state": state})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/file-monitor/start", methods=["POST"])
def start_file_monitoring():
    """Start file monitoring."""
    try:
        state = load_state()
        state["startMonitoring"] = True
        save_state(state)
        
        success = file_protector.start_file_monitoring()
        if success:
            return jsonify({"success": True, "message": "File monitoring started"})
        else:
            return jsonify({"success": False, "error": "Failed to start monitoring"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/stop", methods=["POST"])
def stop_file_monitoring():
    """Stop file monitoring."""
    try:
        state = load_state()
        state["startMonitoring"] = False
        save_state(state)
        
        file_protector.stop_file_monitoring()
        return jsonify({"success": True, "message": "File monitoring stopped"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/local", methods=["GET"])
def get_local_backups():
    """Get list of local backup files."""
    try:
        state = load_state()
        backup_folder = state.get("backup_folder", "")
        
        if not backup_folder or not os.path.exists(backup_folder):
            return jsonify({"success": True, "files": []})
        
        files = []
        for filename in os.listdir(backup_folder):
            file_path = os.path.join(backup_folder, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "name": filename,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        files.sort(key=lambda x: x["modified"], reverse=True)
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/cloud", methods=["GET"])
def get_cloud_backups():
    """Get list of cloud backup files from MongoDB GridFS."""
    try:
        if db is None:
            return jsonify({"success": True, "files": []})
        
        files = []
        for file_doc in db.fs.files.find():
            files.append({
                "name": file_doc["filename"],
                "size": file_doc["length"],
                "uploaded": file_doc.get("uploadDate", datetime.utcnow()).isoformat()
            })
        
        files.sort(key=lambda x: x["uploaded"], reverse=True)
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/upload", methods=["POST"])
def manual_upload():
    """Manually trigger upload to MongoDB."""
    try:
        file_protector.upload_to_mongo()
        return jsonify({"success": True, "message": "Upload completed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/local/<filename>", methods=["GET"])
def download_local_backup(filename):
    """Download a local backup file."""
    try:
        state = load_state()
        backup_folder = state.get("backup_folder", "")
        file_path = os.path.join(backup_folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "File not found"}), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/cloud/<filename>", methods=["GET"])
def download_cloud_backup(filename):
    """Download a file from MongoDB GridFS."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        
        fs = gridfs.GridFS(db)
        file_doc = db.fs.files.find_one({"filename": filename})
        
        if not file_doc:
            return jsonify({"success": False, "error": "File not found"}), 404
        
        file_data = fs.get(file_doc["_id"])
        
        # Save temporarily to send
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_data.read())
            tmp_path = tmp.name
        
        return send_file(tmp_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/local/<filename>", methods=["DELETE"])
def delete_local_backup(filename):
    """Delete a local backup file."""
    try:
        state = load_state()
        backup_folder = state.get("backup_folder", "")
        file_path = os.path.join(backup_folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "File not found"}), 404
        
        os.remove(file_path)
        return jsonify({"success": True, "message": f"Deleted {filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/cloud/<filename>", methods=["DELETE"])
def delete_cloud_backup(filename):
    """Delete a file from MongoDB GridFS."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        
        fs = gridfs.GridFS(db)
        file_doc = db.fs.files.find_one({"filename": filename})
        
        if not file_doc:
            return jsonify({"success": False, "error": "File not found"}), 404
        
        fs.delete(file_doc["_id"])
        return jsonify({"success": True, "message": f"Deleted {filename} from cloud"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
