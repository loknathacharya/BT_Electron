# Scanner → Signals Implementation Plan

## Project Context

**Project**: BT_Electron (BYOD Strategy Backtesting Application)  
**Tech Stack**: 
- Frontend: React + TypeScript + Vite
- Backend: Python (SQLite databases)
- IPC: Electron
- Current Features: Scanner with builder UI, symbol lists, dataset management, backtesting

**Date**: October 22, 2025  
**Status**: ✅ **Review-Approved** (Schema conflicts resolved)  
**Last Updated**: October 22, 2025

---

## 🔍 Review Resolution Summary

### Critical Issues Identified & Fixed

✅ **Issue #1: Table Name Conflict** (CRITICAL)
- **Problem**: Proposed `strategies` table conflicts with existing backtest schema
- **Resolution**: Renamed to `signal_strategies` and `signals` (distinct namespace)
- **Impact**: Zero breaking changes; fully additive implementation

✅ **Issue #2: Cross-Database Foreign Key** (HIGH)
- **Problem**: `signals.dataset_name` FK pointed to `datasets` table in different database
- **Resolution**: Removed FK; using TEXT field + application-layer validation
- **Validation**: `validate_dataset_exists()` method checks market_data.db before insert

✅ **Issue #3: NULL Uniqueness Bug** (MEDIUM)
- **Problem**: `UNIQUE(name, created_by)` with nullable `created_by` allows duplicates
- **Resolution**: `created_by` now NOT NULL with default `'default_user'`
- **Benefit**: Enables future multi-user support

### Design Decisions

**Q: Migrate existing strategies or create new tables?**  
**A**: Create new tables (`signal_strategies`, `signals`) to preserve backtest features

**Q: Where should datasets live for FK enforcement?**  
**A**: Keep in market_data.db; use application validation (standard cross-DB pattern)

**Q: Migration vs. additive?**  
**A**: Fully additive - no schema migrations, no breaking changes

---

## Executive Summary

Convert transient scanner results into persistent **signals** that users can save, manage, and reuse across datasets. This feature transforms one-time scanner hits into actionable trade signals with defined entry and optional exit criteria, enabling systematic tracking, backtesting, and performance analysis.

**Core Value Propositions**:
- Persist scanner discoveries as tradeable signals
- Define entry-only OR entry+exit strategies
- Support single and multi-indicator strategies
- Enable historical backtesting across full dataset history
- Provide strategy reusability across datasets

---

## Phase 1: Database Schema & Backend Foundation

### 1.1 Schema Conflicts Resolution

**CRITICAL FINDINGS FROM REVIEW**:

1. ✅ **Existing `strategies` table conflict**: Current schema in `user_data.db` uses `id` (INTEGER), not `strategy_id` (TEXT/UUID)
2. ✅ **Cross-database FK issue**: `datasets` table is in `market_data.db`, but `signals` would be in `user_data.db`
3. ✅ **NULL uniqueness issue**: `UNIQUE(name, created_by)` with nullable `created_by` allows duplicates

**RESOLUTION STRATEGY**: Use separate tables to preserve existing backtest features

### 1.2 Database Schema Design

**Location**: `backend/main.py` → `DatabaseService.init_user_database()`

Create new tables with distinct names to avoid conflicts with existing `strategies` and `backtest_results`:

```sql
-- Trading Strategies table (separate from backtest strategies)
-- Uses signal_ prefix to distinguish from existing strategies table
CREATE TABLE IF NOT EXISTS signal_strategies (
    id TEXT PRIMARY KEY,                    -- UUID (e.g., 'uuid_12345...')
    name TEXT NOT NULL,
    description TEXT,
    conditions_json TEXT NOT NULL,          -- JSON: {entry: [...], exit: [...]}
    default_direction TEXT NOT NULL,        -- 'long' | 'short' | 'auto'
    scope TEXT NOT NULL DEFAULT 'user',     -- 'global' | 'user'
    created_by TEXT NOT NULL DEFAULT 'default_user',  -- Required, no NULLs
    created_at INTEGER NOT NULL,            -- Unix timestamp
    updated_at INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT,                     -- Additional config (reversal settings, etc.)
    UNIQUE(name, created_by)                -- Safe: created_by is NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signal_strategies_created_by ON signal_strategies(created_by);
CREATE INDEX IF NOT EXISTS idx_signal_strategies_scope ON signal_strategies(scope);
CREATE INDEX IF NOT EXISTS idx_signal_strategies_name ON signal_strategies(name);

-- Signals table
-- Stores in user_data.db, references dataset_name as TEXT (no FK)
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,                    -- UUID
    strategy_id TEXT NOT NULL,
    dataset_name TEXT NOT NULL,             -- TEXT reference (no FK across databases)
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,                -- ISO8601
    direction TEXT NOT NULL,                -- 'long' | 'short'
    entry_values_json TEXT NOT NULL,        -- Snapshot of indicator values at creation
    exit_criteria_json TEXT,                -- Array of exit expressions
    status TEXT NOT NULL DEFAULT 'open',    -- 'open' | 'closed' | 'cancelled'
    created_by TEXT NOT NULL DEFAULT 'default_user',
    created_at INTEGER NOT NULL,
    closed_at INTEGER,                      -- Unix timestamp
    closed_by_signal_id TEXT,               -- For reversal tracking (self-reference)
    close_reason TEXT,                      -- 'manual' | 'exit_condition' | 'reversal'
    historical INTEGER DEFAULT 0,           -- SQLite: use INTEGER for boolean (0/1)
    metadata_json TEXT,                     -- P&L, tags, notes, etc.
    FOREIGN KEY (strategy_id) REFERENCES signal_strategies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_signals_dataset ON signals(dataset_name);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_created_by ON signals(created_by);
CREATE INDEX IF NOT EXISTS idx_signals_dataset_symbol ON signals(dataset_name, symbol);
CREATE INDEX IF NOT EXISTS idx_signals_historical ON signals(historical);
```

**Design Rationale**:

1. **Table Naming**: `signal_strategies` and `signals` (not `strategies`) to avoid collision with existing backtest schema
2. **No Cross-DB FK**: `dataset_name` is TEXT with no FOREIGN KEY, validated at application layer
3. **NOT NULL Constraints**: `created_by` defaults to `'default_user'` to prevent NULL uniqueness issues
4. **Boolean as INTEGER**: SQLite best practice (0=false, 1=true)
5. **Self-referencing FK**: `closed_by_signal_id` references `signals(id)` for reversal tracking

### 1.3 Dataset Validation Helper

**Location**: `backend/main.py` → Add validation method

Since `dataset_name` cannot use FK (cross-database), validate at application layer:

```python
def validate_dataset_exists(self, dataset_name: str) -> bool:
    """Check if dataset exists in market_data.db.
    
    Returns:
        True if dataset exists, False otherwise
    """
    try:
        with sqlite3.connect(self.market_db_path) as conn:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM datasets WHERE name = ?',
                (dataset_name,)
            )
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        print(f"Error validating dataset: {e}", file=sys.stderr)
        return False

def get_dataset_symbols(self, dataset_name: str) -> list[str]:
    """Get all symbols available in a dataset.
    
    Used to validate symbol exists before creating signals.
    """
    try:
        with sqlite3.connect(self.market_db_path) as conn:
            cursor = conn.execute(
                'SELECT DISTINCT symbol FROM price_data WHERE dataset = ? ORDER BY symbol',
                (dataset_name,)
            )
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []
```

### 1.4 Backend CRUD Operations

**Location**: `backend/main.py` → Add new methods to `DatabaseService`

**IMPORTANT**: All methods use `signal_strategies` table (not `strategies`) and UUID string IDs (not INTEGER).

#### Signal Strategies CRUD

```python
def create_signal_strategy(self, strategy_data: dict) -> dict:
    """Create a new trading strategy.
    
    Args:
        strategy_data: {
            'name': str,
            'description': str (optional),
            'conditions': {'entry': [str], 'exit': [str] (optional)},
            'default_direction': 'long' | 'short' | 'auto',
            'scope': 'user' | 'global' (default: 'user'),
            'created_by': str (default: 'default_user'),
            'metadata': dict (optional) - reversal_mode, exit_logic, etc.
        }
    
    Returns:
        {'success': True, 'strategy_id': str} or {'error': str}
    """
    import uuid
    
    try:
        strategy_id = f"uuid_{uuid.uuid4().hex}"
        name = strategy_data.get('name')
        description = strategy_data.get('description', '')
        conditions = strategy_data.get('conditions', {})
        default_direction = strategy_data.get('default_direction', 'auto')
        scope = strategy_data.get('scope', 'user')
        created_by = strategy_data.get('created_by', 'default_user')
        metadata = strategy_data.get('metadata', {})
        
        # Validation
        if not name:
            return {'error': 'Strategy name is required'}
        if not conditions.get('entry'):
            return {'error': 'Entry conditions are required'}
        if default_direction not in ['long', 'short', 'auto']:
            return {'error': 'Invalid default_direction'}
        if scope not in ['user', 'global']:
            return {'error': 'Invalid scope'}
        
        now = int(time.time())
        
        with sqlite3.connect(self.user_db_path) as conn:
            conn.execute('''
                INSERT INTO signal_strategies 
                (id, name, description, conditions_json, default_direction, 
                 scope, created_by, created_at, updated_at, version, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_id, name, description, 
                json.dumps(conditions), default_direction,
                scope, created_by, now, now, 1,
                json.dumps(metadata)
            ))
            conn.commit()
        
        return {'success': True, 'strategy_id': strategy_id}
        
    except sqlite3.IntegrityError as e:
        if 'UNIQUE' in str(e):
            return {'error': f'Strategy name "{name}" already exists for this user'}
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}

def get_signal_strategies(self, created_by: str = None, scope: str = None) -> dict:
    """List all signal strategies with optional filters."""
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            query = 'SELECT * FROM signal_strategies WHERE 1=1'
            params = []
            
            if created_by:
                query += ' AND created_by = ?'
                params.append(created_by)
            if scope:
                query += ' AND scope = ?'
                params.append(scope)
            
            query += ' ORDER BY updated_at DESC'
            
            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            
            strategies = []
            for row in cursor.fetchall():
                strategy = dict(zip(columns, row))
                # Parse JSON fields
                strategy['conditions'] = json.loads(strategy['conditions_json'])
                strategy['metadata'] = json.loads(strategy['metadata_json'] or '{}')
                strategies.append(strategy)
            
            return {'success': True, 'strategies': strategies, 'count': len(strategies)}
    except Exception as e:
        return {'error': str(e)}

def get_signal_strategy(self, strategy_id: str) -> dict:
    """Get single signal strategy by ID."""
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM signal_strategies WHERE id = ?',
                (strategy_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {'error': 'Strategy not found'}
            
            columns = [desc[0] for desc in cursor.description]
            strategy = dict(zip(columns, row))
            strategy['conditions'] = json.loads(strategy['conditions_json'])
            strategy['metadata'] = json.loads(strategy['metadata_json'] or '{}')
            
            return {'success': True, 'strategy': strategy}
    except Exception as e:
        return {'error': str(e)}

def update_signal_strategy(self, strategy_id: str, updates: dict) -> dict:
    """Update signal strategy (increments version)."""
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            # First check if exists
            cursor = conn.execute(
                'SELECT version FROM signal_strategies WHERE id = ?',
                (strategy_id,)
            )
            row = cursor.fetchone()
            if not row:
                return {'error': 'Strategy not found'}
            
            current_version = row[0]
            new_version = current_version + 1
            now = int(time.time())
            
            # Build update query dynamically
            set_clauses = ['updated_at = ?', 'version = ?']
            params = [now, new_version]
            
            if 'name' in updates:
                set_clauses.append('name = ?')
                params.append(updates['name'])
            if 'description' in updates:
                set_clauses.append('description = ?')
                params.append(updates['description'])
            if 'conditions' in updates:
                set_clauses.append('conditions_json = ?')
                params.append(json.dumps(updates['conditions']))
            if 'default_direction' in updates:
                set_clauses.append('default_direction = ?')
                params.append(updates['default_direction'])
            if 'metadata' in updates:
                set_clauses.append('metadata_json = ?')
                params.append(json.dumps(updates['metadata']))
            
            params.append(strategy_id)
            
            query = f"UPDATE signal_strategies SET {', '.join(set_clauses)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()
            
            return {'success': True, 'version': new_version}
            
    except sqlite3.IntegrityError as e:
        if 'UNIQUE' in str(e):
            return {'error': 'Strategy name already exists for this user'}
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}

def delete_signal_strategy(self, strategy_id: str) -> dict:
    """Delete signal strategy (cascades to signals)."""
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            cursor = conn.execute(
                'DELETE FROM signal_strategies WHERE id = ?',
                (strategy_id,)
            )
            
            if cursor.rowcount == 0:
                return {'error': 'Strategy not found'}
            
            conn.commit()
            return {'success': True, 'deleted': strategy_id}
    except Exception as e:
        return {'error': str(e)}
```

#### Signals CRUD

```python
def create_signal(self, signal_data: dict) -> dict:
    """Create a new signal from scanner result.
    
    Args:
        signal_data: {
            'strategy_id': str,
            'dataset_name': str,
            'symbol': str,
            'timestamp': str (ISO8601),
            'direction': 'long' | 'short',
            'entry_values': dict,  # indicator snapshots
            'exit_criteria': [str] (optional),
            'created_by': str (default: 'default_user'),
            'historical': bool (default: False),
            'metadata': dict (optional)
        }
    
    Returns:
        {'success': True, 'signal_id': str} or {'error': str}
    """
    import uuid
    
    try:
        # Validation
        strategy_id = signal_data.get('strategy_id')
        dataset_name = signal_data.get('dataset_name')
        symbol = signal_data.get('symbol')
        timestamp = signal_data.get('timestamp')
        direction = signal_data.get('direction')
        entry_values = signal_data.get('entry_values', {})
        
        if not all([strategy_id, dataset_name, symbol, timestamp, direction]):
            return {'error': 'Missing required fields'}
        
        # Validate strategy exists
        strategy_result = self.get_signal_strategy(strategy_id)
        if 'error' in strategy_result:
            return {'error': f'Invalid strategy_id: {strategy_result["error"]}'}
        
        # Validate dataset exists (application-layer FK)
        if not self.validate_dataset_exists(dataset_name):
            return {'error': f'Dataset "{dataset_name}" not found'}
        
        # Validate symbol exists in dataset (optional but recommended)
        dataset_symbols = self.get_dataset_symbols(dataset_name)
        if dataset_symbols and symbol not in dataset_symbols:
            return {'error': f'Symbol "{symbol}" not found in dataset "{dataset_name}"'}
        
        if direction not in ['long', 'short']:
            return {'error': 'Invalid direction (must be "long" or "short")'}
        
        signal_id = f"uuid_{uuid.uuid4().hex}"
        created_by = signal_data.get('created_by', 'default_user')
        exit_criteria = signal_data.get('exit_criteria', [])
        historical = 1 if signal_data.get('historical', False) else 0
        metadata = signal_data.get('metadata', {})
        now = int(time.time())
        
        with sqlite3.connect(self.user_db_path) as conn:
            conn.execute('''
                INSERT INTO signals 
                (id, strategy_id, dataset_name, symbol, timestamp, direction,
                 entry_values_json, exit_criteria_json, status, created_by,
                 created_at, historical, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id, strategy_id, dataset_name, symbol, timestamp, direction,
                json.dumps(entry_values), json.dumps(exit_criteria),
                'open', created_by, now, historical, json.dumps(metadata)
            ))
            conn.commit()
        
        return {'success': True, 'signal_id': signal_id}
        
    except Exception as e:
        return {'error': str(e)}

def get_signals(self, filters: dict = None) -> dict:
    """List signals with filters: dataset, symbol, strategy_id, status, date range.
    
    Args:
        filters: {
            'dataset_name': str (optional),
            'symbol': str (optional),
            'strategy_id': str (optional),
            'status': str (optional) - 'open', 'closed', 'cancelled',
            'created_by': str (optional),
            'historical': bool (optional),
            'start_date': int (optional) - Unix timestamp,
            'end_date': int (optional) - Unix timestamp,
            'limit': int (optional) - default 100,
            'offset': int (optional) - default 0
        }
    
    Returns:
        {'success': True, 'signals': [...], 'count': int, 'total': int}
    """
    try:
        filters = filters or {}
        
        with sqlite3.connect(self.user_db_path) as conn:
            query = 'SELECT * FROM signals WHERE 1=1'
            params = []
            
            if filters.get('dataset_name'):
                query += ' AND dataset_name = ?'
                params.append(filters['dataset_name'])
            if filters.get('symbol'):
                query += ' AND symbol = ?'
                params.append(filters['symbol'])
            if filters.get('strategy_id'):
                query += ' AND strategy_id = ?'
                params.append(filters['strategy_id'])
            if filters.get('status'):
                query += ' AND status = ?'
                params.append(filters['status'])
            if filters.get('created_by'):
                query += ' AND created_by = ?'
                params.append(filters['created_by'])
            if 'historical' in filters:
                historical_val = 1 if filters['historical'] else 0
                query += ' AND historical = ?'
                params.append(historical_val)
            if filters.get('start_date'):
                query += ' AND created_at >= ?'
                params.append(filters['start_date'])
            if filters.get('end_date'):
                query += ' AND created_at <= ?'
                params.append(filters['end_date'])
            
            # Get total count before pagination
            count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
            cursor = conn.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Add sorting and pagination
            query += ' ORDER BY created_at DESC'
            limit = filters.get('limit', 100)
            offset = filters.get('offset', 0)
            query += ' LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            
            signals = []
            for row in cursor.fetchall():
                signal = dict(zip(columns, row))
                # Parse JSON fields
                signal['entry_values'] = json.loads(signal['entry_values_json'])
                signal['exit_criteria'] = json.loads(signal['exit_criteria_json'] or '[]')
                signal['metadata'] = json.loads(signal['metadata_json'] or '{}')
                # Convert historical INTEGER to boolean
                signal['historical'] = bool(signal['historical'])
                signals.append(signal)
            
            return {
                'success': True,
                'signals': signals,
                'count': len(signals),
                'total': total
            }
    except Exception as e:
        return {'error': str(e)}

def get_signal(self, signal_id: str) -> dict:
    """Get single signal by ID."""
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM signals WHERE id = ?',
                (signal_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {'error': 'Signal not found'}
            
            columns = [desc[0] for desc in cursor.description]
            signal = dict(zip(columns, row))
            signal['entry_values'] = json.loads(signal['entry_values_json'])
            signal['exit_criteria'] = json.loads(signal['exit_criteria_json'] or '[]')
            signal['metadata'] = json.loads(signal['metadata_json'] or '{}')
            signal['historical'] = bool(signal['historical'])
            
            return {'success': True, 'signal': signal}
    except Exception as e:
        return {'error': str(e)}

def update_signal(self, signal_id: str, updates: dict) -> dict:
    """Update signal (e.g., add/edit exit criteria).
    
    Args:
        updates: {
            'exit_criteria': [str] (optional),
            'metadata': dict (optional)
        }
    """
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            # Check if exists
            cursor = conn.execute('SELECT id FROM signals WHERE id = ?', (signal_id,))
            if not cursor.fetchone():
                return {'error': 'Signal not found'}
            
            set_clauses = []
            params = []
            
            if 'exit_criteria' in updates:
                set_clauses.append('exit_criteria_json = ?')
                params.append(json.dumps(updates['exit_criteria']))
            if 'metadata' in updates:
                set_clauses.append('metadata_json = ?')
                params.append(json.dumps(updates['metadata']))
            
            if not set_clauses:
                return {'error': 'No valid fields to update'}
            
            params.append(signal_id)
            query = f"UPDATE signals SET {', '.join(set_clauses)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()
            
            return {'success': True}
    except Exception as e:
        return {'error': str(e)}

def close_signal(self, signal_id: str, reason: str, closed_by_signal_id: str = None) -> dict:
    """Close a signal manually or via monitoring engine.
    
    Args:
        signal_id: Signal to close
        reason: 'manual' | 'exit_condition' | 'reversal'
        closed_by_signal_id: Optional reversal signal ID
    """
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            # Check if exists and is open
            cursor = conn.execute(
                'SELECT status FROM signals WHERE id = ?',
                (signal_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {'error': 'Signal not found'}
            if row[0] != 'open':
                return {'error': f'Signal is already {row[0]}'}
            
            now = int(time.time())
            
            conn.execute('''
                UPDATE signals 
                SET status = ?, closed_at = ?, close_reason = ?, closed_by_signal_id = ?
                WHERE id = ?
            ''', ('closed', now, reason, closed_by_signal_id, signal_id))
            conn.commit()
            
            return {'success': True, 'closed_at': now}
    except Exception as e:
        return {'error': str(e)}

def delete_signal(self, signal_id: str) -> dict:
    """Delete signal record."""
    try:
        with sqlite3.connect(self.user_db_path) as conn:
            cursor = conn.execute(
                'DELETE FROM signals WHERE id = ?',
                (signal_id,)
            )
            
            if cursor.rowcount == 0:
                return {'error': 'Signal not found'}
            
            conn.commit()
            return {'success': True, 'deleted': signal_id}
    except Exception as e:
        return {'error': str(e)}
```

### 1.5 IPC Endpoints

**Location**: `electron/main.ts` → Add IPC handlers

```typescript
// Signal Strategy endpoints
ipcMain.handle('create-signal-strategy', async (event, data) => {
  return await callPython('create_signal_strategy', data);
});

ipcMain.handle('get-signal-strategies', async (event, filters) => {
  return await callPython('get_signal_strategies', filters || {});
});

ipcMain.handle('get-signal-strategy', async (event, strategyId) => {
  return await callPython('get_signal_strategy', { strategy_id: strategyId });
});

ipcMain.handle('update-signal-strategy', async (event, strategyId, updates) => {
  return await callPython('update_signal_strategy', { strategy_id: strategyId, updates });
});

ipcMain.handle('delete-signal-strategy', async (event, strategyId) => {
  return await callPython('delete_signal_strategy', { strategy_id: strategyId });
});

// Signal endpoints
ipcMain.handle('create-signal', async (event, data) => {
  return await callPython('create_signal', data);
});

ipcMain.handle('get-signals', async (event, filters) => {
  return await callPython('get_signals', { filters: filters || {} });
});

ipcMain.handle('get-signal', async (event, signalId) => {
  return await callPython('get_signal', { signal_id: signalId });
});

ipcMain.handle('update-signal', async (event, signalId, updates) => {
  return await callPython('update_signal', { signal_id: signalId, updates });
});

ipcMain.handle('close-signal', async (event, signalId, reason, closedBySignalId) => {
  return await callPython('close_signal', { 
    signal_id: signalId, 
    reason, 
    closed_by_signal_id: closedBySignalId 
  });
});

ipcMain.handle('delete-signal', async (event, signalId) => {
  return await callPython('delete_signal', { signal_id: signalId });
});

// Dataset validation helpers
ipcMain.handle('validate-dataset-exists', async (event, datasetName) => {
  return await callPython('validate_dataset_exists', { dataset_name: datasetName });
});

ipcMain.handle('get-dataset-symbols', async (event, datasetName) => {
  return await callPython('get_dataset_symbols', { dataset_name: datasetName });
});
```

**Note**: Method names changed from `create_strategy` → `create_signal_strategy` to avoid confusion with existing backtest strategy methods.

---

## Phase 2: Expression Engine & Validation

### 2.1 Expression Parser/Evaluator

**Challenge**: The scanner already has expression logic in `scannerBuilderModel.ts` and Python backend. Need to:
1. Standardize expression format between frontend and backend
2. Add validation for expression syntax
3. Support composition with AND/OR/parentheses

**Location**: `backend/main.py` → New class `ExpressionEngine`

```python
class ExpressionEngine:
    """Parse, validate, and evaluate trading signal expressions."""
    
    def parse_expression(self, expr: str) -> dict:
        """Parse expression string into AST.
        
        Examples:
            'RSI(14) > 70'
            'SMA(close, 20) crosses_above SMA(close, 50)'
            '(RSI(14) < 30) and (close > SMA(close, 50))'
        
        Returns:
            {'valid': bool, 'ast': dict, 'error': str (if invalid)}
        """
        pass
    
    def validate_expression(self, expr: str, dataset_name: str, symbol: str) -> dict:
        """Validate that all required indicators/data exist for evaluation."""
        pass
    
    def evaluate_expression(self, expr: str, data: pd.DataFrame, timestamp: str) -> bool:
        """Evaluate expression at specific timestamp with data."""
        pass
    
    def evaluate_exit_criteria(self, criteria_list: list[str], data: pd.DataFrame, 
                              timestamp: str, logic: str = 'any') -> dict:
        """Evaluate multiple exit expressions (OR/AND logic).
        
        Returns:
            {'exit': bool, 'triggered_by': str (expression that triggered)}
        """
        pass
```

### 2.2 Frontend Expression Builder

**Location**: New component `src/components/ExpressionBuilder.tsx`

Reusable component for building entry/exit expressions. Can leverage existing `ScannerBuilder` logic but focused on single expression construction.

```typescript
interface ExpressionBuilderProps {
  value: string;
  onChange: (expression: string) => void;
  datasetName?: string;
  symbol?: string;
  onValidate?: (valid: boolean, error?: string) => void;
}

export const ExpressionBuilder: React.FC<ExpressionBuilderProps> = ({ ... }) => {
  // UI for building expressions with autocomplete, validation
  // Similar to scanner builder but simplified
};
```

---

## Phase 3: Frontend UI Components

### 3.0 TypeScript Type Definitions

**Location**: New file `src/types/signals.ts`

```typescript
// Signal Strategy types
export interface SignalStrategy {
  id: string;                          // UUID string
  name: string;
  description: string;
  conditions: {
    entry: string[];                   // Array of expression strings
    exit?: string[];                   // Optional exit expressions
  };
  default_direction: 'long' | 'short' | 'auto';
  scope: 'user' | 'global';
  created_by: string;
  created_at: number;                  // Unix timestamp
  updated_at: number;
  version: number;
  metadata: {
    reversal_mode?: 'no-auto-reversal' | 'auto-reversal-to-opposite' | 'auto-reversal-with-confirmation';
    exit_logic?: 'any' | 'all';        // For multiple exit conditions
    [key: string]: any;
  };
}

// Signal types
export interface Signal {
  id: string;                          // UUID string
  strategy_id: string;
  dataset_name: string;
  symbol: string;
  timestamp: string;                   // ISO8601
  direction: 'long' | 'short';
  entry_values: Record<string, number>; // Indicator snapshots
  exit_criteria: string[];             // Exit expressions
  status: 'open' | 'closed' | 'cancelled';
  created_by: string;
  created_at: number;
  closed_at?: number;
  closed_by_signal_id?: string;
  close_reason?: 'manual' | 'exit_condition' | 'reversal';
  historical: boolean;
  metadata: {
    tags?: string[];
    notes?: string;
    pnl?: number;
    [key: string]: any;
  };
}

// API request/response types
export interface CreateSignalStrategyRequest {
  name: string;
  description?: string;
  conditions: {
    entry: string[];
    exit?: string[];
  };
  default_direction: 'long' | 'short' | 'auto';
  scope?: 'user' | 'global';
  created_by?: string;
  metadata?: Record<string, any>;
}

export interface CreateSignalRequest {
  strategy_id: string;
  dataset_name: string;
  symbol: string;
  timestamp: string;
  direction: 'long' | 'short';
  entry_values: Record<string, number>;
  exit_criteria?: string[];
  created_by?: string;
  historical?: boolean;
  metadata?: Record<string, any>;
}

export interface SignalFilters {
  dataset_name?: string;
  symbol?: string;
  strategy_id?: string;
  status?: 'open' | 'closed' | 'cancelled';
  created_by?: string;
  historical?: boolean;
  start_date?: number;
  end_date?: number;
  limit?: number;
  offset?: number;
}

// Electron API extensions
declare global {
  interface Window {
    electronAPI: {
      // ... existing methods ...
      
      // Signal strategies
      invoke(channel: 'create-signal-strategy', data: CreateSignalStrategyRequest): Promise<{ success: boolean; strategy_id?: string; error?: string }>;
      invoke(channel: 'get-signal-strategies', filters?: { created_by?: string; scope?: string }): Promise<{ success: boolean; strategies?: SignalStrategy[]; error?: string }>;
      invoke(channel: 'get-signal-strategy', strategyId: string): Promise<{ success: boolean; strategy?: SignalStrategy; error?: string }>;
      invoke(channel: 'update-signal-strategy', strategyId: string, updates: Partial<SignalStrategy>): Promise<{ success: boolean; version?: number; error?: string }>;
      invoke(channel: 'delete-signal-strategy', strategyId: string): Promise<{ success: boolean; error?: string }>;
      
      // Signals
      invoke(channel: 'create-signal', data: CreateSignalRequest): Promise<{ success: boolean; signal_id?: string; error?: string }>;
      invoke(channel: 'get-signals', filters?: SignalFilters): Promise<{ success: boolean; signals?: Signal[]; count?: number; total?: number; error?: string }>;
      invoke(channel: 'get-signal', signalId: string): Promise<{ success: boolean; signal?: Signal; error?: string }>;
      invoke(channel: 'update-signal', signalId: string, updates: Partial<Signal>): Promise<{ success: boolean; error?: string }>;
      invoke(channel: 'close-signal', signalId: string, reason: string, closedBySignalId?: string): Promise<{ success: boolean; closed_at?: number; error?: string }>;
      invoke(channel: 'delete-signal', signalId: string): Promise<{ success: boolean; error?: string }>;
      
      // Helpers
      invoke(channel: 'validate-dataset-exists', datasetName: string): Promise<boolean>;
      invoke(channel: 'get-dataset-symbols', datasetName: string): Promise<string[]>;
    };
  }
}
```

### 3.1 Save Signal Modal

**Location**: New component `src/components/SaveSignalModal.tsx`

Triggered from Scanner results list with "Save as Signal" button.

```typescript
interface SaveSignalModalProps {
  scannerResult: {
    symbol: string;
    timestamp: string;
    indicatorValues: Record<string, number>;
    // ... other scanner output
  };
  scannerSpec: any;  // Current scanner configuration
  datasetName: string;
  onClose: () => void;
  onSave: (signal: SignalData) => Promise<void>;
}

export const SaveSignalModal: React.FC<SaveSignalModalProps> = ({ ... }) => {
  // Form fields:
  // - Strategy Name (text input, required)
  // - Strategy Description (textarea, optional)
  // - Direction (radio: long/short/auto-detect)
  // - Entry Expression (pre-filled from scanner, editable)
  // - Include Exit Criteria (checkbox)
  //   - Exit Expression Builder (shown if checked)
  //   - Exit Logic (radio: any/all for multiple conditions)
  // - Reversal Behavior (dropdown):
  //   - no-auto-reversal (default)
  //   - auto-reversal-to-opposite
  //   - auto-reversal-with-confirmation
  // - Save / Cancel buttons
};
```

### 3.2 Signals List View

**Location**: New component `src/components/SignalsList.tsx`

Full-page view accessible from main navigation.

```typescript
export const SignalsList: React.FC = () => {
  // Filters:
  // - Dataset dropdown
  // - Symbol search/filter
  // - Strategy dropdown
  // - Status: open/closed/cancelled
  // - Date range picker
  
  // Table columns:
  // - Signal ID (truncated, click to expand)
  // - Strategy Name
  // - Symbol
  // - Direction (long/short icon)
  // - Entry Timestamp
  // - Status badge
  // - Actions: View, Edit, Close, Delete
  
  // Pagination + sorting
};
```

### 3.3 Signal Detail View

**Location**: New component `src/components/SignalDetail.tsx`

Modal or side panel for viewing/editing individual signal.

```typescript
interface SignalDetailProps {
  signalId: string;
  onClose: () => void;
  onUpdate: () => void;
}

export const SignalDetail: React.FC<SignalDetailProps> = ({ ... }) => {
  // Display:
  // - Strategy info (name, description, entry conditions)
  // - Symbol, timestamp, direction
  // - Entry values snapshot (table of indicator values)
  // - Exit criteria (editable if status=open)
  // - Status with timeline
  // - Close button (if open)
  // - Chart visualization (optional: show entry point on candlestick)
};
```

### 3.4 Strategy Management View

**Location**: New component `src/components/StrategyManager.tsx`

Manage reusable strategies across datasets.

```typescript
export const StrategyManager: React.FC = () => {
  // List view of saved strategies
  // - Name, Description, Scope (user/global)
  // - Entry/Exit conditions preview
  // - Usage count (# signals using this strategy)
  // - Actions: Edit, Duplicate, Delete
  
  // Create/Edit Strategy form
  // - Reuses ExpressionBuilder for conditions
};
```

### 3.5 Integration with Scanner

**Location**: Modify `src/components/Scanner.tsx`

Add "Save as Signal" button to each row in scanner results table.

```typescript
// In Scanner.tsx results rendering:
{results.map(result => (
  <tr key={result.symbol}>
    <td>{result.symbol}</td>
    {/* ... other columns ... */}
    <td>
      <button onClick={() => openSaveSignalModal(result)}>
        💾 Save as Signal
      </button>
    </td>
  </tr>
))}
```

---

## Phase 4: Monitoring Engine

### 4.1 Signal Monitoring Service

**Location**: `backend/main.py` → New class `SignalMonitor`

Background service that evaluates exit conditions for open signals.

```python
class SignalMonitor:
    """Monitor open signals and trigger exits when conditions are met."""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.running = False
        self._lock = Lock()
    
    def start_monitoring(self):
        """Start background monitoring loop."""
        pass
    
    def stop_monitoring(self):
        """Stop monitoring gracefully."""
        pass
    
    def check_signal(self, signal_id: str) -> dict:
        """Check single signal's exit conditions against latest data.
        
        Returns:
            {'should_exit': bool, 'triggered_by': str, 'reversal': bool}
        """
        pass
    
    def check_all_signals(self):
        """Batch check all open signals (scheduled task)."""
        pass
    
    def handle_exit(self, signal_id: str, reason: str, create_reversal: bool = False):
        """Close signal and optionally create reversal signal."""
        pass
```

### 4.2 Real-time Monitoring Mode

**Option 1**: Polling (simpler)
- Schedule periodic checks (e.g., every 5 minutes) for open signals
- Evaluate exit conditions against latest available data
- Send IPC events to frontend when signals close

**Option 2**: Event-driven (advanced)
- Listen for new data imports
- Immediately evaluate affected signals
- More responsive but requires data import hooks

**Recommendation**: Start with Option 1 (polling), add Option 2 later if needed.

### 4.3 Frontend Monitoring UI

**Location**: Add to `SignalsList.tsx`

```typescript
// Real-time updates indicator
const useSignalMonitoring = () => {
  useEffect(() => {
    const handler = (event: any, payload: any) => {
      if (payload.type === 'signal-closed') {
        // Refresh signals list
        // Show notification toast
      }
    };
    
    const off = window.electronAPI.on('signal-update', handler);
    return () => off();
  }, []);
};
```

---

## Phase 5: Historical Backtesting

### 5.1 Historical Signal Generator

**Location**: `backend/main.py` → New method in `DatabaseService`

```python
def run_strategy_historical(self, strategy_id: str, dataset_name: str, 
                           symbol: str = None, start_date: str = None, 
                           end_date: str = None) -> dict:
    """Run strategy across full historical data for a dataset.
    
    Args:
        strategy_id: Strategy to backtest
        dataset_name: Dataset to run against
        symbol: Specific symbol or None for all symbols in dataset
        start_date/end_date: Optional time range (ISO8601)
    
    Returns:
        {
            'success': bool,
            'signals_generated': int,
            'signals': [signal_id, ...],
            'performance': {
                'total_entries': int,
                'total_exits': int,
                'avg_duration': float (hours),
                'win_rate': float (if P&L tracked)
            }
        }
    
    Process:
        1. Load full historical data for dataset/symbol
        2. Calculate all required indicators
        3. Evaluate entry conditions at each bar
        4. When entry triggers, create historical signal
        5. Continue monitoring for exit (if defined)
        6. Store all signals with historical=True flag
        7. Generate performance report
    """
    pass
```

### 5.2 Batch Processing & Progress Reporting

For large datasets:
- Process in chunks (e.g., 100 symbols at a time)
- Use ThreadPoolExecutor for parallel processing
- Send progress events via IPC
- Support pause/resume

```python
def run_strategy_historical_batch(self, strategy_id: str, dataset_name: str,
                                  progress_callback: callable = None) -> dict:
    """Historical backtest with progress reporting."""
    
    symbols = self.get_symbols_for_dataset(dataset_name)
    total = len(symbols)
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for symbol in symbols:
            future = executor.submit(
                self.run_strategy_historical,
                strategy_id, dataset_name, symbol
            )
            futures[future] = symbol
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if progress_callback:
                progress_callback({
                    'phase': 'running',
                    'completed': completed,
                    'total': total,
                    'symbol': futures[future]
                })
    
    return {'success': True, 'total_signals': ...}
```

### 5.3 Frontend Historical Backtest UI

**Location**: New component `src/components/HistoricalBacktest.tsx`

```typescript
export const HistoricalBacktest: React.FC = () => {
  // Form inputs:
  // - Strategy selector
  // - Dataset selector
  // - Symbol filter (all or specific list)
  // - Date range
  // - Run button
  
  // Progress display:
  // - Progress bar with symbol count
  // - Cancel button
  
  // Results view:
  // - Total signals generated
  // - Performance metrics table
  // - Export to CSV button
  // - View signals button (filter signals list)
};
```

---

## Phase 6: Advanced Features

### 6.1 Auto-Reversal Logic

**Implementation Notes**:
- Stored in `strategies.metadata_json`:
  ```json
  {
    "reversal_mode": "no-auto-reversal" | "auto-reversal-to-opposite" | "auto-reversal-with-confirmation",
    "reversal_condition": "opposite_entry" | "custom_expression"
  }
  ```
- When monitoring detects exit AND reversal_mode is enabled:
  1. Close current signal with `close_reason='reversal'`
  2. Create new signal with opposite direction
  3. Link via `closed_by_signal_id`

### 6.2 Signal Tagging & Notes

Extend `signals.metadata_json`:
```json
{
  "tags": ["momentum", "breakout"],
  "notes": "User comments about this signal",
  "custom_fields": { ... }
}
```

### 6.3 P&L Tracking Integration

If entry/exit prices are tracked, calculate:
- P&L per signal
- Win/loss rate
- Average gain/loss
- Display in signals list and detail views

### 6.4 Alerting System

**Future Enhancement**: Push notifications or webhooks when:
- New signal created
- Signal closed
- Exit condition approaching

---

## Phase 7: Testing Strategy

### 7.1 Unit Tests

**Location**: `tests/test_signals.py`

```python
def test_create_strategy():
    """Test strategy creation and validation."""
    pass

def test_create_signal():
    """Test signal creation from scanner result."""
    pass

def test_expression_validation():
    """Test expression parser with valid/invalid inputs."""
    pass

def test_exit_evaluation():
    """Test exit condition evaluation logic."""
    pass

def test_reversal_flow():
    """Test auto-reversal signal generation."""
    pass

def test_historical_backtest():
    """Test historical signal generation."""
    pass
```

### 7.2 Integration Tests

Test full workflows:
1. Scanner → Save Signal → View in list
2. Create strategy → Run historical backtest → Export results
3. Open signal → Edit exit criteria → Monitor → Auto-close

### 7.3 Manual Acceptance Criteria

✅ **Entry-only signals**:
- [ ] Save signal from scanner with no exit
- [ ] Verify status remains 'open'
- [ ] Manually close signal
- [ ] Verify status changes to 'closed'

✅ **Entry+exit signals**:
- [ ] Save signal with exit condition
- [ ] Monitoring engine evaluates condition
- [ ] Signal auto-closes when condition met
- [ ] Frontend shows closed status

✅ **Auto-reversal**:
- [ ] Enable auto-reversal on strategy
- [ ] Signal closes on exit
- [ ] Opposite signal created automatically
- [ ] Signals linked via `closed_by_signal_id`

✅ **Historical backtest**:
- [ ] Run strategy on full dataset
- [ ] Generates multiple historical signals
- [ ] Performance metrics calculated
- [ ] Export to CSV works

---

## Review Findings & Resolutions

### Original Review Issues

**Issue 1: Existing `strategies` table conflict**
- ❌ **Problem**: Plan defined new `strategies` table with UUID primary key, but existing schema uses INTEGER `id`
- ✅ **Resolution**: Renamed tables to `signal_strategies` and `signals` to preserve existing backtest infrastructure
- **Impact**: Zero breaking changes to existing features; signals system is fully additive

**Issue 2: Cross-database foreign key constraint**
- ❌ **Problem**: `signals.dataset_name` FK referenced `datasets` table in different database (market_data.db)
- ✅ **Resolution**: Removed FK constraint, using TEXT field with application-layer validation via `validate_dataset_exists()`
- **Trade-off**: Slightly weaker referential integrity, but enables proper database separation
- **Mitigation**: Validation in `create_signal()` ensures only valid datasets are referenced

**Issue 3: NULL uniqueness in UNIQUE constraint**
- ❌ **Problem**: `UNIQUE(name, created_by)` with nullable `created_by` allows duplicate names (SQLite treats NULLs as distinct)
- ✅ **Resolution**: Made `created_by` NOT NULL with default value `'default_user'`
- **Impact**: All strategies and signals must have an owner (supports future multi-user features)

### Open Questions Answered

**Q1: Migrate/replace existing strategies or create new tables?**

**A**: **Create new tables** (`signal_strategies`, `signals`) to preserve existing backtest features.

**Rationale**:
- Existing `strategies` table is tightly coupled to `backtest_results` and `trades`
- Renaming avoids breaking changes to ParameterOptimizer, BacktestEngine, etc.
- Signals are conceptually different from backtest configurations
- Allows independent evolution of both systems

**Migration Path** (if needed later):
```python
def migrate_backtest_strategies_to_signals():
    """Optional: Convert existing backtest strategies to signal strategies."""
    # Not required for MVP, but available if users want to reuse backtest configs
    pass
```

**Q2: Where should dataset metadata live to enforce FK?**

**A**: **Keep datasets in market_data.db**; use application-layer validation instead of FK.

**Rationale**:
- Datasets are market data (price_data, symbols) → belong in market DB
- Signals are user decisions/actions → belong in user DB
- SQLite doesn't support cross-database FKs
- Application validation is standard pattern for cross-DB references

**Validation Strategy**:
```python
# In create_signal():
if not self.validate_dataset_exists(dataset_name):
    return {'error': 'Dataset not found'}
```

**Alternative Considered**: Duplicate `datasets` metadata in user DB
- ❌ Rejected: Creates data synchronization issues
- ❌ Rejected: Violates single source of truth principle

**Q3: Schema strategy - migration vs. additive?**

**A**: **Fully additive** - no migrations required.

**Implementation Checklist**:
- ✅ New tables with distinct names (`signal_strategies`, `signals`)
- ✅ No modifications to existing tables
- ✅ No dependencies on existing schema changes
- ✅ Backward compatible with all existing features
- ✅ Forward compatible (future migrations can build on this)

---

## Implementation Timeline

### Sprint 1 (Week 1-2): Foundation ✅ Review-approved
- [ ] **Database schema** (signal_strategies, signals tables with corrected design)
- [ ] **Backend CRUD** (create_signal_strategy, create_signal, etc. - all methods renamed)
- [ ] **Dataset validation helpers** (validate_dataset_exists, get_dataset_symbols)
- [ ] **IPC endpoint setup** (create-signal-strategy, create-signal, etc.)
- [ ] **Basic expression parser/validator**
- [ ] **TypeScript type definitions** (src/types/signals.ts)

**Deliverables**:
- Working database schema in user_data.db
- All 12 signal strategy/signal CRUD methods functional
- Unit tests for CRUD operations
- IPC communication verified

**Success Criteria**:
- Can create signal_strategy via IPC
- Can create signal with dataset validation
- Queries return properly formatted JSON
- No breaking changes to existing features

### Sprint 2 (Week 3-4): Core UI
- [ ] SaveSignalModal component
- [ ] SignalsList component
- [ ] SignalDetail component
- [ ] Integration with Scanner (Save button)

### Sprint 3 (Week 5-6): Monitoring & Backtesting
- [ ] SignalMonitor service
- [ ] Real-time monitoring loop
- [ ] Historical backtest implementation
- [ ] HistoricalBacktest UI component

### Sprint 4 (Week 7-8): Polish & Advanced Features
- [ ] StrategyManager component
- [ ] Auto-reversal logic
- [ ] Performance metrics & analytics
- [ ] Testing & bug fixes

**Total Estimated Time**: 8 weeks

---

## Dependencies & Prerequisites

1. **Existing Features** (already implemented):
   - ✅ Scanner with builder UI
   - ✅ Dataset management
   - ✅ Symbol lists
   - ✅ SQLite database infrastructure
   - ✅ IPC communication layer

2. **New Dependencies**:
   - None required (use existing stack)

3. **Data Requirements**:
   - Historical price data in `market_data.db`
   - Indicator calculation already exists in scanner

---

## Risk Assessment & Mitigation

| Risk | Impact | Mitigation | Status |
|------|--------|-----------|--------|
| Schema conflicts with existing tables | **CRITICAL** | ✅ Use distinct table names (signal_strategies, signals) | **RESOLVED** |
| Cross-database FK enforcement | **HIGH** | ✅ Application-layer validation in create_signal() | **RESOLVED** |
| NULL uniqueness bugs | **MEDIUM** | ✅ NOT NULL constraint on created_by with default | **RESOLVED** |
| Expression parser complexity | High | Reuse existing scanner expression logic; start simple | Open |
| Performance with large datasets | Medium | Batching, pagination, indexes; use existing patterns | Open |
| Race conditions in monitoring | Medium | Use locks in SignalMonitor; transaction-safe updates | Open |
| UI complexity for multi-indicator | Medium | Phase implementation: single-indicator first | Open |
| Data inconsistency (stale dataset refs) | Low | Validation on create; background cleanup job (future) | Open |

### Database Safety Checklist

**Pre-deployment verification**:
- [ ] Test schema on fresh database (no existing data)
- [ ] Test schema with existing user_data.db (verify no table name conflicts)
- [ ] Verify `CREATE TABLE IF NOT EXISTS` logic (existing tables untouched)
- [ ] Test application-layer dataset validation (reject invalid dataset_name)
- [ ] Verify created_by default value prevents NULLs
- [ ] Test CASCADE DELETE (strategy deletion removes signals)
- [ ] Verify indexes are created correctly
- [ ] Test rollback behavior on constraint violations

**Existing feature protection**:
- [ ] Run full backtest suite (verify strategies table unchanged)
- [ ] Test ParameterOptimizer (verify no interference)
- [ ] Test Scanner (verify saved_scans table unchanged)
- [ ] Test symbol lists (verify no interference)
- [ ] Verify database file sizes (no unexpected growth)

**Validation tests**:
- [ ] Attempt to create signal with non-existent dataset (should fail)
- [ ] Attempt to create signal with non-existent strategy (should fail)
- [ ] Attempt to create signal with invalid symbol (should warn/fail)
- [ ] Attempt duplicate strategy name for same user (should fail)
- [ ] Attempt duplicate strategy name for different users (should succeed)

---

## Success Metrics

1. **Functionality**:
   - Users can save signals from scanner (100% of attempts succeed)
   - Historical backtest generates accurate signals
   - Monitoring engine closes signals within 5 min of condition trigger

2. **Performance**:
   - Signal creation < 500ms
   - Historical backtest: 10,000 bars/second
   - UI remains responsive during monitoring

3. **Adoption**:
   - 50%+ of scanner runs result in saved signals
   - Users create 5+ reusable strategies
   - Historical backtest used on 10+ datasets

---

## Future Enhancements (Post-MVP)

1. **Visual Timeline**: Show signal lifecycle on charts
2. **Signal Comparison**: Compare performance of multiple strategies side-by-side
3. **Machine Learning Integration**: Auto-suggest exit conditions based on historical performance
4. **Alert System**: Email/push notifications for signal events
5. **Portfolio Integration**: Link signals to portfolio positions
6. **Trade Journal**: Convert signals to journal entries with notes
7. **Strategy Marketplace**: Share strategies with community (if multi-user)

---

## References

- Original Specification: `docs/scanner_signal`
- Scanner Implementation: `src/components/Scanner.tsx`
- Backend Service: `backend/main.py`
- Database Schema: `DatabaseService.init_user_database()`

---

## Approval & Next Steps

**Document Status**: ✅ Ready for Review

**Review Required By**:
- [ ] Product Owner
- [ ] Lead Developer
- [ ] UX Designer (for UI mockups)

**Next Actions After Approval**:
1. Create feature branch: `feature/scanner-signals`
2. Set up Sprint 1 task board
3. Begin database schema implementation
4. Schedule daily standups for coordination

---

## Appendix A: Schema Comparison

### Existing Schema (Unchanged)

**user_data.db** - Backtest System:
```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    -- Integer ID
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    rules_json TEXT NOT NULL,
    parameters_json TEXT,
    created_at INTEGER,
    updated_at INTEGER
);

CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,           -- References strategies.id
    symbol TEXT NOT NULL,
    -- ... backtest metrics ...
    FOREIGN KEY (strategy_id) REFERENCES strategies (id)
);
```

**market_data.db** - Market Data:
```sql
CREATE TABLE datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    symbols_json TEXT,
    -- ... metadata ...
);

CREATE TABLE symbol_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    symbols_json TEXT NOT NULL,
    FOREIGN KEY (dataset_name) REFERENCES datasets (name)
);
```

### New Schema (Additive)

**user_data.db** - Signals System:
```sql
CREATE TABLE signal_strategies (
    id TEXT PRIMARY KEY,                     -- UUID string (different from strategies.id)
    name TEXT NOT NULL,
    conditions_json TEXT NOT NULL,           -- Different from rules_json
    -- ... signal-specific fields ...
    UNIQUE(name, created_by)                 -- Multi-column unique
);

CREATE TABLE signals (
    id TEXT PRIMARY KEY,                     -- UUID string
    strategy_id TEXT NOT NULL,               -- References signal_strategies.id
    dataset_name TEXT NOT NULL,              -- TEXT reference (no FK)
    -- ... signal tracking fields ...
    FOREIGN KEY (strategy_id) REFERENCES signal_strategies(id)
);
```

**Key Differences**:

| Aspect | Backtest System | Signals System |
|--------|----------------|----------------|
| **Table Prefix** | None (`strategies`) | `signal_` prefix |
| **Primary Key** | INTEGER AUTOINCREMENT | TEXT (UUID) |
| **Strategy Definition** | `rules_json` | `conditions_json` (entry/exit) |
| **Purpose** | Historical analysis | Real-time tracking |
| **Results Storage** | `backtest_results` table | `signals.metadata_json` |
| **Dataset Reference** | Inline in backtest params | Validated TEXT field |
| **Multi-user** | Single unique name | `UNIQUE(name, created_by)` |

**Coexistence**:
- ✅ No table name conflicts
- ✅ No column name conflicts
- ✅ No FK conflicts
- ✅ Independent evolution paths
- ✅ Can optionally bridge them (future feature)

---

## Appendix B: Example Data Flow

### Creating a Signal from Scanner Result

**1. User runs scanner**:
```typescript
// Scanner.tsx
const scanResult = {
  symbol: 'AAPL',
  timestamp: '2025-10-22T10:30:00Z',
  close: 175.50,
  RSI_14: 72.3,
  SMA_20: 170.25,
  // ... other indicators
};
```

**2. User clicks "Save as Signal"**:
```typescript
// SaveSignalModal.tsx
const handleSave = async () => {
  // First, create or select strategy
  const strategyResult = await window.electronAPI.invoke('create-signal-strategy', {
    name: 'RSI Overbought',
    description: 'Short when RSI > 70',
    conditions: {
      entry: ['RSI(14) > 70'],
      exit: ['RSI(14) < 50']
    },
    default_direction: 'short',
    metadata: {
      reversal_mode: 'auto-reversal-to-opposite'
    }
  });
  
  if (!strategyResult.success) {
    // Handle existing strategy or use selected one
  }
  
  // Then create signal
  const signalResult = await window.electronAPI.invoke('create-signal', {
    strategy_id: strategyResult.strategy_id,
    dataset_name: currentDataset,
    symbol: scanResult.symbol,
    timestamp: scanResult.timestamp,
    direction: 'short',
    entry_values: {
      close: scanResult.close,
      RSI_14: scanResult.RSI_14,
      SMA_20: scanResult.SMA_20
    },
    exit_criteria: ['RSI(14) < 50']
  });
  
  if (signalResult.success) {
    toast.success(`Signal created: ${signalResult.signal_id}`);
  }
};
```

**3. Backend processes**:
```python
# backend/main.py → create_signal()

# Validates:
✓ Strategy exists (signal_strategies table)
✓ Dataset exists (cross-DB check to market_data.db)
✓ Symbol exists in dataset (optional)
✓ Direction is valid

# Inserts:
INSERT INTO signals (
  id='uuid_abc123',
  strategy_id='uuid_def456',
  dataset_name='my_portfolio',
  symbol='AAPL',
  timestamp='2025-10-22T10:30:00Z',
  direction='short',
  entry_values_json='{"close": 175.50, "RSI_14": 72.3, ...}',
  exit_criteria_json='["RSI(14) < 50"]',
  status='open',
  created_at=1729593000,
  historical=0
)

# Returns:
{'success': True, 'signal_id': 'uuid_abc123'}
```

**4. Monitoring engine evaluates exit**:
```python
# SignalMonitor.check_signal('uuid_abc123')

# Loads latest data for AAPL
# Evaluates: RSI(14) < 50
# If true → calls close_signal('uuid_abc123', 'exit_condition')
# If reversal enabled → creates new long signal
```

---

## Appendix C: Migration Path (Future Optional)

If users want to convert existing backtest strategies to signal strategies:

```python
def migrate_backtest_strategy_to_signal_strategy(backtest_strategy_id: int) -> dict:
    """Convert a backtest strategy to a signal strategy.
    
    NOTE: This is optional and not required for MVP.
    Useful if users want to track live signals using backtest configs.
    """
    try:
        # 1. Load backtest strategy
        with sqlite3.connect(self.user_db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM strategies WHERE id = ?',
                (backtest_strategy_id,)
            )
            row = cursor.fetchone()
            if not row:
                return {'error': 'Backtest strategy not found'}
            
            # 2. Parse rules_json → conditions_json
            rules = json.loads(row[3])  # rules_json column
            
            # 3. Create signal_strategy
            signal_strategy = {
                'name': f"{row[1]}_signals",  # Append _signals to name
                'description': f"Migrated from backtest: {row[2]}",
                'conditions': {
                    'entry': rules.get('entry_rules', []),
                    'exit': rules.get('exit_rules', [])
                },
                'default_direction': 'auto',
                'scope': 'user',
                'metadata': {
                    'migrated_from_backtest_id': backtest_strategy_id
                }
            }
            
            return self.create_signal_strategy(signal_strategy)
            
    except Exception as e:
        return {'error': str(e)}
```

---

*Implementation plan updated: October 22, 2025*  
*Reviewed and revised based on schema conflict analysis*  
*Status: ✅ Ready for implementation*

