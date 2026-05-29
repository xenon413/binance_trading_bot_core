# Binance Trading Bot Core

This repository contains the core architecture and infrastructure for a high-frequency, multi-threaded cryptocurrency trading bot designed for the Binance exchange. The bot is built in Python and demonstrates scalable software architecture, real-time data streaming, state machine-based order execution, and robust testing practices.

> [!NOTE]
> Proprietary trading strategies (alpha) and production configurations have been omitted from this repository to protect intellectual property. A complete `demo.py` strategy is provided to demonstrate how strategies integrate with the execution engine.

## Key Features

*   **Robust State Machine Execution**: The core `Engine` (`trading/engine.py`) and `SignalHandle` (`trading/signal_handle.py`) orchestrate state transitions, allowing for complex order flows (e.g., holding, hedging, retracement, exit) while maintaining high reliability.
*   **Real-time WebSocket & REST API Integrations**: Custom wrappers for Binance (`core/binance_api/`) handle high-throughput WebSocket streams for live market data and fast REST API execution for orders.
*   **Multi-Threading & Resource Monitoring**: Utilizes dedicated worker threads (`worker_threads/`) for system stability, including RAM monitoring and time synchronization to avoid API rate limits and drift.
*   **Data Validation & Typing**: Fully typed with Python's static typing and utilizes Pydantic (`core/schema/`) to enforce strict data schemas, minimizing runtime errors.
*   **Plug-and-Play Strategy Interface**: The `Strat` base class (`trading/strat/base.py`) enforces an Object-Oriented interface, allowing new strategies to be dropped in without altering core engine logic.

## Project Structure

```text
binance-trading-bot-core/
├── config/                  # Configuration files (demo setups provided)
├── core/
│   ├── binance_api/         # REST and WebSocket wrappers
│   ├── interface/           # Base interfaces for threads and services
│   ├── schema/              # Pydantic data models for validation
│   ├── log_handle.py        # Centralized logging configuration
│   └── base_thread.py       # Threading abstractions
├── tests/                   # Pytest suite for unit and integration testing
├── trading/
│   ├── strat/
│   │   ├── base.py          # Abstract base class for strategies
│   │   └── demo.py          # Example Moving Average cross strategy
│   ├── engine.py            # Main execution loop
│   └── signal_handle.py     # State management for trading signals
├── utils/                   # Reusable utility functions
├── worker_threads/          # Background system monitors (RAM, Wifi, Time)
├── main.py                  # Entry point
└── conftest.py              # Pytest fixtures
```

## Getting Started

### 1. Installation

Ensure you have Python 3.10+ installed.

```powershell
# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file based on the provided template:

```powershell
copy .env.example .env
```

*(For testing and backtesting with the demo strategy, actual API keys are not required).*

### 3. Running the Tests

The project uses `pytest` for testing. Run the test suite to verify the core engine:

```powershell
pytest tests/
# Or use the provided script
.\run_test.ps1
```

### 4. Running the Demo Backtest

You can launch the bot in backtest mode using the provided demo configuration. This configuration utilizes the `demo.py` moving average crossover strategy.

```powershell
python main.py -c config/demo_backtest.json
```

## Architecture Overview

The system is designed around a multi-threaded observer pattern. 
- The **WebSocket Streamers** collect real-time data.
- The **Engine** ticks on incoming data and triggers **Strategies**.
- **Strategies** yield `SignalStatus` events.
- **SignalHandle** processes these events to emit `OpenOrder` or `CloseOrder` events via the **REST API Wrapper**.

This separation of concerns ensures that strategies remain pure logic, while the engine handles execution, retries, and state transitions.
