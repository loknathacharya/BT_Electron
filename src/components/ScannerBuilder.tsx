import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ATTRS,
  INDICATORS,
  TIMEFRAMES,
  type AttrName,
  type IndicatorName,
  type Logic,
  type CompareOp,
  type CrossType,
  type Offset,
  type Measure,
  type MeasureAttr,
  type MeasureExpr,
  type MeasureIndicator,
  type MeasureConst,
  type Rule,
  type RuleCompare,
  type RuleCrossover,
  type Group,
  type BuilderTree,
  type Timeframe,
  type ArithOperator,
} from './scannerBuilderModel';

const CMP_LABELS: Record<CompareOp, string> = {
  '>': 'Greater than',
  '>=': 'Greater or equal',
  '<': 'Less than',
  '<=': 'Less or equal',
  '==': 'Equals',
  '!=': 'Not equal',
};

const CROSS_LABELS: Record<CrossType, string> = {
  CROSSES_ABOVE: 'Crossed above',
  CROSSES_BELOW: 'Crossed below',
};

const TIMEFRAME_LABELS: Record<Timeframe, string> = {
  '1D': 'Daily',
  '1h': 'Hourly',
  '15m': '15 Min',
  '5m': '5 Min',
};

const KIND_LABELS: Record<'attr' | 'indicator' | 'const' | 'expr', string> = {
  attr: 'Attribute',
  indicator: 'Indicator',
  const: 'Number',
  expr: 'Formula',
};

const ARITH_OPERATORS: ArithOperator[] = ['+', '-', '*', '/'];

const newRule = (): Rule => ({
  id: Math.random().toString(36).slice(2),
  kind: 'rule',
  op: 'compare',
  cmp: '>',
  left: { kind: 'attr', name: 'close' },
  right: { kind: 'const', value: 100 },
});

const newGroup = (logic: Logic = 'AND'): Group => ({
  id: Math.random().toString(36).slice(2),
  kind: 'group',
  logic,
  children: [newRule()],
});

const getDefaultIndicatorParams = (name: IndicatorName): any => {
  if (['SMA', 'EMA', 'RSI', 'BB_MIDDLE', 'BB_UPPER', 'BB_LOWER'].includes(name)) {
    return { period: 14, src: { type: 'attr', name: 'close' } };
  }
  if (name === 'MACD') {
    return { fast: 12, slow: 26, signal: 9, output: 'line', src: { type: 'attr', name: 'close' } };
  }
  if (['ATR', 'ADX'].includes(name)) {
    return { period: 14 };
  }
  return {};
};

const timeframeDisplay = (tf?: Timeframe) => (tf ? TIMEFRAME_LABELS[tf] || tf : 'Main');

const attrDisplay = (name: AttrName) => name.charAt(0).toUpperCase() + name.slice(1);

const offsetDisplay = (offset?: Offset) => {
  if (!offset) return 'No offset';
  if (offset.kind === 'lookback') return `${offset.bars} bars ago`;
  return `Index ${offset.n}`;
};

const indicatorSummary = (name: IndicatorName, params?: any) => {
  const clean = name.replace(/_/g, ' ');
  if (!params) return clean;
  if (name === 'MACD') {
    const fast = params.fast ?? 12;
    const slow = params.slow ?? 26;
    const signal = params.signal ?? 9;
    return `MACD(${fast}, ${slow}, ${signal})`;
  }
  if (['BB_MIDDLE', 'BB_UPPER', 'BB_LOWER'].includes(name)) {
    const period = params.period ?? 20;
    const std = params.std ?? 2;
    return `${clean}(${period}, ${std})`;
  }
  if (['SMA', 'EMA', 'RSI', 'ATR', 'ADX'].includes(name)) {
    const period = params.period ?? 14;
    return `${clean}(${period})`;
  }
  return clean;
};

const cloneMeasure = (measure: Measure): Measure => JSON.parse(JSON.stringify(measure)) as Measure;

const takeTimeframe = (measure?: Measure): Timeframe | undefined =>
  measure && 'timeframe' in measure ? (measure as any).timeframe : undefined;

const takeOffset = (measure?: Measure): Offset | undefined =>
  measure && 'offset' in measure ? (measure as any).offset : undefined;

const createAttrMeasure = (seed?: Measure): MeasureAttr => {
  const base: MeasureAttr = { kind: 'attr', name: 'close' };
  const tf = takeTimeframe(seed);
  const off = takeOffset(seed);
  if (tf) base.timeframe = tf;
  if (off) base.offset = off;
  return base;
};

const createIndicatorMeasure = (seed?: Measure): MeasureIndicator => {
  const base: MeasureIndicator = {
    kind: 'indicator',
    name: 'SMA',
    params: getDefaultIndicatorParams('SMA'),
  };
  const tf = takeTimeframe(seed);
  const off = takeOffset(seed);
  if (tf) base.timeframe = tf;
  if (off) base.offset = off;
  return base;
};

const createConstMeasure = (): MeasureConst => ({ kind: 'const', value: 0 });

const createExpressionMeasure = (seed?: Measure): MeasureExpr => {
  const baseOperand = seed ? cloneMeasure(seed) : createIndicatorMeasure();
  const expr: Array<Measure | ArithOperator> = [baseOperand, '*', { kind: 'const', value: 1 }];
  const exprMeasure: MeasureExpr = { kind: 'expr', expr };
  const tf = takeTimeframe(seed);
  const off = takeOffset(seed);
  if (tf) exprMeasure.timeframe = tf;
  if (off) exprMeasure.offset = off;
  return exprMeasure;
};

function Token({
  children,
  onClick,
  title,
  className,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  title?: string;
  className?: string;
}) {
  const classes = ['token'];
  if (className) classes.push(className);
  return (
    <button type="button" className={classes.join(' ')} onClick={onClick} title={title}>
      {children}
    </button>
  );
}

function NumberInput({
  value,
  onChange,
  min,
  step,
  className,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  step?: number;
  className?: string;
}) {
  const classes = ['token-input'];
  if (className) classes.push(className);
  return (
    <input
      className={classes.join(' ')}
      type="number"
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      min={min}
      step={step}
    />
  );
}

function TimeframeEditor({ value, onChange }: { value?: Timeframe; onChange: (tf?: Timeframe) => void }) {
  return (
    <div className="popover">
      <div className="popover-row">
        <label>Timeframe</label>
        <select value={value || ''} onChange={(e) => onChange((e.target.value || undefined) as any)}>
          <option value="">Main</option>
          {TIMEFRAMES.map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>
      </div>
      <div className="popover-actions">
        <button type="button" className="btn btn-secondary" onClick={() => onChange(value)}>
          Close
        </button>
      </div>
    </div>
  );
}

function OffsetEditor({ value, onChange }: { value?: Offset; onChange: (offset?: Offset) => void }) {
  const [mode, setMode] = useState<'none' | 'lookback' | 'ordinal'>(value ? value.kind : 'none');
  const [bars, setBars] = useState(value?.kind === 'lookback' ? value.bars : 1);
  const [index, setIndex] = useState(value?.kind === 'ordinal' ? value.n : 0);

  useEffect(() => {
    setMode(value ? value.kind : 'none');
    if (value?.kind === 'lookback') setBars(value.bars);
    if (value?.kind === 'ordinal') setIndex(value.n);
  }, [value]);

  const apply = () => {
    if (mode === 'none') {
      onChange(undefined);
    } else if (mode === 'lookback') {
      onChange({ kind: 'lookback', bars: Math.max(1, bars) });
    } else {
      onChange({ kind: 'ordinal', n: index });
    }
  };

  return (
    <div className="popover">
      <div className="popover-row">
        <label>Offset type</label>
        <select value={mode} onChange={(e) => setMode(e.target.value as any)}>
          <option value="none">No offset</option>
          <option value="lookback">Lookback (bars ago)</option>
          <option value="ordinal">Specific index</option>
        </select>
      </div>
      {mode === 'lookback' && (
        <div className="popover-row">
          <label>Bars</label>
          <NumberInput value={bars} onChange={setBars} min={1} />
        </div>
      )}
      {mode === 'ordinal' && (
        <div className="popover-row">
          <label>Index</label>
          <NumberInput value={index} onChange={setIndex} />
        </div>
      )}
      <div className="popover-actions">
        <button type="button" className="btn btn-secondary" onClick={() => onChange(value)}>
          Cancel
        </button>
        <button type="button" className="btn" onClick={apply}>
          Apply
        </button>
      </div>
    </div>
  );
}

function IndicatorEditor({
  name,
  params,
  onChange,
}: {
  name: IndicatorName;
  params?: any;
  onChange: (next: any) => void;
}) {
  const [local, setLocal] = useState<any>(params || getDefaultIndicatorParams(name));

  useEffect(() => {
    setLocal(params || getDefaultIndicatorParams(name));
  }, [name, params]);

  const set = (next: any) => setLocal((prev: any) => ({ ...(prev || {}), ...next }));

  return (
    <div className="popover">
      <div className="popover-row">
        <label>Price source</label>
        <select
          value={(local?.src?.name as AttrName) || 'close'}
          onChange={(e) => set({ src: { type: 'attr', name: e.target.value as AttrName } })}
        >
          {ATTRS.map((a) => (
            <option key={a} value={a}>
              {attrDisplay(a)}
            </option>
          ))}
        </select>
      </div>
      {['SMA', 'EMA', 'RSI', 'ATR', 'ADX', 'BB_MIDDLE', 'BB_UPPER', 'BB_LOWER'].includes(name) && (
        <div className="popover-row">
          <label>Period</label>
          <NumberInput value={Number(local?.period || 14)} onChange={(v) => set({ period: v })} min={1} />
        </div>
      )}
      {name === 'MACD' && (
        <>
          <div className="popover-row">
            <label>Fast</label>
            <NumberInput value={Number(local?.fast || 12)} onChange={(v) => set({ fast: v })} min={1} />
          </div>
          <div className="popover-row">
            <label>Slow</label>
            <NumberInput value={Number(local?.slow || 26)} onChange={(v) => set({ slow: v })} min={1} />
          </div>
          <div className="popover-row">
            <label>Signal</label>
            <NumberInput value={Number(local?.signal || 9)} onChange={(v) => set({ signal: v })} min={1} />
          </div>
          <div className="popover-row">
            <label>Output</label>
            <select value={local?.output || 'line'} onChange={(e) => set({ output: e.target.value })}>
              <option value="line">Line</option>
              <option value="signal">Signal</option>
              <option value="hist">Histogram</option>
            </select>
          </div>
        </>
      )}
      {['BB_MIDDLE', 'BB_UPPER', 'BB_LOWER'].includes(name) && (
        <div className="popover-row">
          <label>Std Dev</label>
          <NumberInput value={Number(local?.std || 2)} onChange={(v) => set({ std: v })} min={1} />
        </div>
      )}
      <div className="popover-actions">
        <button type="button" className="btn btn-secondary" onClick={() => onChange(params || {})}>
          Reset
        </button>
        <button type="button" className="btn" onClick={() => onChange(local || {})}>
          Apply
        </button>
      </div>
    </div>
  );
}

function Sentence({ tree }: { tree: BuilderTree }) {
  const text = useMemo(() => {
    const measureToText = (m: Measure): string => {
      if (m.kind === 'const') return String(m.value);
      const prefix = `${timeframeDisplay((m as MeasureAttr | MeasureIndicator | MeasureExpr).timeframe)} `;
      const offset = (m as MeasureAttr | MeasureIndicator | MeasureExpr).offset
        ? ` (${offsetDisplay((m as MeasureAttr | MeasureIndicator | MeasureExpr).offset)})`
        : '';
      if (m.kind === 'attr') return `${prefix}${attrDisplay(m.name)}${offset}`.trim();
      if (m.kind === 'indicator') return `${prefix}${indicatorSummary(m.name, m.params)}${offset}`.trim();
      if (m.kind === 'expr') {
        const exprText = m.expr
          .map((token) => (typeof token === 'string' ? token : measureToText(token)))
          .join(' ');
        return `${prefix}(${exprText})${offset}`.trim();
      }
      return '';
    };

    const ruleToText = (r: Rule): string => {
      if (r.op === 'compare') return `${measureToText(r.left)} ${CMP_LABELS[(r as RuleCompare).cmp]} ${measureToText(r.right)}`;
      return `${measureToText(r.left)} ${CROSS_LABELS[(r as RuleCrossover).type]} ${measureToText(r.right)}`;
    };

    const groupToText = (g: Group): string => {
      const parts = g.children.map((child) =>
        child.kind === 'group' ? `(${groupToText(child as Group)})` : ruleToText(child as Rule),
      );
      return parts.join(` ${g.logic} `);
    };

    return `Stock passes ${tree.logic === 'AND' ? 'all' : 'any'} of the below filters: ${groupToText(tree)}`;
  }, [tree]);

  const [intro, details] = useMemo(() => {
    const parts = text.split(':');
    return [parts[0], parts.slice(1).join(':')];
  }, [text]);

  return (
    <div className="sentence-preview chartink-sentence">
      <strong>{intro}</strong>
      {details && <span className="chartink-sentence-text">{details.trim()}</span>}
    </div>
  );
}

function MeasureToken({
  measure,
  onChange,
  allowExpr = true,
}: {
  measure: Measure;
  onChange: (m: Measure) => void;
  allowExpr?: boolean;
}) {
  const [showTF, setShowTF] = useState(false);
  const [showOffset, setShowOffset] = useState(false);
  const [showAttrSelect, setShowAttrSelect] = useState(false);
  const [showIndicatorSelect, setShowIndicatorSelect] = useState(false);
  const [showIndicatorParams, setShowIndicatorParams] = useState(false);
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  const [showExprBuilder, setShowExprBuilder] = useState(false);
  const [exprOp, setExprOp] = useState<ArithOperator>('*');
  const [exprOperandKind, setExprOperandKind] = useState<'const' | 'attr' | 'indicator'>('const');

  const kind = measure.kind;
  const supportsTemporal = kind !== 'const';
  const timeframe =
    supportsTemporal && 'timeframe' in measure ? (measure as MeasureAttr | MeasureIndicator | MeasureExpr).timeframe : undefined;
  const offset =
    supportsTemporal && 'offset' in measure ? (measure as MeasureAttr | MeasureIndicator | MeasureExpr).offset : undefined;

  const applyTimeframe = (tf?: Timeframe) => {
    if (!supportsTemporal) return;
    const next = { ...(measure as any) };
    if (tf) next.timeframe = tf;
    else delete next.timeframe;
    onChange(next);
    setShowTF(false);
  };

  const applyOffset = (off?: Offset) => {
    if (!supportsTemporal) return;
    const next = { ...(measure as any) };
    if (off) next.offset = off;
    else delete next.offset;
    onChange(next);
    setShowOffset(false);
  };

  const changeKind = (nextKind: 'attr' | 'indicator' | 'const' | 'expr') => {
    setShowTypeMenu(false);
    if (nextKind === kind) return;
    if (nextKind === 'attr') return onChange(createAttrMeasure(measure));
    if (nextKind === 'indicator') return onChange(createIndicatorMeasure(measure));
    if (nextKind === 'const') return onChange(createConstMeasure());
    if (nextKind === 'expr') return onChange(createExpressionMeasure(measure));
  };

  const typeChip = (
    <>
      <Token className="chip chip-kind" onClick={() => setShowTypeMenu((s) => !s)} title="Change value type">
        {KIND_LABELS[kind]}
      </Token>
      {showTypeMenu && (
        <div className="popover">
          <div className="popover-row">
            <label>Value type</label>
            <select value={kind} onChange={(e) => changeKind(e.target.value as any)}>
              <option value="attr">Attribute</option>
              <option value="indicator">Indicator</option>
              <option value="const">Number</option>
              {allowExpr && <option value="expr">Formula</option>}
            </select>
          </div>
          <div className="popover-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setShowTypeMenu(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );

  if (measure.kind === 'const') {
    return (
      <div className="measure-display measure-const">
        {typeChip}
        <NumberInput value={measure.value} onChange={(v) => onChange({ kind: 'const', value: v })} className="const-input" />
      </div>
    );
  }

  if (measure.kind === 'attr') {
    return (
      <div className="measure-display">
        {typeChip}
        <Token className="chip chip-timeframe" onClick={() => setShowTF((s) => !s)} title="Change timeframe">
          {timeframeDisplay(timeframe)}
        </Token>
        {showTF && <TimeframeEditor value={timeframe} onChange={applyTimeframe} />}
        <Token className="chip chip-measure chip-attr" onClick={() => setShowAttrSelect((s) => !s)} title="Change attribute">
          {attrDisplay(measure.name)}
        </Token>
        {showAttrSelect && (
          <div className="popover">
            <div className="popover-row">
              <label>Attribute</label>
              <select
                value={measure.name}
                onChange={(e) => {
                  onChange({ ...measure, name: e.target.value as AttrName });
                  setShowAttrSelect(false);
                }}
              >
                {ATTRS.map((a) => (
                  <option key={a} value={a}>
                    {attrDisplay(a)}
                  </option>
                ))}
              </select>
            </div>
            <div className="popover-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setShowAttrSelect(false)}>
                Close
              </button>
            </div>
          </div>
        )}
        <Token className="chip chip-offset" onClick={() => setShowOffset((s) => !s)} title="Offset / lookback">
          {offsetDisplay(offset)}
        </Token>
        {showOffset && <OffsetEditor value={offset} onChange={applyOffset} />}
      </div>
    );
  }

  if (measure.kind === 'indicator') {
    const handleIndicatorChange = (nextName: IndicatorName) => {
      const nextParams = measure.name === nextName ? measure.params : getDefaultIndicatorParams(nextName);
      onChange({ ...measure, name: nextName, params: nextParams });
    };

    return (
      <div className="measure-display">
        {typeChip}
        <Token className="chip chip-timeframe" onClick={() => setShowTF((s) => !s)} title="Change timeframe">
          {timeframeDisplay(timeframe)}
        </Token>
        {showTF && <TimeframeEditor value={timeframe} onChange={applyTimeframe} />}
        <Token className="chip chip-measure chip-indicator" onClick={() => setShowIndicatorSelect((s) => !s)} title="Change indicator">
          {indicatorSummary(measure.name, measure.params)}
        </Token>
        {showIndicatorSelect && (
          <div className="popover">
            <div className="popover-row">
              <label>Indicator</label>
              <select
                value={measure.name}
                onChange={(e) => {
                  handleIndicatorChange(e.target.value as IndicatorName);
                  setShowIndicatorSelect(false);
                }}
              >
                {INDICATORS.map((ind) => (
                  <option key={ind} value={ind}>
                    {indicatorSummary(ind, measure.params)}
                  </option>
                ))}
              </select>
            </div>
            <div className="popover-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setShowIndicatorSelect(false)}>
                Close
              </button>
            </div>
          </div>
        )}
        <Token className="chip chip-params" onClick={() => setShowIndicatorParams((s) => !s)} title="Indicator parameters">
          Params
        </Token>
        {showIndicatorParams && (
          <IndicatorEditor
            name={measure.name}
            params={measure.params}
            onChange={(p) => {
              onChange({ ...measure, params: p });
              setShowIndicatorParams(false);
            }}
          />
        )}
        <Token className="chip chip-offset" onClick={() => setShowOffset((s) => !s)} title="Offset / lookback">
          {offsetDisplay(offset)}
        </Token>
        {showOffset && <OffsetEditor value={offset} onChange={applyOffset} />}
      </div>
    );
  }

  const exprMeasure = measure as MeasureExpr;

  const updateExprTokens = (tokens: Array<Measure | ArithOperator>) => {
    onChange({ ...exprMeasure, expr: tokens });
  };

  const setOperandAt = (index: number, nextOperand: Measure) => {
    const nextTokens = exprMeasure.expr.slice();
    nextTokens[index] = nextOperand;
    updateExprTokens(nextTokens);
  };

  const removeOperandAt = (index: number) => {
    const nextTokens = exprMeasure.expr.slice();
    if (index === 0) {
      nextTokens.splice(0, nextTokens.length > 1 ? 2 : 1);
    } else {
      nextTokens.splice(index - 1, 2);
    }
    if (!nextTokens.length) {
      onChange(createConstMeasure());
      return;
    }
    if (typeof nextTokens[0] === 'string') {
      nextTokens.shift();
    }
    updateExprTokens(nextTokens);
  };

  const cycleOperator = (idx: number) => {
    const current = exprMeasure.expr[idx] as ArithOperator;
    const nextIdx = (ARITH_OPERATORS.indexOf(current) + 1) % ARITH_OPERATORS.length;
    const nextTokens = exprMeasure.expr.slice();
    nextTokens[idx] = ARITH_OPERATORS[nextIdx];
    updateExprTokens(nextTokens);
  };

  const appendExprTerm = () => {
    const operand =
      exprOperandKind === 'const' ? createConstMeasure() : exprOperandKind === 'attr' ? createAttrMeasure() : createIndicatorMeasure();
    updateExprTokens([...exprMeasure.expr, exprOp, operand]);
    setShowExprBuilder(false);
  };

  return (
    <div className="measure-display measure-expr">
      {typeChip}
      <Token className="chip chip-timeframe" onClick={() => setShowTF((s) => !s)} title="Change timeframe">
        {timeframeDisplay(timeframe)}
      </Token>
      {showTF && <TimeframeEditor value={timeframe} onChange={applyTimeframe} />}

      <div className="expr-tokens">
        {exprMeasure.expr.map((token, idx) => {
          const key = `${idx}-${typeof token === 'string' ? token : (token as any).kind}`;
          if (typeof token === 'string') {
            return (
              <Token key={key} className="chip chip-operator" onClick={() => cycleOperator(idx)} title="Toggle operator">
                {token}
              </Token>
            );
          }
          const operandIndex = Math.floor(idx / 2);
          return (
            <div key={key} className="expr-operand">
              <MeasureToken measure={token} onChange={(next) => setOperandAt(idx, next)} allowExpr={false} />
              {operandIndex > 0 && (
                <button type="button" className="icon-btn" title="Remove operand" onClick={() => removeOperandAt(idx)}>
                  Del
                </button>
              )}
            </div>
          );
        })}
      </div>

      <Token className="chip chip-params" onClick={() => setShowExprBuilder((s) => !s)} title="Add arithmetic term">
        + Term
      </Token>
      {showExprBuilder && (
        <div className="popover">
          <div className="popover-row">
            <label>Operator</label>
            <select value={exprOp} onChange={(e) => setExprOp(e.target.value as ArithOperator)}>
              {ARITH_OPERATORS.map((op) => (
                <option key={op} value={op}>
                  {op}
                </option>
              ))}
            </select>
          </div>
          <div className="popover-row">
            <label>Operand</label>
            <select value={exprOperandKind} onChange={(e) => setExprOperandKind(e.target.value as any)}>
              <option value="const">Number</option>
              <option value="attr">Attribute</option>
              <option value="indicator">Indicator</option>
            </select>
          </div>
          <div className="popover-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setShowExprBuilder(false)}>
              Cancel
            </button>
            <button type="button" className="btn" onClick={appendExprTerm}>
              Add
            </button>
          </div>
        </div>
      )}

      <Token className="chip chip-offset" onClick={() => setShowOffset((s) => !s)} title="Offset / lookback">
        {offsetDisplay(offset)}
      </Token>
      {showOffset && <OffsetEditor value={offset} onChange={applyOffset} />}
    </div>
  );
}

function RuleRow({ rule, onChange, onRemove }: { rule: Rule; onChange: (r: Rule) => void; onRemove: () => void }) {
  const [showOperator, setShowOperator] = useState(false);

  const updateLeft = (measure: Measure) => {
    if (rule.op === 'compare') {
      onChange({ ...(rule as RuleCompare), left: measure });
    } else {
      onChange({ ...(rule as RuleCrossover), left: measure });
    }
  };

  const updateRight = (measure: Measure) => {
    if (rule.op === 'compare') {
      onChange({ ...(rule as RuleCompare), right: measure });
    } else {
      onChange({ ...(rule as RuleCrossover), right: measure });
    }
  };

  const updateCompareOperator = (cmp: CompareOp) => {
    if (rule.op === 'compare') {
      onChange({ ...(rule as RuleCompare), cmp });
    }
  };

  const updateCrossoverType = (type: CrossType) => {
    if (rule.op === 'crossover') {
      onChange({ ...(rule as RuleCrossover), type });
    }
  };

  const switchOp = (next: 'compare' | 'crossover') => {
    if (next === rule.op) return;
    if (next === 'compare') {
      onChange({
        id: rule.id,
        kind: 'rule',
        op: 'compare',
        cmp: '>',
        left: rule.left,
        right: rule.right,
      });
    } else {
      onChange({
        id: rule.id,
        kind: 'rule',
        op: 'crossover',
        type: 'CROSSES_ABOVE',
        left: rule.left,
        right: rule.right,
      });
    }
  };

  const operatorLabel =
    rule.op === 'compare' ? CMP_LABELS[(rule as RuleCompare).cmp] : CROSS_LABELS[(rule as RuleCrossover).type];

  return (
    <div className="chartink-rule">
      <div className="chartink-rule-body">
        <MeasureToken measure={rule.left} onChange={updateLeft} />

        <div className="chartink-operator">
          <Token className="chip chip-operator" onClick={() => setShowOperator((s) => !s)} title="Change condition operator">
            {operatorLabel}
          </Token>
          {showOperator && (
            <div className="popover">
              <div className="popover-row">
                <label>Condition type</label>
                <select
                  value={rule.op}
                  onChange={(e) => {
                    switchOp(e.target.value as 'compare' | 'crossover');
                  }}
                >
                  <option value="compare">Compare</option>
                  <option value="crossover">Crossover</option>
                </select>
              </div>
              <div className="popover-row">
                <label>{rule.op === 'compare' ? 'Comparison' : 'Crossover'}</label>
                {rule.op === 'compare' ? (
                  <select value={(rule as RuleCompare).cmp} onChange={(e) => updateCompareOperator(e.target.value as CompareOp)}>
                    {Object.entries(CMP_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <select value={(rule as RuleCrossover).type} onChange={(e) => updateCrossoverType(e.target.value as CrossType)}>
                    {Object.entries(CROSS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div className="popover-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowOperator(false)}>
                  Close
                </button>
              </div>
            </div>
          )}
        </div>

        <MeasureToken measure={rule.right} onChange={updateRight} />
      </div>
      <div className="chartink-rule-actions">
        <button type="button" className="icon-btn" title="Remove condition" onClick={onRemove}>
          X
        </button>
      </div>
    </div>
  );
}

function GroupBox({ group, onChange, onRemove }: { group: Group; onChange: (g: Group) => void; onRemove?: () => void }) {
  const [showLogicSelect, setShowLogicSelect] = useState(false);

  const setLogic = (logic: Logic) => onChange({ ...group, logic });
  const addRule = () => onChange({ ...group, children: [...group.children, newRule()] });
  const addGroup = () => onChange({ ...group, children: [...group.children, newGroup('AND')] });
  const updateChild = (idx: number, child: Group | Rule) => {
    const children = group.children.slice();
    children[idx] = child;
    onChange({ ...group, children });
  };
  const removeChild = (idx: number) => {
    const children = group.children.slice();
    children.splice(idx, 1);
    onChange({ ...group, children });
  };

  return (
    <div className="chartink-group">
      <div className="chartink-group-header">
        <div className="chartink-group-title">
          <Token className="chip chip-logic" onClick={() => setShowLogicSelect((s) => !s)} title="Toggle group logic">
            {group.logic === 'AND' ? 'All conditions (AND)' : 'Any condition (OR)'}
          </Token>
          {showLogicSelect && (
            <div className="popover">
              <div className="popover-row">
                <label>Group logic</label>
                <select
                  value={group.logic}
                  onChange={(e) => {
                    setLogic(e.target.value as Logic);
                    setShowLogicSelect(false);
                  }}
                >
                  <option value="AND">All conditions (AND)</option>
                  <option value="OR">Any condition (OR)</option>
                </select>
              </div>
              <div className="popover-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowLogicSelect(false)}>
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="chartink-group-toolbar">
          {onRemove && (
            <button type="button" className="icon-btn" title="Remove group" onClick={onRemove}>
              Del
            </button>
          )}
        </div>
      </div>

      <div className="chartink-group-children">
        {group.children.map((child, idx) => (
          <div key={(child as any).id} className={`chartink-group-node${idx === group.children.length - 1 ? ' is-last' : ''}`}>
            {child.kind === 'group' ? (
              <GroupBox group={child as Group} onChange={(g) => updateChild(idx, g)} onRemove={() => removeChild(idx)} />
            ) : (
              <RuleRow rule={child as Rule} onChange={(r) => updateChild(idx, r)} onRemove={() => removeChild(idx)} />
            )}
          </div>
        ))}
      </div>

      <div className="chartink-group-actions">
        <button type="button" className="btn-chip" onClick={addRule}>
          + Condition
        </button>
        <button type="button" className="btn-chip secondary" onClick={addGroup}>
          + Nested Group
        </button>
      </div>
    </div>
  );
}

export default function ScannerBuilder({ value, onChange }: { value?: BuilderTree; onChange: (tree: BuilderTree) => void }) {
  const [tree, setTree] = useState<BuilderTree>(value ?? newGroup('AND'));
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (value) {
      setTree(value);
    }
  }, [value]);

  const update = useCallback(
    (g: Group) => {
      setTree(g);
      onChange(g);
    },
    [onChange],
  );

  const filteredAttrs = useMemo(
    () => ATTRS.filter((a) => a.toLowerCase().includes(search.toLowerCase())),
    [search],
  );
  const filteredIndicators = useMemo(
    () => INDICATORS.filter((i) => i.toLowerCase().includes(search.toLowerCase())),
    [search],
  );

  const addAttrRule = (attr: AttrName) => {
    const rule: Rule = {
      id: Math.random().toString(36).slice(2),
      kind: 'rule',
      op: 'compare',
      cmp: '>',
      left: { kind: 'attr', name: attr },
      right: { kind: 'const', value: 0 },
    };
    update({ ...tree, children: [...tree.children, rule] });
  };

  const addIndicatorRule = (ind: IndicatorName) => {
    const rule: Rule = {
      id: Math.random().toString(36).slice(2),
      kind: 'rule',
      op: 'compare',
      cmp: '>',
      left: { kind: 'indicator', name: ind, params: getDefaultIndicatorParams(ind) },
      right: { kind: 'const', value: 0 },
    };
    update({ ...tree, children: [...tree.children, rule] });
  };

  return (
    <div className="scanner-builder">
      <div className="chartink-builder">
        <div className="chartink-palette">
          <div>
            <input
              className="token-input chartink-palette-search"
              placeholder="Search attribute/indicator"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div>
            <div className="token-label chartink-palette-heading">Attributes</div>
            <div className="chartink-palette-grid">
              {filteredAttrs.map((a) => (
                <Token key={a} className="chip chip-palette" onClick={() => addAttrRule(a)} title="Add attribute condition">
                  {attrDisplay(a)}
                </Token>
              ))}
            </div>
          </div>
          <div>
            <div className="token-label chartink-palette-heading">Indicators</div>
            <div className="chartink-palette-grid">
              {filteredIndicators.map((i) => (
                <Token key={i} className="chip chip-palette" onClick={() => addIndicatorRule(i)} title="Add indicator condition">
                  {indicatorSummary(i)}
                </Token>
              ))}
            </div>
          </div>
        </div>
        <div className="chartink-preview-panel">
          <Sentence tree={tree} />
        </div>
      </div>

      <GroupBox group={tree} onChange={update} />

      <div className="builder-help">
        <p className="helper-text">
          Tips: Click the colored chips to edit timeframe, indicator settings, offsets, or build formulas. Nested groups let you mix AND/OR logic just
          like Chartink.
        </p>
      </div>
    </div>
  );
}
