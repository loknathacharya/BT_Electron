#!/usr/bin/env python3
"""
Unit tests for Signal Strategies and Signals feature
Phase 1: Database Schema & Backend Foundation
"""

import sys
import os
import tempfile
import shutil
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

from main import DatabaseService


def cleanup_db(db_service, tmpdir):
    """Safely close connections and cleanup temp directory"""
    try:
        # Close database connections
        if hasattr(db_service, 'user_conn') and db_service.user_conn:
            db_service.user_conn.close()
        if hasattr(db_service, 'market_conn') and db_service.market_conn:
            db_service.market_conn.close()
    except:
        pass
    
    try:
        # Clean up temp directory
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
    except:
        pass


def test_signal_strategy_crud():
    """Test signal strategy CRUD operations"""
    print("\n=== Testing Signal Strategy CRUD ===")
    
    # Create temp database
    tmpdir = tempfile.mkdtemp()
    db_service = None
    
    try:
        db_service = DatabaseService(db_dir=tmpdir)
        
        # Test 1: Create strategy
        print("\n1. Testing create_signal_strategy...")
        strategy_data = {
            'name': 'RSI Overbought',
            'description': 'Short when RSI > 70',
            'conditions': {
                'entry': ['RSI(14) > 70'],
                'exit': ['RSI(14) < 50']
            },
            'default_direction': 'short',
            'scope': 'user',
            'metadata': {
                'reversal_mode': 'no-auto-reversal'
            }
        }
        
        result = db_service.create_signal_strategy(strategy_data)
        assert result.get('success'), f"Failed to create strategy: {result.get('error')}"
        strategy_id = result['strategy_id']
        assert strategy_id.startswith('uuid_'), "Strategy ID should start with 'uuid_'"
        print(f"✓ Created strategy: {strategy_id}")
        
        # Test 2: Get strategy
        print("\n2. Testing get_signal_strategy...")
        result = db_service.get_signal_strategy(strategy_id)
        assert result.get('success'), f"Failed to get strategy: {result.get('error')}"
        strategy = result['strategy']
        assert strategy['name'] == 'RSI Overbought'
        assert strategy['default_direction'] == 'short'
        assert len(strategy['conditions']['entry']) == 1
        print(f"✓ Retrieved strategy: {strategy['name']}")
        
        # Test 3: List strategies
        print("\n3. Testing get_signal_strategies...")
        result = db_service.get_signal_strategies()
        assert result.get('success'), f"Failed to list strategies: {result.get('error')}"
        assert result['count'] == 1
        print(f"✓ Listed {result['count']} strategy(ies)")
        
        # Test 4: Update strategy
        print("\n4. Testing update_signal_strategy...")
        updates = {
            'description': 'Short when RSI > 70 (Updated)',
            'metadata': {'reversal_mode': 'auto-reversal-to-opposite'}
        }
        result = db_service.update_signal_strategy(strategy_id, updates)
        assert result.get('success'), f"Failed to update strategy: {result.get('error')}"
        assert result['version'] == 2, "Version should increment to 2"
        print(f"✓ Updated strategy to version {result['version']}")
        
        # Test 5: Delete strategy
        print("\n5. Testing delete_signal_strategy...")
        result = db_service.delete_signal_strategy(strategy_id)
        assert result.get('success'), f"Failed to delete strategy: {result.get('error')}"
        assert result['deleted'] == strategy_id
        print(f"✓ Deleted strategy: {strategy_id}")
        
        # Test 6: Verify deletion
        result = db_service.get_signal_strategies()
        assert result['count'] == 0, "Strategy count should be 0 after deletion"
        print("✓ Verified deletion")
        
        print("\n✅ All signal strategy CRUD tests passed!")
        
    finally:
        cleanup_db(db_service, tmpdir)


def test_signal_crud():
    """Test signal CRUD operations"""
    print("\n=== Testing Signal CRUD ===")
    
    tmpdir = tempfile.mkdtemp()
    db_service = None
    
    try:
        db_service = DatabaseService(db_dir=tmpdir)
        
        # Setup: Create a strategy and dataset first
        print("\nSetup: Creating strategy and dataset...")
        strategy_data = {
            'name': 'Test Strategy',
            'conditions': {'entry': ['RSI(14) > 70']},
            'default_direction': 'long'
        }
        strategy_result = db_service.create_signal_strategy(strategy_data)
        strategy_id = strategy_result['strategy_id']
        
        # Create test dataset
        dataset_result = db_service.create_dataset('test_dataset', 'Test dataset for signals')
        assert dataset_result.get('success'), f"Failed to create dataset: {dataset_result.get('error')}"
        print("✓ Setup complete")
        
        # Test 1: Create signal
        print("\n1. Testing create_signal...")
        signal_data = {
            'strategy_id': strategy_id,
            'dataset_name': 'test_dataset',
            'symbol': 'AAPL',
            'timestamp': '2025-10-22T10:30:00Z',
            'direction': 'long',
            'entry_values': {
                'close': 175.50,
                'RSI_14': 72.3
            },
            'exit_criteria': ['RSI(14) < 50']
        }
        
        result = db_service.create_signal(signal_data)
        assert result.get('success'), f"Failed to create signal: {result.get('error')}"
        signal_id = result['signal_id']
        assert signal_id.startswith('uuid_'), "Signal ID should start with 'uuid_'"
        print(f"✓ Created signal: {signal_id}")
        
        # Test 2: Get signal
        print("\n2. Testing get_signal...")
        result = db_service.get_signal(signal_id)
        assert result.get('success'), f"Failed to get signal: {result.get('error')}"
        signal = result['signal']
        assert signal['symbol'] == 'AAPL'
        assert signal['status'] == 'open'
        assert signal['historical'] == False
        print(f"✓ Retrieved signal for {signal['symbol']}")
        
        # Test 3: List signals
        print("\n3. Testing get_signals...")
        result = db_service.get_signals()
        assert result.get('success'), f"Failed to list signals: {result.get('error')}"
        assert result['count'] == 1
        assert result['total'] == 1
        print(f"✓ Listed {result['count']} signal(s)")
        
        # Test 4: Filter signals
        print("\n4. Testing get_signals with filters...")
        filters = {'symbol': 'AAPL', 'status': 'open'}
        result = db_service.get_signals(filters)
        assert result['count'] == 1
        print(f"✓ Filtered signals: found {result['count']}")
        
        # Test 5: Update signal
        print("\n5. Testing update_signal...")
        updates = {
            'metadata': {'tags': ['momentum', 'breakout'], 'notes': 'Test note'}
        }
        result = db_service.update_signal(signal_id, updates)
        assert result.get('success'), f"Failed to update signal: {result.get('error')}"
        print("✓ Updated signal metadata")
        
        # Test 6: Close signal
        print("\n6. Testing close_signal...")
        result = db_service.close_signal(signal_id, 'manual')
        assert result.get('success'), f"Failed to close signal: {result.get('error')}"
        assert result.get('closed_at'), "Should return closed_at timestamp"
        print(f"✓ Closed signal at {result['closed_at']}")
        
        # Test 7: Verify signal is closed
        result = db_service.get_signal(signal_id)
        assert result['signal']['status'] == 'closed'
        assert result['signal']['close_reason'] == 'manual'
        print("✓ Verified signal status is 'closed'")
        
        # Test 8: Delete signal
        print("\n8. Testing delete_signal...")
        result = db_service.delete_signal(signal_id)
        assert result.get('success'), f"Failed to delete signal: {result.get('error')}"
        print(f"✓ Deleted signal: {signal_id}")
        
        print("\n✅ All signal CRUD tests passed!")
        
    finally:
        cleanup_db(db_service, tmpdir)


def test_validation_helpers():
    """Test dataset validation helper methods"""
    print("\n=== Testing Dataset Validation Helpers ===")
    
    tmpdir = tempfile.mkdtemp()
    db_service = None
    
    try:
        db_service = DatabaseService(db_dir=tmpdir)
        
        # Create test dataset
        print("\nSetup: Creating test dataset...")
        dataset_result = db_service.create_dataset('validation_test', 'Test dataset')
        assert dataset_result.get('success')
        print("✓ Setup complete")
        
        # Test 1: Validate existing dataset
        print("\n1. Testing validate_dataset_exists (existing)...")
        exists = db_service.validate_dataset_exists('validation_test')
        assert exists == True, "Should return True for existing dataset"
        print("✓ Validated existing dataset")
        
        # Test 2: Validate non-existing dataset
        print("\n2. Testing validate_dataset_exists (non-existing)...")
        exists = db_service.validate_dataset_exists('nonexistent_dataset')
        assert exists == False, "Should return False for non-existing dataset"
        print("✓ Correctly identified non-existing dataset")
        
        # Test 3: Get dataset symbols (empty)
        print("\n3. Testing get_dataset_symbols (empty)...")
        symbols = db_service.get_dataset_symbols('validation_test')
        assert isinstance(symbols, list), "Should return a list"
        assert len(symbols) == 0, "Should be empty for dataset with no data"
        print(f"✓ Retrieved {len(symbols)} symbols")
        
        print("\n✅ All validation helper tests passed!")
        
    finally:
        cleanup_db(db_service, tmpdir)


def test_error_cases():
    """Test error handling and edge cases"""
    print("\n=== Testing Error Cases ===")
    
    tmpdir = tempfile.mkdtemp()
    db_service = None
    
    try:
        db_service = DatabaseService(db_dir=tmpdir)
        
        # Test 1: Create strategy without name
        print("\n1. Testing create_signal_strategy without name...")
        result = db_service.create_signal_strategy({'conditions': {'entry': ['test']}})
        assert 'error' in result, "Should return error for missing name"
        print(f"✓ Correctly rejected: {result['error']}")
        
        # Test 2: Create strategy without entry conditions
        print("\n2. Testing create_signal_strategy without entry conditions...")
        result = db_service.create_signal_strategy({'name': 'Test', 'conditions': {}})
        assert 'error' in result, "Should return error for missing entry conditions"
        print(f"✓ Correctly rejected: {result['error']}")
        
        # Test 3: Get non-existent strategy
        print("\n3. Testing get_signal_strategy with invalid ID...")
        result = db_service.get_signal_strategy('uuid_invalid')
        assert 'error' in result, "Should return error for non-existent strategy"
        print(f"✓ Correctly rejected: {result['error']}")
        
        # Test 4: Create signal with non-existent strategy
        print("\n4. Testing create_signal with invalid strategy_id...")
        signal_data = {
            'strategy_id': 'uuid_invalid',
            'dataset_name': 'test',
            'symbol': 'AAPL',
            'timestamp': '2025-01-01T00:00:00Z',
            'direction': 'long',
            'entry_values': {}
        }
        result = db_service.create_signal(signal_data)
        assert 'error' in result, "Should return error for invalid strategy_id"
        print(f"✓ Correctly rejected: {result['error']}")
        
        # Test 5: Create signal with non-existent dataset
        print("\n5. Testing create_signal with invalid dataset_name...")
        # First create a valid strategy
        strategy_data = {
            'name': 'Test',
            'conditions': {'entry': ['RSI(14) > 70']},
            'default_direction': 'long'
        }
        strategy_result = db_service.create_signal_strategy(strategy_data)
        
        signal_data['strategy_id'] = strategy_result['strategy_id']
        signal_data['dataset_name'] = 'nonexistent_dataset'
        result = db_service.create_signal(signal_data)
        assert 'error' in result, "Should return error for invalid dataset_name"
        print(f"✓ Correctly rejected: {result['error']}")
        
        # Test 6: Close already closed signal
        print("\n6. Testing close_signal on already closed signal...")
        # Create valid dataset and signal
        db_service.create_dataset('test_dataset', 'Test')
        signal_data['dataset_name'] = 'test_dataset'
        signal_result = db_service.create_signal(signal_data)
        signal_id = signal_result['signal_id']
        
        # Close it once
        db_service.close_signal(signal_id, 'manual')
        
        # Try to close again
        result = db_service.close_signal(signal_id, 'manual')
        assert 'error' in result, "Should return error for already closed signal"
        print(f"✓ Correctly rejected: {result['error']}")
        
        print("\n✅ All error case tests passed!")
        
    finally:
        cleanup_db(db_service, tmpdir)


def main():
    """Run all tests"""
    print("=" * 60)
    print("SCANNER → SIGNALS: Phase 1 Tests")
    print("Database Schema & Backend Foundation")
    print("=" * 60)
    
    try:
        test_signal_strategy_crud()
        test_signal_crud()
        test_validation_helpers()
        test_error_cases()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)
        print("\nPhase 1 implementation is complete and verified:")
        print("  ✅ Database schema (signal_strategies, signals tables)")
        print("  ✅ Signal strategy CRUD operations")
        print("  ✅ Signal CRUD operations")
        print("  ✅ Dataset validation helpers")
        print("  ✅ Error handling and edge cases")
        print("\nReady for Phase 2: Expression Engine & Validation")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
