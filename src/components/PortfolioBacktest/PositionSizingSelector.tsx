import React from 'react';
import {
  PositionSizingConfig,
  PositionSizingMethod,
  POSITION_SIZING_DESCRIPTIONS,
  getPositionSizingDefaults
} from '../../types/portfolio';
import './PositionSizingSelector.css';

interface PositionSizingSelectorProps {
  config: PositionSizingConfig;
  onChange: (config: PositionSizingConfig) => void;
  showAdvanced?: boolean;
}

export const PositionSizingSelector: React.FC<PositionSizingSelectorProps> = ({
  config,
  onChange,
  showAdvanced = false
}) => {
  const handleMethodChange = (method: PositionSizingMethod) => {
    const defaults = getPositionSizingDefaults(method);
    onChange({ ...defaults, method });
  };

  const handleParameterChange = (param: keyof PositionSizingConfig, value: number) => {
    onChange({ ...config, [param]: value });
  };

  const renderMethodSpecificParams = () => {
    switch (config.method) {
      case 'fixed_amount':
        return (
          <div className="method-params">
            <label>
              <span className="param-label">Fixed Amount ($)</span>
              <input
                type="number"
                min="100"
                max="100000"
                step="100"
                value={config.fixedAmount || 10000}
                onChange={(e) => handleParameterChange('fixedAmount', parseFloat(e.target.value))}
              />
              <span className="param-hint">Dollar amount per trade</span>
            </label>
          </div>
        );

      case 'percent_risk':
        return (
          <div className="method-params">
            <label>
              <span className="param-label">Risk Per Trade (%)</span>
              <input
                type="number"
                min="0.1"
                max="10"
                step="0.1"
                value={config.riskPerTrade || 2.0}
                onChange={(e) => handleParameterChange('riskPerTrade', parseFloat(e.target.value))}
              />
              <span className="param-hint">Percentage of portfolio to risk</span>
            </label>
            <p className="info-message">
              ℹ️ Requires stop-loss to be set in Risk Management
            </p>
          </div>
        );

      case 'volatility_target':
        return (
          <div className="method-params">
            <label>
              <span className="param-label">Volatility Target</span>
              <input
                type="number"
                min="0.05"
                max="0.50"
                step="0.05"
                value={config.volatilityTarget || 0.15}
                onChange={(e) => handleParameterChange('volatilityTarget', parseFloat(e.target.value))}
              />
              <span className="param-hint">Target portfolio volatility (0.15 = 15%)</span>
            </label>
            <p className="info-message">
              ℹ️ Inverse volatility sizing - lower volatility = larger position
            </p>
          </div>
        );

      case 'atr_based':
        return (
          <div className="method-params">
            <label>
              <span className="param-label">ATR Multiplier</span>
              <input
                type="number"
                min="0.5"
                max="5.0"
                step="0.5"
                value={config.atrMultiplier || 2.0}
                onChange={(e) => handleParameterChange('atrMultiplier', parseFloat(e.target.value))}
              />
              <span className="param-hint">Multiplier for Average True Range</span>
            </label>
            <p className="info-message">
              ℹ️ Popular for trend-following strategies (2-3x ATR typical)
            </p>
          </div>
        );

      case 'kelly_criterion':
        return (
          <div className="method-params kelly-params">
            <label>
              <span className="param-label">Expected Win Rate (%)</span>
              <input
                type="number"
                min="30"
                max="90"
                step="1"
                value={config.kellyWinRate || 55}
                onChange={(e) => handleParameterChange('kellyWinRate', parseFloat(e.target.value))}
              />
              <span className="param-hint">Historical win percentage</span>
            </label>

            <label>
              <span className="param-label">Average Win (%)</span>
              <input
                type="number"
                min="1"
                max="50"
                step="0.5"
                value={config.kellyAvgWin || 8}
                onChange={(e) => handleParameterChange('kellyAvgWin', parseFloat(e.target.value))}
              />
              <span className="param-hint">Average winning trade %</span>
            </label>

            <label>
              <span className="param-label">Average Loss (%)</span>
              <input
                type="number"
                min="1"
                max="50"
                step="0.5"
                value={config.kellyAvgLoss || 4}
                onChange={(e) => handleParameterChange('kellyAvgLoss', parseFloat(e.target.value))}
              />
              <span className="param-hint">Average losing trade %</span>
            </label>

            <div className="kelly-warning">
              <span className="warning-icon">⚠️</span>
              <p>
                <strong>Kelly Criterion is aggressive!</strong><br />
                System uses fractional Kelly (25%) for safer sizing.
                Capped at 20% maximum position size.
              </p>
            </div>
          </div>
        );

      case 'equal_weight':
      default:
        return (
          <div className="method-params">
            <p className="info-message">
              ℹ️ Allocates exactly 2% of current portfolio value to each trade.
              Simple, ensures diversification, and requires no additional parameters.
            </p>
          </div>
        );
    }
  };

  return (
    <div className="position-sizing-selector">
      <h3 className="section-title">
        <span className="icon">💰</span>
        Position Sizing Method
      </h3>

      <div className="method-selector">
        <select
          value={config.method}
          onChange={(e) => handleMethodChange(e.target.value as PositionSizingMethod)}
          className="method-dropdown"
        >
          <option value="equal_weight">Equal Weight (2% per position)</option>
          <option value="fixed_amount">Fixed Dollar Amount</option>
          <option value="percent_risk">Percent Risk (Risk-based)</option>
          <option value="volatility_target">Volatility Targeting</option>
          <option value="atr_based">ATR-based Sizing</option>
          <option value="kelly_criterion">Kelly Criterion</option>
        </select>

        <p className="method-description">
          {POSITION_SIZING_DESCRIPTIONS[config.method]}
        </p>
      </div>

      {renderMethodSpecificParams()}

      {showAdvanced && (
        <div className="advanced-options">
          <h4>Advanced Options</h4>
          <p className="coming-soon">Additional position sizing constraints coming soon...</p>
        </div>
      )}
    </div>
  );
};
