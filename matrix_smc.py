import MetaTrader5 as mt5
import pandas as pd
import time
import json
import requests
import os
import io
import base64
import mplfinance as mpf
from datetime import datetime
from google import genai
from google.genai import types
from PIL import Image

# ==========================================
# 📐 CONFIGURAÇÕES DE TESTE E SMC (DIA)
# ==========================================
SYMBOL = "EURUSD.r" 
FIBO_RATIO = 1.618
CORPO_MINIMO_PARA_USAR_WICK = 0.60  
FICHEIRO_JSON = "fibo_data.json" 

# --- CONFIGURAÇÃO TELEGRAM E IA ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- FILTROS INSTITUCIONAIS ---
MIN_GAP_POINTS = 30  

# Lista de Timeframes
TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1
}

# Controle de Frequência da IA (em segundos)
INTERVALOS_IA = {
    "M1": 15 * 60,           # 15 minutos
    "M5": 60 * 60,           # 1 hora
    "M15": 60 * 60,          # 1 hora
    "M30": 60 * 60,          # 1 hora
    "H1": 60 * 60,           # 1 hora
    "H4": 4 * 60 * 60,       # 4 horas
    "D1": 24 * 60 * 60,      # 1 dia
    "W1": 7 * 24 * 60 * 60,  # 1 semana
    "MN1": 30 * 24 * 60 * 60 # 1 mês (aprox)
}

# =============================================================================
# 🧠 ORÁCULO DE EXTRAÇÃO VISUAL (GEMINI 3.1 PRO)
# =============================================================================
def analisar_swings_gemini(tf_name, img_b64):
    """Envia o gráfico gerado para a IA e extrai Swings visuais e Resumo."""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        img_bytes = base64.b64decode(img_b64)
        pil_image = Image.open(io.BytesIO(img_bytes))

        prompt = f"""
        És um analista Quant e mestre em Ondas de Elliott. Analisa este gráfico de {SYMBOL} no timeframe {tf_name}.
        Ignora o ruído das velas individuais e foca-te na estrutura macro visual.
        Retorna APENAS um JSON válido identificando os últimos grandes topos e fundos e um resumo do Price Action / Elliott.
        Exemplo do formato exigido:
        {{
            "swings_visuais": [
                {{"tipo": "H", "preco": 1.16100}},
                {{"tipo": "L", "preco": 1.15500}}
            ],
            "resumo_visual": "O mercado fez uma Onda 3 forte e está a retrair na Onda 4 usando a EMA55 como suporte."
        }}
        """
        response = client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=[pil_image, prompt],
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")
        )
        res = json.loads(response.text)
        return res.get("swings_visuais", []), res.get("resumo_visual", "Análise não disponível.")
    except Exception as e:
        print(f"⚠️ Erro IA ao extrair dados no {tf_name}: {e}")
        return [], "Erro na análise IA."

# =============================================================================
# 👁️ APEX VISION - MÓDULO DE GERAÇÃO DE IMAGEM OHLC (TODOS OS TFs)
# =============================================================================
def gerar_imagem_grafico_base64(symbol, tf_code, tf_name):
    if tf_name in ["M1", "M5"]: num_velas_visiveis = 200
    elif tf_name in ["M15", "M30", "H1"]: num_velas_visiveis = 150
    elif tf_name in ["H4", "D1"]: num_velas_visiveis = 120
    else: num_velas_visiveis = 100

    rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, num_velas_visiveis + 200)
    if rates is None or len(rates) < 50: return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'tick_volume']].rename(
        columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'}
    )

    df['EMA21'] = df['Close'].ewm(span=21).mean()
    df['EMA55'] = df['Close'].ewm(span=55).mean()
    df['SMA100'] = df['Close'].rolling(100).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    
    df_visivel = df.iloc[-num_velas_visiveis:]
    buffer = io.BytesIO()
    
    apds = [
        mpf.make_addplot(df_visivel['EMA21'], color='lime', width=1.2),
        mpf.make_addplot(df_visivel['EMA55'], color='red', width=1.2),
        mpf.make_addplot(df_visivel['SMA100'], color='dodgerblue', width=1.2),
        mpf.make_addplot(df_visivel['SMA200'], color='darkorange', width=1.2)
    ]
    
    titulo = f'APEX VISION - {symbol} ({tf_name} Elliott View)\nLEGENDA: EMA21(Verde) | EMA55(Vermelho) | SMA100(Azul) | SMA200(Laranja)'

    try:
        mpf.plot(df_visivel, type='candle', style='nightclouds', 
                 addplot=apds,
                 title=titulo,
                 ylabel='Preço',
                 volume=True, ylabel_lower='Vol',
                 datetime_format='%d/%m %H:%M',
                 savefig=dict(fname=buffer, bbox_inches='tight', pad_inches=0.2), 
                 figscale=1.2, 
                 closefig=True 
        )
        
        buffer.seek(0)
        image_bytes = buffer.read()
        buffer.close()
        return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        print(f"⚠️ Erro ao gerar imagem Apex Vision para {tf_name}: {e}")
        return None

# =============================================================================
# 🔗 INTEGRAÇÃO DE CORRELAÇÃO MACRO E HEATMAP DE LIQUIDEZ
# =============================================================================
def carregar_correlacao_macro():
    terminal_info = mt5.terminal_info()
    if terminal_info is None: return {}
    caminho_common = os.path.join(terminal_info.commondata_path, "Files", "correlation_matrix.json")
    if os.path.exists(caminho_common):
        try:
            with open(caminho_common, 'r', encoding='utf-8') as f:
                matriz = json.load(f)
                return matriz.get(SYMBOL, {})
        except:
            return {}
    return {}

def formatar_top_correlacoes(correlacoes_dict):
    if not correlacoes_dict: return "S/ Dados Macro"
    lista = {k: v for k, v in correlacoes_dict.items() if k != SYMBOL}
    if not lista: return "S/ Pares Extra"
    sorted_corr = sorted(lista.items(), key=lambda item: abs(item[1]), reverse=True)
    resumo = " | ".join([f"{k}: {v:+.2f}" for k, v in sorted_corr[:3]])
    return resumo

def mapear_liquidez_heatmap(symbol):
    """Lê o Livro de Ofertas (DOM) do MT5 e devolve os maiores blocos de ordens institucionais."""
    if not mt5.market_book_add(symbol):
        return {"status": "indisponivel", "motivo": "A corretora não fornece dados Level 2 (DOM) para este ativo."}

    book = mt5.market_book_get(symbol)
    if not book:
        mt5.market_book_release(symbol)
        return {"status": "indisponivel", "motivo": "DOM está vazio neste momento."}

    asks = [] # Resistências / Muralhas de Venda
    bids = [] # Suportes / Colchões de Compra

    for item in book:
        if item.type == mt5.BOOK_TYPE_SELL:
            asks.append({'preco': item.price, 'volume': item.volume})
        elif item.type == mt5.BOOK_TYPE_BUY:
            bids.append({'preco': item.price, 'volume': item.volume})

    # Ordenar por volume (maiores blocos primeiro) e guardar o Top 3
    top_asks = sorted(asks, key=lambda x: x['volume'], reverse=True)[:3]
    top_bids = sorted(bids, key=lambda x: x['volume'], reverse=True)[:3]

    mt5.market_book_release(symbol)

    return {
        "status": "ativo",
        "muralhas_de_venda_topo": top_asks,
        "colchoes_de_compra_fundo": top_bids
    }

# =============================================================================
# 📟 FUNÇÕES DE ANÁLISE SMC
# =============================================================================
def conectar_mt5():
    # Forçar a ligação EXCLUSIVA à FPMarkets
    mt5_path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"
    if not mt5.initialize(path=mt5_path):
        print(f"❌ Erro ao iniciar MT5 da FPMarkets. Detalhe: {mt5.last_error()}")
        quit()

# -----------------------------------------------------------------------------
def extrair_historico_swings(df, limite):
    swings_crus = []
    for i in range(len(df)):
        c_open, c_high, c_low, c_close, c_time = df.iloc[i][['open', 'high', 'low', 'close', 'time']]
        if c_high == c_low: continue 
        if c_close >= c_open:
            swings_crus.append({'idx': i, 'type': 'L', 'price': c_low, 'time': c_time})
            swings_crus.append({'idx': i+0.5, 'type': 'H', 'price': c_close, 'time': c_time})
        else:
            swings_crus.append({'idx': i, 'type': 'H', 'price': c_high, 'time': c_time})
            swings_crus.append({'idx': i+0.5, 'type': 'L', 'price': c_close, 'time': c_time})

    swings_limpos = []
    for p in swings_crus:
        if not swings_limpos: swings_limpos.append(p)
        else:
            ultimo = swings_limpos[-1]
            if p['type'] == ultimo['type']:
                if (p['type'] == 'H' and p['price'] > ultimo['price']) or (p['type'] == 'L' and p['price'] < ultimo['price']):
                    swings_limpos[-1] = p
            else: swings_limpos.append(p)

    swings_finais = swings_limpos[-limite:]
    swing_high = next((p['price'] for p in reversed(swings_finais) if p['type'] == 'H'), None)
    swing_low = next((p['price'] for p in reversed(swings_finais) if p['type'] == 'L'), None)
    last_high_idx = next((p['idx'] for p in reversed(swings_finais) if p['type'] == 'H'), -1)
    last_low_idx = next((p['idx'] for p in reversed(swings_finais) if p['type'] == 'L'), -1)

    amplitude = (swing_high - swing_low) if (swing_high and swing_low) else 0
    direcao = "🔴 VENDA" if last_high_idx > last_low_idx else "🟢 COMPRA"

    historico_json = []
    for i, p in enumerate(swings_finais):
        ext_1618 = 0.0
        if i > 0:
            prev_p = swings_finais[i-1]
            amp_swing = abs(prev_p['price'] - p['price'])
            if p['type'] == 'H': 
                ext_1618 = p['price'] - (amp_swing * FIBO_RATIO)
                if df['low'].iloc[int(p['idx']):].min() <= ext_1618: ext_1618 = 0.0
            else: 
                ext_1618 = p['price'] + (amp_swing * FIBO_RATIO)
                if df['high'].iloc[int(p['idx']):].max() >= ext_1618: ext_1618 = 0.0
        
        historico_json.append({"tipo": p['type'], "preco": round(p['price'], 5), "data": pd.to_datetime(p['time'], unit='s').strftime('%Y-%m-%d %H:%M'), "extensao_1618_invertida": round(ext_1618, 5)})

    str_display = ("... " if len(swings_finais) > 3 else "") + " ➔ ".join([f"{p['price']:.5f}{p['type']}" for p in swings_finais[-3:]])
    
    lucas_time_dict = {"candles_restantes": "N/A", "racio_ativo": 0.0}
    h_swings = [p for p in swings_finais if p['type'] == 'H']
    l_swings = [p for p in swings_finais if p['type'] == 'L']
    
    if len(swings_finais) >= 2 and h_swings and l_swings:
        max_h = max(h_swings, key=lambda x: x['price'])
        min_l = min(l_swings, key=lambda x: x['price'])
        idx_start = min(int(max_h['idx']), int(min_l['idx']))
        idx_end = max(int(max_h['idx']), int(min_l['idx']))
        duracao = max(1, idx_end - idx_start)
        idx_atual = len(df) - 1
        
        # Substituição de Fibo por Lucas Sequence Multipliers
        for ratio in [1, 3, 4, 7, 11, 18, 29, 47, 76, 123, 199]:
            velas_restantes = (idx_end + int(duracao * ratio)) - idx_atual
            if velas_restantes > 0:
                lucas_time_dict = {"candles_restantes": velas_restantes, "racio_ativo": ratio}; break
        if lucas_time_dict["candles_restantes"] == "N/A": lucas_time_dict["candles_restantes"] = "Excedeu"

    return swing_high, swing_low, amplitude, direcao, historico_json, str_display, lucas_time_dict

def analisar_psicologia_pa(df):
    if len(df) < 30: return "Sem Histórico"
    recentes = df.iloc[-6:-1]; historico = df.iloc[-26:-6]
    avg_vol = historico['tick_volume'].mean() or 1
    max_vol_candle = recentes.loc[recentes['tick_volume'].idxmax()]
    vol_ratio = max_vol_candle['tick_volume'] / avg_vol
    rng = max(0.00001, max_vol_candle['high'] - max_vol_candle['low'])
    upper_wick = max_vol_candle['high'] - max(max_vol_candle['open'], max_vol_candle['close'])
    lower_wick = min(max_vol_candle['open'], max_vol_candle['close']) - max_vol_candle['low']
    body = abs(max_vol_candle['close'] - max_vol_candle['open'])
    
    if vol_ratio > 1.8:
        if (upper_wick / rng) > 0.5: return "🛑 Stop Hunt Topo"
        if (lower_wick / rng) > 0.5: return "🛑 Stop Hunt Fundo"
        if (body / rng) > 0.7: return "🚀 Inst. Deslocamento (Bull)" if max_vol_candle['close'] > max_vol_candle['open'] else "🚀 Inst. Deslocamento (Bear)"
        return "⚖️ Acumulação Institucional"
    return "📉 Exaustão Retalho (Vácuo)" if vol_ratio < 0.6 else "⏳ Fluxo Normal"

def encontrar_fvg_nao_mitigado(df):
    maior_gap, maior_tam = "Nenhum", 0.0
    min_gap_size = MIN_GAP_POINTS * mt5.symbol_info(SYMBOL).point
    for i in range(1, len(df)-1):
        c_an, c_ant = df.iloc[i], df.iloc[i-1]
        if (abs(c_an['close'] - c_an['open']) / (c_an['high'] - c_an['low'] or 1)) < 0.40: continue
        if c_an['close'] > c_ant['close']:
            fvg_bot, mitigado, lowest = c_ant['close'], False, df.iloc[i:]['low'].min()
            if lowest > fvg_bot:
                tam = lowest - fvg_bot
                if tam >= min_gap_size and tam > maior_tam:
                    maior_tam = tam; maior_gap = f"⬆️ {fvg_bot:.5f}-{lowest:.5f}"
        elif c_an['close'] < c_ant['close']:
            fvg_top, mitigado, highest = c_ant['close'], False, df.iloc[i:]['high'].max()
            if highest < fvg_top:
                tam = fvg_top - highest
                if tam >= min_gap_size and tam > maior_tam:
                    maior_tam = tam; maior_gap = f"⬇️ {highest:.5f}-{fvg_top:.5f}"
    return maior_gap

def calcular_pivots_fibo(df):
    h, l, c = df.iloc[-2][['high', 'low', 'close']]
    pp = (h + l + c) / 3.0
    r_hl = h - l
    return {"PP": round(pp, 5), "R1": round(pp + r_hl*0.382, 5), "R2": round(pp + r_hl*0.618, 5), "R3": round(pp + r_hl, 5),
            "S1": round(pp - r_hl*0.382, 5), "S2": round(pp - r_hl*0.618, 5), "S3": round(pp - r_hl, 5)}

def identificar_barreira_pivot_proxima(current_price, pivots):
    niveis = sorted(pivots.items(), key=lambda x: abs(current_price - x[1]))
    nome, valor = niveis[0]
    tipo = "Centro" if nome == "PP" else ("Resistência" if current_price < valor else "Suporte")
    return f"{nome} ({valor:.5f}) - {tipo}"

def calcular_fibo():
    correlacao_raw = carregar_correlacao_macro()
    top_correlacao_str = formatar_top_correlacoes(correlacao_raw)
    
    agora_dt = datetime.now()
    agora_ts = time.time()
    wd = agora_dt.weekday() # 0=Seg, ..., 4=Sex, 5=Sáb, 6=Dom
    h = agora_dt.hour
    
    # Lógica de bloqueio: Sexta a partir das 22h até Domingo às 21h59
    pausa_fim_semana = False
    if (wd == 4 and h >= 22) or (wd == 5) or (wd == 6 and h < 22):
        pausa_fim_semana = True

    # 🛡️ DESFIBRILHADOR DE CONEXÃO: Garante que o ativo está acordado no Market Watch!
    if not mt5.symbol_select(SYMBOL, True):
        print(f"⚠️ ERRO DE CONEXÃO: Não foi possível selecionar {SYMBOL}. A tentar religar ao MT5...")
        return # Sai deste ciclo e tenta no próximo

    # 🛡️ PROTEÇÃO DE MEMÓRIA (RETRY DE LEITURA DO JSON)
    dados_antigos = {}
    if os.path.exists(FICHEIRO_JSON):
        leitura_ok = False
        for _ in range(10): # Tenta ler durante 5 segundos
            try:
                with open(FICHEIRO_JSON, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    if conteudo.strip(): # Garante que não lê ficheiro vazio a meio da escrita
                        dados_antigos = json.loads(conteudo)
                        leitura_ok = True
                        break
            except Exception:
                time.sleep(0.5) # Ficheiro bloqueado pelo Berserker, espera e tenta de novo
        
        if not leitura_ok:
            print("⚠️ ERRO CRÍTICO: Ficheiro JSON bloqueado pelo Berserker. Abortando ciclo para evitar Amnésia de Tokens.")
            return # Sai imediatamente para não corromper o histórico

    print(f"\n{'='*285}")
    print(f" 🔍 ANÁLISE SMC + PIVOTS + LUCAS TIME + CORRELAÇÃO - {SYMBOL}")
    print(f" 🕒 {agora_dt.strftime('%H:%M:%S')} | 🔗 TOP CORRELAÇÕES (8Y): {top_correlacao_str}")
    print(f"{'='*285}")
    
    header = f"{'TF':<4} | {'TENDÊNCIA':<10} | {'PREÇO ATUAL':<12} | {'PATH':<28} | {'ALVO 1.618':<12} | {'MACRO':<14} | {'BARREIRA PIVOT':<28} | {'LUCAS TIME':<16} | {'PRICE ACTION':<28}"
    print(header)
    print("-" * 285)

    dados_json = {}
    
    # --- 🔥 MANTER O BLOCO APEX_VISION ANTIGO PARA NÃO APAGAR A MEMÓRIA DA IA 🔥 ---
    dados_json["apex_vision"] = dados_antigos.get("apex_vision", {}) 
    dados_json["correlacao_macro_8y"] = correlacao_raw 
    
    # --- 🗺️ EXTRAIR O HEATMAP DE LIQUIDEZ ---
    print("🗺️ A extrair HeatMap de Liquidez (Livro de Ofertas)...")
    dados_json["heatmap_liquidez"] = mapear_liquidez_heatmap(SYMBOL)
    
    print("👁️ APEX VISION: A processar gráficos e sincronizar chamadas IA...")

    for tf_name, tf_code in TIMEFRAMES.items():
        rates = mt5.copy_rates_from_pos(SYMBOL, tf_code, 0, 500)
        
        # 🛡️ SE AS VELAS FALHAREM (Ex: Fim de semana ou quebra de net), CONTINUA SEM CORROMPER
        if rates is None or len(rates) < 50: 
            print(f"⚠️ {tf_name}: Servidor não devolveu velas suficientes. A ignorar TF temporariamente.")
            continue
            
        df = pd.DataFrame(rates)
        
        df['sma_100'], df['sma_200'] = df['close'].rolling(100).mean(), df['close'].rolling(200).mean()
        df['ema_21'], df['ema_55'] = df['close'].ewm(span=21).mean(), df['close'].ewm(span=55).mean()
        
        # 🛡️ PROTEÇÃO ANTI-CRASH DO TICK: Evita o erro fatal "NoneType has no attribute ask"
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            print(f"⚠️ {tf_name}: Servidor cortou o Tick de Preço Atual. Usar o fecho da última vela M1 como recurso.")
            current_price = df['close'].iloc[-1]
        else:
            current_price = tick.ask

        swing_high, swing_low, amplitude, direction, hist_json, str_swings, lucas_time = extrair_historico_swings(df, 50)
        
        target = (swing_high + (amplitude * 0.618)) if direction == "🟢 COMPRA" else (swing_low - (amplitude * 0.618))
        pivots = calcular_pivots_fibo(df)
        barreira = identificar_barreira_pivot_proxima(current_price, pivots)
        
        bias = "ALTA" if current_price > df['sma_200'].iloc[-1] else "BAIXA"
        zona = "(ZONA)" if min(df['ema_21'].iloc[-1], df['ema_55'].iloc[-1]) <= current_price <= max(df['ema_21'].iloc[-1], df['ema_55'].iloc[-1]) else ""
        pa = analisar_psicologia_pa(df)
        
        # --- GERAÇÃO DA IMAGEM PARA ESTE TIMEFRAME ---
        img_b64 = gerar_imagem_grafico_base64(SYMBOL, tf_code, tf_name)

        # --- SINCRONIZAÇÃO E EXTRAÇÃO IA ---
        tf_antigo = dados_antigos.get(tf_name, {})
        ultima_chamada_ts = tf_antigo.get("ultima_chamada_ia_ts", 0)
        intervalo_necessario = INTERVALOS_IA.get(tf_name, 3600)
        
        swings_ia = tf_antigo.get("swings_ia", [])
        resumo_ia = tf_antigo.get("resumo_ia", "A aguardar o primeiro ciclo da IA...")
        data_analise_ia = tf_antigo.get("ultima_analise_ia", "Nunca")

        # Verifica o relógio E o Escudo de Fim de Semana
        if img_b64 and (agora_ts - ultima_chamada_ts) >= intervalo_necessario:
            if pausa_fim_semana:
                print(f"   💤 Pausa Fim de Semana: Chamada IA cancelada para {tf_name}.")
            else:
                # 🛑 BLOQUEIO DE TOKENS: Só envia para a IA se for D1, W1 ou MN1
                if tf_name in ["D1", "W1", "MN1"]:
                    print(f"   🤖 Consultando Gemini 3.1 Pro para leitura visual do {tf_name}...")
                    novos_swings, novo_resumo = analisar_swings_gemini(tf_name, img_b64)
                    if novo_resumo != "Erro na análise IA.":
                        swings_ia = novos_swings
                        resumo_ia = novo_resumo
                        ultima_chamada_ts = agora_ts
                        data_analise_ia = agora_dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        print(f"   ⏳ A arrefecer a API por 4 segundos para evitar bloqueios...")
                        time.sleep(4)
                else:
                    resumo_ia = "IA Desativada neste TF para poupar tokens."
                    swings_ia = []
                    ultima_chamada_ts = agora_ts  # Atualiza o timestamp para evitar spam no loop
                    data_analise_ia = agora_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Constrói o JSON para o TF, mantendo a matemática crua, mas adicionando a visão IA
        dados_json[tf_name] = {
            "tendencia": "COMPRA" if "COMPRA" in direction else "VENDA",
            "preco_atual": round(current_price, 5),
            "alvo_1618": round(target, 5),
            "nivel_critico": round(swing_low if "COMPRA" in direction else swing_high, 5),
            "gap_fvg": encontrar_fvg_nao_mitigado(df),
            "price_action_atual": pa,
            "historico_swings": hist_json,
            "pivots_fibo": pivots,
            "medias_moveis": {"bias_macro": bias, "zona_recarga": bool(zona)},
            "lucas_time": lucas_time,
            "swings_ia": swings_ia,
            "resumo_ia": resumo_ia,
            "ultima_analise_ia": data_analise_ia,
            "ultima_chamada_ia_ts": ultima_chamada_ts 
        }
        
        # Módulo de compatibilidade com o teu Berserker atual:
        if tf_name == "H1":
            dados_json["apex_vision"]["chart_base64"] = img_b64 if img_b64 else "Falha"
            dados_json["apex_vision"]["timeframe"] = "H1"
        
        l_time_str = f"{lucas_time['candles_restantes']}c (x{lucas_time['racio_ativo']})" if isinstance(lucas_time['candles_restantes'], int) else "Expira"
        print(f"{tf_name:<4} | {direction:<10} | {current_price:<12.5f} | {str_swings:<28} | {target:<12.5f} | {bias+' '+zona:<14} | {barreira:<28} | {l_time_str:<16} | {pa[:28]:<28}")

    print("-" * 285)
    print("✅ Processamento concluído. JSON atualizado com Escrita Atómica.")
    
    # 🛡️ SÓ GRAVA O JSON SE TIVER EXTRAÍDO DADOS COM SUCESSO (Evita limpar o ficheiro por erro)
    if "H1" in dados_json or "M1" in dados_json:
        tmp_file = FICHEIRO_JSON + ".tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f: 
            json.dump(dados_json, f, indent=4)
        os.replace(tmp_file, FICHEIRO_JSON)
        
        terminal = mt5.terminal_info()
        if terminal:
            mt5_path = os.path.join(terminal.data_path, "MQL5", "Files", FICHEIRO_JSON)
            tmp_mt5 = mt5_path + ".tmp"
            with open(tmp_mt5, 'w', encoding='utf-8') as f: 
                json.dump(dados_json, f, indent=4)
            os.replace(tmp_mt5, mt5_path)

if __name__ == "__main__":
    conectar_mt5()
    while True:
        try:
            calcular_fibo()
        except KeyboardInterrupt: 
            break
        except Exception as e:
            # 🛡️ A BARREIRA FINAL: O ciclo de extração nunca morre
            print(f"⚠️ Erro Fatal Inesperado no Ciclo Principal: {e}. A reiniciar extração em 5 min...")
        
        time.sleep(300)