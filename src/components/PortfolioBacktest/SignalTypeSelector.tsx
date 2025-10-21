import React from 'react';
import { SignalType, SIGNAL_TYPE_INFO } from '../../types/portfolio';
import './SignalTypeSelector.css';

interface SignalTypeSelectorProps {
  signalType: SignalType;
  onChange: (signalType: SignalType) => void;
}

export const SignalTypeSelector: React.FC<SignalTypeSelectorProps> = ({
  signalType,
  onChange
}) => {
  const longInfo = SIGNAL_TYPE_INFO.long;
  const shortInfo = SIGNAL_TYPE_INFO.short;

  return (
    <div className="signal-type-selector">
      <h3 className="section-title">
        <span className="icon">📊</span>
        Signal Type
      </h3>

      <div className="signal-type-buttons">
        <button
          className={`signal-type-button long ${signalType === 'long' ? 'active' : ''}`}
          onClick={() => onChange('long')}
          type="button"
        >
          <div className="button-header">
            <span className="button-icon">{longInfo.icon}</span>
            <span className="button-label">{longInfo.label}</span>
          </div>
          <div className="button-description">{longInfo.description}</div>
          <div className="button-details">
            <div className="detail-item">
              <span className="detail-label">Profit when:</span>
              <span className="detail-value">{longInfo.profitWhen}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Stop-loss:</span>
              <span className="detail-value">{longInfo.stopLossLogic}</span>
            </div>
          </div>
        </button>

        <button
          className={`signal-type-button short ${signalType === 'short' ? 'active' : ''}`}
          onClick={() => onChange('short')}
          type="button"
        >
          <div className="button-header">
            <span className="button-icon">{shortInfo.icon}</span>
            <span className="button-label">{shortInfo.label}</span>
          </div>
          <div className="button-description">{shortInfo.description}</div>
          <div className="button-details">
            <div className="detail-item">
              <span className="detail-label">Profit when:</span>
              <span className="detail-value">{shortInfo.profitWhen}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Stop-loss:</span>
              <span className="detail-value">{shortInfo.stopLossLogic}</span>
            </div>
          </div>
        </button>
      </div>

      <div className="signal-type-info">
        <p className="info-text">
          ℹ️ Signal type determines how P&L is calculated and when stop-loss/take-profit triggers occur.
          Choose the type that matches your scanner's signal generation logic.
        </p>
      </div>
    </div>
  );
};
