#!/usr/bin/env python3
"""
Test suite for Backup & Recovery System
"""

import sys
import os
import json
import tempfile
import sqlite3
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.backup_manager import BackupManager, RecoveryManager


def create_test_database(db_path: Path):
    """Create a simple test database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create a simple table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_data (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value REAL
        )
    """)
    
    # Insert some data
    cursor.execute("INSERT INTO test_data (name, value) VALUES ('test1', 100.0)")
    cursor.execute("INSERT INTO test_data (name, value) VALUES ('test2', 200.0)")
    
    conn.commit()
    conn.close()
    
    print(f"Created test database: {db_path}")


def test_backup_creation():
    """Test creating a backup"""
    print("\n=== Test: Backup Creation ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / 'db'
        db_dir.mkdir()
        
        # Create test database
        test_db = db_dir / 'test.db'
        create_test_database(test_db)
        
        # Create backup manager
        backup_mgr = BackupManager(db_dir=db_dir)
        
        # Create backup
        result = backup_mgr.create_backup(backup_type='test')
        
        print(f"Backup result: {json.dumps(result, indent=2)}")
        
        assert result['success'], "Backup creation should succeed"
        assert result['files_backed_up'] == 1, "Should backup 1 file"
        assert result['total_size'] > 0, "Backup should have size > 0"
        
        print("✓ Backup creation test passed")


def test_backup_verification():
    """Test verifying a backup"""
    print("\n=== Test: Backup Verification ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / 'db'
        db_dir.mkdir()
        
        # Create test database
        test_db = db_dir / 'test.db'
        create_test_database(test_db)
        
        # Create backup
        backup_mgr = BackupManager(db_dir=db_dir)
        result = backup_mgr.create_backup(backup_type='test')
        backup_name = result['backup_name']
        
        # Verify backup
        verification = backup_mgr.verify_backup(backup_name)
        
        print(f"Verification result: {json.dumps(verification, indent=2)}")
        
        assert verification['valid'], "Backup verification should pass"
        assert verification['files_verified'] == 1, "Should verify 1 file"
        
        print("✓ Backup verification test passed")


def test_backup_restoration():
    """Test restoring from a backup"""
    print("\n=== Test: Backup Restoration ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / 'db'
        db_dir.mkdir()
        
        # Create test database
        test_db = db_dir / 'test.db'
        create_test_database(test_db)
        
        # Create backup
        backup_mgr = BackupManager(db_dir=db_dir)
        result = backup_mgr.create_backup(backup_type='test')
        backup_name = result['backup_name']
        
        # Modify database
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_data (name, value) VALUES ('test3', 300.0)")
        conn.commit()
        conn.close()
        
        # Delete database
        test_db.unlink()
        
        # Restore from backup
        restore_result = backup_mgr.restore_backup(backup_name)
        
        print(f"Restore result: {json.dumps(restore_result, indent=2)}")
        
        assert restore_result['success'], "Restoration should succeed"
        assert test_db.exists(), "Database should be restored"
        
        # Verify restored data
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_data")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 2, "Restored database should have original 2 records"
        
        print("✓ Backup restoration test passed")


def test_database_integrity_check():
    """Test database integrity checking"""
    print("\n=== Test: Database Integrity Check ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / 'db'
        db_dir.mkdir()
        
        # Create test database
        test_db = db_dir / 'test.db'
        create_test_database(test_db)
        
        # Check integrity
        recovery_mgr = RecoveryManager(db_dir=db_dir)
        result = recovery_mgr.check_database_integrity('test.db')
        
        print(f"Integrity check result: {json.dumps(result, indent=2)}")
        
        assert result['valid'], "Integrity check should pass for valid database"
        
        print("✓ Database integrity check test passed")


def test_backup_listing():
    """Test listing backups"""
    print("\n=== Test: Backup Listing ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / 'db'
        db_dir.mkdir()
        
        # Create test database
        test_db = db_dir / 'test.db'
        create_test_database(test_db)
        
        # Create multiple backups
        backup_mgr = BackupManager(db_dir=db_dir)
        backup_mgr.create_backup(backup_type='test1')
        backup_mgr.create_backup(backup_type='test2')
        backup_mgr.create_backup(backup_type='test3')
        
        # List backups
        backups = backup_mgr.list_backups()
        
        print(f"Found {len(backups)} backups")
        
        assert len(backups) == 3, "Should have 3 backups"
        
        print("✓ Backup listing test passed")


def test_backup_deletion():
    """Test deleting a backup"""
    print("\n=== Test: Backup Deletion ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / 'db'
        db_dir.mkdir()
        
        # Create test database
        test_db = db_dir / 'test.db'
        create_test_database(test_db)
        
        # Create backup
        backup_mgr = BackupManager(db_dir=db_dir)
        result = backup_mgr.create_backup(backup_type='test')
        backup_name = result['backup_name']
        
        # Delete backup
        delete_result = backup_mgr.delete_backup(backup_name)
        
        print(f"Delete result: {json.dumps(delete_result, indent=2)}")
        
        assert delete_result['success'], "Deletion should succeed"
        
        # Verify backup is gone
        backups = backup_mgr.list_backups()
        assert len(backups) == 0, "Should have no backups after deletion"
        
        print("✓ Backup deletion test passed")


def test_backup_statistics():
    """Test backup statistics"""
    print("\n=== Test: Backup Statistics ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / 'db'
        db_dir.mkdir()
        
        # Create test database
        test_db = db_dir / 'test.db'
        create_test_database(test_db)
        
        # Create backups
        backup_mgr = BackupManager(db_dir=db_dir)
        backup_mgr.create_backup(backup_type='test1')
        backup_mgr.create_backup(backup_type='test2')
        
        # Get statistics
        stats = backup_mgr.get_backup_statistics()
        
        print(f"Statistics: {json.dumps(stats, indent=2)}")
        
        assert stats['total_backups'] == 2, "Should have 2 backups"
        assert stats['total_size'] > 0, "Total size should be > 0"
        
        print("✓ Backup statistics test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("BACKUP & RECOVERY SYSTEM TESTS")
    print("=" * 60)
    
    try:
        test_backup_creation()
        test_backup_verification()
        test_backup_restoration()
        test_database_integrity_check()
        test_backup_listing()
        test_backup_deletion()
        test_backup_statistics()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
