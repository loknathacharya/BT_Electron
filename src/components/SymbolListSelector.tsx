import React from 'react';
import { useSymbolLists, SymbolList } from '../hooks/useSymbolLists';

interface SymbolListSelectorProps {
  datasetName: string | null;
  selectedList: string | null;
  onListSelect: (listName: string | null, symbols: string[]) => void;
  label?: string;
  showAllOption?: boolean;
  disabled?: boolean;
}

const SymbolListSelector: React.FC<SymbolListSelectorProps> = ({
  datasetName,
  selectedList,
  onListSelect,
  label = 'Symbol List',
  showAllOption = true,
  disabled = false
}) => {
  const { symbolLists, loading, error } = useSymbolLists(datasetName);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    
    if (value === '' || value === 'ALL') {
      onListSelect(null, []);
    } else {
      const selected = symbolLists.find(list => list.name === value);
      if (selected) {
        onListSelect(selected.name, selected.symbols);
      }
    }
  };

  if (!datasetName) {
    return (
      <div style={{ padding: '8px', color: '#666', fontSize: '13px', fontStyle: 'italic' }}>
        Please select a dataset first
      </div>
    );
  }

  return (
    <div className="symbol-list-selector" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <label style={{ fontSize: '13px', fontWeight: 'bold', color: '#333' }}>
        {label}:
      </label>
      
      {error && (
        <div style={{ fontSize: '12px', color: '#d32f2f', padding: '4px' }}>
          {error}
        </div>
      )}
      
      <select
        value={selectedList || (showAllOption ? 'ALL' : '')}
        onChange={handleChange}
        disabled={disabled || loading}
        style={{
          padding: '8px',
          border: '1px solid #ddd',
          borderRadius: '4px',
          fontSize: '14px',
          backgroundColor: disabled ? '#f5f5f5' : '#fff',
          cursor: disabled ? 'not-allowed' : 'pointer'
        }}
      >
        {showAllOption && <option value="ALL">All Symbols</option>}
        {!showAllOption && <option value="">-- Select a symbol list --</option>}
        
        {loading ? (
          <option disabled>Loading...</option>
        ) : symbolLists.length === 0 ? (
          <option disabled>No symbol lists available</option>
        ) : (
          symbolLists.map(list => (
            <option key={list.id} value={list.name}>
              {list.name} ({list.symbol_count} symbols)
            </option>
          ))
        )}
      </select>
      
      {selectedList && !loading && (
        <div style={{ fontSize: '12px', color: '#666', padding: '4px' }}>
          {(() => {
            const selected = symbolLists.find(l => l.name === selectedList);
            return selected ? (
              <>
                <strong>{selected.symbol_count} symbols</strong>
                {selected.description && ` - ${selected.description}`}
              </>
            ) : null;
          })()}
        </div>
      )}
      
      {!loading && symbolLists.length === 0 && datasetName && (
        <div style={{ fontSize: '12px', color: '#999', padding: '4px', fontStyle: 'italic' }}>
          No custom lists. Create one in Data Management → Symbol Lists
        </div>
      )}
    </div>
  );
};

export default SymbolListSelector;
