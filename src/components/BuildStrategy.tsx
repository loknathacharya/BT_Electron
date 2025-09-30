import React, { useState } from 'react';

const BuildStrategy: React.FC = () => {
  const [strategyName, setStrategyName] = useState('');
  const [selectedIndicator, setSelectedIndicator] = useState('');

  const indicators = [
    'Simple Moving Average (SMA)',
    'Exponential Moving Average (EMA)',
    'Relative Strength Index (RSI)',
    'Moving Average Convergence Divergence (MACD)',
    'Bollinger Bands',
    'Stochastic Oscillator',
  ];

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Build Strategy</h2>
        <p>
          Create trading strategies using technical indicators and conditions.
          Build entry and exit rules using our visual strategy builder.
        </p>
      </div>

      <div className="strategy-builder">
        <div className="strategy-form">
          <div className="form-group">
            <label htmlFor="strategy-name">Strategy Name:</label>
            <input
              type="text"
              id="strategy-name"
              value={strategyName}
              onChange={(e) => setStrategyName(e.target.value)}
              placeholder="e.g., My Moving Average Strategy"
            />
          </div>

          <div className="strategy-sections">
            <div className="strategy-section">
              <h3>Entry Conditions</h3>
              <p className="section-description">
                Define when to enter a position (buy or sell)
              </p>

              <div className="conditions-builder">
                <div className="condition-group">
                  <select className="condition-type">
                    <option value="">Select condition type...</option>
                    <option value="indicator">Technical Indicator</option>
                    <option value="price">Price Action</option>
                    <option value="time">Time-based</option>
                  </select>
                </div>

                <div className="condition-group">
                  <select
                    value={selectedIndicator}
                    onChange={(e) => setSelectedIndicator(e.target.value)}
                  >
                    <option value="">Select indicator...</option>
                    {indicators.map((indicator) => (
                      <option key={indicator} value={indicator}>
                        {indicator}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedIndicator && (
                  <div className="condition-params">
                    <div className="param-group">
                      <label>Period:</label>
                      <input type="number" placeholder="14" min="1" />
                    </div>
                    <div className="param-group">
                      <label>Comparison:</label>
                      <select>
                        <option value="greater">Greater than</option>
                        <option value="less">Less than</option>
                        <option value="crosses_above">Crosses above</option>
                        <option value="crosses_below">Crosses below</option>
                      </select>
                    </div>
                  </div>
                )}

                <button className="btn">Add Condition</button>
              </div>
            </div>

            <div className="strategy-section">
              <h3>Exit Conditions</h3>
              <p className="section-description">
                Define when to exit a position
              </p>

              <div className="exit-conditions">
                <div className="exit-condition">
                  <input type="checkbox" id="stop-loss" />
                  <label htmlFor="stop-loss">Stop Loss</label>
                  <input
                    type="number"
                    placeholder="2.0"
                    step="0.1"
                    min="0"
                  />
                  <span>%</span>
                </div>

                <div className="exit-condition">
                  <input type="checkbox" id="take-profit" />
                  <label htmlFor="take-profit">Take Profit</label>
                  <input
                    type="number"
                    placeholder="4.0"
                    step="0.1"
                    min="0"
                  />
                  <span>%</span>
                </div>

                <div className="exit-condition">
                  <input type="checkbox" id="time-exit" />
                  <label htmlFor="time-exit">Time-based Exit</label>
                  <input
                    type="number"
                    placeholder="30"
                    min="1"
                  />
                  <span>days</span>
                </div>
              </div>
            </div>

            <div className="strategy-section">
              <h3>Position Sizing</h3>
              <p className="section-description">
                Configure how much capital to risk per trade
              </p>

              <div className="position-sizing">
                <div className="sizing-option">
                  <input type="radio" id="fixed-percent" name="sizing" />
                  <label htmlFor="fixed-percent">Fixed Percentage</label>
                  <input type="number" placeholder="1.0" step="0.1" min="0.1" max="100" />
                  <span>% of portfolio</span>
                </div>

                <div className="sizing-option">
                  <input type="radio" id="fixed-amount" name="sizing" />
                  <label htmlFor="fixed-amount">Fixed Amount</label>
                  <input type="number" placeholder="1000" min="1" />
                  <span>currency units</span>
                </div>
              </div>
            </div>
          </div>

          <div className="strategy-actions">
            <button className="btn">Save Strategy</button>
            <button className="btn btn-secondary">Preview Strategy</button>
            <button className="btn btn-secondary">Load Strategy</button>
          </div>
        </div>

        <div className="strategy-preview">
          <h3>Strategy Preview</h3>
          <div className="preview-content">
            <div className="placeholder-content">
              <div className="placeholder-icon">📈</div>
              <h4>Strategy Summary</h4>
              <p>Your strategy configuration will appear here</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BuildStrategy;