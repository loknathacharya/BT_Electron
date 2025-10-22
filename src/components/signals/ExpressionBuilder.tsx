import React, { useState, useEffect, useCallback } from 'react';
import {
  ValidateExpressionResult,
  ParseExpressionResult,
  ExpressionOperator
} from '../../types/signals';

interface ExpressionBuilderProps {
  value: string;
  onChange: (expression: string) => void;
  datasetName?: string;
  symbol?: string;
  onValidate?: (valid: boolean, error?: string) => void;
  placeholder?: string;
  label?: string;
  helpText?: string;
}

const COMPARISON_OPERATORS: ExpressionOperator[] = ['>', '<', '>=', '<=', '==', '!='];
const SPECIAL_OPERATORS: ExpressionOperator[] = ['crosses_above', 'crosses_below'];
const LOGICAL_OPERATORS: ExpressionOperator[] = ['and', 'or'];

const KNOWN_INDICATORS = [
  'RSI', 'SMA', 'EMA', 'MACD', 'BB', 'ATR', 'ADX', 'Stochastic',
  'close', 'open', 'high', 'low', 'volume'
];

export const ExpressionBuilder: React.FC<ExpressionBuilderProps> = ({
  value,
  onChange,
  datasetName,
  symbol,
  onValidate,
  placeholder = 'e.g., RSI(14) > 70',
  label = 'Expression',
  helpText
}) => {
  const [validationResult, setValidationResult] = useState<ValidateExpressionResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Debounced validation
  useEffect(() => {
    if (!value || value.trim().length === 0) {
      setValidationResult(null);
      if (onValidate) onValidate(false);
      return;
    }

    const timer = setTimeout(() => {
      validateExpression(value);
    }, 500);

    return () => clearTimeout(timer);
  }, [value, datasetName, symbol]);

  const validateExpression = useCallback(async (expr: string) => {
    setIsValidating(true);
    try {
      const result = await window.electron.invoke('validate_expression', {
        expression: expr,
        dataset_name: datasetName,
        symbol: symbol
      });

      setValidationResult(result as ValidateExpressionResult);
      
      if (onValidate) {
        onValidate(result.valid, result.error);
      }
    } catch (error) {
      const errorResult: ValidateExpressionResult = {
        valid: false,
        error: error instanceof Error ? error.message : 'Validation failed'
      };
      setValidationResult(errorResult);
      if (onValidate) onValidate(false, errorResult.error);
    } finally {
      setIsValidating(false);
    }
  }, [datasetName, symbol, onValidate]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);

    // Show suggestions for indicators
    const lastWord = newValue.split(/\s+/).pop() || '';
    if (lastWord.length > 0) {
      const matching = KNOWN_INDICATORS.filter(ind => 
        ind.toLowerCase().startsWith(lastWord.toLowerCase())
      );
      if (matching.length > 0 && matching.length < 5) {
        setSuggestions(matching);
        setShowSuggestions(true);
      } else {
        setShowSuggestions(false);
      }
    } else {
      setShowSuggestions(false);
    }
  };

  const insertOperator = (operator: string) => {
    const newValue = value ? `${value} ${operator} ` : `${operator} `;
    onChange(newValue);
  };

  const insertIndicator = (indicator: string) => {
    // Replace last word with indicator
    const words = value.split(/\s+/);
    words[words.length - 1] = indicator;
    onChange(words.join(' '));
    setShowSuggestions(false);
  };

  const insertTemplate = (template: string) => {
    onChange(template);
  };

  return (
    <div className="expression-builder">
      <div className="expression-builder-header">
        <label className="expression-label">
          {label}
          {isValidating && <span className="validation-spinner"> ⟳</span>}
        </label>
        <button
          type="button"
          className="help-toggle"
          onClick={() => setShowHelp(!showHelp)}
          title="Show help"
        >
          ?
        </button>
      </div>

      <div className="expression-input-wrapper">
        <input
          type="text"
          value={value}
          onChange={handleInputChange}
          placeholder={placeholder}
          className={`expression-input ${
            validationResult?.valid === false ? 'error' : 
            validationResult?.valid === true ? 'success' : ''
          }`}
        />

        {showSuggestions && suggestions.length > 0 && (
          <div className="expression-suggestions">
            {suggestions.map(sugg => (
              <div
                key={sugg}
                className="suggestion-item"
                onClick={() => insertIndicator(sugg)}
              >
                {sugg}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Validation feedback */}
      {validationResult && (
        <div className="validation-feedback">
          {validationResult.valid ? (
            <div className="validation-success">
              ✓ Valid expression
              {validationResult.required_indicators && validationResult.required_indicators.length > 0 && (
                <span className="required-indicators">
                  {' '}(requires: {validationResult.required_indicators.join(', ')})
                </span>
              )}
            </div>
          ) : (
            <div className="validation-error">
              ✗ {validationResult.error}
            </div>
          )}
          
          {validationResult.warnings && validationResult.warnings.length > 0 && (
            <div className="validation-warnings">
              {validationResult.warnings.map((warning, idx) => (
                <div key={idx} className="warning-item">⚠ {warning}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Quick insert buttons */}
      <div className="expression-tools">
        <div className="tool-section">
          <span className="tool-label">Operators:</span>
          <div className="button-group">
            {COMPARISON_OPERATORS.map(op => (
              <button
                key={op}
                type="button"
                className="tool-button"
                onClick={() => insertOperator(op)}
                title={`Insert ${op}`}
              >
                {op}
              </button>
            ))}
          </div>
        </div>

        <div className="tool-section">
          <span className="tool-label">Special:</span>
          <div className="button-group">
            {SPECIAL_OPERATORS.map(op => (
              <button
                key={op}
                type="button"
                className="tool-button"
                onClick={() => insertOperator(op)}
                title={`Insert ${op}`}
              >
                {op.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="tool-section">
          <span className="tool-label">Logic:</span>
          <div className="button-group">
            {LOGICAL_OPERATORS.map(op => (
              <button
                key={op}
                type="button"
                className="tool-button"
                onClick={() => insertOperator(op)}
                title={`Insert ${op}`}
              >
                {op}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Templates */}
      <div className="expression-templates">
        <span className="tool-label">Templates:</span>
        <div className="template-buttons">
          <button
            type="button"
            className="template-button"
            onClick={() => insertTemplate('RSI(14) > 70')}
          >
            RSI Overbought
          </button>
          <button
            type="button"
            className="template-button"
            onClick={() => insertTemplate('RSI(14) < 30')}
          >
            RSI Oversold
          </button>
          <button
            type="button"
            className="template-button"
            onClick={() => insertTemplate('SMA(close, 20) crosses_above SMA(close, 50)')}
          >
            Golden Cross
          </button>
          <button
            type="button"
            className="template-button"
            onClick={() => insertTemplate('close > SMA(close, 20)')}
          >
            Above SMA
          </button>
        </div>
      </div>

      {/* Help panel */}
      {showHelp && (
        <div className="expression-help">
          <h4>Expression Syntax Help</h4>
          
          <section>
            <h5>Basic Comparison</h5>
            <code>RSI(14) &gt; 70</code>
            <p>Compare indicator value to threshold</p>
          </section>

          <section>
            <h5>Cross Detection</h5>
            <code>SMA(close, 20) crosses_above SMA(close, 50)</code>
            <p>Detect when one indicator crosses above/below another</p>
          </section>

          <section>
            <h5>Logical Combination</h5>
            <code>(RSI(14) &lt; 30) and (close &gt; SMA(close, 50))</code>
            <p>Combine multiple conditions with 'and' or 'or'</p>
          </section>

          <section>
            <h5>Supported Indicators</h5>
            <p>{KNOWN_INDICATORS.join(', ')}</p>
          </section>

          <section>
            <h5>Operators</h5>
            <ul>
              <li><strong>Comparison:</strong> &gt;, &lt;, &gt;=, &lt;=, ==, !=</li>
              <li><strong>Special:</strong> crosses_above, crosses_below</li>
              <li><strong>Logical:</strong> and, or</li>
            </ul>
          </section>
        </div>
      )}

      {helpText && (
        <div className="expression-help-text">
          {helpText}
        </div>
      )}

      <style>{`
        .expression-builder {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .expression-builder-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .expression-label {
          font-weight: 600;
          font-size: 0.9rem;
        }

        .validation-spinner {
          display: inline-block;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .help-toggle {
          background: #f0f0f0;
          border: 1px solid #ccc;
          border-radius: 50%;
          width: 24px;
          height: 24px;
          cursor: pointer;
          font-weight: bold;
        }

        .help-toggle:hover {
          background: #e0e0e0;
        }

        .expression-input-wrapper {
          position: relative;
        }

        .expression-input {
          width: 100%;
          padding: 0.5rem;
          border: 2px solid #ccc;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
          font-size: 0.95rem;
        }

        .expression-input.success {
          border-color: #4caf50;
        }

        .expression-input.error {
          border-color: #f44336;
        }

        .expression-suggestions {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          background: white;
          border: 1px solid #ccc;
          border-top: none;
          max-height: 150px;
          overflow-y: auto;
          z-index: 10;
        }

        .suggestion-item {
          padding: 0.5rem;
          cursor: pointer;
        }

        .suggestion-item:hover {
          background: #f0f0f0;
        }

        .validation-feedback {
          font-size: 0.85rem;
        }

        .validation-success {
          color: #4caf50;
        }

        .validation-error {
          color: #f44336;
        }

        .validation-warnings {
          margin-top: 0.25rem;
        }

        .warning-item {
          color: #ff9800;
        }

        .required-indicators {
          color: #666;
          font-size: 0.8rem;
        }

        .expression-tools, .expression-templates {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          align-items: center;
        }

        .tool-section {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .tool-label {
          font-size: 0.85rem;
          color: #666;
          font-weight: 500;
        }

        .button-group, .template-buttons {
          display: flex;
          gap: 0.25rem;
          flex-wrap: wrap;
        }

        .tool-button, .template-button {
          padding: 0.25rem 0.5rem;
          font-size: 0.8rem;
          border: 1px solid #ccc;
          background: white;
          border-radius: 3px;
          cursor: pointer;
        }

        .tool-button:hover, .template-button:hover {
          background: #f0f0f0;
        }

        .template-button {
          padding: 0.35rem 0.75rem;
        }

        .expression-help {
          background: #f9f9f9;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          padding: 1rem;
          font-size: 0.85rem;
        }

        .expression-help h4 {
          margin: 0 0 0.75rem 0;
          font-size: 1rem;
        }

        .expression-help h5 {
          margin: 0.75rem 0 0.25rem 0;
          font-size: 0.9rem;
        }

        .expression-help section {
          margin-bottom: 0.75rem;
        }

        .expression-help code {
          background: #e8e8e8;
          padding: 0.2rem 0.4rem;
          border-radius: 3px;
          font-family: 'Courier New', monospace;
          display: block;
          margin: 0.25rem 0;
        }

        .expression-help p {
          margin: 0.25rem 0;
          color: #666;
        }

        .expression-help ul {
          margin: 0.5rem 0;
          padding-left: 1.5rem;
        }

        .expression-help li {
          margin: 0.25rem 0;
        }

        .expression-help-text {
          font-size: 0.85rem;
          color: #666;
          font-style: italic;
        }
      `}</style>
    </div>
  );
};
