from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime
import os
from pymongo import MongoClient
import gridfs

app = Flask(__name__)
CORS(app)

# Environment
# Prefer MONGO_URI from environment; fall back to the provided cluster for convenience.
MONGO_URI = os.environ.get("MONGO_URI") or "mongodb+srv://nishanthck09072004_db_user:b9hoRGMqNCbGSK98@cluster0.yyhfish.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = os.environ.get("DB_NAME", "vigilantlog")

client = MongoClient(MONGO_URI) if MONGO_URI else None
db = client[DB_NAME] if client else None


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"ok": True, "time": now_iso()})


# ====== USER-HOSTNAME MAPPING ENDPOINTS ======
# These endpoints link usernames to hostnames for proper data isolation

@app.route("/api/file-monitor/user-mapping/<username>", methods=["GET"])
def get_user_hostname_mapping(username):
    """Get the hostname mapping for a specific username."""
    try:
        if db is None:
            return jsonify({
                "error": "Database not configured",
                "message": "Database connection failed"
            }), 500
        
        if not username or not username.strip():
            return jsonify({
                "error": "Invalid request",
                "message": "Username parameter is required"
            }), 400
        
        # Find the username-hostname mapping in MongoDB
        mapping = db.user_hostname_mapping.find_one({"username": username})
        
        if not mapping:
            return jsonify({
                "error": "User hostname mapping not found",
                "message": "No hostname configured for this user"
            }), 404
        
        # Return the mapping (exclude MongoDB _id field)
        return jsonify({
            "username": mapping["username"],
            "hostname": mapping["hostname"],
            "createdAt": mapping.get("createdAt", now_iso()),
            "updatedAt": mapping.get("updatedAt", now_iso())
        })
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": f"Failed to fetch user hostname mapping: {str(e)}"
        }), 500


@app.route("/api/file-monitor/user-mapping", methods=["POST"])
def save_user_hostname_mapping():
    """Create or update a username-to-hostname mapping."""
    try:
        if db is None:
            return jsonify({
                "error": "Database not configured",
                "message": "Database connection failed"
            }), 500
        
        data = request.json or {}
        username = data.get("username", "").strip()
        hostname = data.get("hostname", "").strip()
        
        # Validate inputs
        if not username or not hostname:
            return jsonify({
                "error": "Validation error",
                "message": "Username and hostname are required"
            }), 400
        
        if len(username) > 100:
            return jsonify({
                "error": "Validation error",
                "message": "Username must be 100 characters or less"
            }), 400
        
        if len(hostname) > 100:
            return jsonify({
                "error": "Validation error",
                "message": "Hostname must be 100 characters or less"
            }), 400
        
        # Check if mapping already exists
        existing_mapping = db.user_hostname_mapping.find_one({"username": username})
        is_new = existing_mapping is None
        
        current_time = now_iso()
        
        # Prepare the mapping document
        mapping_doc = {
            "username": username,
            "hostname": hostname,
            "updatedAt": current_time
        }
        
        # If new, add createdAt
        if is_new:
            mapping_doc["createdAt"] = current_time
        
        # Update or insert the mapping
        db.user_hostname_mapping.update_one(
            {"username": username},
            {"$set": mapping_doc},
            upsert=True
        )
        
        # Fetch the updated document to return
        updated_mapping = db.user_hostname_mapping.find_one({"username": username})
        
        return jsonify({
            "success": True,
            "message": "User hostname mapping created successfully" if is_new else "User hostname mapping updated successfully",
            "data": {
                "username": updated_mapping["username"],
                "hostname": updated_mapping["hostname"],
                "createdAt": updated_mapping.get("createdAt", current_time),
                "updatedAt": updated_mapping.get("updatedAt", current_time)
            }
        })
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": f"Failed to save user hostname mapping: {str(e)}"
        }), 500


# ====== FILE MONITORING CONFIGURATION ENDPOINTS ======
# Note: The backend only stores configuration in MongoDB.
# Actual file monitoring happens on the user's desktop via the .exe agent.

@app.route("/api/file-monitor/state", methods=["GET"])
def get_file_monitor_state():
    """Get file monitoring configuration state from MongoDB."""
    try:
        if db is None:
            return jsonify({
                "success": True,
                "state": {
                    "monitor_folders": [],
                    "backup_folder": "",
                    "startMonitoring": False
                },
                "monitoring_active": False
            })
        # Get device-specific config from MongoDB
        device_id = request.args.get("deviceId", "default")
        if not device_id:
            device_id = "default"
        config = db.file_monitor_config.find_one({"device_id": device_id})
        
        if not config:
            return jsonify({
                "success": True,
                "state": {
                    "monitor_folders": [],
                    "backup_folder": "",
                    "startMonitoring": False
                },
                "monitoring_active": False
            })
        
        return jsonify({
            "success": True,
            "state": {
                "monitor_folders": config.get("monitor_folders", []),
                "backup_folder": config.get("backup_folder", ""),
                "startMonitoring": config.get("startMonitoring", False)
            },
            "monitoring_active": config.get("startMonitoring", False)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/state", methods=["POST"])
def update_file_monitor_state():
    """Update file monitoring configuration in MongoDB."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        data = request.json or {}
        device_id = data.get("device_id") or "default"
        
        # Update or insert config in MongoDB
        config = {
            "device_id": device_id,
            "monitor_folders": data.get("monitor_folders", []),
            "backup_folder": data.get("backup_folder", ""),
            "startMonitoring": data.get("startMonitoring", False),
            "updated_at": now_iso()
        }
        
        db.file_monitor_config.update_one(
            {"device_id": device_id},
            {"$set": config},
            upsert=True
        )
        
        return jsonify({"success": True, "state": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/file-monitor/start", methods=["POST"])
def start_file_monitoring():
    """Signal to start file monitoring (desktop agent will pick this up)."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        data = request.json or {}
        device_id = data.get("device_id") or "default"
        
        # Update MongoDB config
        db.file_monitor_config.update_one(
            {"device_id": device_id},
            {"$set": {"startMonitoring": True, "updated_at": now_iso()}},
            upsert=True
        )
        
        return jsonify({
            "success": True, 
            "message": "Monitoring signal sent. Desktop agent will start within 60 seconds."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/stop", methods=["POST"])
def stop_file_monitoring():
    """Signal to stop file monitoring (desktop agent will pick this up)."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        data = request.json or {}
        device_id = data.get("device_id") or "default"
        
        # Update MongoDB config
        db.file_monitor_config.update_one(
            {"device_id": device_id},
            {"$set": {"startMonitoring": False, "updated_at": now_iso()}},
            upsert=True
        )
        
        return jsonify({
            "success": True, 
            "message": "Stop signal sent. Desktop agent will stop within 60 seconds."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/local", methods=["GET"])
def get_local_backups():
    """Get local backup metadata reported by desktop agents."""
    try:
        if db is None:
            return jsonify({"success": True, "files": []})
        
        device_id = request.args.get("deviceId", "default")
        if not device_id:
            device_id = "default"
        
        # Get local backup metadata from MongoDB
        metadata = db.local_backup_metadata.find_one({"device_id": device_id})
        
        if not metadata or "files" not in metadata:
            return jsonify({"success": True, "files": []})
        
        return jsonify({"success": True, "files": metadata["files"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/local/report", methods=["POST"])
def report_local_backups():
    """Desktop agent reports local backup file metadata."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        
        data = request.json or {}
        device_id = data.get("device_id") or "default"
        files = data.get("files", [])
        
        # Store metadata in MongoDB
        db.local_backup_metadata.update_one(
            {"device_id": device_id},
            {"$set": {"device_id": device_id, "files": files, "updated_at": now_iso()}},
            upsert=True
        )
        
        return jsonify({"success": True, "message": f"Reported {len(files)} local backups"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/cloud", methods=["GET"])
def get_cloud_backups():
    """Get list of cloud backup files from MongoDB GridFS (filtered by device_id if provided)."""
    try:
        if db is None:
            return jsonify({"success": True, "files": []})
        
        # Get device_id from query params (optional - for filtering)
        device_id = request.args.get("deviceId")
        
        files = []
        query = {}
        
        # If device_id is provided, filter by it
        if device_id:
            query = {"metadata.device_id": device_id}
        
        for file_doc in db.fs.files.find(query):
            files.append({
                "name": file_doc["filename"],
                "size": file_doc["length"],
                "uploaded": file_doc.get("uploadDate", datetime.utcnow()).isoformat(),
                "device_id": file_doc.get("metadata", {}).get("device_id", "unknown")
            })
        
        files.sort(key=lambda x: x["uploaded"], reverse=True)
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/upload", methods=["POST"])
def manual_upload():
    """Upload endpoint - desktop agent will upload files to GridFS with device_id metadata."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "Empty filename"}), 400
        
        # Get device_id from form data or default to "default"
        device_id = request.form.get('device_id', 'default')
        
        # Save to GridFS
        fs = gridfs.GridFS(db)
        
        # Delete old version if exists (same filename and device_id)
        old_file = db.fs.files.find_one({
            "filename": file.filename,
            "metadata.device_id": device_id
        })
        if old_file:
            fs.delete(old_file["_id"])
        
        # Upload new version with device_id metadata
        fs.put(
            file.read(),
            filename=file.filename,
            uploadDate=datetime.utcnow(),
            metadata={"device_id": device_id}
        )
        
        return jsonify({"success": True, "message": f"Uploaded {file.filename} for device {device_id}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/file-monitor/backups/local/<filename>", methods=["GET"])
def download_local_backup(filename):
    """Local backups are on the user's machine, not accessible from server."""
    return jsonify({
        "success": False, 
        "error": "Local backups are on your computer. Access them through the desktop agent."
    }), 404


@app.route("/api/file-monitor/backups/cloud/<filename>", methods=["GET"])
def download_cloud_backup(filename):
    """Download a file from MongoDB GridFS (optionally filtered by device_id)."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        
        # Get device_id from query params (optional - for security filtering)
        device_id = request.args.get("deviceId")
        
        fs = gridfs.GridFS(db)
        
        # Build query
        query = {"filename": filename}
        if device_id:
            query["metadata.device_id"] = device_id
        
        file_doc = db.fs.files.find_one(query)
        
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
    """Local backups are on the user's machine, not accessible from server."""
    return jsonify({
        "success": False, 
        "error": "Local backups are on your computer. Delete them through the desktop agent."
    }), 404


@app.route("/api/file-monitor/backups/cloud/<filename>", methods=["DELETE"])
def delete_cloud_backup(filename):
    """Delete a file from MongoDB GridFS (optionally filtered by device_id)."""
    try:
        if db is None:
            return jsonify({"success": False, "error": "Database not configured"}), 500
        
        # Get device_id from query params (optional - for security filtering)
        device_id = request.args.get("deviceId")
        
        fs = gridfs.GridFS(db)
        
        # Build query
        query = {"filename": filename}
        if device_id:
            query["metadata.device_id"] = device_id
        
        file_doc = db.fs.files.find_one(query)
        
        if not file_doc:
            return jsonify({"success": False, "error": "File not found or access denied"}), 404
        
        fs.delete(file_doc["_id"])
        return jsonify({"success": True, "message": f"Deleted {filename} from cloud"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
