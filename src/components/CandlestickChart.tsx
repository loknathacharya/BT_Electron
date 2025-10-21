import React, { useEffect, useRef, useState } from 'react';

interface ChartState {
  startIndex: number;
  endIndex: number;
  minPrice: number;
  maxPrice: number;
}

interface CrosshairPosition {
  x: number;
  y: number;
  visible: boolean;
  candleIndex?: number;
  priceValue?: number;
}

const CandlestickChart: React.FC<{ data: Array<any>; height?: number }> = ({ data, height = 400 }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [width, setWidth] = useState(800);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [crosshair, setCrosshair] = useState<CrosshairPosition>({ x: 0, y: 0, visible: false });
  
  // Sort data in ascending chronological order (oldest to newest)
  const sortedData = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    
    // Create a copy and sort by date/timestamp
    const copy = [...data];
    copy.sort((a, b) => {
      const dateA = new Date(a.date || a.timestamp || a.name || 0).getTime();
      const dateB = new Date(b.date || b.timestamp || b.name || 0).getTime();
      return dateA - dateB;
    });
    return copy;
  }, [data]);
  
  const [chartState, setChartState] = useState<ChartState>(() => {
    if (!sortedData || sortedData.length === 0) return { startIndex: 0, endIndex: 0, minPrice: 0, maxPrice: 0 };
    
    // Show latest data on the right by default (last 100 candles or all if less)
    const initialVisible = Math.min(100, sortedData.length);
    const startIdx = Math.max(0, sortedData.length - initialVisible);
    
    const allPrices = sortedData.flatMap((d: any) => [d.open, d.high, d.low, d.close]).filter((n: any) => typeof n === 'number');
    return {
      startIndex: startIdx,
      endIndex: sortedData.length,
      minPrice: Math.min(...allPrices),
      maxPrice: Math.max(...allPrices)
    };
  });

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) setWidth(containerRef.current.clientWidth || 800);
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  // Recalculate chart state when data changes (show latest data on right)
  useEffect(() => {
    if (!sortedData || sortedData.length === 0) return;
    
    const initialVisible = Math.min(100, sortedData.length);
    const startIdx = Math.max(0, sortedData.length - initialVisible);
    
    const allPrices = sortedData.flatMap((d: any) => [d.open, d.high, d.low, d.close]).filter((n: any) => typeof n === 'number');
    setChartState({
      startIndex: startIdx,
      endIndex: sortedData.length,
      minPrice: Math.min(...allPrices),
      maxPrice: Math.max(...allPrices)
    });
  }, [sortedData]);

  // Add keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case '=':
          case '+':
            e.preventDefault();
            handleZoomIn();
            break;
          case '-':
          case '_':
            e.preventDefault();
            handleZoomOut();
            break;
        }
      } else {
        switch (e.key) {
          case 'ArrowLeft':
            e.preventDefault();
            handlePanLeft();
            break;
          case 'ArrowRight':
            e.preventDefault();
            handlePanRight();
            break;
          case 'Home':
            e.preventDefault();
            handlePanToStart();
            break;
          case 'End':
            e.preventDefault();
            handlePanToEnd();
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [chartState, sortedData]);

  if (!sortedData || sortedData.length === 0) return <div style={{ padding: 20, color: '#666' }}>No chart data</div>;

  const margin = { top: 20, right: 60, bottom: 60, left: 60 };
  const innerWidth = Math.max(200, width - margin.left - margin.right);
  const innerHeight = Math.max(120, height - margin.top - margin.bottom);

  const volumeRatio = 0.22;
  const priceHeight = innerHeight * (1 - volumeRatio);
  const volumeHeight = innerHeight * volumeRatio;

  const visibleData = sortedData.slice(chartState.startIndex, chartState.endIndex);
  const maxVolume = Math.max(...visibleData.map((d: any) => d.volume || 0), 1);

  const xStep = innerWidth / Math.max(1, visibleData.length);
  const candleWidth = Math.max(2, Math.min(20, xStep * 0.6));

  // Recalculate price range based on visible data for responsive scaling
  const visiblePrices = visibleData.flatMap((d: any) => [d.high, d.low]).filter((n: any) => typeof n === 'number');
  const visibleMinPrice = visiblePrices.length > 0 ? Math.min(...visiblePrices) : chartState.minPrice;
  const visibleMaxPrice = visiblePrices.length > 0 ? Math.max(...visiblePrices) : chartState.maxPrice;
  
  // Add 2% padding to top and bottom
  const priceRange = visibleMaxPrice - visibleMinPrice;
  const paddedMin = visibleMinPrice - priceRange * 0.02;
  const paddedMax = visibleMaxPrice + priceRange * 0.02;

  const priceToY = (p: number) => {
    if (paddedMax === paddedMin) return margin.top + priceHeight / 2;
    const pct = (p - paddedMin) / (paddedMax - paddedMin);
    return margin.top + (1 - pct) * priceHeight;
  };

  const yToPrice = (y: number) => {
    const pct = 1 - (y - margin.top) / priceHeight;
    return paddedMin + pct * (paddedMax - paddedMin);
  };

  const volumeToHeight = (v: number) => (v / maxVolume) * volumeHeight;

  // Generate adaptive price ticks based on range
  const generatePriceTicks = () => {
    const range = paddedMax - paddedMin;
    const numTicks = 8;
    const rawStep = range / numTicks;
    
    // Round to nice numbers
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const normalizedStep = rawStep / magnitude;
    let niceStep: number;
    
    if (normalizedStep <= 1) niceStep = magnitude;
    else if (normalizedStep <= 2) niceStep = 2 * magnitude;
    else if (normalizedStep <= 5) niceStep = 5 * magnitude;
    else niceStep = 10 * magnitude;
    
    const ticks: number[] = [];
    const firstTick = Math.ceil(paddedMin / niceStep) * niceStep;
    for (let tick = firstTick; tick <= paddedMax; tick += niceStep) {
      ticks.push(tick);
    }
    return ticks;
  };

  const priceTicks = generatePriceTicks();

  // Handle mouse wheel zoom (centered on mouse position)
  const handleWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    const chartX = mouseX - margin.left;
    const mouseRatio = chartX / innerWidth;
    
    const direction = e.deltaY > 0 ? 1 : -1; // 1 for zoom out, -1 for zoom in
    const zoomFactor = 0.15;

    setChartState(prev => {
      const range = prev.endIndex - prev.startIndex;
      const zoomAmount = Math.max(1, Math.floor(range * zoomFactor));
      
      // Calculate zoom centered on mouse position
      const leftAmount = Math.floor(zoomAmount * mouseRatio);
      const rightAmount = zoomAmount - leftAmount;
      
      let newStart = prev.startIndex + leftAmount * direction;
      let newEnd = prev.endIndex - rightAmount * direction;

      // Bounds checking
      newStart = Math.max(0, newStart);
      newEnd = Math.min(sortedData.length, newEnd);
      
      // Minimum 5 candles visible
      if (newEnd - newStart < 5) {
        const center = Math.floor((prev.startIndex + prev.endIndex) / 2);
        newStart = Math.max(0, center - 2);
        newEnd = Math.min(sortedData.length, newStart + 5);
      }

      return { ...prev, startIndex: newStart, endIndex: newEnd };
    });
  };

  // Handle mouse down for panning
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    setIsDragging(true);
    setDragStart(e.clientX);
  };

  // Handle mouse move for panning
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDragging || dragStart === null) return;

    const delta = e.clientX - dragStart;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;

    const pxPerCandle = rect.width / Math.max(1, chartState.endIndex - chartState.startIndex);
    const candlesDelta = Math.round(-delta / pxPerCandle);

    setChartState(prev => {
      let newStart = prev.startIndex + candlesDelta;
      let newEnd = prev.endIndex + candlesDelta;

      // Bounds checking
      if (newStart < 0) {
        newStart = 0;
        newEnd = prev.endIndex - prev.startIndex;
      }
      if (newEnd > data.length) {
        newEnd = data.length;
        newStart = data.length - (prev.endIndex - prev.startIndex);
      }

      return { ...prev, startIndex: newStart, endIndex: newEnd };
    });

    setDragStart(e.clientX);
  };

  // Handle mouse up for panning
  const handleMouseUp = () => {
    setIsDragging(false);
    setDragStart(null);
  };

  // Handle double-click to reset to latest data view
  const handleDoubleClick = () => {
    if (!data || data.length === 0) return;
    
    const initialVisible = Math.min(100, data.length);
    const startIdx = Math.max(0, data.length - initialVisible);
    
    const allPrices = data.flatMap((d: any) => [d.open, d.high, d.low, d.close]).filter((n: any) => typeof n === 'number');
    setChartState({
      startIndex: startIdx,
      endIndex: data.length,
      minPrice: Math.min(...allPrices),
      maxPrice: Math.max(...allPrices)
    });
  };

  // Handle crosshair movement
  const handleMouseMoveChart = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isDragging) {
      handleMouseMove(e);
      return;
    }

    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    // Check if mouse is in chart area
    if (mouseX >= margin.left && mouseX <= margin.left + innerWidth &&
        mouseY >= margin.top && mouseY <= margin.top + priceHeight) {
      
      const chartX = mouseX - margin.left;
      const candleIndex = Math.floor(chartX / xStep);
      const actualIndex = chartState.startIndex + candleIndex;
      
      if (actualIndex >= chartState.startIndex && actualIndex < chartState.endIndex) {
        const priceValue = yToPrice(mouseY);
        setCrosshair({ x: mouseX, y: mouseY, visible: true, candleIndex: actualIndex, priceValue });
      } else {
        setCrosshair({ x: mouseX, y: mouseY, visible: false });
      }
    } else {
      setCrosshair({ x: mouseX, y: mouseY, visible: false });
    }
  };

  const handleMouseLeaveChart = () => {
    setCrosshair({ x: 0, y: 0, visible: false });
    if (isDragging) {
      handleMouseUp();
    }
  };

  // Handle zoom in button
  const handleZoomIn = () => {
    setChartState(prev => {
      const range = prev.endIndex - prev.startIndex;
      const zoomAmount = Math.max(1, Math.floor(range * 0.1));
      let newStart = prev.startIndex + zoomAmount;
      let newEnd = prev.endIndex - zoomAmount;

      if (newEnd - newStart < 2) return prev;
      return { ...prev, startIndex: newStart, endIndex: newEnd };
    });
  };

  // Handle zoom out button
  const handleZoomOut = () => {
    setChartState(prev => {
      const range = prev.endIndex - prev.startIndex;
      const zoomAmount = Math.max(1, Math.floor(range * 0.1));
      let newStart = Math.max(0, prev.startIndex - zoomAmount);
      let newEnd = Math.min(data.length, prev.endIndex + zoomAmount);

      return { ...prev, startIndex: newStart, endIndex: newEnd };
    });
  };

  // Handle pan left
  const handlePanLeft = () => {
    setChartState(prev => {
      const range = prev.endIndex - prev.startIndex;
      const panAmount = Math.max(1, Math.floor(range * 0.2));
      let newStart = Math.max(0, prev.startIndex - panAmount);
      let newEnd = Math.min(sortedData.length, prev.endIndex - panAmount);

      if (newStart === prev.startIndex && newEnd === prev.endIndex) {
        newStart = 0;
        newEnd = prev.endIndex - prev.startIndex;
      }

      return { ...prev, startIndex: newStart, endIndex: newEnd };
    });
  };

  // Handle pan right
  const handlePanRight = () => {
    setChartState(prev => {
      const range = prev.endIndex - prev.startIndex;
      const panAmount = Math.max(1, Math.floor(range * 0.2));
      let newStart = Math.min(sortedData.length - (prev.endIndex - prev.startIndex), prev.startIndex + panAmount);
      let newEnd = newStart + (prev.endIndex - prev.startIndex);

      if (newEnd > sortedData.length) {
        newEnd = sortedData.length;
        newStart = Math.max(0, newEnd - (prev.endIndex - prev.startIndex));
      }

      return { ...prev, startIndex: newStart, endIndex: newEnd };
    });
  };

  // Handle pan to start
  const handlePanToStart = () => {
    setChartState(prev => {
      const range = prev.endIndex - prev.startIndex;
      return { ...prev, startIndex: 0, endIndex: range };
    });
  };

  // Handle pan to end (latest data)
  const handlePanToEnd = () => {
    setChartState(prev => {
      const range = prev.endIndex - prev.startIndex;
      return { ...prev, startIndex: Math.max(0, sortedData.length - range), endIndex: sortedData.length };
    });
  };

  return (
    <div ref={containerRef} style={{ width: '100%', position: 'relative' }}>
      {/* Info Panel */}
      <div style={{
        padding: '8px 12px',
        backgroundColor: '#1e1e1e',
        color: '#ddd',
        borderRadius: '4px',
        marginBottom: '8px',
        display: 'flex',
        gap: '16px',
        alignItems: 'center',
        fontSize: '12px',
        flexWrap: 'wrap'
      }}>
        <div style={{ fontWeight: 600 }}>
          {chartState.startIndex + 1} - {chartState.endIndex} / {data.length}
        </div>
        {crosshair.visible && crosshair.candleIndex !== undefined && (
          <>
            <div style={{ color: '#4CAF50' }}>
              {sortedData[crosshair.candleIndex]?.name || ''}
            </div>
            <div>O: {sortedData[crosshair.candleIndex]?.open?.toFixed(2)}</div>
            <div>H: {sortedData[crosshair.candleIndex]?.high?.toFixed(2)}</div>
            <div>L: {sortedData[crosshair.candleIndex]?.low?.toFixed(2)}</div>
            <div>C: {sortedData[crosshair.candleIndex]?.close?.toFixed(2)}</div>
            <div style={{ color: '#8884d8' }}>
              Vol: {sortedData[crosshair.candleIndex]?.volume?.toLocaleString() || '0'}
            </div>
          </>
        )}
      </div>
      <svg 
        ref={svgRef}
        width="100%" 
        height={height} 
        viewBox={`0 0 ${width} ${height}`} 
        preserveAspectRatio="xMidYMid meet"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMoveChart}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeaveChart}
        onDoubleClick={handleDoubleClick}
        style={{ 
          cursor: isDragging ? 'grabbing' : 'crosshair', 
          userSelect: 'none',
          backgroundColor: '#0a0a0a',
          borderRadius: '4px'
        }}
      >
        <rect x={0} y={0} width={width} height={height} fill="#0a0a0a" />

        {/* Price grid & labels */}
        {priceTicks.map((tick, i) => {
          const y = priceToY(tick);
          const decimalPlaces = tick < 1 ? 4 : tick < 10 ? 3 : 2;
          return (
            <g key={`price-${i}`}>
              <line 
                x1={margin.left} 
                x2={margin.left + innerWidth} 
                y1={y} 
                y2={y} 
                stroke="#2a2a2a" 
                strokeWidth={1}
              />
              <text 
                x={margin.left + innerWidth + 5} 
                y={y + 4} 
                fontSize={11} 
                fill="#999"
                textAnchor="start"
              >
                {tick.toFixed(decimalPlaces)}
              </text>
            </g>
          );
        })}

        {/* Candles & volume */}
        {visibleData.map((d, i) => {
          const actualIndex = chartState.startIndex + i;
          const cx = margin.left + xStep * i + xStep / 2;
          const highY = priceToY(d.high);
          const lowY = priceToY(d.low);
          const openY = priceToY(d.open);
          const closeY = priceToY(d.close);
          const top = Math.min(openY, closeY);
          const bodyHeight = Math.max(1, Math.abs(openY - closeY));

          const isUp = d.close >= d.open;
          const candleColor = d.candleColor || (isUp ? '#26a69a' : '#ef5350');
          const wickColor = d.wickColor || candleColor;

          const volH = volumeToHeight(d.volume || 0);
          const volX = cx - candleWidth / 2;
          const volY = margin.top + priceHeight + (volumeHeight - volH);
          const volColor = isUp ? '#26a69a' : '#ef5350';

          return (
            <g key={actualIndex}>
              <line x1={cx} x2={cx} y1={highY} y2={lowY} stroke={wickColor} strokeWidth={Math.max(1, candleWidth * 0.1)} />
              <rect 
                x={cx - candleWidth / 2} 
                y={top} 
                width={candleWidth} 
                height={bodyHeight} 
                fill={candleColor} 
                stroke={candleColor} 
                strokeWidth={0.5} 
              />
              <rect 
                x={volX} 
                y={volY} 
                width={candleWidth} 
                height={volH} 
                fill={volColor} 
                opacity={0.5} 
              />
            </g>
          );
        })}

        {/* X labels */}
        {(() => {
          const maxLabels = Math.min(10, visibleData.length);
          const step = Math.max(1, Math.floor(visibleData.length / maxLabels));
          const y = margin.top + priceHeight + volumeHeight + 18;
          return visibleData.map((d, i) => {
            if (i % step !== 0 && i !== visibleData.length - 1) return null;
            const x = margin.left + xStep * i + xStep / 2;
            return (
              <text 
                key={`x-${i}`} 
                x={x} 
                y={y} 
                textAnchor="middle" 
                fontSize={10} 
                fill="#999"
              >
                {d.name}
              </text>
            );
          });
        })()}

        {/* Crosshair */}
        {crosshair.visible && (
          <g>
            <line 
              x1={crosshair.x} 
              x2={crosshair.x} 
              y1={margin.top} 
              y2={margin.top + priceHeight} 
              stroke="#888" 
              strokeWidth={1} 
              strokeDasharray="4 4"
              pointerEvents="none"
            />
            <line 
              x1={margin.left} 
              x2={margin.left + innerWidth} 
              y1={crosshair.y} 
              y2={crosshair.y} 
              stroke="#888" 
              strokeWidth={1} 
              strokeDasharray="4 4"
              pointerEvents="none"
            />
            {/* Price label on Y axis */}
            {crosshair.priceValue !== undefined && (
              <g>
                <rect 
                  x={margin.left + innerWidth + 2} 
                  y={crosshair.y - 10} 
                  width={54} 
                  height={20} 
                  fill="#555" 
                  rx={2}
                />
                <text 
                  x={margin.left + innerWidth + 29} 
                  y={crosshair.y + 4} 
                  fontSize={11} 
                  fill="#fff" 
                  textAnchor="middle"
                >
                  {crosshair.priceValue.toFixed(2)}
                </text>
              </g>
            )}
          </g>
        )}

        {/* Axis labels */}
        <text x={margin.left + 5} y={margin.top + 12} fontSize={11} fill="#999">Price</text>
        <text x={margin.left + 5} y={margin.top + priceHeight + 12} fontSize={11} fill="#999">Volume</text>
      </svg>

      {/* Instructions */}
      <div style={{
        marginTop: '6px',
        fontSize: '10px',
        color: '#666',
        display: 'flex',
        gap: '12px',
        flexWrap: 'wrap',
        padding: '4px 8px',
        backgroundColor: '#1a1a1a',
        borderRadius: '3px'
      }}>
        <span>�️ Scroll: Zoom</span>
        <span>⌨️ Ctrl +/-: Zoom</span>
        <span>←→: Pan</span>
        <span>Home/End: First/Latest</span>
        <span>Drag: Pan</span>
        <span>Double-click: Reset</span>
      </div>
    </div>
  );
};

export default CandlestickChart;
