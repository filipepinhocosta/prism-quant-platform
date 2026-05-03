# Prism Quant: AI-Driven Algorithmic Trading & Analytics Platform
![Prism Quant Main Dashboard](dashboard-main.png)
Prism Quant is a full-stack, institutional-grade quantitative trading platform. It bridges high-frequency MetaTrader 5 (MT5) execution with advanced LLM reasoning (Google Gemini 2.0 Flash) and Smart Money Concepts (SMC).
![Berserker AI Oracle & Multi-Timeframe Analysis](dashboard-ai.png)
Designed for absolute autonomy, it features real-time Order Flow (DOM) heatmaps, Elliott Wave fractal analysis mapped with the Lucas Sequence, and direct low-latency order execution via a React-based remote dashboard.

## 🚀 Key Features

* **AI "Berserker" Oracle:** Integrates the Google Gemini API to parse complex macroeconomic data, correlate 8-year macro matrices, and generate real-time trade signals based on live chart images (Base64 encoded via MPLFinance).
* **Direct MT5 Execution Bridge:** FastAPI backend communicates directly with the MetaTrader 5 terminal (`FPMarkets`), allowing seamless order placement, TP/SL modification, and position tracking with microsecond latency.
* **Institutional Liquidity Tracking (DOM):** Real-time extraction and visualization of "Sell Walls" and "Buy Cushions" (Bid/Ask heatmaps) to identify institutional footprints.
* **Elliott Wave & Lucas Sequence Visualizer:** Custom React SVG engine that visually tracks market structures (Impulse/Retracement phases) and calculates incoming fractal pivots using the Lucas time-sequence.
* **Dynamic Risk Calculator:** Automated lot-sizing based on precise structural targets and 1:500 margin constraints.

## 🛠️ System Architecture

1. **Frontend (React / TypeScript):** A sleek, dark-mode-ready dashboard providing real-time ticker data, advanced SVG charting, order management, and a dedicated UI for the Gemini-powered Financial Assistant.
2. **Backend (FastAPI / Python):** The high-performance core handling MT5 initialization, live chart rendering (`mplfinance`), algorithmic signal processing, and asynchronous API calls to Finnhub for macroeconomic events.
3. **Execution Layer (MT5 C++ API):** Python MT5 integration executing secure, deviation-controlled `TRADE_ACTION_DEAL` requests directly into the broker's liquidity pool.

## 💻 Tech Stack

* **Backend:** Python 3.9+, FastAPI, Pandas, MPLFinance, MetaTrader5 API, Google GenAI.
* **Frontend:** React, TypeScript, TailwindCSS/Bootstrap, Lucide-React, React-Markdown.
* **Infrastructure:** Designed for Windows Server / VPS deployment (requires local MT5 terminal instance).

## ⚡ Core Modules Code Highlight

### AI Execution Bridge (FastAPI)
The backend securely extracts live MT5 candlesticks, packages them with institutional SMC variables (`fibo_data.json`), and feeds them into the Gemini model for predictive confirmation before allowing frontend one-click execution.

### Dynamic Risk & Elliott Math (React)
Calculates margin requirements and generates proportional lot sizes automatically based on the dynamically plotted Elliott Wave extremities, factoring in account equity in real-time.

## 🔒 Setup & Installation

*Note: This repository contains the core logic and interface. Proprietary JSON data feeds (`fibo_data.json`, `elliott_memory.json`) and API keys are not included for security reasons.*

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/prism-quant-platform.git](https://github.com/yourusername/prism-quant-platform.git)
