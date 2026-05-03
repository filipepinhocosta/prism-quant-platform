import MetaTrader5 as mt5
import pandas as pd
import time
import sys
import json
import os
import requests
import base64
import io
from PIL import Image
from datetime import datetime
from google import genai
from google.genai import types

# --- FORÇAR VISÃO FULL HD ---
import ctypes 
try: ctypes.windll.user32.SetProcessDPIAware()
except Exception: pass

# =============================================================================
# ⚔️ APEX BERSERKER V40.10 - EURUSD MULTIMODAL + HFT SWEEP (TURTLE SOUP)
# =============================================================================
SYMBOL = "EURUSD.r" 
MAGIC_NUMBER = 888888
SETTINGS_FILE = "apex_settings.json"

CAMINHO_ATUAL = os.path.dirname(os.path.abspath(__file__))
FIBO_JSON_FILE = os.path.join(CAMINHO_ATUAL, "fibo_data.json")
NEWS_JSON_FILE = os.path.join(CAMINHO_ATUAL, "news_calendar.json")
MM_JSON_FILE = os.path.join(CAMINHO_ATUAL, "money_management.json")
DOM_JSON_FILE = os.path.join(CAMINHO_ATUAL, "dom_data.json")
ELLIOTT_MEMORY_FILE = os.path.join(CAMINHO_ATUAL, "elliott_memory.json") 
SOFT_SL_FILE = os.path.join(CAMINHO_ATUAL, "soft_sl.json") 

# --- CONFIGURAÇÃO DO CONTABILISTA DIGITAL ---
ARQUIVO_CUSTOS = os.path.join(CAMINHO_ATUAL, "billing_metrics.json")
TABELA_PRECOS_GEMINI = {
    "gemini-3.1-pro-preview": {"in": 1.25, "out": 5.00},
    "gemini-1.5-flash": {"in": 0.075, "out": 0.30}
}

# --- CONFIGURAÇÕES PADRÃO ---
DEFAULT_CONFIG = {
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "RISK_PERCENTAGE": 10.0,
    "MAX_LOT_SIZE": 10.0,
    "MAX_SPREAD_POINTS": 30,     
    "MAX_SWEEP_POINTS": 50,         # NOVO HFT: Se furar a liquidez mais do que 5 pips, é inversão real. Abortar.
    "CATASTROPHIC_SL_POINTS": 1000, 
    "PARTIAL_PROFIT_POINTS": 40,    
    "PARTIAL_CLOSE_PERCENT": 50.0,  
    "MOVE_TO_BREAKEVEN": True,      
    "SEARCH_INTERVAL_MINUTES": 15, 
    "PAUSE_NEW_TRADES_NIGHT": True, 
    "START_HOUR": 7,  
    "END_HOUR": 20,   
    "PAUSE_ON_WEEKENDS": True,
    "NEWS_FILTER_MINUTES": 20 
}

def log(msg):
    try: print(f"[BERSERKER] {datetime.now().strftime('%H:%M:%S')} | {msg}")
    except: pass

def load_settings():
    settings = DEFAULT_CONFIG.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f: settings.update(json.load(f))
        except: pass
    return settings

def boot_mt5():
    mt5_path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"
    if not mt5.initialize(path=mt5_path): raise Exception(f"MT5 Init Failed")

def registar_custos_ia(modelo_usado, prompt_tokens, output_tokens):
    try:
        precos = TABELA_PRECOS_GEMINI.get(modelo_usado, {"in": 0.0, "out": 0.0})
        custo_in = (prompt_tokens / 1_000_000) * precos["in"]
        custo_out = (output_tokens / 1_000_000) * precos["out"]
        custo_total = custo_in + custo_out
        mes_atual = datetime.now().strftime('%Y-%m')

        dados_faturacao = {}
        if os.path.exists(ARQUIVO_CUSTOS):
            with open(ARQUIVO_CUSTOS, 'r', encoding='utf-8') as f:
                dados_faturacao = json.load(f)

        if mes_atual not in dados_faturacao:
            dados_faturacao[mes_atual] = {"total_prompt_tokens": 0, "total_output_tokens": 0, "custo_estimado_usd": 0.0, "total_chamadas": 0}

        dados_faturacao[mes_atual]["total_prompt_tokens"] += prompt_tokens
        dados_faturacao[mes_atual]["total_output_tokens"] += output_tokens
        dados_faturacao[mes_atual]["custo_estimado_usd"] += custo_total
        dados_faturacao[mes_atual]["total_chamadas"] += 1

        with open(ARQUIVO_CUSTOS, 'w', encoding='utf-8') as f: json.dump(dados_faturacao, f, indent=4)
        log(f"💸 Faturação IA: +${custo_total:.5f} | Mês Atual: ${dados_faturacao[mes_atual]['custo_estimado_usd']:.3f}")
    except Exception as e:
        pass

def get_upcoming_news(minutes_range=120):
    if not os.path.exists(NEWS_JSON_FILE): return []
    try:
        with open(NEWS_JSON_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        agora = datetime.now()
        noticias_proximas = []
        for n in data.get("noticias_alto_impacto", []):
            try:
                data_hora_str = f"{n['data']} {n['hora']}"
                data_hora_noticia = datetime.strptime(data_hora_str, '%Y-%m-%d %H:%M')
                diff = (data_hora_noticia - agora).total_seconds() / 60.0
                if -20 <= diff <= minutes_range:
                    n['minutos_para_evento'] = round(diff, 1)
                    noticias_proximas.append(n)
            except: continue
        return noticias_proximas
    except: return []

def verificar_janela_lucas(velas_passadas, margem_erro=2): # Margem alargada para permitir que o Sweep se forme
    lucas_seq = [11, 18, 29, 47, 76, 123, 199, 322]
    for numero_lucas in lucas_seq:
        if abs(velas_passadas - numero_lucas) <= margem_erro:
            return True, numero_lucas
    return False, None

# =============================================================================
# 🎯 MÁQUINA DE ESTADOS ELLIOTT (HFT SWEEP MODE)
# =============================================================================
def calcular_sniper_m1_stealth(simbolo, tendencia_macro_h1, max_sweep_points=50):
    estado = {"fase": "PROCURAR", "direcao": tendencia_macro_h1, "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}
    
    if os.path.exists(ELLIOTT_MEMORY_FILE):
        try:
            with open(ELLIOTT_MEMORY_FILE, 'r') as f: 
                loaded_state = json.load(f)
                if isinstance(loaded_state, dict):
                    estado.update(loaded_state)
        except: pass

    if estado.get("direcao") != "NENHUMA" and estado.get("direcao") != tendencia_macro_h1:
        log("🔄 [M1] Oráculo Macro inverteu a bússola! Reset à memória stealth.")
        estado = {"fase": "PROCURAR", "direcao": tendencia_macro_h1, "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}

    rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, 300) 
    if rates is None or len(rates) == 0: return "ABORTAR", 0.0, 0.0, 0.0
    df = pd.DataFrame(rates)
    df['time'] = df['time'].astype(int)
    
    preco_atual = float(df['close'].iloc[-1])
    acao_furtiva = "AGUARDAR_OCULTO"
    alvo_tp = 0.0
    sl_estrutural = 0.0

    symbol_info = mt5.symbol_info(simbolo)
    point = symbol_info.point if symbol_info else 0.00001
    max_sweep_real = max_sweep_points * point

    if tendencia_macro_h1 == "BULL":
        if estado.get("fase") == "PROCURAR":
            min_idx = df['low'].idxmin()
            min_recente = float(df['low'].min())
            max_recente = float(df['high'].max())
            amplitude = max_recente - min_recente
            
            if amplitude > 0.00050: 
                inicio_time = int(df['time'].iloc[min_idx])
                estado.update({
                    "fase": "ATIVA", "direcao": "BULL", "inicio": min_recente, "extremo": max_recente, 
                    "inicio_time": inicio_time, "onda_atual": "RETRAÇÃO_2_4"
                })
                log(f"🌊 [M1] Impulso detetado. À espera que o retalho seja caçado abaixo de {min_recente:.5f}")
        
        elif estado.get("fase") == "ATIVA":
            inicio_time = estado.get("inicio_time", 0)
            
            if inicio_time > 0 and (df['time'] == inicio_time).any():
                df_onda = df[df['time'] >= inicio_time]
            else:
                log("⏳ [M1] Onda M1 expirou (>5h). Reiniciar...")
                estado = {"fase": "PROCURAR", "direcao": "BULL", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}
                with open(ELLIOTT_MEMORY_FILE, 'w') as f: json.dump(estado, f)
                return "ABORTAR", 0.0, 0.0, 0.0
                
            max_onda = float(df_onda['high'].max())
            min_onda = float(df_onda['low'].min())
            
            amp_atual = estado.get("extremo", 0) - estado.get("inicio", 0)
            alvo_tp = estado.get("inicio", 0) + (amp_atual * 1.618)

            # 1. Invalidação Real (Quebra estrutural além do Sweep permitido)
            if min_onda < estado.get("inicio", 0) - max_sweep_real:
                log("❌ [M1] Inversão Genuína! O suporte rasgou mais de 5 pips. Não é sweep, é dump.")
                estado = {"fase": "PROCURAR", "direcao": "BULL", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}
                acao_furtiva = "ABORTAR"
                
            # 2. Sucesso Prematuro
            elif max_onda >= alvo_tp:
                log("🎯 [M1] Alvo 1.618 penetrado prematuramente. Reiniciar...")
                estado = {"fase": "PROCURAR", "direcao": "BULL", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}
                acao_furtiva = "ABORTAR"
                
            # 3. Expansão
            elif max_onda > estado.get("extremo", 0):
                estado["extremo"] = max_onda
                estado["onda_atual"] = "IMPULSO_3_5"
                log(f"🚀 [M1] Novo Topo: {max_onda:.5f}. Mantendo a armadilha de liquidez no fundo.")

            # 4. GATILHO HFT SWEEP (Turtle Soup)
            elif estado.get("fase") == "ATIVA": 
                # Condição 1: Preço foi lá abaixo caçar os stops do retalho
                if min_onda < estado.get("inicio", 0):
                    # Condição 2: Preço recuperou (Os HFTs absorveram a liquidez e voltaram para dentro da zona)
                    if preco_atual >= estado.get("inicio", 0):
                        idx_inicio = df.index[df['time'] == inicio_time][0]
                        idx_atual = df.index[-1]
                        velas_passadas = idx_atual - idx_inicio
                        
                        janela_aberta, num_lucas = verificar_janela_lucas(velas_passadas)
                        if janela_aberta:
                            log(f"🔥 LIQUIDITY SWEEP! Retalho caçado + Recuperação + Lucas {num_lucas}. ENTRADA HFT!")
                            acao_furtiva = "ATACAR_MERCADO_BULL"
                            # O novo Soft SL passa a ser a ponta extrema do pavio que fez a limpeza
                            sl_estrutural = min_onda 
                            estado = {"fase": "PROCURAR", "direcao": "BULL", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}

    elif tendencia_macro_h1 == "BEAR":
        if estado.get("fase") == "PROCURAR":
            max_idx = df['high'].idxmax()
            max_recente = float(df['high'].max())
            min_recente = float(df['low'].min())
            amplitude = max_recente - min_recente
            
            if amplitude > 0.00050:
                inicio_time = int(df['time'].iloc[max_idx])
                estado.update({
                    "fase": "ATIVA", "direcao": "BEAR", "inicio": max_recente, "extremo": min_recente, 
                    "inicio_time": inicio_time, "onda_atual": "RETRAÇÃO_2_4"
                })
                log(f"🌊 [M1] Impulso detetado. À espera que o retalho seja caçado acima de {max_recente:.5f}")
        
        elif estado.get("fase") == "ATIVA":
            inicio_time = estado.get("inicio_time", 0)
            
            if inicio_time > 0 and (df['time'] == inicio_time).any():
                df_onda = df[df['time'] >= inicio_time]
            else:
                log("⏳ [M1] Onda M1 expirou (>5h). Reiniciar...")
                estado = {"fase": "PROCURAR", "direcao": "BEAR", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}
                with open(ELLIOTT_MEMORY_FILE, 'w') as f: json.dump(estado, f)
                return "ABORTAR", 0.0, 0.0, 0.0
                
            max_onda = float(df_onda['high'].max())
            min_onda = float(df_onda['low'].min())
            
            amp_atual = estado.get("inicio", 0) - estado.get("extremo", 0)
            alvo_tp = estado.get("inicio", 0) - (amp_atual * 1.618)

            if max_onda > estado.get("inicio", 0) + max_sweep_real:
                log("❌ [M1] Inversão Genuína! A resistência rasgou mais de 5 pips. Não é sweep, é pump.")
                estado = {"fase": "PROCURAR", "direcao": "BEAR", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}
                acao_furtiva = "ABORTAR"
                
            elif min_onda <= alvo_tp:
                log("🎯 [M1] Alvo 1.618 penetrado prematuramente. Reiniciar...")
                estado = {"fase": "PROCURAR", "direcao": "BEAR", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}
                acao_furtiva = "ABORTAR"
                
            elif min_onda < estado.get("extremo", 0):
                estado["extremo"] = min_onda
                estado["onda_atual"] = "IMPULSO_3_5"
                log(f"🚀 [M1] Novo Fundo: {min_onda:.5f}. Mantendo a armadilha de liquidez no topo.")

            elif estado.get("fase") == "ATIVA":
                if max_onda > estado.get("inicio", 0): # Furou o topo
                    if preco_atual <= estado.get("inicio", 0): # Recuperou e fechou a armadilha
                        idx_inicio = df.index[df['time'] == inicio_time][0]
                        idx_atual = df.index[-1]
                        velas_passadas = idx_atual - idx_inicio
                        
                        janela_aberta, num_lucas = verificar_janela_lucas(velas_passadas)
                        if janela_aberta:
                            log(f"🔥 LIQUIDITY SWEEP! Retalho caçado + Recuperação + Lucas {num_lucas}. ENTRADA HFT!")
                            acao_furtiva = "ATACAR_MERCADO_BEAR"
                            # O novo Soft SL passa a ser a ponta extrema do pavio que fez a limpeza
                            sl_estrutural = max_onda 
                            estado = {"fase": "PROCURAR", "direcao": "BEAR", "inicio": 0.0, "extremo": 0.0, "inicio_time": 0, "onda_atual": "PESQUISA"}

    try:
        with open(ELLIOTT_MEMORY_FILE, 'w') as f: json.dump(estado, f)
    except Exception as e:
        log(f"⚠️ Erro ao gravar estado: {e}")
        
    return acao_furtiva, preco_atual, alvo_tp, sl_estrutural

# =============================================================================
# 🧠 CÉREBRO LLM MULTIMODAL
# =============================================================================
def consultar_oraculo_multimodal(settings, posicoes_abertas=None, ordens_pendentes=None, session_status="DAY"):
    if not os.path.exists(FIBO_JSON_FILE): return "AGUARDAR", "Sem dados JSON", 1.0, 0.0, 0.0, 0.0
    try:
        with open(FIBO_JSON_FILE, 'r', encoding='utf-8') as f: full_data = json.load(f)
    except: return "AGUARDAR", "Erro JSON", 1.0, 0.0, 0.0, 0.0

    radar_dom_data = {"status": "Inativo / Sem dados"}
    if os.path.exists(DOM_JSON_FILE):
        try:
            with open(DOM_JSON_FILE, 'r', encoding='utf-8') as f: radar_dom_data = json.load(f)
        except Exception as e: log(f"⚠️ Falha ao ler Ponte DOM: {e}")

    apex_vision = full_data.get("apex_vision", {})
    b64_chart = apex_vision.get("chart_base64", "")
    if not b64_chart or "Falha" in b64_chart:
        return "AGUARDAR", "Sem visão do gráfico H1", 1.0, 0.0, 0.0, 0.0

    try:
        if "base64," in b64_chart: b64_chart = b64_chart.split("base64,")[1]
        chart_bytes = base64.b64decode(b64_chart)
        pil_image = Image.open(io.BytesIO(chart_bytes))
    except Exception as e:
        return "AGUARDAR", "Erro conversão imagem", 1.0, 0.0, 0.0, 0.0

    l_m15 = full_data.get("M15", {})
    l_h1 = full_data.get("H1", {})
    l_d1 = full_data.get("D1", {})
    l_w1 = full_data.get("W1", {})
    l_mn1 = full_data.get("MN1", {})
    correlacao = full_data.get("correlacao_macro_8y", {})
    upcoming_news = get_upcoming_news(180) 
    
    resumo_texto_smc = {
        "SYMBOL": SYMBOL,
        "PRECO_ATUAL": l_m15.get("preco_atual", 0),
        "ALVO_H4": full_data.get("H4", {}).get("alvo_1618", 0),
        "TENDENCIA_H1": l_h1.get("tendencia", "S/D"),
        "PRICE_ACTION_D1": l_d1.get("price_action_atual", "S/D"),
        "DADOS_CORRELACAO_8Y": correlacao,
        "CALENDARIO_FUNDAMENTAL_PROXIMO": upcoming_news,
        "SESSAO_ATUAL": session_status,
        "CONTEXTO_MACRO_IA": {
            "DIARIO": l_d1.get("resumo_ia", "S/D"),
            "SEMANAL": l_w1.get("resumo_ia", "S/D")
        }
    }

    estado_ordens = ""
    total_pnl = 0
    if posicoes_abertas:
        for p in posicoes_abertas:
            total_pnl += (p.profit + p.swap)
            estado_ordens += f"- POSIÇÃO {p.ticket}: {'BUY' if p.type==0 else 'SELL'} {p.volume}L @ {p.price_open}\n"

    api_key = settings.get("GEMINI_API_KEY", "")
    if not api_key: return "AGUARDAR", "Sem API Key", 1.0, 0.0, 0.0, 0.0

    prompt = f"""
    És um Gestor de Hedge Fund Quantitativo e Mestre em Ondas de Elliott.
    Analisa a imagem do gráfico H1 anexa e os dados SMC/Macro. Ativo: EURUSD.r.
    
    DADOS SMC: {json.dumps(resumo_texto_smc, indent=1)}
    PORTFÓLIO: {estado_ordens if estado_ordens else 'Nenhuma ordem'} | PnL: {total_pnl:.2f}

    RESPOSTA JSON ESTRITO:
    {{
      "decisao": "COMPRA" | "VENDA" | "COMPRA_LIMIT" | "VENDA_LIMIT" | "AGUARDAR" | "FECHAR_TUDO",
      "preco_entrada": 0.0, 
      "motivo": "Explicação técnica da análise",
      "take_profit": 0.0,
      "stop_loss": 0.0,
      "lot_multiplier": 1.0
    }}
    """

    try:
        client = genai.Client(api_key=api_key)
        log(f"🧠 A consultar Oráculo (Modo: {session_status})...")
        
        nome_do_modelo = 'gemini-3.1-pro-preview'
        response = client.models.generate_content(
            model=nome_do_modelo,
            contents=[pil_image, prompt],
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")
        )
        
        res = json.loads(response.text)
        action = res.get("decisao", "AGUARDAR")
        motivo = res.get("motivo", "Análise Multimodal SMC")
        preco_entrada = float(res.get("preco_entrada", 0.0))
        
        log(f"👔 ORÁCULO: {action} | {motivo[:60]}...")
        
        try:
            if "apex_vision" not in full_data: full_data["apex_vision"] = {}
            full_data["apex_vision"]["ultima_decisao_berserker"] = action
            full_data["apex_vision"]["ultimo_motivo_berserker"] = motivo
            with open(FIBO_JSON_FILE, 'w', encoding='utf-8') as f: json.dump(full_data, f, indent=4)
        except: pass
        
        return action, motivo, float(res.get("lot_multiplier", 1.0)), float(res.get("take_profit", 0.0)), float(res.get("stop_loss", 0.0)), preco_entrada
    except Exception as e:
        log(f"⚠️ Erro API Multimodal: {e}")
        return "AGUARDAR", "Erro de Análise LLM", 1.0, 0.0, 0.0, 0.0

def calculate_dynamic_lot(settings, multiplier=1.0):
    try:
        acc = mt5.account_info()
        if acc is None or acc.balance < 100.0: return 0.01

        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None: return 0.01

        target_margin = acc.balance * (settings.get("RISK_PERCENTAGE", 10.0) / 100.0)
        margin_per_lot = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, SYMBOL, 1.0, tick.ask)
        if margin_per_lot is None or margin_per_lot <= 0: return 0.01

        base_lot = target_margin / margin_per_lot
        sym_info = mt5.symbol_info(SYMBOL)
        lot_step = sym_info.volume_step if sym_info else 0.01
        min_lot = sym_info.volume_min if sym_info else 0.01
        max_lot_settings = settings.get("MAX_LOT_SIZE", 10.0)
        
        final_lot = round(base_lot / lot_step) * lot_step
        final_lot = max(final_lot, min_lot) 
        final_lot = min(final_lot * multiplier, max_lot_settings) 
        return round(final_lot, 2)
    except Exception as e:
        return 0.01

def open_order(order_type, volume, comment="APEX", tp=0.0, sl=0.0, price_limit=0.0):
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None: return None
    is_pending = order_type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT]
    
    if order_type == mt5.ORDER_TYPE_BUY: price = tick.ask
    elif order_type == mt5.ORDER_TYPE_SELL: price = tick.bid
    else: price = price_limit 
        
    req = {
        "action": mt5.TRADE_ACTION_PENDING if is_pending else mt5.TRADE_ACTION_DEAL, 
        "symbol": SYMBOL, 
        "volume": float(volume),
        "type": order_type, 
        "price": price, 
        "magic": MAGIC_NUMBER, 
        "tp": tp, 
        "sl": sl,
        "comment": str(comment)[:31], 
        "type_time": mt5.ORDER_TIME_GTC
    }
    if not is_pending: req["type_filling"] = mt5.ORDER_FILLING_IOC
        
    res = mt5.order_send(req)
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        tipo_msg = "PENDENTE" if is_pending else "A MERCADO"
        log(f"✅ ORDEM {tipo_msg} EXECUTADA | Ticket: {res.order} | {SYMBOL}: {volume}L @ {price} | Motivo: {comment}")
        return res.order
    return None

def get_session_status(settings):
    now = datetime.now()
    if settings.get("PAUSE_ON_WEEKENDS", True) and now.weekday() >= 5: return "WEEKEND"
    h = now.hour
    start = settings.get("START_HOUR", 7)
    end = settings.get("END_HOUR", 20)
    if start < end: is_day = start <= h < end
    else: is_day = h >= start or h < end
    return "DAY" if is_day else "NIGHT"

def main():
    log("🧠 BERSERKER V40.10 EURUSD (HFT Sweep Mode + Parcial Inteligente) ATIVO...")
    boot_mt5()
    ultimo_pedido_api = 0

    while True:
        try:
            settings = load_settings()
            positions = mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)
            pending_orders = mt5.orders_get(symbol=SYMBOL, magic=MAGIC_NUMBER) 
            agora = time.time()
            now_dt = datetime.now()
            session_status = get_session_status(settings)

            if session_status == "WEEKEND":
                log("💤 Fim de semana. A aguardar abertura do mercado.")
                time.sleep(3600); continue

            proximas_noticias = get_upcoming_news(settings.get("NEWS_FILTER_MINUTES", 20))
            is_news_lockdown = any(abs(n['minutos_para_evento']) <= settings.get("NEWS_FILTER_MINUTES", 20) for n in proximas_noticias)
            if is_news_lockdown:
                log(f"🚨 LOCKDOWN FUNDAMENTAL: Notícia iminente. Congelamento tático ativo.")
                time.sleep(60); continue

            # ====================================================================
            # 🛡️ GESTÃO ESTRUTURAL DA ORDEM: Soft SL & Micro-Parcial Inteligente
            # ====================================================================
            if positions and os.path.exists(SOFT_SL_FILE):
                try:
                    with open(SOFT_SL_FILE, 'r') as f: 
                        soft_sl_data = json.load(f)
                        
                    rates_sl = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 1, 1)
                    if rates_sl and len(rates_sl) > 0:
                        last_close = rates_sl[0]['close']
                        ponto_zero_hft = soft_sl_data.get("ponto_zero", 0.0) # Isto agora é o Wick do Sweep
                        dir_trade = soft_sl_data.get("direcao", "")
                        partial_taken = soft_sl_data.get("partial_taken", False)
                        
                        symbol_info = mt5.symbol_info(SYMBOL)
                        point = symbol_info.point if symbol_info else 0.00001
                        volume_min = symbol_info.volume_min if symbol_info else 0.01
                        volume_step = symbol_info.volume_step if symbol_info else 0.01
                        
                        for p in positions:
                            if p.ticket == soft_sl_data.get("ticket"):
                                # 1. VERIFICAR O SOFT SL
                                if dir_trade == "BULL" and last_close < ponto_zero_hft:
                                    log(f"☠️ [SOFT SL] HFT Sweep Falhou! Vela M1 fechou abaixo do wick ({last_close:.5f} < {ponto_zero_hft:.5f}). Abortar!")
                                    mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume, "type": mt5.ORDER_TYPE_SELL, "position": p.ticket})
                                    os.remove(SOFT_SL_FILE) 
                                    continue
                                
                                elif dir_trade == "BEAR" and last_close > ponto_zero_hft:
                                    log(f"☠️ [SOFT SL] HFT Sweep Falhou! Vela M1 fechou acima do wick ({last_close:.5f} > {ponto_zero_hft:.5f}). Abortar!")
                                    mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume, "type": mt5.ORDER_TYPE_BUY, "position": p.ticket})
                                    os.remove(SOFT_SL_FILE)
                                    continue

                                # 2. VERIFICAR O MICRO-PARCIAL INTELIGENTE
                                if not partial_taken:
                                    lucro_pontos = 0
                                    if dir_trade == "BULL": lucro_pontos = (last_close - p.price_open) / point
                                    elif dir_trade == "BEAR": lucro_pontos = (p.price_open - last_close) / point
                                    
                                    partial_points = settings.get("PARTIAL_PROFIT_POINTS", 40)
                                    if lucro_pontos >= partial_points:
                                        pct_close = settings.get("PARTIAL_CLOSE_PERCENT", 50.0) / 100.0
                                        vol_fechar_raw = p.volume * pct_close
                                        
                                        vol_fechar = round(vol_fechar_raw / volume_step) * volume_step
                                        
                                        if vol_fechar < volume_min or (p.volume - vol_fechar) < volume_min:
                                            vol_fechar = p.volume
                                        
                                        tipo_fecho = mt5.ORDER_TYPE_SELL if dir_trade == "BULL" else mt5.ORDER_TYPE_BUY
                                        preco_fecho = mt5.symbol_info_tick(SYMBOL).bid if dir_trade == "BULL" else mt5.symbol_info_tick(SYMBOL).ask
                                        
                                        req_parcial = {
                                            "action": mt5.TRADE_ACTION_DEAL,
                                            "symbol": SYMBOL,
                                            "volume": float(round(vol_fechar, 2)),
                                            "type": tipo_fecho,
                                            "position": p.ticket,
                                            "price": preco_fecho,
                                            "magic": MAGIC_NUMBER,
                                            "comment": "MICRO_PARCIAL",
                                            "type_time": mt5.ORDER_TIME_GTC,
                                            "type_filling": mt5.ORDER_FILLING_IOC,
                                        }
                                        res_parcial = mt5.order_send(req_parcial)
                                        
                                        if res_parcial and res_parcial.retcode == mt5.TRADE_RETCODE_DONE:
                                            if vol_fechar == p.volume:
                                                log(f"💰 [LUCRO ESCALA] +{lucro_pontos:.1f} pts! Ordem TOTAL fechada ({vol_fechar}L).")
                                            else:
                                                log(f"💰 [LUCRO ESCALA] +{lucro_pontos:.1f} pts! {vol_fechar}L fechados. Dinheiro garantido.")
                                                if settings.get("MOVE_TO_BREAKEVEN", True):
                                                    req_be = {
                                                        "action": mt5.TRADE_ACTION_SLTP,
                                                        "position": p.ticket,
                                                        "sl": p.price_open,
                                                        "tp": p.tp 
                                                    }
                                                    mt5.order_send(req_be)
                                                    log(f"🛡️ [BREAKEVEN] Stop Loss movido para: {p.price_open:.5f} (Risco Zero).")
                                            
                                            soft_sl_data["partial_taken"] = True
                                            with open(SOFT_SL_FILE, 'w') as f: json.dump(soft_sl_data, f)
                except Exception as e:
                    pass

            if not positions and os.path.exists(SOFT_SL_FILE):
                try: os.remove(SOFT_SL_FILE)
                except: pass

            # ====================================================================
            # 👁️ VIGILÂNCIA CONTÍNUA DO FANTASMA (A cada 10 seg)
            # ====================================================================
            estado_mem = {"fase": "INATIVA"}
            if os.path.exists(ELLIOTT_MEMORY_FILE):
                try:
                    with open(ELLIOTT_MEMORY_FILE, 'r') as f: 
                        loaded = json.load(f)
                        if isinstance(loaded, dict): estado_mem = loaded
                except: pass

            if estado_mem.get("fase") == "ATIVA":
                dir_mem = estado_mem.get("direcao", "BULL")
                
                catastrophic_sl_points = settings.get("CATASTROPHIC_SL_POINTS", 1000)
                max_sweep = settings.get("MAX_SWEEP_POINTS", 50)
                
                acao_furtiva, entrada_m1, tp_m1, sl_estrutural = calcular_sniper_m1_stealth(SYMBOL, dir_mem, max_sweep_points=max_sweep)
                
                symbol_info = mt5.symbol_info(SYMBOL)
                point = symbol_info.point if symbol_info else 0.00001
                sl_catastrophic_real = catastrophic_sl_points * point
                
                if acao_furtiva == "ATACAR_MERCADO_BULL" and not positions:
                    sl_fisico = sl_estrutural - sl_catastrophic_real
                    log(f"⚡ [SWEEP DETETADO] Compra HFT Executada! (Soft SL no Wick: {sl_estrutural:.5f})")
                    ticket = open_order(mt5.ORDER_TYPE_BUY, calculate_dynamic_lot(settings), comment="AI_HFT_SWEEP", tp=tp_m1, sl=sl_fisico)
                    
                    if ticket:
                        with open(SOFT_SL_FILE, "w") as f:
                            json.dump({"ticket": ticket, "ponto_zero": sl_estrutural, "direcao": "BULL", "partial_taken": False}, f)
                            
                elif acao_furtiva == "ATACAR_MERCADO_BEAR" and not positions:
                    sl_fisico = sl_estrutural + sl_catastrophic_real
                    log(f"⚡ [SWEEP DETETADO] Venda HFT Executada! (Soft SL no Wick: {sl_estrutural:.5f})")
                    ticket = open_order(mt5.ORDER_TYPE_SELL, calculate_dynamic_lot(settings), comment="AI_HFT_SWEEP", tp=tp_m1, sl=sl_fisico)
                    
                    if ticket:
                        with open(SOFT_SL_FILE, "w") as f:
                            json.dump({"ticket": ticket, "ponto_zero": sl_estrutural, "direcao": "BEAR", "partial_taken": False}, f)

            # ====================================================================
            # 🧠 ORÁCULO H1 (De 15 em 15 minutos)
            # ====================================================================
            deve_chamar_ia = False
            if session_status == "DAY":
                intervalo = settings.get("SEARCH_INTERVAL_MINUTES", 15) * 60
                if (agora - ultimo_pedido_api) > intervalo: deve_chamar_ia = True
            elif session_status == "NIGHT":
                if now_dt.hour == 3 and (agora - ultimo_pedido_api) > 3600: deve_chamar_ia = True

            if deve_chamar_ia:
                sinal, mot, mult, tp, sl, preco_entrada = consultar_oraculo_multimodal(
                    settings, posicoes_abertas=positions, ordens_pendentes=pending_orders, session_status=session_status
                )
                ultimo_pedido_api = agora
                
                if session_status == "NIGHT" and sinal in ["COMPRA", "VENDA"]:
                    sinal = "AGUARDAR"

                if sinal in ["COMPRA_LIMIT", "VENDA_LIMIT"]:
                    dir_m1 = "BULL" if sinal == "COMPRA_LIMIT" else "BEAR"
                    log(f"🔎 Oráculo: {dir_m1}. A armar emboscada HFT p/ Varredura de Liquidez (Turtle Soup)...")
                    calcular_sniper_m1_stealth(SYMBOL, dir_m1)
                    sinal = "CANCELAR_PENDENTES"

                lote_execucao = calculate_dynamic_lot(settings, mult)
                
                if not positions and not pending_orders:
                    if sinal in ["COMPRA", "VENDA"]:
                        open_order(mt5.ORDER_TYPE_BUY if sinal=="COMPRA" else mt5.ORDER_TYPE_SELL, 
                                   lote_execucao, comment=f"AI_ORACLE:{mot[:10]}", tp=tp, sl=sl)
                
                elif sinal in ["FECHAR_TUDO", "CANCELAR_PENDENTES"]:
                    if pending_orders:
                        for o_pendente in pending_orders:
                            mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o_pendente.ticket})
                    if positions and sinal == "FECHAR_TUDO":
                        for p in positions:
                            mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": p.volume, "type": 1 if p.type==0 else 0, "position": p.ticket})

            time.sleep(10)
        except Exception as e:
            log(f"Erro no ciclo principal: {e}"); time.sleep(10)

if __name__ == "__main__":
    main()