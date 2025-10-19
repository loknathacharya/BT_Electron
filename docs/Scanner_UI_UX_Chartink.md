## Key UI/UX components & how they’re presented

Here are the major components of the scanner, and how the UI/UX handles each:

1. Filter / Rule builder

You start by adding a filter via a “plus” or “add filter” icon/menu. 


Once you pick something like a stock attribute (e.g., “Close”, or “Volume”), it auto-adds an offset (like “Latest”, or “1 day ago”) so you don’t have to think too deeply about the timeframe at first. 


Then you pick an operation (comparison, arithmetic, or crossover) and set constants or link to other indicators. For example: “Latest Close > Number 500”. 


For indicators (like RSI, SMA, MACD) you select them, and the UI shows parameters (e.g., “(close,20)”) which you can click to change. 


There is support for grouping filters/sub-filters, combining via “AND/OR” logic (“passes all”, “passes any”) via toggles or UI selections. 


2. Visual grammar and clarity

The UI is designed to read almost like a sentence: “Stock passes all of the below filters in cash segment: Latest Close > Number 200” etc. This improves clarity and reduces cognitive load. 


Color-coding, icons for filter types, and clear labels (like “Stock Attribute”, “Indicator”, “Offset”) help you understand what each part does.

There is context help in the user-guide (and likely in the UI via tooltips) — e.g., explaining what “offset” means, or how “crossed above” works. 


3. Scan Results & Workflow

After you build your filters, you click “Run Scan” to get results. The UI shows a table of stocks matching the criteria.

Options are provided to Save Scan, so you can reuse your filter setup later without rebuilding from scratch.

There’s also a Create Alert button (for premium users) so you can be notified when stocks meet your criteria. 


4. Time-frame / Offset control

For attributes/indicators you can change the “Latest” prefix to “1 day ago”, “2 days ago”, “Weekly”, “Monthly” etc via dropdown or click. This lets you build filters to compare past vs present. 


The UI supports intraday timeframes (for premium users) like 1-2-3 minute intervals. The UI for selecting the timeframe is built into the filter. 
Chartink

5. Segment / Scope filter

At the top of the scan builder you can select the “Segment” that the scan applies to (for example: cash stocks, futures, watchlists). This helps narrow the universe. 


The UI allows you to change the segment via a dropdown.

## Key building blocks (what to implement)

Token / Chip — clickable visual unit (e.g., Latest, Close, SMA(20)) that opens a small editor when clicked.

Typeahead / Combobox — for selecting indicators, symbols, intervals. (@headlessui/react Combobox or downshift)

Operator picker — small popup/list for choosing >, <, crossed above, = etc.

Parameter editor — inline inputs (sliders or numeric inputs) inside a popover for things like SMA length.

Group container — displays AND / OR label and holds conditions/child groups (collapsible).

Sentence preview — read-only, tokenized sentence built from your JSON that updates live. Offer copy-to-clipboard.

Results panel — runs the JSON to backend and streams/loads results.

Undo/Redo (optional) — improves experimentation UX.

## Important UX & accessibility details

Keyboard first: allow tab navigation, arrow selection in typeaheads, Enter to accept.

ARIA: use accessible Combobox and Popover components rather than hand-rolled div menus.

Avoid contentEditable for tokens — use inputs in popovers instead. (contentEditable is hard to manage and breaks accessibility.)

Focus management: when a popover opens, focus the first control; return focus to the token on close.

Visual affordances: hover states, small chevrons, and microcopy (tooltips) explaining operators (e.g., what “crosses above” means).

Mobile friendliness: popovers should become full-sheet modals on small screens.

Validation: inline validation for missing params before you allow run/save.

## Minimal interaction patterns (how clicks behave)

Click token → open popover with selector / numeric input.

Click operator icon → open operator menu; selecting operator updates JSON and previews sentence.

Click a parameter chip (e.g., 20) → convert to quick edit (slider / numeric input).

Click group header (AND) → toggle to OR (small dropdown).

Click anywhere outside popover → close and commit changes.

Hover a sentence token → highlight matching UI component in the builder.

Click a saved template → load JSON into builder.