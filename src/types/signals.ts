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

// API Response types
export interface ApiResponse<T = any> {
  success: boolean;
  error?: string;
  requestId?: string;
  data?: T;
}

export interface SignalStrategyResponse extends ApiResponse {
  strategy_id?: string;
  strategy?: SignalStrategy;
  strategies?: SignalStrategy[];
  count?: number;
  version?: number;
  deleted?: string;
}

export interface SignalResponse extends ApiResponse {
  signal_id?: string;
  signal?: Signal;
  signals?: Signal[];
  count?: number;
  total?: number;
  closed_at?: number;
  deleted?: string;
}

export interface DatasetValidationResponse extends ApiResponse {
  exists?: boolean;
  symbols?: string[];
}

