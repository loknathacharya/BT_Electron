import React, { useEffect, useRef, useState } from 'react';

const CandlestickChart: React.FC<{ data: Array<any>; height?: number }> = ({ data, height = 400 }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(800);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) setWidth(containerRef.current.clientWidth || 800);
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  if (!data || data.length === 0) return <div style={{ padding: 20, color: '#666' }}>No chart data</div>;

  const margin = { top: 20, right: 60, bottom: 60, left: 60 };
  const innerWidth = Math.max(200, width - margin.left - margin.right);
  const innerHeight = Math.max(120, height - margin.top - margin.bottom);

  const volumeRatio = 0.22;
  const priceHeight = innerHeight * (1 - volumeRatio);
  const volumeHeight = innerHeight * volumeRatio;

  const allPrices = data.flatMap((d: any) => [d.open, d.high, d.low, d.close]).filter((n: any) => typeof n === 'number');
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);
  const maxVolume = Math.max(...data.map((d: any) => d.volume || 0), 1);

  const xStep = innerWidth / data.length;
  const candleWidth = Math.max(4, Math.min(20, xStep * 0.6));

  const priceToY = (p: number) => {
    if (maxPrice === minPrice) return margin.top + priceHeight / 2;
    const pct = (p - minPrice) / (maxPrice - minPrice);
    return margin.top + (1 - pct) * priceHeight;
  };

  const volumeToHeight = (v: number) => (v / maxVolume) * volumeHeight;

  const yTicks = 4;
  const ticks: number[] = [];
  for (let i = 0; i <= yTicks; i++) ticks.push(minPrice + (i / yTicks) * (maxPrice - minPrice));

  return (
    <div ref={containerRef} style={{ width: '100%', height }}>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
        <rect x={0} y={0} width={width} height={height} fill="transparent" />

        {/* Price grid & labels */}
        {ticks.map((t, i) => {
          const y = margin.top + (1 - i / yTicks) * priceHeight;
          return (
            <g key={i}>
              <line x1={margin.left} x2={margin.left + innerWidth} y1={y} y2={y} stroke="#eee" strokeDasharray="3 3" />
              <text x={10} y={y + 4} fontSize={12} fill="#666">{t.toFixed(2)}</text>
            </g>
          );
        })}

        {/* Candles & volume */}
        {data.map((d, i) => {
          const cx = margin.left + xStep * i + xStep / 2;
          const highY = priceToY(d.high);
          const lowY = priceToY(d.low);
          const openY = priceToY(d.open);
          const closeY = priceToY(d.close);
          const top = Math.min(openY, closeY);
          const bodyHeight = Math.max(1, Math.abs(openY - closeY));

          const volH = volumeToHeight(d.volume || 0);
          const volX = cx - candleWidth / 2;
          const volY = margin.top + priceHeight + (volumeHeight - volH);

          return (
            <g key={i}>
              <line x1={cx} x2={cx} y1={highY} y2={lowY} stroke={d.wickColor || '#333'} strokeWidth={1} />
              <rect x={cx - candleWidth / 2} y={top} width={candleWidth} height={bodyHeight} fill={d.candleColor || '#4CAF50'} stroke="#333" />
              <rect x={volX} y={volY} width={candleWidth} height={volH} fill="#8884d8" opacity={0.6} />
            </g>
          );
        })}

        {/* X labels */}
        {(() => {
          const maxLabels = Math.min(8, data.length);
          const step = Math.max(1, Math.floor(data.length / maxLabels));
          const y = margin.top + priceHeight + volumeHeight + 18;
          return data.map((d, i) => {
            if (i % step !== 0) return null;
            const x = margin.left + xStep * i + xStep / 2;
            return (
              <text key={`x-${i}`} x={x} y={y} textAnchor="middle" fontSize={11} fill="#333" transform={`rotate(-45 ${x} ${y})`}>
                {d.name}
              </text>
            );
          });
        })()}

        <text x={width - 8} y={margin.top + priceHeight - 6} fontSize={12} fill="#666" textAnchor="end">Price</text>
        <text x={width - 8} y={margin.top + priceHeight + volumeHeight + 6} fontSize={12} fill="#666" textAnchor="end">Volume</text>
      </svg>
    </div>
  );
};

export default CandlestickChart;
