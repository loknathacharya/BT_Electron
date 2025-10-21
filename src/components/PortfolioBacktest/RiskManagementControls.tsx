import React from 'react';
import { RiskManagementConfig } from '../../types/portfolio';
import './RiskManagementControls.css';

interface RiskManagementControlsProps {
  config: RiskManagementConfig;
  onChange: (config: RiskManagementConfig) => void;
}

export const RiskManagementControls: React.FC<RiskManagementControlsProps> = ({
  config,
  onChange
}) => {
  const handleChange = (field: keyof RiskManagementConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const handleNumericChange = (field: keyof RiskManagementConfig, value: string) => {
    const numValue = value === '' ? null : parseFloat(value);
    onChange({ ...config, [field]: numValue });
  };

  return (
    <div className="risk-management-controls">
      <h3 className="section-title">
        <span className="icon">⚖️</span>
        Risk Management
      </h3>

      <div className="controls-grid">
        {/* Stop Loss */}
        <div className="control-group">
          <label className="control-label">
            <input
              type="checkbox"
              checked={config.stopLossPct !== null}
              onChange={(e) => handleNumericChange('stopLossPct', e.target.checked ? '5' : '')}
            />
            <span>Stop Loss (%)</span>
          </label>
          {config.stopLossPct !== null && (
            <input
              type="number"
              min="0.5"
              max="50"
              step="0.5"
              value={config.stopLossPct}
              onChange={(e) => handleNumericChange('stopLossPct', e.target.value)}
              className="numeric-input"
              placeholder="5.0"
            />
          )}
          <p className="control-hint">Exit when price moves against position by this %</p>
        </div>

        {/* Take Profit */}
        <div className="control-group">
          <label className="control-label">
            <input
              type="checkbox"
              checked={config.takeProfitPct !== null}
              onChange={(e) => handleNumericChange('takeProfitPct', e.target.checked ? '10' : '')}
            />
            <span>Take Profit (%)</span>
          </label>
          {config.takeProfitPct !== null && (
            <input
              type="number"
              min="1"
              max="200"
              step="1"
              value={config.takeProfitPct}
              onChange={(e) => handleNumericChange('takeProfitPct', e.target.value)}
              className="numeric-input"
              placeholder="10.0"
            />
          )}
          <p className="control-hint">Exit when profit reaches this %</p>
        </div>

        {/* Holding Period */}
        <div className="control-group">
          <label className="control-label">
            <input
              type="checkbox"
              checked={config.holdingPeriodDays !== null}
              onChange={(e) => handleNumericChange('holdingPeriodDays', e.target.checked ? '30' : '')}
            />
            <span>Max Holding Period (days)</span>
          </label>
          {config.holdingPeriodDays !== null && (
            <input
              type="number"
              min="1"
              max="365"
              step="1"
              value={config.holdingPeriodDays}
              onChange={(e) => handleNumericChange('holdingPeriodDays', e.target.value)}
              className="numeric-input"
              placeholder="30"
            />
          )}
          <p className="control-hint">Exit after this many days regardless of P&L</p>
        </div>

        {/* Leverage Control */}
        <div className="control-group full-width">
          <label className="control-label checkbox-label">
            <input
              type="checkbox"
              checked={config.allowLeverage}
              onChange={(e) => handleChange('allowLeverage', e.target.checked)}
            />
            <span>Allow Leverage</span>
          </label>
          {!config.allowLeverage ? (
            <p className="control-hint success">
              ✓ Total position value cannot exceed portfolio value
            </p>
          ) : (
            <p className="control-hint warning">
              ⚠️ Positions can exceed portfolio value - use with caution
            </p>
          )}
        </div>

        {/* One Trade Per Instrument */}
        <div className="control-group full-width">
          <label className="control-label checkbox-label">
            <input
              type="checkbox"
              checked={config.oneTradePerInstrument}
              onChange={(e) => handleChange('oneTradePerInstrument', e.target.checked)}
            />
            <span>One Trade Per Instrument</span>
          </label>
          <p className="control-hint">
            Prevents multiple concurrent positions in the same symbol
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="risk-summary">
        <h4>Active Risk Controls</h4>
        <ul>
          {config.stopLossPct && (
            <li>Stop Loss: {config.stopLossPct}%</li>
          )}
          {config.takeProfitPct && (
            <li>Take Profit: {config.takeProfitPct}%</li>
          )}
          {config.holdingPeriodDays && (
            <li>Max Holding: {config.holdingPeriodDays} days</li>
          )}
          {config.allowLeverage && (
            <li className="warning-item">Leverage: Allowed</li>
          )}
          {config.oneTradePerInstrument && (
            <li>One Trade Per Instrument: Yes</li>
          )}
          {!config.stopLossPct && !config.takeProfitPct && !config.holdingPeriodDays && (
            <li className="info-item">No automatic exits configured</li>
          )}
        </ul>
      </div>
    </div>
  );
};
