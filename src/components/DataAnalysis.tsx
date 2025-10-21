import React, { useState, useEffect } from 'react';

interface SymbolAnalysis {
  symbol: string;
  basic_info?: {
    start_date: string;
    end_date: string;
    total_records: number;
    unique_dates: number;
    days_span: number;
  };
  quality_metrics?: {
    completeness_score: number;
    integrity_score: number;
    null_fields: Record<string, number>;
    data_errors: Record<string, number>;
  };
  missing_periods?: Array<{
    gap_start_date: string;
    gap_end_date: string;
    gap_days: number;
    date_before: string;
    date_after: string;
  }>;
  comparable_symbols?: {
    status: string;
    comparable_gaps?: Array<any>;
  };
  summary?: {
    overall_score: number;
    quality_rating: string;
    status: string;
    data_coverage: string;
    coverage_percentage: number;
    missing_gaps_count: number;
    recommendation: string;
  };
  error?: string;
}

interface SymbolTableRow {
  symbol: string;
  startDate: string;
  endDate: string;
  totalRecords: number;
  dataPoints: string;
  coverage: number;
  qualityScore: number;
  qualityRating: string;
  missingGaps: number;
  status: string;
}

const DataAnalysis: React.FC = () => {
  const [symbols, setSymbols] = useState<SymbolTableRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolAnalysis | null>(null);
  const [sortConfig, setSortConfig] = useState<{ key: string; order: 'asc' | 'desc' }>({ key: 'symbol', order: 'asc' });

  // Fetch data analysis on component mount
  useEffect(() => {
    fetchDataAnalysis();
  }, []);

  const fetchDataAnalysis = async () => {
    setLoading(true);
    setError('');

    try {
      if (!window.electronAPI) {
        setError('Electron API not available');
        return;
      }

      const result = await window.electronAPI.invoke('analyze-data-quality');

      if (result.error) {
        setError(result.error);
        return;
      }

      if (Array.isArray(result)) {
        // Convert analysis results to table format
        const tableData: SymbolTableRow[] = result
          .filter((item: SymbolAnalysis) => !item.error)
          .map((item: SymbolAnalysis) => ({
            symbol: item.symbol,
            startDate: item.basic_info?.start_date || 'N/A',
            endDate: item.basic_info?.end_date || 'N/A',
            totalRecords: item.basic_info?.total_records || 0,
            dataPoints: `${item.basic_info?.unique_dates || 0}/${item.basic_info?.days_span || 0}`,
            coverage: Math.round((item.basic_info?.unique_dates || 0) / Math.max(1, item.basic_info?.days_span || 1) * 100),
            qualityScore: item.summary?.overall_score || 0,
            qualityRating: item.summary?.quality_rating || 'Unknown',
            missingGaps: item.missing_periods?.length || 0,
            status: item.summary?.status || '?'
          }));

        setSymbols(tableData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (key: string) => {
    let order: 'asc' | 'desc' = 'asc';
    if (sortConfig.key === key && sortConfig.order === 'asc') {
      order = 'desc';
    }
    setSortConfig({ key, order });
  };

  const sortedSymbols = [...symbols].sort((a, b) => {
    const aVal = (a as any)[sortConfig.key];
    const bVal = (b as any)[sortConfig.key];

    if (typeof aVal === 'string') {
      return sortConfig.order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    } else {
      return sortConfig.order === 'asc' ? (aVal - bVal) : (bVal - aVal);
    }
  });

  const getQualityColor = (score: number) => {
    if (score >= 95) return '#4CAF50'; // Green
    if (score >= 85) return '#8BC34A'; // Light Green
    if (score >= 70) return '#FFC107'; // Yellow
    if (score >= 50) return '#FF9800'; // Orange
    return '#F44336'; // Red
  };

  const getCoverageColor = (percentage: number) => {
    if (percentage >= 95) return '#4CAF50';
    if (percentage >= 80) return '#8BC34A';
    if (percentage >= 60) return '#FFC107';
    return '#FF9800';
  };

  const SortIcon = ({ column }: { column: string }) => {
    if (sortConfig.key !== column) return <span style={{ opacity: 0.3 }}>⇅</span>;
    return <span>{sortConfig.order === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: '20px' }}>
          <h2 style={{ marginBottom: '8px', color: '#333' }}>📊 Data Quality Analysis</h2>
          <p style={{ color: '#666', marginBottom: '16px' }}>
            Comprehensive analysis of all imported symbols including date ranges, data completeness, and quality metrics.
          </p>
          <button
            onClick={fetchDataAnalysis}
            disabled={loading}
            style={{
              padding: '10px 16px',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Analyzing...' : '🔄 Refresh Analysis'}
          </button>
        </div>

        {error && (
          <div style={{ padding: '12px 16px', backgroundColor: '#ffebee', color: '#d32f2f', borderRadius: '4px', marginBottom: '20px' }}>
            Error: {error}
          </div>
        )}

        {symbols.length === 0 && !loading && !error && (
          <div style={{ padding: '40px', backgroundColor: 'white', borderRadius: '8px', textAlign: 'center', color: '#999' }}>
            <p style={{ fontSize: '16px', marginBottom: '12px' }}>No data available</p>
            <p style={{ fontSize: '13px' }}>Import data to see quality analysis</p>
          </div>
        )}

        {symbols.length > 0 && (
          <>
            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>Total Symbols</div>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#2196F3' }}>{symbols.length}</div>
              </div>
              <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>Total Records</div>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#4CAF50' }}>
                  {symbols.reduce((sum, s) => sum + s.totalRecords, 0).toLocaleString()}
                </div>
              </div>
              <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>Avg Quality Score</div>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: getQualityColor(symbols.reduce((sum, s) => sum + s.qualityScore, 0) / symbols.length) }}>
                  {Math.round(symbols.reduce((sum, s) => sum + s.qualityScore, 0) / symbols.length)}%
                </div>
              </div>
              <div style={{ backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>Symbols with Gaps</div>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#FF9800' }}>
                  {symbols.filter(s => s.missingGaps > 0).length}
                </div>
              </div>
            </div>

            {/* Data Table */}
            <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '13px'
                }}>
                  <thead style={{ backgroundColor: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                    <tr>
                      {[
                        { key: 'symbol', label: 'Symbol' },
                        { key: 'startDate', label: 'Start Date' },
                        { key: 'endDate', label: 'End Date' },
                        { key: 'totalRecords', label: 'Records' },
                        { key: 'dataPoints', label: 'Data Points' },
                        { key: 'coverage', label: 'Coverage %' },
                        { key: 'qualityScore', label: 'Quality Score' },
                        { key: 'qualityRating', label: 'Rating' },
                        { key: 'missingGaps', label: 'Gaps' },
                        { key: 'status', label: 'Status' }
                      ].map(col => (
                        <th
                          key={col.key}
                          onClick={() => handleSort(col.key)}
                          style={{
                            padding: '12px 8px',
                            textAlign: 'left',
                            fontWeight: 600,
                            color: '#333',
                            cursor: 'pointer',
                            userSelect: 'none',
                            backgroundColor: sortConfig.key === col.key ? '#e3f2fd' : undefined,
                            transition: 'background-color 0.2s'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            {col.label}
                            <SortIcon column={col.key} />
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedSymbols.map((row, idx) => (
                      <tr
                        key={row.symbol}
                        onClick={() => setSelectedSymbol(row as any)}
                        style={{
                          borderBottom: '1px solid #eee',
                          backgroundColor: idx % 2 === 0 ? 'white' : '#fafafa',
                          cursor: 'pointer',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#f0f0f0'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = idx % 2 === 0 ? 'white' : '#fafafa'; }}
                      >
                        <td style={{ padding: '10px 8px', fontWeight: 600, color: '#2196F3' }}>{row.symbol}</td>
                        <td style={{ padding: '10px 8px', fontSize: '12px' }}>{row.startDate}</td>
                        <td style={{ padding: '10px 8px', fontSize: '12px' }}>{row.endDate}</td>
                        <td style={{ padding: '10px 8px', textAlign: 'right' }}>{row.totalRecords.toLocaleString()}</td>
                        <td style={{ padding: '10px 8px', fontSize: '12px' }}>{row.dataPoints}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <div style={{
                            display: 'inline-block',
                            backgroundColor: getCoverageColor(row.coverage),
                            color: 'white',
                            padding: '2px 6px',
                            borderRadius: '3px',
                            fontSize: '11px',
                            fontWeight: 'bold'
                          }}>
                            {row.coverage}%
                          </div>
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <div style={{
                            display: 'inline-block',
                            backgroundColor: getQualityColor(row.qualityScore),
                            color: 'white',
                            padding: '2px 6px',
                            borderRadius: '3px',
                            fontSize: '11px',
                            fontWeight: 'bold'
                          }}>
                            {Math.round(row.qualityScore)}%
                          </div>
                        </td>
                        <td style={{ padding: '10px 8px', fontSize: '12px' }}>{row.qualityRating}</td>
                        <td style={{ padding: '10px 8px', textAlign: 'center', color: row.missingGaps > 0 ? '#FF9800' : '#999' }}>
                          {row.missingGaps}
                        </td>
                        <td style={{ padding: '10px 8px', fontSize: '18px', textAlign: 'center' }}>{row.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Selected Symbol Details */}
            {selectedSymbol && (
              <div style={{ marginTop: '24px', padding: '16px', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ margin: 0, color: '#2196F3' }}>Details for {selectedSymbol.symbol}</h3>
                  <button
                    onClick={() => setSelectedSymbol(null)}
                    style={{
                      backgroundColor: '#f5f5f5',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      padding: '6px 12px',
                      cursor: 'pointer',
                      color: '#666'
                    }}
                  >
                    ✕ Close
                  </button>
                </div>

                {/* Additional details would go here */}
                <p style={{ color: '#666', fontSize: '13px' }}>
                  Select a symbol from the table above to see detailed analysis, missing periods, and alternative symbols.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default DataAnalysis;
