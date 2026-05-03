<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prism Quant - README</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            line-height: 1.6;
            color: #24292f;
            background-color: #ffffff;
            max-width: 850px;
            margin: 0 auto;
            padding: 32px;
        }
        h1, h2, h3 {
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }
        h1 {
            font-size: 2em;
            border-bottom: 1px solid #hsla(210,18%,87%,1);
            padding-bottom: 0.3em;
        }
        h2 {
            font-size: 1.5em;
            border-bottom: 1px solid #hsla(210,18%,87%,1);
            padding-bottom: 0.3em;
        }
        h3 {
            font-size: 1.25em;
        }
        p, ul, ol {
            margin-top: 0;
            margin-bottom: 16px;
        }
        ul, ol {
            padding-left: 2em;
        }
        li {
            margin-bottom: 0.25em;
        }
        code {
            font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace;
            font-size: 85%;
            background-color: rgba(175, 184, 193, 0.2);
            padding: 0.2em 0.4em;
            border-radius: 6px;
        }
        pre {
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
            overflow: auto;
            font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace;
            font-size: 85%;
            line-height: 1.45;
        }
        pre code {
            background-color: transparent;
            padding: 0;
            border-radius: 0;
        }
        em {
            font-style: italic;
        }
        strong {
            font-weight: 600;
        }
    </style>
</head>
<body>

    <h1>Prism Quant: AI-Driven Algorithmic Trading &amp; Analytics Platform</h1>

    <p>Prism Quant is a full-stack, institutional-grade quantitative trading platform. It bridges high-frequency MetaTrader 5 (MT5) execution with advanced LLM reasoning (Google Gemini 2.0 Flash) and Smart Money Concepts (SMC).</p>

    <p>Designed for absolute autonomy, it features real-time Order Flow (DOM) heatmaps, Elliott Wave fractal analysis mapped with the Lucas Sequence, and direct low-latency order execution via a React-based remote dashboard.</p>

    <h2>🚀 Key Features</h2>
    <ul>
        <li><strong>AI "Berserker" Oracle:</strong> Integrates the Google Gemini API to parse complex macroeconomic data, correlate 8-year macro matrices, and generate real-time trade signals based on live chart images (Base64 encoded via MPLFinance).</li>
        <li><strong>Direct MT5 Execution Bridge:</strong> FastAPI backend communicates directly with the MetaTrader 5 terminal (<code>FPMarkets</code>), allowing seamless order placement, TP/SL modification, and position tracking with microsecond latency.</li>
        <li><strong>Institutional Liquidity Tracking (DOM):</strong> Real-time extraction and visualization of "Sell Walls" and "Buy Cushions" (Bid/Ask heatmaps) to identify institutional footprints.</li>
        <li><strong>Elliott Wave &amp; Lucas Sequence Visualizer:</strong> Custom React SVG engine that visually tracks market structures (Impulse/Retracement phases) and calculates incoming fractal pivots using the Lucas time-sequence.</li>
        <li><strong>Dynamic Risk Calculator:</strong> Automated lot-sizing based on precise structural targets and 1:500 margin constraints.</li>
    </ul>

    <h2>🛠️ System Architecture</h2>
    <ol>
        <li><strong>Frontend (React / TypeScript):</strong> A sleek, dark-mode-ready dashboard providing real-time ticker data, advanced SVG charting, order management, and a dedicated UI for the Gemini-powered Financial Assistant.</li>
        <li><strong>Backend (FastAPI / Python):</strong> The high-performance core handling MT5 initialization, live chart rendering (<code>mplfinance</code>), algorithmic signal processing, and asynchronous API calls to Finnhub for macroeconomic events.</li>
        <li><strong>Execution Layer (MT5 C++ API):</strong> Python MT5 integration executing secure, deviation-controlled <code>TRADE_ACTION_DEAL</code> requests directly into the broker's liquidity pool.</li>
    </ol>

    <h2>💻 Tech Stack</h2>
    <ul>
        <li><strong>Backend:</strong> Python 3.9+, FastAPI, Pandas, MPLFinance, MetaTrader5 API, Google GenAI.</li>
        <li><strong>Frontend:</strong> React, TypeScript, TailwindCSS/Bootstrap, Lucide-React, React-Markdown.</li>
        <li><strong>Infrastructure:</strong> Designed for Windows Server / VPS deployment (requires local MT5 terminal instance).</li>
    </ul>

    <h2>⚡ Core Modules Code Highlight</h2>

    <h3>AI Execution Bridge (FastAPI)</h3>
    <p>The backend securely extracts live MT5 candlesticks, packages them with institutional SMC variables (<code>fibo_data.json</code>), and feeds them into the Gemini model for predictive confirmation before allowing frontend one-click execution.</p>

    <h3>Dynamic Risk &amp; Elliott Math (React)</h3>
    <p>Calculates margin requirements and generates proportional lot sizes automatically based on the dynamically plotted Elliott Wave extremities, factoring in account equity in real-time.</p>

    <h2>🔒 Setup &amp; Installation</h2>
    <p><em>Note: This repository contains the core logic and interface. Proprietary JSON data feeds (<code>fibo_data.json</code>, <code>elliott_memory.json</code>) and API keys are not included for security reasons.</em></p>

    <ol>
        <li>
            <strong>Clone the repository:</strong>
<pre><code>git clone https://github.com/yourusername/prism-quant-platform.git</code></pre>
        </li>
        <li>
            <strong>Backend Setup:</strong>
<pre><code>cd backend
pip install -r requirements.txt
# Ensure MT5 is installed and modify MT5_TERMINAL_PATH in main.py if necessary.
uvicorn main:app --reload</code></pre>
        </li>
        <li>
            <strong>Frontend Setup:</strong>
<pre><code>cd frontend
npm install
npm start</code></pre>
        </li>
    </ol>

    <h2>📝 License</h2>
    <p>This project is for educational and portfolio demonstration purposes. Trading in financial markets carries a high level of risk.</p>

</body>
</html>