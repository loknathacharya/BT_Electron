#!/usr/bin/env python3
"""
Backup & Recovery Manager for BYOD Backtesting Application
Handles automatic backups, corruption detection, and database recovery
"""

import os
import sys
import json
import shutil
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import zipfile


class BackupManager:
    """Manages database backups with retention policies and integrity verification"""
    
    def __init__(self, db_dir: Optional[Path] = None, backup_dir: Optional[Path] = None):
        """
        Initialize BackupManager
        
        Args:
            db_dir: Directory containing databases to backup
            backup_dir: Directory to store backups (defaults to db_dir/backups)
        """
        if db_dir is None:
            self.db_dir = Path.home() / '.byod_backtesting'
        else:
            self.db_dir = Path(db_dir)
        
        if backup_dir is None:
            self.backup_dir = self.db_dir / 'backups'
        else:
            self.backup_dir = Path(backup_dir)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Default configuration
        self.config = {
            'retention_days': 30,
            'max_backups': 50,
            'auto_backup_enabled': True,
            'backup_on_startup': True,
            'verify_integrity': True
        }
        
        self._load_config()
    
    def _load_config(self):
        """Load backup configuration from file"""
        config_path = self.backup_dir / 'backup_config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
            except Exception as e:
                print(f"Warning: Failed to load backup config: {e}", file=sys.stderr)
    
    def save_config(self):
        """Save backup configuration to file"""
        config_path = self.backup_dir / 'backup_config.json'
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving backup config: {e}", file=sys.stderr)
            return False
    
    def create_backup(self, backup_type: str = 'auto') -> Dict:
        """
        Create a backup of all databases
        
        Args:
            backup_type: Type of backup ('auto', 'manual', 'pre-migration')
        
        Returns:
            Dict with backup information
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            backup_path.mkdir(exist_ok=True)
            
            # Find all .db files in db_dir
            db_files = list(self.db_dir.glob('*.db'))
            
            if not db_files:
                return {
                    'success': False,
                    'error': 'No database files found to backup'
                }
            
            backed_up_files = []
            total_size = 0
            
            for db_file in db_files:
                try:
                    # Copy database file
                    dest_file = backup_path / db_file.name
                    shutil.copy2(db_file, dest_file)
                    
                    # Calculate checksum
                    checksum = self._calculate_checksum(dest_file)
                    
                    file_size = dest_file.stat().st_size
                    total_size += file_size
                    
                    backed_up_files.append({
                        'name': db_file.name,
                        'size': file_size,
                        'checksum': checksum
                    })
                    
                except Exception as e:
                    print(f"Warning: Failed to backup {db_file.name}: {e}", file=sys.stderr)
            
            # Create metadata file
            metadata = {
                'backup_name': backup_name,
                'backup_type': backup_type,
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'files': backed_up_files,
                'total_size': total_size,
                'version': '1.0'
            }
            
            metadata_path = backup_path / 'metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Verify backup integrity
            if self.config['verify_integrity']:
                verification = self.verify_backup(backup_name)
                if not verification['valid']:
                    return {
                        'success': False,
                        'error': f"Backup verification failed: {verification.get('error', 'Unknown error')}"
                    }
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            return {
                'success': True,
                'backup_name': backup_name,
                'backup_path': str(backup_path),
                'files_backed_up': len(backed_up_files),
                'total_size': total_size,
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Backup failed: {str(e)}"
            }
    
    def list_backups(self) -> List[Dict]:
        """List all available backups with metadata"""
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if not backup_dir.is_dir():
                continue
            
            if not backup_dir.name.startswith('backup_'):
                continue
            
            metadata_path = backup_dir / 'metadata.json'
            if not metadata_path.exists():
                continue
            
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    backups.append(metadata)
            except Exception as e:
                print(f"Warning: Failed to read backup metadata from {backup_dir.name}: {e}", file=sys.stderr)
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return backups
    
    def verify_backup(self, backup_name: str) -> Dict:
        """
        Verify backup integrity by checking checksums
        
        Args:
            backup_name: Name of the backup to verify
        
        Returns:
            Dict with verification results
        """
        backup_path = self.backup_dir / backup_name
        metadata_path = backup_path / 'metadata.json'
        
        if not backup_path.exists():
            return {
                'valid': False,
                'error': 'Backup directory not found'
            }
        
        if not metadata_path.exists():
            return {
                'valid': False,
                'error': 'Backup metadata not found'
            }
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            files_verified = 0
            mismatches = []
            
            for file_info in metadata.get('files', []):
                file_path = backup_path / file_info['name']
                
                if not file_path.exists():
                    mismatches.append(f"{file_info['name']}: File missing")
                    continue
                
                # Verify checksum
                current_checksum = self._calculate_checksum(file_path)
                expected_checksum = file_info.get('checksum')
                
                if current_checksum != expected_checksum:
                    mismatches.append(f"{file_info['name']}: Checksum mismatch")
                else:
                    files_verified += 1
            
            if mismatches:
                return {
                    'valid': False,
                    'error': 'Integrity check failed',
                    'mismatches': mismatches,
                    'files_verified': files_verified
                }
            
            return {
                'valid': True,
                'files_verified': files_verified,
                'backup_name': backup_name
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f"Verification error: {str(e)}"
            }
    
    def restore_backup(self, backup_name: str, target_dir: Optional[Path] = None) -> Dict:
        """
        Restore databases from a backup
        
        Args:
            backup_name: Name of the backup to restore
            target_dir: Directory to restore to (defaults to db_dir)
        
        Returns:
            Dict with restoration results
        """
        backup_path = self.backup_dir / backup_name
        
        if target_dir is None:
            target_dir = self.db_dir
        else:
            target_dir = Path(target_dir)
        
        if not backup_path.exists():
            return {
                'success': False,
                'error': 'Backup not found'
            }
        
        # Verify backup first
        verification = self.verify_backup(backup_name)
        if not verification['valid']:
            return {
                'success': False,
                'error': f"Cannot restore corrupted backup: {verification.get('error')}"
            }
        
        try:
            # Create backup of current state before restoring
            pre_restore_backup = self.create_backup(backup_type='pre-restore')
            
            metadata_path = backup_path / 'metadata.json'
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            restored_files = []
            
            for file_info in metadata.get('files', []):
                source_file = backup_path / file_info['name']
                dest_file = target_dir / file_info['name']
                
                # Backup existing file if it exists
                if dest_file.exists():
                    backup_file = dest_file.with_suffix(dest_file.suffix + '.pre-restore')
                    shutil.copy2(dest_file, backup_file)
                
                # Restore file
                shutil.copy2(source_file, dest_file)
                restored_files.append(file_info['name'])
            
            return {
                'success': True,
                'backup_name': backup_name,
                'restored_files': restored_files,
                'pre_restore_backup': pre_restore_backup.get('backup_name')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Restoration failed: {str(e)}"
            }
    
    def delete_backup(self, backup_name: str) -> Dict:
        """Delete a specific backup"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {
                'success': False,
                'error': 'Backup not found'
            }
        
        try:
            shutil.rmtree(backup_path)
            return {
                'success': True,
                'backup_name': backup_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to delete backup: {str(e)}"
            }
    
    def _cleanup_old_backups(self):
        """Remove old backups according to retention policy"""
        backups = self.list_backups()
        
        # Remove backups older than retention days
        cutoff_date = datetime.now() - timedelta(days=self.config['retention_days'])
        
        for backup in backups:
            try:
                backup_date = datetime.fromisoformat(backup['datetime'])
                if backup_date < cutoff_date:
                    self.delete_backup(backup['backup_name'])
            except Exception as e:
                print(f"Warning: Failed to process backup {backup.get('backup_name')}: {e}", file=sys.stderr)
        
        # Keep only max_backups most recent
        backups = self.list_backups()
        if len(backups) > self.config['max_backups']:
            for backup in backups[self.config['max_backups']:]:
                self.delete_backup(backup['backup_name'])
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def get_backup_statistics(self) -> Dict:
        """Get statistics about backups"""
        backups = self.list_backups()
        
        if not backups:
            return {
                'total_backups': 0,
                'total_size': 0,
                'oldest_backup': None,
                'newest_backup': None
            }
        
        total_size = sum(b.get('total_size', 0) for b in backups)
        
        return {
            'total_backups': len(backups),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_backup': backups[-1]['datetime'] if backups else None,
            'newest_backup': backups[0]['datetime'] if backups else None,
            'retention_days': self.config['retention_days'],
            'max_backups': self.config['max_backups']
        }


class RecoveryManager:
    """Manages database recovery and corruption detection"""
    
    def __init__(self, db_dir: Optional[Path] = None):
        """Initialize RecoveryManager"""
        if db_dir is None:
            self.db_dir = Path.home() / '.byod_backtesting'
        else:
            self.db_dir = Path(db_dir)
    
    def check_database_integrity(self, db_name: str) -> Dict:
        """
        Check database integrity using SQLite's PRAGMA integrity_check
        
        Args:
            db_name: Name of the database file (e.g., 'market_data.db')
        
        Returns:
            Dict with integrity check results
        """
        db_path = self.db_dir / db_name
        
        if not db_path.exists():
            return {
                'valid': False,
                'error': f"Database file not found: {db_name}"
            }
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            conn.close()
            
            if result and result[0] == 'ok':
                return {
                    'valid': True,
                    'database': db_name,
                    'message': 'Database integrity OK'
                }
            else:
                return {
                    'valid': False,
                    'database': db_name,
                    'error': f"Integrity check failed: {result}"
                }
                
        except sqlite3.DatabaseError as e:
            return {
                'valid': False,
                'database': db_name,
                'error': f"Database error: {str(e)}",
                'corrupted': True
            }
        except Exception as e:
            return {
                'valid': False,
                'database': db_name,
                'error': f"Error checking integrity: {str(e)}"
            }
    
    def check_all_databases(self) -> Dict:
        """Check integrity of all databases"""
        db_files = list(self.db_dir.glob('*.db'))
        
        results = {
            'total': len(db_files),
            'valid': 0,
            'corrupted': 0,
            'databases': []
        }
        
        for db_file in db_files:
            check_result = self.check_database_integrity(db_file.name)
            results['databases'].append(check_result)
            
            if check_result.get('valid'):
                results['valid'] += 1
            else:
                results['corrupted'] += 1
        
        return results
    
    def recover_from_wal(self, db_name: str) -> Dict:
        """
        Attempt to recover database from WAL (Write-Ahead Log) file
        
        Args:
            db_name: Name of the database file
        
        Returns:
            Dict with recovery results
        """
        db_path = self.db_dir / db_name
        wal_path = self.db_dir / f"{db_name}-wal"
        
        if not db_path.exists():
            return {
                'success': False,
                'error': 'Database file not found'
            }
        
        if not wal_path.exists():
            return {
                'success': False,
                'error': 'No WAL file found'
            }
        
        try:
            # Create backup before recovery attempt
            backup_path = db_path.with_suffix('.db.pre-recovery')
            shutil.copy2(db_path, backup_path)
            
            # Open database connection (this will automatically checkpoint WAL)
            conn = sqlite3.connect(db_path)
            
            # Force checkpoint
            cursor = conn.cursor()
            cursor.execute("PRAGMA wal_checkpoint(FULL)")
            
            conn.close()
            
            # Verify integrity after recovery
            integrity = self.check_database_integrity(db_name)
            
            if integrity.get('valid'):
                return {
                    'success': True,
                    'database': db_name,
                    'message': 'Successfully recovered from WAL',
                    'backup_created': str(backup_path)
                }
            else:
                return {
                    'success': False,
                    'database': db_name,
                    'error': 'WAL checkpoint completed but database still corrupted',
                    'backup_created': str(backup_path)
                }
                
        except Exception as e:
            return {
                'success': False,
                'database': db_name,
                'error': f"Recovery failed: {str(e)}"
            }
    
    def export_database(self, db_name: str, export_format: str = 'sql') -> Dict:
        """
        Export database to SQL or JSON format for recovery purposes
        
        Args:
            db_name: Name of the database file
            export_format: 'sql' or 'json'
        
        Returns:
            Dict with export results
        """
        db_path = self.db_dir / db_name
        
        if not db_path.exists():
            return {
                'success': False,
                'error': 'Database file not found'
            }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            if export_format == 'sql':
                export_path = self.db_dir / f"{db_name}_{timestamp}.sql"
                
                conn = sqlite3.connect(db_path)
                
                with open(export_path, 'w') as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")
                
                conn.close()
                
                return {
                    'success': True,
                    'export_path': str(export_path),
                    'format': 'sql',
                    'size': export_path.stat().st_size
                }
            
            else:
                return {
                    'success': False,
                    'error': f"Unsupported export format: {export_format}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Export failed: {str(e)}"
            }


def main():
    """Test the backup and recovery managers"""
    backup_mgr = BackupManager()
    recovery_mgr = RecoveryManager()
    
    print("=== Backup & Recovery Manager Test ===\n")
    
    # Create a backup
    print("Creating backup...")
    result = backup_mgr.create_backup(backup_type='manual')
    print(json.dumps(result, indent=2))
    
    # List backups
    print("\nListing backups...")
    backups = backup_mgr.list_backups()
    print(f"Found {len(backups)} backups")
    
    # Check database integrity
    print("\nChecking database integrity...")
    integrity = recovery_mgr.check_all_databases()
    print(json.dumps(integrity, indent=2))
    
    # Get statistics
    print("\nBackup statistics...")
    stats = backup_mgr.get_backup_statistics()
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
