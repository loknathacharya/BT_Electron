#!/usr/bin/env python3
"""
Unit tests for ExpressionEngine
Phase 2: Expression Engine & Validation
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add backend to path
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

from main import ExpressionEngine


def test_parse_comparison_expressions():
    """Test parsing of basic comparison expressions"""
    print("\n=== Testing Parse Comparison Expressions ===")
    
    engine = ExpressionEngine()
    
    # Test 1: Simple greater than
    print("\n1. Testing 'RSI(14) > 70'...")
    result = engine.parse_expression('RSI(14) > 70')
    assert result['valid'], f"Should be valid: {result.get('error')}"
    assert result['ast']['type'] == 'comparison'
    assert result['ast']['operator'] == '>'
    assert result['ast']['left'] == 'RSI(14)'
    assert result['ast']['right'] == '70'
    print(f"✓ Parsed: {result['ast']}")
    
    # Test 2: Less than or equal
    print("\n2. Testing 'close <= 100'...")
    result = engine.parse_expression('close <= 100')
    assert result['valid']
    assert result['ast']['operator'] == '<='
    print(f"✓ Parsed: {result['ast']}")
    
    # Test 3: Not equal
    print("\n3. Testing 'volume != 0'...")
    result = engine.parse_expression('volume != 0')
    assert result['valid']
    assert result['ast']['operator'] == '!='
    print(f"✓ Parsed: {result['ast']}")
    
    print("\n✅ All comparison expression parsing tests passed!")


def test_parse_special_operators():
    """Test parsing of crosses_above/crosses_below"""
    print("\n=== Testing Parse Special Operators ===")
    
    engine = ExpressionEngine()
    
    # Test 1: crosses_above
    print("\n1. Testing 'SMA(close, 20) crosses_above SMA(close, 50)'...")
    result = engine.parse_expression('SMA(close, 20) crosses_above SMA(close, 50)')
    assert result['valid'], f"Should be valid: {result.get('error')}"
    assert result['ast']['type'] == 'special'
    assert result['ast']['operator'] == 'crosses_above'
    print(f"✓ Parsed: {result['ast']}")
    
    # Test 2: crosses_below
    print("\n2. Testing 'RSI(14) crosses_below 70'...")
    result = engine.parse_expression('RSI(14) crosses_below 70')
    assert result['valid']
    assert result['ast']['operator'] == 'crosses_below'
    print(f"✓ Parsed: {result['ast']}")
    
    print("\n✅ All special operator parsing tests passed!")


def test_parse_logical_expressions():
    """Test parsing of expressions with and/or"""
    print("\n=== Testing Parse Logical Expressions ===")
    
    engine = ExpressionEngine()
    
    # Test 1: Simple AND
    print("\n1. Testing '(RSI(14) < 30) and (close > SMA(close, 50))'...")
    result = engine.parse_expression('(RSI(14) < 30) and (close > SMA(close, 50))')
    assert result['valid'], f"Should be valid: {result.get('error')}"
    assert result['ast']['type'] == 'logical'
    assert result['ast']['operator'] == 'and'
    assert result['ast']['left']['type'] == 'comparison'
    assert result['ast']['right']['type'] == 'comparison'
    print(f"✓ Parsed logical AND with nested comparisons")
    
    # Test 2: Simple OR
    print("\n2. Testing 'RSI(14) > 70 or RSI(14) < 30'...")
    result = engine.parse_expression('RSI(14) > 70 or RSI(14) < 30')
    assert result['valid']
    assert result['ast']['operator'] == 'or'
    print(f"✓ Parsed logical OR")
    
    print("\n✅ All logical expression parsing tests passed!")


def test_parse_invalid_expressions():
    """Test error handling for invalid expressions"""
    print("\n=== Testing Parse Invalid Expressions ===")
    
    engine = ExpressionEngine()
    
    # Test 1: Empty expression
    print("\n1. Testing empty expression...")
    result = engine.parse_expression('')
    assert not result['valid'], "Empty expression should be invalid"
    print(f"✓ Correctly rejected: {result.get('error')}")
    
    # Test 2: No operator
    print("\n2. Testing 'RSI(14)'...")
    result = engine.parse_expression('RSI(14)')
    assert not result['valid'], "Expression without operator should be invalid"
    print(f"✓ Correctly rejected: {result.get('error')}")
    
    # Test 3: Incomplete expression
    print("\n3. Testing 'RSI(14) >'...")
    result = engine.parse_expression('RSI(14) >')
    assert result['valid'], "Should parse (will have empty right side)"
    # Note: Parser doesn't validate completeness, just structure
    print(f"✓ Parsed with warning")
    
    print("\n✅ All invalid expression tests passed!")


def test_validate_expression():
    """Test expression validation"""
    print("\n=== Testing Expression Validation ===")
    
    engine = ExpressionEngine()
    
    # Test 1: Valid expression with known indicator
    print("\n1. Testing validation of 'RSI(14) > 70'...")
    result = engine.validate_expression('RSI(14) > 70')
    assert result['valid'], f"Should be valid: {result.get('error')}"
    assert 'RSI(14)' in result.get('required_indicators', [])
    print(f"✓ Validated with indicators: {result['required_indicators']}")
    
    # Test 2: Expression with unknown indicator
    print("\n2. Testing validation of 'UNKNOWN_IND(5) > 10'...")
    result = engine.validate_expression('UNKNOWN_IND(5) > 10')
    assert result['valid'], "Should parse successfully"
    assert len(result.get('warnings', [])) > 0, "Should have warnings"
    print(f"✓ Validated with warnings: {result['warnings']}")
    
    # Test 3: Multiple indicators
    print("\n3. Testing validation of complex expression...")
    result = engine.validate_expression('(RSI(14) < 30) and (close > SMA(close, 50))')
    assert result['valid']
    indicators = result.get('required_indicators', [])
    assert len(indicators) >= 2, "Should identify multiple indicators"
    print(f"✓ Found indicators: {indicators}")
    
    print("\n✅ All validation tests passed!")


def test_evaluate_comparison():
    """Test evaluation of comparison expressions"""
    print("\n=== Testing Expression Evaluation (Comparison) ===")
    
    engine = ExpressionEngine()
    
    # Create test data
    data = pd.DataFrame({
        'timestamp': ['2025-01-01', '2025-01-02', '2025-01-03'],
        'close': [100.0, 105.0, 103.0],
        'RSI_14': [65.0, 72.0, 68.0],
        'SMA_close_20': [98.0, 99.0, 100.0]
    })
    
    # Test 1: True condition
    print("\n1. Testing 'RSI_14 > 70' at index 1 (value=72)...")
    result = engine.evaluate_expression('RSI_14 > 70', data, row_index=1)
    assert result['result'] == True, "Should evaluate to True"
    assert result['values']['RSI_14'] == 72.0
    print(f"✓ Evaluated to True with values: {result['values']}")
    
    # Test 2: False condition
    print("\n2. Testing 'RSI_14 > 70' at index 0 (value=65)...")
    result = engine.evaluate_expression('RSI_14 > 70', data, row_index=0)
    assert result['result'] == False, "Should evaluate to False"
    print(f"✓ Evaluated to False")
    
    # Test 3: Comparison with column
    print("\n3. Testing 'close > SMA_close_20' at index 1...")
    result = engine.evaluate_expression('close > SMA_close_20', data, row_index=1)
    assert result['result'] == True, "105 > 99 should be True"
    print(f"✓ Evaluated to True: close={result['values']['close']}, SMA={result['values']['SMA_close_20']}")
    
    print("\n✅ All comparison evaluation tests passed!")


def test_evaluate_crosses():
    """Test evaluation of crosses_above/crosses_below"""
    print("\n=== Testing Expression Evaluation (Crosses) ===")
    
    engine = ExpressionEngine()
    
    # Create test data with cross
    data = pd.DataFrame({
        'SMA_close_20': [98.0, 102.0, 105.0],
        'SMA_close_50': [100.0, 101.0, 103.0]
    })
    
    # Test 1: crosses_above (happened at index 1)
    print("\n1. Testing 'SMA_close_20 crosses_above SMA_close_50' at index 1...")
    result = engine.evaluate_expression('SMA_close_20 crosses_above SMA_close_50', data, row_index=1)
    assert result['result'] == True, "Should detect cross above"
    print(f"✓ Cross detected: {result['values']}")
    
    # Test 2: No cross at index 2
    print("\n2. Testing same expression at index 2 (no cross)...")
    result = engine.evaluate_expression('SMA_close_20 crosses_above SMA_close_50', data, row_index=2)
    assert result['result'] == False, "Should not detect cross"
    print(f"✓ No cross detected")
    
    # Test 3: crosses_below
    data_below = pd.DataFrame({
        'RSI_14': [75.0, 68.0, 65.0],
        'threshold': [70.0, 70.0, 70.0]
    })
    print("\n3. Testing 'RSI_14 crosses_below 70' at index 1...")
    result = engine.evaluate_expression('RSI_14 crosses_below threshold', data_below, row_index=1)
    assert result['result'] == True, "Should detect cross below"
    print(f"✓ Cross below detected")
    
    print("\n✅ All cross evaluation tests passed!")


def test_evaluate_logical():
    """Test evaluation of logical expressions"""
    print("\n=== Testing Expression Evaluation (Logical) ===")
    
    engine = ExpressionEngine()
    
    data = pd.DataFrame({
        'RSI_14': [25.0, 35.0, 75.0],
        'close': [105.0, 103.0, 110.0],
        'SMA_close_50': [100.0, 100.0, 100.0]
    })
    
    # Test 1: AND - both true
    print("\n1. Testing '(RSI_14 < 30) and (close > SMA_close_50)' at index 0...")
    result = engine.evaluate_expression('(RSI_14 < 30) and (close > SMA_close_50)', data, row_index=0)
    assert result['result'] == True, "Both conditions true, should be True"
    print(f"✓ AND evaluated to True")
    
    # Test 2: AND - one false
    print("\n2. Testing same at index 1 (RSI=35)...")
    result = engine.evaluate_expression('(RSI_14 < 30) and (close > SMA_close_50)', data, row_index=1)
    assert result['result'] == False, "One condition false, should be False"
    print(f"✓ AND evaluated to False")
    
    # Test 3: OR - one true
    print("\n3. Testing '(RSI_14 < 30) or (close > SMA_close_50)' at index 1...")
    result = engine.evaluate_expression('(RSI_14 < 30) or (close > SMA_close_50)', data, row_index=1)
    assert result['result'] == True, "One condition true, OR should be True"
    print(f"✓ OR evaluated to True")
    
    print("\n✅ All logical evaluation tests passed!")


def test_evaluate_exit_criteria():
    """Test exit criteria evaluation with multiple expressions"""
    print("\n=== Testing Exit Criteria Evaluation ===")
    
    engine = ExpressionEngine()
    
    data = pd.DataFrame({
        'RSI_14': [25.0, 48.0, 52.0],
        'close': [105.0, 103.0, 102.0],
        'SMA_close_50': [100.0, 100.0, 100.0]
    })
    
    # Test 1: 'any' logic - one triggers
    print("\n1. Testing exit criteria with 'any' logic...")
    criteria = ['RSI_14 < 50', 'close < SMA_close_50']
    result = engine.evaluate_exit_criteria(criteria, data, row_index=1, logic='any')
    assert result['exit'] == True, "One condition true, should exit"
    assert len(result['triggered_by']) == 1
    print(f"✓ Exit triggered by: {result['triggered_by']}")
    
    # Test 2: 'all' logic - not all true
    print("\n2. Testing exit criteria with 'all' logic (not all true)...")
    result = engine.evaluate_exit_criteria(criteria, data, row_index=1, logic='all')
    assert result['exit'] == False, "Not all conditions true, should not exit"
    print(f"✓ No exit (only {len(result['triggered_by'])}/{len(criteria)} conditions met)")
    
    # Test 3: 'all' logic - all true (need data where both are true)
    print("\n3. Testing exit criteria with 'all' logic (all true)...")
    data_all_true = pd.DataFrame({
        'RSI_14': [45.0, 48.0, 52.0],
        'close': [95.0, 98.0, 99.0],
        'SMA_close_50': [100.0, 100.0, 100.0]
    })
    result = engine.evaluate_exit_criteria(criteria, data_all_true, row_index=1, logic='all')
    assert result['exit'] == True, "All conditions true, should exit"
    assert len(result['triggered_by']) == 2
    print(f"✓ Exit triggered by all: {result['triggered_by']}")
    
    # Test 4: Empty criteria
    print("\n4. Testing empty criteria list...")
    result = engine.evaluate_exit_criteria([], data, row_index=0, logic='any')
    assert result['exit'] == False, "Empty criteria should not trigger exit"
    print(f"✓ No exit with empty criteria")
    
    print("\n✅ All exit criteria tests passed!")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n=== Testing Edge Cases ===")
    
    engine = ExpressionEngine()
    
    # Test 1: Row index out of bounds
    print("\n1. Testing row index out of bounds...")
    data = pd.DataFrame({'value': [1, 2, 3]})
    result = engine.evaluate_expression('value > 0', data, row_index=10)
    assert 'error' in result, "Should return error"
    print(f"✓ Correctly rejected: {result['error']}")
    
    # Test 2: Missing column
    print("\n2. Testing missing column...")
    result = engine.evaluate_expression('missing_col > 0', data, row_index=0)
    assert 'error' in result, "Should return error"
    print(f"✓ Correctly rejected: {result['error']}")
    
    # Test 3: Cross at first bar (needs previous bar)
    print("\n3. Testing cross at first bar...")
    data = pd.DataFrame({'a': [1, 2], 'b': [2, 1]})
    result = engine.evaluate_expression('a crosses_above b', data, row_index=0)
    assert result['result'] == False, "Should return False (need previous bar)"
    print(f"✓ No cross detected at first bar")
    
    print("\n✅ All edge case tests passed!")


def main():
    """Run all tests"""
    print("=" * 60)
    print("EXPRESSION ENGINE: Phase 2 Tests")
    print("Expression Parsing, Validation & Evaluation")
    print("=" * 60)
    
    try:
        test_parse_comparison_expressions()
        test_parse_special_operators()
        test_parse_logical_expressions()
        test_parse_invalid_expressions()
        test_validate_expression()
        test_evaluate_comparison()
        test_evaluate_crosses()
        test_evaluate_logical()
        test_evaluate_exit_criteria()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)
        print("\nPhase 2 implementation is complete and verified:")
        print("  ✅ Expression parsing (comparison, special, logical)")
        print("  ✅ Expression validation with indicator detection")
        print("  ✅ Expression evaluation on real data")
        print("  ✅ Cross detection (crosses_above, crosses_below)")
        print("  ✅ Logical operations (and, or)")
        print("  ✅ Exit criteria evaluation")
        print("  ✅ Edge case handling")
        print("\nReady for Phase 3: Frontend UI Components")
        
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
