import React from 'react';
import './TabSuggestions.css';

interface TabSuggestionsProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  hasLeverageData: boolean;
}

const SUGGESTIONS: Record<string, {
  text: string;
  suggestedTabs: Array<{ tab: string; label: string; reason: string }>;
}> = {
  'overview': {
    text: 'Understand portfolio-level performance',
    suggestedTabs: [
      { tab: 'analytics', label: '📊 Analytics', reason: 'Analyze trade patterns' },
      { tab: 'trades', label: '📋 Trades', reason: 'Review individual trades' }
    ]
  },
  'analytics': {
    text: 'Explore trade behavior and distributions',
    suggestedTabs: [
      { tab: 'trades', label: '📋 Trades', reason: 'See the actual trade details' },
      { tab: 'monte-carlo', label: '🎲 Monte Carlo', reason: 'Forecast future performance' }
    ]
  },
  'trades': {
    text: 'Review trade-by-trade history',
    suggestedTabs: [
      { tab: 'analytics', label: '📊 Analytics', reason: 'Visualize patterns' },
      { tab: 'invested', label: '💰 Capital', reason: 'See capital deployment' }
    ]
  },
  'invested': {
    text: 'Track capital utilization over time',
    suggestedTabs: [
      { tab: 'overview', label: '📊 Overview', reason: 'See returns achieved' },
      { tab: 'trades', label: '📋 Trades', reason: 'Review trading activity' }
    ]
  },
  'monte-carlo': {
    text: 'Forecast future performance scenarios',
    suggestedTabs: [
      { tab: 'optimization', label: '🔍 Optimization', reason: 'Find better parameters' },
      { tab: 'analytics', label: '📊 Analytics', reason: 'Review historical data' }
    ]
  },
  'leverage': {
    text: 'Analyze leverage usage and risk',
    suggestedTabs: [
      { tab: 'overview', label: '📊 Overview', reason: 'See portfolio performance' },
      { tab: 'analytics', label: '📊 Analytics', reason: 'See win/loss distribution' }
    ]
  },
  'optimization': {
    text: 'Search for optimal parameters',
    suggestedTabs: [
      { tab: 'overview', label: '📊 Overview', reason: 'Compare with current results' },
      { tab: 'trades', label: '📋 Trades', reason: 'Review trade details' }
    ]
  }
};

export const TabSuggestions: React.FC<TabSuggestionsProps> = ({
  currentTab,
  onTabChange,
  hasLeverageData
}) => {
  const suggestion = SUGGESTIONS[currentTab];
  if (!suggestion) return null;

  return (
    <div className="tab-suggestions">
      <div className="suggestions-content">
        <div className="suggestion-text">
          💡 <strong>{suggestion.text}</strong>
        </div>
        <div className="suggested-tabs">
          {suggestion.suggestedTabs.map(({ tab, label, reason }) => (
            <button
              key={tab}
              className="suggested-tab"
              onClick={() => onTabChange(tab)}
              title={reason}
            >
              <span className="tab-label">{label}</span>
              <span className="tab-reason">{reason}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
