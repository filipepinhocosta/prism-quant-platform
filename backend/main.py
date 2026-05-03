import os
import io
import base64
import json
import time
import shutil 
import tempfile 

# --- A CORREÇÃO MÁGICA PARA SERVIDORES WEB ---
import matplotlib
matplotlib.use('Agg')
# ---------------------------------------------

import pandas as pd
import mplfinance as mpf
import MetaTrader5 as mt5
from fastapi import APIRouter, HTTPException
from google import genai
from pydantic import BaseModel
import datetime

# Router limpo, sem dependências de autenticação
router = APIRouter(
    prefix="/markets",
    tags=["Mercados"]
)

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

# --- MODELOS PARA RECEBER DADOS DO REACT ---
class TradeRequest(BaseModel):
    symbol: str
    type: str # 'BUY' ou 'SELL'
    volume: float

class OrderModifyRequest(BaseModel):
    tp: float
    sl: float

def get_live_chart_base64(symbol: str, timeframe_str: str, n_candles: int = 100):
    # Força a ligação à instalação específica do FPMarkets
    terminal_path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

    if not mt5.initialize(terminal_path):
        print(f"Erro ao inicializar MT5: {mt5.last_error()}")
        return None

    tf = TIMEFRAME_MAP.get(timeframe_str, mt5.TIMEFRAME_H1)

    # Extrai os dados
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_candles)
    if rates is None or len(rates) == 0:
        print(f"Erro ao obter dados para o símbolo {symbol}: {mt5.last_error()}")
        return None

    # Constrói o gráfico
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'}, inplace=True)

    mc = mpf.make_marketcolors(up='#22c55e', down='#ef4444', inherit=True)
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle='dotted', facecolor='#ffffff')

    buf = io.BytesIO()
    mpf.plot(df, type='candle', style=s, volume=True,
             title=f"\n{symbol} - {timeframe_str} (Last {n_candles})",
             savefig=dict(fname=buf, format='png', dpi=100))

    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return img_base64

@router.get("/data")
def get_market_data():
    json_path = r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\4E1B9836A5621221B1E6ED37C3B8887D\MQL5\Files\fibo_data.json"

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Ficheiro JSON não encontrado no MT5.")

    max_retries = 10
    last_error = ""

    for attempt in range(max_retries):
        for enc in ['utf-8', 'utf-16', 'latin-1']:
            try:
                with open(json_path, 'r', encoding=enc) as f:
                    content = f.read()
                    if not content.strip():
                        raise ValueError("Ficheiro vazio neste milissegundo.")
                    return json.loads(content)

            except (json.JSONDecodeError, UnicodeError, ValueError) as e:
                last_error = f"[{enc}] {str(e)}"
                continue
            except PermissionError:
                last_error = "PermissionError (Ficheiro Trancado)"
                break 

        time.sleep(0.2) 

    raise HTTPException(status_code=500, detail=f"Falha de sincronização com o MT5. Último erro: {last_error}")

@router.get("/live-chart/{tf}")
def get_timeframe_chart(tf: str):
    symbol = "EURUSD.r"

    chart = get_live_chart_base64(symbol, tf)
    if not chart:
        raise HTTPException(status_code=500, detail=f"Não foi possível extrair o gráfico para {symbol}. Verifica se o MT5 está aberto.")

    return {"chart": chart}

@router.get("/elliott-memory")
def get_elliott_memory():
    filepath = r"C:\Users\Administrator\Desktop\APEX_SYSTEM\elliott_memory.json"

    if not os.path.exists(filepath):
        return {"fase": "INATIVA"}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Erro ao ler elliott_memory.json: {e}")
        return {"fase": "INATIVA"}

@router.get("/account")
def get_account_info():
    terminal_path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

    if not mt5.initialize(terminal_path):
        raise HTTPException(status_code=500, detail="Erro ao conectar ao MT5 para ler a conta.")

    acc_info = mt5.account_info()
    if acc_info is None:
        raise HTTPException(status_code=500, detail="Não foi possível obter os dados da conta. Verifica o MT5.")

    return acc_info._asdict()

@router.get("/ticker/{symbol}")
def get_ticker(symbol: str):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"bid": 0, "ask": 0}
    return {"bid": tick.bid, "ask": tick.ask}

@router.get("/orders")
def get_open_orders():
    orders = mt5.positions_get()
    if orders is None:
        return []

    result = []
    for o in orders:
        result.append({
            "ticket": o.ticket,
            "symbol": o.symbol,
            "type": o.type,
            "volume": o.volume,
            "price_open": o.price_open,
            "profit": o.profit,
            "tp": o.tp, 
            "sl": o.sl  
        })
    return result

@router.post("/orders/{ticket}/close")
def close_order(ticket: int):
    position = mt5.positions_get(ticket=ticket)
    if position is None or len(position) == 0:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")

    pos = position[0]
    tick = mt5.symbol_info_tick(pos.symbol)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": pos.ticket,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,
        "price": tick.bid if pos.type == 0 else tick.ask,
        "deviation": 20,
        "magic": 234000,
        "comment": "Fechado pelo PRISM ERP",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=500, detail=f"Erro ao fechar ordem: {result.comment}")

    return {"message": "Ordem fechada com sucesso!"}

@router.post("/orders/{ticket}/modify")
def modify_order(ticket: int, req: OrderModifyRequest):
    terminal_path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"
    if not mt5.initialize(terminal_path):
        raise HTTPException(status_code=500, detail="Erro ao conectar ao MT5 para modificar ordem.")

    position = mt5.positions_get(ticket=ticket)
    if position is None or len(position) == 0:
        raise HTTPException(status_code=404, detail="Ordem não encontrada no MT5.")

    pos = position[0]

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": pos.ticket,
        "symbol": pos.symbol,
        "sl": float(req.sl),
        "tp": float(req.tp),
        "magic": pos.magic
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=500, detail=f"Erro MT5 ao modificar TP/SL: {result.comment}")

    return {"message": "Take Profit e Stop Loss modificados com sucesso!"}

@router.get("/news")
def get_news_json():
    filepath = r"C:\Users\Administrator\Desktop\APEX_SYSTEM\news_calendar.json"
    if not os.path.exists(filepath):
        return {"noticias_alto_impacto": []}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler JSON de notícias: {str(e)}")

@router.post("/news/update")
def update_news_json(payload: dict):
    filepath = r"C:\Users\Administrator\Desktop\APEX_SYSTEM\news_calendar.json"
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        return {"message": "Calendário de notícias atualizado e guardado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gravar JSON de notícias: {str(e)}")

@router.post("/chat")
def chat_markets(payload: dict):
    gemini_client = genai.Client(api_key=os.environ.get("API_GEMINI_KEY"))
    symbol = payload.get("symbol", "Mercado")
    msg = payload.get("message", "")

    prompt = f"És o 'Prism Quant', um assistente financeiro institucional. O utilizador perguntou-te: '{msg}' sobre o ativo {symbol}. Responde em Português de Portugal de forma profissional, concisa e focada em análise quantitativa e price action."

    try:
        response = gemini_client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return {"reply": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candles/{symbol}/{tf}")
def get_raw_candles(symbol: str, tf: str, count: int = 240):
    terminal_path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"
    if not mt5.initialize(terminal_path):
        raise HTTPException(status_code=500, detail="Erro ao conectar ao MT5.")

    timeframe = TIMEFRAME_MAP.get(tf, mt5.TIMEFRAME_M1)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

    if rates is None or len(rates) == 0:
        return []

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%H:%M')
    return df[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records')

@router.post("/orders/open")
def open_trade(req: TradeRequest):
    terminal_path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"
    if not mt5.initialize(terminal_path):
        raise HTTPException(status_code=500, detail="Erro MT5")

    order_type = mt5.ORDER_TYPE_BUY if req.type == 'BUY' else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(req.symbol)
    if not tick:
        raise HTTPException(status_code=500, detail="Símbolo não encontrado ou mercado fechado.")

    price = tick.ask if req.type == 'BUY' else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": req.symbol,
        "volume": float(req.volume),
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "Ordem PRISM React",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=500, detail=f"Erro ao abrir ordem: {result.comment}")

    return {"message": f"Ordem {req.type} de {req.volume} lotes aberta com sucesso!"}