"""
MongoDB Index Setup Script for User-Hostname Mapping

This script creates the necessary indexes for optimal performance
of the user-hostname mapping feature.

Run this script once after deploying the backend changes:
    python setup_indexes.py
"""

import os
from pymongo import MongoClient, ASCENDING

# Get MongoDB URI from environment or use default
MONGO_URI = os.environ.get("MONGO_URI") or "mongodb+srv://nishanthck09072004_db_user:b9hoRGMqNCbGSK98@cluster0.yyhfish.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = os.environ.get("DB_NAME", "vigilantlog")

def setup_indexes():
    """Create indexes for user_hostname_mapping collection."""
    try:
        print(f"Connecting to MongoDB: {DB_NAME}")
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # Create index on username (unique)
        print("Creating unique index on username...")
        db.user_hostname_mapping.create_index(
            [("username", ASCENDING)],
            unique=True,
            name="username_unique_idx"
        )
        print("✓ Created unique index on username")
        
        # Create index on hostname for faster lookups
        print("Creating index on hostname...")
        db.user_hostname_mapping.create_index(
            [("hostname", ASCENDING)],
            name="hostname_idx"
        )
        print("✓ Created index on hostname")
        
        # Create index on device_id in file_monitor_config for faster lookups
        print("Creating index on device_id in file_monitor_config...")
        db.file_monitor_config.create_index(
            [("device_id", ASCENDING)],
            unique=True,
            name="device_id_unique_idx"
        )
        print("✓ Created unique index on device_id in file_monitor_config")
        
        # Create index on device_id in local_backup_metadata
        print("Creating index on device_id in local_backup_metadata...")
        db.local_backup_metadata.create_index(
            [("device_id", ASCENDING)],
            unique=True,
            name="device_id_unique_idx"
        )
        print("✓ Created unique index on device_id in local_backup_metadata")
        
        # Create index on metadata.device_id in GridFS files
        print("Creating index on metadata.device_id in fs.files...")
        db.fs.files.create_index(
            [("metadata.device_id", ASCENDING)],
            name="device_id_metadata_idx"
        )
        print("✓ Created index on metadata.device_id in fs.files")
        
        print("\n✅ All indexes created successfully!")
        
        # List existing indexes
        print("\n📋 Existing indexes in user_hostname_mapping:")
        for index in db.user_hostname_mapping.list_indexes():
            print(f"  - {index['name']}: {index['key']}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("VigilantLog - MongoDB Index Setup")
    print("=" * 60)
    print()
    
    success = setup_indexes()
    
    if success:
        print("\n" + "=" * 60)
        print("Setup completed successfully!")
        print("You can now use the user-hostname mapping feature.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Setup failed. Please check the error messages above.")
        print("=" * 60)

