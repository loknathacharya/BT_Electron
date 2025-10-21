# Proposed Application Architecture

This document outlines the proposed architectural changes to introduce a guided, step-by-step workflow into the application.

## 1. High-Level Goal

The primary goal is to transform the application from a collection of disconnected tabs into a unified, linear workflow that guides the user from data import to analysis. This addresses the core UX issues of a confusing user journey and lack of data persistence between views.

## 2. Core Architectural Changes

-   **Global State Management:** Introduce a `WorkflowContext` using React's Context API. This will act as a single source of truth for the application state, holding data like the imported dataset, scanner definitions, and backtest results.
-   **Guided Workflow (Stepper):** Replace the current tab-based navigation (`react-router-dom`) with a state-driven "stepper" or "wizard" component. This component will render the correct view based on the user's current step in the workflow.

## 3. Proposed User & Data Flow

The following diagram illustrates the new architecture and the flow of data through the `WorkflowContext`.

```mermaid
graph TD
    subgraph App [React Application]
        A[WorkflowProvider]
    end

    subgraph WorkflowContext [Global State: WorkflowContext]
        state_step[currentStep: number]
        state_data[datasetId: string | null]
        state_scan[scannerSpec: object | null]
        state_signals[signals: object | null]
        state_backtest[backtestResults: object | null]
    end

    subgraph Stepper [UI Stepper]
        direction LR
        subgraph "Step 1: Import"
            C1[ImportData Component]
        end
        subgraph "Step 2: Scan"
            C2[Scanner Component]
        end
        subgraph "Step 3: Backtest"
            C3[BacktestEngine Component]
        end
        subgraph "Step 4: Analyze"
            C4[Analysis Components]
        end
    end

    A --> Stepper;
    A --> WorkflowContext;

    C1 -- "onComplete: update(datasetId)" --> WorkflowContext;
    WorkflowContext -- "reads datasetId" --> C2;
    C2 -- "onComplete: update(scannerSpec)" --> WorkflowContext;
    WorkflowContext -- "reads scannerSpec" --> C3;
    C3 -- "onComplete: update(backtestResults)" --> WorkflowContext;
    WorkflowContext -- "reads backtestResults" --> C4;
```

### Flow Explanation:

1.  The main `App` is wrapped by the `WorkflowProvider`, making the global state available everywhere.
2.  The `Stepper` component reads the `currentStep` from the context and displays the appropriate component (e.g., `ImportData` for step 1).
3.  When the user completes a step (e.g., successfully imports a file), the component calls a function from the context to update the global state (e.g., `setDatasetId(...)`).
4.  The `Stepper` automatically advances the user to the next step.
5.  The next component in the sequence (e.g., `Scanner`) reads the data it needs from the `WorkflowContext` (e.g., the `datasetId`) to perform its function.
6.  This process continues linearly, ensuring data flows seamlessly and the user is always guided to the next logical action.
