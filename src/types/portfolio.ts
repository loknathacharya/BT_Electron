/**
 * TypeScript type definitions for Portfolio Backtest Enhancement
 * Phase 2: Frontend Enhancement
 */

// ============================================================================
// Position Sizing Types
// ============================================================================

export type PositionSizingMethod =
  | 'equal_weight'
  | 'fixed_amount'
  | 'percent_risk'
  | 'volatility_target'
  | 'atr_based'
  | 'kelly_criterion';

export interface PositionSizingConfig {
  method: PositionSizingMethod;
  riskPerTrade?: number;        // For percent_risk method (%)
  fixedAmount?: number;          // For fixed_amount method ($)
  volatilityTarget?: number;     // For volatility_target method (decimal)
  atrMultiplier?: number;        // For atr_based method
  kellyWinRate?: number;         // For kelly_criterion method (%)
  kellyAvgWin?: number;          // For kelly_criterion method (%)
  kellyAvgLoss?: number;         // For kelly_criterion method (%)
}

export const POSITION_SIZING_DESCRIPTIONS: Record<PositionSizingMethod, string> = {
  equal_weight: '2% of portfolio per position - Simple and diversified',
  fixed_amount: 'Same dollar amount per trade - Stable capital deployment',
  percent_risk: 'Risk fixed % based on stop-loss - Risk-conscious trading',
  volatility_target: 'Size by instrument volatility - Professional portfolios',
  atr_based: 'Size by Average True Range - Trend-following strategies',
  kelly_criterion: 'Optimal mathematical sizing - Experienced traders only'
};

// ============================================================================
// Signal Type
// ============================================================================

export type SignalType = 'long' | 'short';

export interface SignalTypeInfo {
  type: SignalType;
  label: string;
  icon: string;
  description: string;
  profitWhen: string;
  stopLossLogic: string;
}

export const SIGNAL_TYPE_INFO: Record<SignalType, SignalTypeInfo> = {
  long: {
    type: 'long',
    label: 'Long Signals',
    icon: '📈',
    description: 'Buy & Hold',
    profitWhen: 'Price increases',
    stopLossLogic: 'Exit when price falls below entry'
  },
  short: {
    type: 'short',
    label: 'Short Signals',
    icon: '📉',
    description: 'Sell & Cover',
    profitWhen: 'Price decreases',
    stopLossLogic: 'Exit when price rises above entry'
  }
};

// ============================================================================
// Risk Management
// ============================================================================

export interface RiskManagementConfig {
  allowLeverage: boolean;
  oneTradePerInstrument: boolean;
  stopLossPct: number | null;
  takeProfitPct: number | null;
  holdingPeriodDays: number | null;
  trailingStopPct?: number | null;
  maxDrawdownLimit?: number | null;
}

// ============================================================================
// Trade Analytics
// ============================================================================

export interface Trade {
  symbol: string;
  entryDate: string;
  exitDate: string;
  entryPrice: number;
  exitPrice: number;
  shares: number;
  direction: SignalType;
  pnl: number;
  pnlPct: number;
  exitReason: ExitReason;
  holdingPeriod: number;
  positionValue: number;
}

export type ExitReason = 'take_profit' | 'stop_loss' | 'time_exit' | 'manual';

export interface TradeAnalytics {
  totalReturn: number;
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  averageWin: number;
  averageLoss: number;
  maxDrawdown: number;
  sharpeRatio: number;
  maxConsecutiveWins: number;
  maxConsecutiveLosses: number;
  
  // Enhanced analytics
  exitReasons: Record<ExitReason, number>;
  holdingPeriods: number[];
  plDistribution: number[];
  plTimeline: Array<{
    date: string;
    pl: number;
    pnlPct: number;
    reason: ExitReason;
    symbol: string;
  }>;
}

// ============================================================================
// Monte Carlo Simulation
// ============================================================================

export interface MonteCarloConfig {
  nSimulations: number;
  nTrades: number;
}

export interface MonteCarloResults {
  simulations: number[];
  percentile5: number;
  percentile50: number;
  percentile95: number;
  mean: number;
  std: number;
  probabilityProfit: number;
  probabilityLoss10: number;
  error?: string;
}

// ============================================================================
// Leverage Analysis
// ============================================================================

export interface LeverageMetrics {
  averageLeverage: number;
  maxLeverage: number;
  leverageDistribution: Record<string, number>;
  highLeverageTrades: number;
  leverageRiskScore: number;
}

export interface LeverageAnalysis {
  metrics: LeverageMetrics;
  leverageTimeline: Array<{
    date: string;
    leverage: number;
  }>;
  leverageVsPerformance: Array<{
    leverage: number;
    returnPct: number;
  }>;
}

// ============================================================================
// Invested Capital
// ============================================================================

export interface InvestedCapitalPoint {
  date: string;
  investedValue: number;
  availableCash: number;
  totalValue: number;
  utilizationPct: number;
}

export interface InvestedCapitalAllocation {
  symbol: string;
  value: number;
  percentage: number;
}

// ============================================================================
// Portfolio Backtest Results
// ============================================================================

export interface PortfolioBacktestResults {
  trades: Trade[];
  equityCurve: Array<{
    date: string;
    value: number;
  }>;
  metrics: TradeAnalytics;
  analytics: TradeAnalytics;
  leverageMetrics?: LeverageMetrics;
  investedCapitalTimeline?: InvestedCapitalPoint[];
  configuration: {
    symbols: string[];
    initialCapital: number;
    positionSizing: PositionSizingConfig;
    signalType: SignalType;
    riskManagement: RiskManagementConfig;
  };
}

// ============================================================================
// Parameter Optimization (Phase 4 - Optional)
// ============================================================================

export interface ParameterRange {
  min: number;
  max: number;
  step: number;
}

export interface OptimizationConfig {
  parameters: {
    holdingPeriod?: ParameterRange;
    stopLoss?: ParameterRange;
    takeProfit?: ParameterRange;
    positionSizing?: PositionSizingMethod[];
  };
  metric: 'totalReturn' | 'sharpeRatio' | 'profitFactor';
  nParallel?: number;
}

export interface OptimizationResult {
  params: Record<string, any>;
  metrics: TradeAnalytics;
  rank: number;
}

// ============================================================================
// UI State
// ============================================================================

export interface PortfolioBacktestState {
  // Configuration
  positionSizing: PositionSizingConfig;
  signalType: SignalType;
  riskManagement: RiskManagementConfig;
  
  // Results
  results: PortfolioBacktestResults | null;
  
  // UI State
  isRunning: boolean;
  activeTab: ResultTab;
  showAdvancedOptions: boolean;
  
  // Monte Carlo
  monteCarloConfig: MonteCarloConfig;
  monteCarloResults: MonteCarloResults | null;
  runningMonteCarlo: boolean;
}

export type ResultTab = 
  | 'equity-curve'
  | 'trade-log'
  | 'trade-analytics'
  | 'monte-carlo'
  | 'leverage'
  | 'invested-capital'
  | 'optimization';

// ============================================================================
// Helper Functions
// ============================================================================

export function getPositionSizingDefaults(method: PositionSizingMethod): PositionSizingConfig {
  const defaults: PositionSizingConfig = {
    method,
    riskPerTrade: 2.0,
    fixedAmount: 10000,
    volatilityTarget: 0.15,
    atrMultiplier: 2.0,
    kellyWinRate: 55,
    kellyAvgWin: 8,
    kellyAvgLoss: 4
  };
  return defaults;
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

export function formatPercentage(value: number, decimals: number = 2): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatNumber(value: number, decimals: number = 2): string {
  return value.toFixed(decimals);
}
