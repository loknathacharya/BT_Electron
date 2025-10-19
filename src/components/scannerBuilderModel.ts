// Shared model and conversion utilities for ScannerBuilder

export type Timeframe = '1D' | '1h' | '15m' | '5m';
export type AttrName = 'open' | 'high' | 'low' | 'close' | 'volume';
export type IndicatorName = 'SMA' | 'EMA' | 'RSI' | 'MACD' | 'ATR' | 'BB_MIDDLE' | 'BB_UPPER' | 'BB_LOWER' | 'ADX' | 'VWAP';
export type Logic = 'AND' | 'OR';
export type CompareOp = '>' | '>=' | '<' | '<=' | '==' | '!=';
export type CrossType = 'CROSSES_ABOVE' | 'CROSSES_BELOW';

export type Offset = { kind: 'lookback'; bars: number } | { kind: 'ordinal'; n: number };

export type MeasureAttr = { kind: 'attr'; name: AttrName; timeframe?: Timeframe; offset?: Offset };
export type MeasureIndicator = {
  kind: 'indicator';
  name: IndicatorName;
  timeframe?: Timeframe;
  offset?: Offset;
  params?: any;
};
export type MeasureConst = { kind: 'const'; value: number };
export type ArithOperator = '+' | '-' | '*' | '/';
export type MeasureExpr = {
  kind: 'expr';
  expr: Array<Measure | ArithOperator>;
  timeframe?: Timeframe;
  offset?: Offset;
};
export type Measure = MeasureAttr | MeasureIndicator | MeasureConst | MeasureExpr;

export type RuleCompare = { id: string; kind: 'rule'; op: 'compare'; cmp: CompareOp; left: Measure; right: Measure };
export type RuleCrossover = { id: string; kind: 'rule'; op: 'crossover'; type: CrossType; left: Measure; right: Measure };
export type Rule = RuleCompare | RuleCrossover;

export type Group = { id: string; kind: 'group'; logic: Logic; children: Array<Group | Rule> };

export type BuilderTree = Group;

export const ATTRS: AttrName[] = ['open', 'high', 'low', 'close', 'volume'];
export const INDICATORS: IndicatorName[] = ['SMA','EMA','RSI','MACD','ATR','BB_MIDDLE','BB_UPPER','BB_LOWER','ADX','VWAP'];
export const TIMEFRAMES: Timeframe[] = ['1D','1h','15m','5m'];

// Convert builder tree to backend filter AST
export function treeToFilters(tree: BuilderTree): any[] {
  function measureToNode(m: Measure): any {
    if ((m as any).kind === 'const') return { type: 'const', value: (m as MeasureConst).value };
    if ((m as any).kind === 'attr') {
      const a = m as MeasureAttr; const node: any = { type: 'attr', name: a.name };
      if (a.timeframe) node.timeframe = a.timeframe; if (a.offset) node.offset = a.offset; return node;
    }
    if ((m as any).kind === 'expr') {
      const expr = (m as MeasureExpr).expr.map((token) => (typeof token === 'string' ? token : measureToNode(token)));
      const node: any = { type: 'expr', expr };
      if ((m as MeasureExpr).timeframe) node.timeframe = (m as MeasureExpr).timeframe;
      if ((m as MeasureExpr).offset) node.offset = (m as MeasureExpr).offset;
      return node;
    }
    const i = m as MeasureIndicator; const node: any = { type: 'indicator', name: i.name, params: i.params || {} };
    if (i.timeframe) node.timeframe = i.timeframe; if (i.offset) node.offset = i.offset; return node;
  }
  function groupToNode(g: Group): any {
    return {
      op: 'logical',
      logic: g.logic,
      children: g.children.map(ch => ch.kind === 'group' ? groupToNode(ch as Group) : ruleToNode(ch as Rule))
    };
  }
  function ruleToNode(r: Rule): any {
    if (r.op === 'compare') {
      return { op: 'compare', cmp: r.cmp, left: measureToNode(r.left), right: measureToNode(r.right) };
    }
    return { op: 'crossover', type: r.type, left: measureToNode(r.left), right: measureToNode(r.right) };
  }
  // Wrap single root group as the only filter entry
  return [groupToNode(tree)];
}
