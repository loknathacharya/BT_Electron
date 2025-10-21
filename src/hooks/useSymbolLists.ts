import { useState, useEffect } from 'react';

export interface SymbolList {
  id: number;
  name: string;
  dataset_name: string;
  description: string;
  symbols: string[];
  symbol_count: number;
  created_at: number;
  updated_at: number;
  metadata?: any;
}

export const useSymbolLists = (datasetName: string | null) => {
  const [symbolLists, setSymbolLists] = useState<SymbolList[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (datasetName) {
      fetchSymbolLists();
    } else {
      setSymbolLists([]);
    }
  }, [datasetName]);

  const fetchSymbolLists = async () => {
    if (!window.electronAPI || !datasetName) return;

    setLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.invoke('get-symbol-lists', {
        dataset_name: datasetName
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setSymbolLists(result.symbol_lists || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch symbol lists');
      console.error('Error fetching symbol lists:', err);
    } finally {
      setLoading(false);
    }
  };

  const getSymbolsByListName = (listName: string): string[] => {
    const list = symbolLists.find(l => l.name === listName);
    return list ? list.symbols : [];
  };

  return {
    symbolLists,
    loading,
    error,
    refetch: fetchSymbolLists,
    getSymbolsByListName
  };
};
