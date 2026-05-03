import React, { useState, useEffect, useRef } from 'react';
import {
    TrendingUp, TrendingDown, Activity, RefreshCw, BarChart2,
    Layers, Clock, Target, AlertCircle, BrainCircuit, Map,
    Wallet, DollarSign, PieChart, ShieldAlert, EyeOff, Eye, List, Newspaper, X, Send, Info, CheckCircle, Calculator, Edit2, Save, Calendar, Database, Shield, Zap
} from 'lucide-react';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';

export default function FinancialMarkets() {
    // --- ESTADOS BASE ---
    const [data, setData] = useState<any>(null);
    const [accountInfo, setAccountInfo] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    // --- ESTADOS DO TERMINAL ---
    const [activeTF, setActiveTF] = useState('H1');
    const [symbol, setSymbol] = useState('EURUSD.r');
    const [showCharts, setShowCharts] = useState(false);
    const [liveChart, setLiveChart] = useState<string | null>(null);
    const [chartLoading, setChartLoading] = useState(false);
    const [ticker, setTicker] = useState({ bid: 0, ask: 0 });
    const [m1Candles, setM1Candles] = useState<any[]>([]);

    // --- ESTADO DA ONDA DE ELLIOTT (APPEX MEMORY) ---
    const [elliottMemory, setElliottMemory] = useState<any>(null);

    // --- ESTADOS DAS ORDENS E TRADING ---
    const [orders, setOrders] = useState<any[]>([]);
    const [closingOrder, setClosingOrder] = useState<number | null>(null);
    const [tradeVolume, setTradeVolume] = useState<number>(0.01);
    const [confirmTrade, setConfirmTrade] = useState<{show: boolean, type: 'BUY'|'SELL'|null, processing: boolean}>({show: false, type: null, processing: false});

    // Edição de TP/SL
    const [editingOrder, setEditingOrder] = useState<number | null>(null);
    const [editTpSl, setEditTpSl] = useState({ tp: 0, sl: 0 });

    // --- ESTADOS DAS NOTÍCIAS E IA ---
    const [newsData, setNewsData] = useState<any>(null);
    const [showNewsEditor, setShowNewsEditor] = useState(false);
    const [newsJsonText, setNewsJsonText] = useState("");

    const [chatHistory, setChatHistory] = useState<{role: 'user'|'ai', content: string}[]>([]);
    const [chatMessage, setChatMessage] = useState('');
    const [isAiTyping, setIsAiTyping] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    const timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1'];
    const availableSymbols = ['EURUSD.r', 'GBPUSD.r', 'USDJPY.r', 'XAUUSD.r', 'US500', 'GER40'];

    useEffect(() => {
        fetchAllData();
        const interval = setInterval(fetchTickerAndOrders, 5000);
        return () => clearInterval(interval);
    }, [symbol]);

    useEffect(() => {
        if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory, isAiTyping]);

    const fetchAllData = async () => {
        setLoading(true);
        try {
            const [marketRes, accountRes, newsRes] = await Promise.all([
                api.get('/markets/data'),
                api.get('/markets/account').catch(() => ({ data: null })),
                api.get(`/markets/news`).catch(() => ({ data: null }))
            ]);
            setData(marketRes.data);
            setAccountInfo(accountRes.data);
            setNewsData(newsRes.data);

            fetchTickerAndOrders();
            if (showCharts) fetchLiveChart(activeTF);
        } catch (error) {
            console.error("Erro ao carregar dados:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchTickerAndOrders = async () => {
        try {
            const [tickerRes, ordersRes, elliottRes, candlesRes] = await Promise.all([
                api.get(`/markets/ticker/${symbol}`),
                api.get('/markets/orders'),
                api.get('/markets/elliott-memory').catch(() => ({ data: null })),
                api.get(`/markets/candles/${symbol}/M1?count=240`).catch(() => ({ data: [] }))
            ]);
            setTicker(tickerRes.data);
            setOrders(ordersRes.data);
            if (elliottRes.data) setElliottMemory(elliottRes.data);
            if (candlesRes.data) setM1Candles(candlesRes.data);
        } catch (error) { console.error(error); }
    };

    const fetchLiveChart = async (tf: string) => {
        setChartLoading(true);
        try {
            const res = await api.get(`/markets/live-chart/${tf}?symbol=${symbol}`);
            setLiveChart(res.data.chart);
        } catch (error) { setLiveChart(null); }
        finally { setChartLoading(false); }
    };

    const handleTFChange = (tf: string) => {
        setActiveTF(tf);
        if (showCharts) fetchLiveChart(tf);
    };

    const toggleCharts = () => {
        const newState = !showCharts;
        setShowCharts(newState);
        if (newState && !liveChart) fetchLiveChart(activeTF);
    };

    // --- FUNÇÕES DE EDIÇÃO DO JSON DE NOTÍCIAS ---
    const handleOpenNewsEditor = () => {
        setNewsJsonText(JSON.stringify(newsData, null, 2));
        setShowNewsEditor(true);
    };

    const handleSaveNews = async () => {
        try {
            const parsedJson = JSON.parse(newsJsonText);
            await api.post('/markets/news/update', parsedJson);
            setNewsData(parsedJson);
            setShowNewsEditor(false);
            alert("Calendário de notícias atualizado com sucesso!");
        } catch (error) {
            alert("Formato JSON inválido ou erro ao guardar. Verifica a sintaxe.");
        }
    };

    // --- FUNÇÕES DE TRADING E ORDENS ---
    const handleCloseOrder = async (ticket: number) => {
        if (!window.confirm(`Tens a certeza que queres FECHAR a ordem #${ticket}?`)) return;
        setClosingOrder(ticket);
        try {
            await api.post(`/markets/orders/${ticket}/close`);
            fetchTickerAndOrders();
            api.get('/markets/account').then(res => setAccountInfo(res.data));
        } catch (error) {
            alert('Erro ao fechar ordem. Verifica a ligação ao MT5.');
        } finally {
            setClosingOrder(null);
        }
    };

    const startEditingOrder = (order: any) => {
        setEditingOrder(order.ticket);
        setEditTpSl({ tp: order.tp || 0, sl: order.sl || 0 });
    };

    const handleSaveTpSl = async (ticket: number) => {
        if (!window.confirm(`Confirmar alteração de TP/SL para a ordem #${ticket}?`)) return;
        try {
            await api.post(`/markets/orders/${ticket}/modify`, {
                tp: editTpSl.tp,
                sl: editTpSl.sl
            });
            setEditingOrder(null);
            fetchTickerAndOrders();
        } catch (error: any) {
            alert(`Erro ao modificar ordem: ${error.response?.data?.detail || 'Desconhecido'}`);
        }
    };

    const handleExecuteTrade = async () => {
        if (!confirmTrade.type) return;
        setConfirmTrade(prev => ({...prev, processing: true}));

        try {
            await api.post('/markets/orders/open', {
                symbol: symbol,
                type: confirmTrade.type,
                volume: tradeVolume
            });
            setConfirmTrade({show: false, type: null, processing: false});
            fetchTickerAndOrders();
            api.get('/markets/account').then(res => setAccountInfo(res.data));
        } catch (error: any) {
            alert(`Erro ao abrir ordem: ${error.response?.data?.detail || 'Desconhecido'}`);
            setConfirmTrade(prev => ({...prev, processing: false}));
        }
    };

    const handleSendChat = async () => {
        if (!chatMessage.trim()) return;
        const newMsg = { role: 'user' as const, content: chatMessage };
        setChatHistory(prev => [...prev, newMsg]);
        setChatMessage('');
        setIsAiTyping(true);

        try {
            const res = await api.post('/markets/chat', { message: newMsg.content, symbol });
            setChatHistory(prev => [...prev, { role: 'ai', content: res.data.reply }]);
        } catch (error) {
            setChatHistory(prev => [...prev, { role: 'ai', content: '❌ Erro de comunicação com o modelo.' }]);
        } finally {
            setIsAiTyping(false);
        }
    };

    const formatMoney = (val: number, currency: string = 'USD') => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency }).format(val);
    };

    if (loading || !data) {
        return (
            <div className="container-fluid h-100 d-flex flex-column align-items-center justify-content-center bg-body-tertiary">
                <div className="spinner-border text-primary mb-3" role="status"></div>
                <h5 className="fw-bold text-muted">A inicializar Terminal e a conectar ao MT5...</h5>
            </div>
        );
    }

    const decision = data.apex_vision?.ultima_decisao_berserker || "AGUARDAR";

    return (
        <div className="container-fluid p-3 p-md-4 bg-body-tertiary min-vh-100 custom-scrollbar overflow-auto dark-terminal">

            {/* --- HEADER TOOLBAR --- */}
            <div className="row g-3 mb-4 align-items-center">
                <div className="col-12 col-xl-4">
                    <h3 className="fw-bold text-body m-0 d-flex align-items-center gap-2">
                        <Activity size={28} className="text-primary"/> Terminal PRISM
                    </h3>
                    <p className="text-muted small m-0 mt-1">Status: Online • {data.apex_vision?.ultima_analise_berserker || "Aguardando sincronização"}</p>
                </div>

                <div className="col-12 col-xl-8 d-flex flex-wrap justify-content-xl-end gap-2 align-items-center">

                    <div className="input-group shadow-sm" style={{width: 'auto'}}>
                        <span className="input-group-text bg-white fw-bold border-secondary-subtle">Ativo</span>
                        <select className="form-select fw-bold text-primary border-secondary-subtle" value={symbol} onChange={e => setSymbol(e.target.value)}>
                            {availableSymbols.map(sym => <option key={sym} value={sym}>{sym}</option>)}
                        </select>
                    </div>

                    <div className="d-flex align-items-center gap-3 bg-white border border-secondary-subtle rounded-3 px-3 py-1 shadow-sm">
                        <div className="d-flex flex-column align-items-end">
                            <span className="small text-muted" style={{fontSize: '0.65rem'}}>BID (Venda)</span>
                            <span className="fw-black text-danger font-monospace lh-1">{ticker.bid > 0 ? ticker.bid.toFixed(5) : '---'}</span>
                        </div>
                        <div className="vr"></div>
                        <div className="d-flex flex-column align-items-start">
                            <span className="small text-muted" style={{fontSize: '0.65rem'}}>ASK (Compra)</span>
                            <span className="fw-black text-success font-monospace lh-1">{ticker.ask > 0 ? ticker.ask.toFixed(5) : '---'}</span>
                        </div>
                    </div>

                    <div className={`px-3 py-1 rounded-3 shadow-sm border d-flex align-items-center gap-2 bg-white`}>
                        <span className="small fw-bold text-muted text-uppercase">Sinal:</span>
                        <span className={`fw-black ${decision === 'COMPRA' ? 'text-success' : decision === 'VENDA' ? 'text-danger' : 'text-warning'}`}>
                            {decision === 'COMPRA' ? <TrendingUp size={18} className="me-1"/> : <TrendingDown size={18} className="me-1"/>}
                            {decision}
                        </span>
                    </div>

                    <button className={`btn fw-bold d-flex align-items-center gap-2 shadow-sm ${showCharts ? 'btn-secondary' : 'btn-primary'}`} onClick={toggleCharts}>
                        {showCharts ? <EyeOff size={16}/> : <Eye size={16}/>} {showCharts ? 'Ocultar Gráficos' : 'Ver Gráficos'}
                    </button>

                    <button className="btn btn-outline-secondary bg-white rounded-3 shadow-sm" onClick={fetchTickerAndOrders} title="Forçar Sincronização">
                        <RefreshCw size={18} className={chartLoading || loading ? "spin-animation" : ""} />
                    </button>
                </div>
            </div>

            {/* --- RESUMO DA CONTA MT5 --- */}
            {accountInfo && (
                <div className="row g-3 mb-4">
                    <div className="col-6 col-md-3">
                        <div className="card border-0 shadow-sm rounded-4 bg-white h-100">
                            <div className="card-body p-3 d-flex align-items-center gap-3">
                                <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary"><Wallet size={20}/></div>
                                <div>
                                    <div className="text-muted small fw-bold text-uppercase" style={{fontSize: '0.65rem'}}>Saldo</div>
                                    <h5 className="fw-black m-0 text-dark">{formatMoney(accountInfo.balance, accountInfo.currency)}</h5>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-6 col-md-3">
                        <div className="card border-0 shadow-sm rounded-4 bg-white h-100">
                            <div className="card-body p-3 d-flex align-items-center gap-3">
                                <div className="bg-info bg-opacity-10 p-2 rounded-3 text-info"><PieChart size={20}/></div>
                                <div>
                                    <div className="text-muted small fw-bold text-uppercase" style={{fontSize: '0.65rem'}}>Equity</div>
                                    <h5 className="fw-black m-0 text-dark">{formatMoney(accountInfo.equity, accountInfo.currency)}</h5>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-6 col-md-3">
                        <div className="card border-0 shadow-sm rounded-4 bg-white h-100">
                            <div className="card-body p-3 d-flex align-items-center gap-3">
                                <div className={`p-2 rounded-3 ${accountInfo.profit >= 0 ? 'bg-success bg-opacity-10 text-success' : 'bg-danger bg-opacity-10 text-danger'}`}><DollarSign size={20}/></div>
                                <div>
                                    <div className="text-muted small fw-bold text-uppercase" style={{fontSize: '0.65rem'}}>Floating</div>
                                    <h5 className={`fw-black m-0 ${accountInfo.profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                        {formatMoney(accountInfo.profit, accountInfo.currency)}
                                    </h5>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-6 col-md-3">
                        <div className="card border-0 shadow-sm rounded-4 bg-white h-100">
                            <div className="card-body p-3 d-flex align-items-center gap-3">
                                <div className={`p-2 rounded-3 ${accountInfo.margin_level > 100 ? 'bg-success bg-opacity-10 text-success' : 'bg-danger bg-opacity-10 text-danger'}`}><ShieldAlert size={20}/></div>
                                <div>
                                    <div className="text-muted small fw-bold text-uppercase" style={{fontSize: '0.65rem'}}>Margem</div>
                                    <h5 className="fw-black m-0 text-dark">{accountInfo.margin_level?.toFixed(2)}%</h5>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div className="row g-4">

                {/* --- COLUNA ESQUERDA: GRÁFICOS E ORDENS --- */}
                <div className="col-12 col-xl-8 d-flex flex-column gap-4">

                    {/* ORÁCULO BERSERKER (MOTIVO E ANÁLISE) SEMPRE VISÍVEL */}
                    {data.apex_vision?.ultimo_motivo_berserker && (
                        <div className="card border-0 shadow-sm rounded-4 border-primary-subtle bg-primary bg-opacity-10">
                            <div className="card-body p-3 d-flex gap-3 align-items-start">
                                <div className="bg-primary text-white p-2 rounded-3 flex-shrink-0 mt-1">
                                    <BrainCircuit size={24} />
                                </div>
                                <div className="flex-grow-1">
                                    <div className="d-flex justify-content-between align-items-center mb-1">
                                        <h6 className="fw-bold text-primary m-0 d-flex align-items-center gap-2">
                                            Oráculo Berserker
                                            <span className={`badge border ${decision === 'COMPRA' ? 'bg-success text-white border-success' : decision === 'VENDA' ? 'bg-danger text-white border-danger' : 'bg-warning text-dark border-warning'}`}>
                                                Sinal: {decision}
                                            </span>
                                        </h6>
                                        <span className="text-muted fw-bold d-flex align-items-center gap-1 bg-white px-2 py-1 rounded-2 shadow-sm" style={{fontSize: '0.65rem'}}>
                                            <Clock size={12}/> {data.apex_vision.ultima_analise_berserker || "Recente"}
                                        </span>
                                    </div>
                                    <p className="small text-dark mb-0 lh-sm fw-medium pt-1">{data.apex_vision.ultimo_motivo_berserker}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {showCharts && (
                        <>
                            {/* APEX VISION */}
                            <div className="card border-0 shadow-sm rounded-4 overflow-hidden">
                                <div className="card-header bg-white border-bottom-0 p-3 d-flex justify-content-between align-items-center">
                                    <h6 className="fw-bold m-0 d-flex align-items-center gap-2 text-primary"><Map size={18}/> Apex Vision {data.apex_vision?.timeframe}</h6>
                                </div>
                                <div className="card-body p-0 bg-dark text-center overflow-hidden">
                                    {data.apex_vision?.chart_base64 && (
                                        <img src={`data:image/png;base64,${data.apex_vision.chart_base64}`} alt="Market Analysis" className="img-fluid w-100 invert-chart" style={{minHeight: '350px', objectFit: 'cover'}}/>
                                    )}
                                </div>
                            </div>

                            {/* SELETOR E LIVE CHART */}
                            <div className="bg-white rounded-4 shadow-sm p-2 d-flex gap-1 border overflow-auto custom-scrollbar">
                                {timeframes.map(tf => (
                                    <button key={tf} onClick={() => handleTFChange(tf)} className={`btn btn-sm px-4 py-2 rounded-pill fw-bold transition-all ${activeTF === tf ? 'btn-primary shadow-sm text-white' : 'btn-light text-muted'}`}>
                                        {tf}
                                    </button>
                                ))}
                            </div>

                            <div className="card border-0 shadow-sm rounded-4 overflow-hidden">
                                <div className="card-header bg-white border-bottom-0 p-3 d-flex justify-content-between align-items-center">
                                    <h6 className="fw-bold m-0 d-flex align-items-center gap-2 text-dark"><Activity size={18} className="text-success"/> Live Chart ({activeTF})</h6>
                                    {chartLoading && <div className="spinner-border spinner-border-sm text-primary"></div>}
                                </div>
                                <div className="card-body p-0 bg-dark d-flex align-items-center justify-content-center overflow-hidden" style={{minHeight: '400px'}}>
                                    {liveChart ? (
                                        <img src={`data:image/png;base64,${liveChart}`} alt="Live Chart" className="img-fluid w-100 invert-chart" />
                                    ) : (
                                        <div className="text-center p-5 text-muted">A carregar velas do MT5...</div>
                                    )}
                                </div>
                            </div>
                        </>
                    )}

                    {/* LISTA DE ORDENS EM ABERTO */}
                    <div className="card border-0 shadow-sm rounded-4 flex-grow-1">
                        <div className="card-header bg-white p-3 border-bottom d-flex justify-content-between align-items-center">
                            <h6 className="fw-bold m-0 d-flex align-items-center gap-2"><List size={18} className="text-primary"/> Posições Abertas</h6>
                            <span className="badge bg-secondary">{orders.length}</span>
                        </div>
                        <div className="card-body p-0 overflow-auto custom-scrollbar" style={{maxHeight: '350px'}}>
                            <table className="table table-hover align-middle m-0 small">
                                <thead className="bg-light sticky-top">
                                <tr>
                                    <th className="border-0 text-muted fw-bold">Ticket</th>
                                    <th className="border-0 text-muted fw-bold">Símbolo</th>
                                    <th className="border-0 text-muted fw-bold">Tipo</th>
                                    <th className="border-0 text-muted fw-bold text-end">Volume</th>
                                    <th className="border-0 text-muted fw-bold text-end">Open</th>
                                    <th className="border-0 text-muted fw-bold text-center">TP / SL</th>
                                    <th className="border-0 text-muted fw-bold text-end">Lucro</th>
                                    <th className="border-0 text-muted fw-bold text-end px-3">Ações</th>
                                </tr>
                                </thead>
                                <tbody>
                                {orders.map(o => (
                                    <tr key={o.ticket}>
                                        <td className="font-monospace text-muted">{o.ticket}</td>
                                        <td className="fw-bold">{o.symbol}</td>
                                        <td>
                                                <span className={`badge ${o.type === 0 ? 'bg-success' : 'bg-danger'} bg-opacity-10 ${o.type === 0 ? 'text-success' : 'text-danger'} border`}>
                                                    {o.type === 0 ? 'BUY' : 'SELL'}
                                                </span>
                                        </td>
                                        <td className="text-end fw-medium">{o.volume}</td>
                                        <td className="text-end font-monospace">{o.price_open.toFixed(5)}</td>

                                        {/* COLUNA DE EDIÇÃO DE TP / SL */}
                                        <td className="text-center">
                                            {editingOrder === o.ticket ? (
                                                <div className="d-flex flex-column gap-1 align-items-center justify-content-center">
                                                    <div className="input-group input-group-sm" style={{width: '120px'}}>
                                                        <span className="input-group-text p-1 px-2" style={{fontSize: '0.65rem'}}>TP</span>
                                                        <input type="number" step="0.00001" className="form-control form-control-sm text-end p-1 font-monospace" value={editTpSl.tp} onChange={e => setEditTpSl({...editTpSl, tp: Number(e.target.value)})} />
                                                    </div>
                                                    <div className="input-group input-group-sm" style={{width: '120px'}}>
                                                        <span className="input-group-text p-1 px-2" style={{fontSize: '0.65rem'}}>SL</span>
                                                        <input type="number" step="0.00001" className="form-control form-control-sm text-end p-1 font-monospace" value={editTpSl.sl} onChange={e => setEditTpSl({...editTpSl, sl: Number(e.target.value)})} />
                                                    </div>
                                                    <div className="d-flex gap-1 mt-1">
                                                        <button className="btn btn-sm btn-success p-1 py-0" onClick={() => handleSaveTpSl(o.ticket)}><CheckCircle size={14}/></button>
                                                        <button className="btn btn-sm btn-light border p-1 py-0" onClick={() => setEditingOrder(null)}><X size={14}/></button>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="d-flex flex-column align-items-center justify-content-center position-relative group-hover">
                                                    <span className="text-success font-monospace" style={{fontSize: '0.75rem'}}>TP: {o.tp > 0 ? o.tp.toFixed(5) : '---'}</span>
                                                    <span className="text-danger font-monospace" style={{fontSize: '0.75rem'}}>SL: {o.sl > 0 ? o.sl.toFixed(5) : '---'}</span>
                                                    <button className="btn btn-sm btn-light border position-absolute end-0 top-50 translate-middle-y shadow-sm" style={{opacity: 0.8}} onClick={() => startEditingOrder(o)}>
                                                        <Edit2 size={12} />
                                                    </button>
                                                </div>
                                            )}
                                        </td>

                                        <td className={`text-end fw-bold font-monospace ${o.profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                            {formatMoney(o.profit)}
                                        </td>
                                        <td className="text-end px-3">
                                            <button
                                                className="btn btn-sm btn-outline-danger fw-bold py-0"
                                                onClick={() => handleCloseOrder(o.ticket)}
                                                disabled={closingOrder === o.ticket}
                                            >
                                                {closingOrder === o.ticket ? 'A Fechar...' : <><X size={14}/> Fechar</>}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                {orders.length === 0 && (
                                    <tr><td colSpan={8} className="text-center p-4 text-muted">Nenhuma ordem em aberto.</td></tr>
                                )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* CALENDÁRIO ECONÓMICO (NOVO) */}
                    <div className="card border-0 shadow-sm rounded-4">
                        <div className="card-header bg-white p-3 border-bottom d-flex justify-content-between align-items-center">
                            <h6 className="fw-bold m-0 d-flex align-items-center gap-2"><Calendar size={18} className="text-primary"/> Notícias de Alto Impacto ({newsData?.moeda_alvo || 'S/D'})</h6>
                            <button className="btn btn-sm btn-light border shadow-sm d-flex align-items-center gap-1 fw-bold" onClick={handleOpenNewsEditor}>
                                <Edit2 size={14}/> JSON
                            </button>
                        </div>
                        <div className="card-body p-0 overflow-auto custom-scrollbar" style={{maxHeight: '300px'}}>
                            {newsData && newsData.noticias_alto_impacto ? (
                                <table className="table table-hover align-middle m-0 small">
                                    <thead className="bg-light sticky-top">
                                    <tr>
                                        <th className="border-0 text-muted fw-bold">Data</th>
                                        <th className="border-0 text-muted fw-bold">Hora</th>
                                        <th className="border-0 text-muted fw-bold text-center">Faltam</th>
                                        <th className="border-0 text-muted fw-bold w-100">Evento Fundamental</th>
                                    </tr>
                                    </thead>
                                    <tbody>
                                    {newsData.noticias_alto_impacto.map((n: any, idx: number) => {
                                        const eventDate = new Date(`${n.data}T${n.hora}:00`);
                                        const diffMins = isNaN(eventDate.getTime()) ? null : Math.round((eventDate.getTime() - Date.now()) / 60000);

                                        return (
                                            <tr key={idx}>
                                                <td className="fw-bold text-muted">{n.data}</td>
                                                <td className="font-monospace text-primary fw-bold">{n.hora}</td>
                                                <td className="text-center">
                                                    {diffMins === null ? (
                                                        <span className="text-muted">--</span>
                                                    ) : diffMins < 0 ? (
                                                        <span className="badge bg-secondary opacity-50">Passou</span>
                                                    ) : diffMins <= 60 ? (
                                                        <span className="badge bg-danger text-white pulse-warning">{diffMins} min</span>
                                                    ) : (
                                                        <span className="badge bg-primary bg-opacity-10 text-primary border border-primary-subtle">{diffMins} min</span>
                                                    )}
                                                </td>
                                                <td>
                                                    <span className="badge bg-danger bg-opacity-10 text-danger border border-danger-subtle me-2">ALTO</span>
                                                    <span className="fw-medium text-dark">{n.evento}</span>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="text-center p-4 text-muted">Nenhum dado de notícias encontrado.</div>
                            )}
                        </div>
                    </div>
                </div>

                {/* --- COLUNA DIREITA: ESTATÍSTICAS E IA --- */}
                <div className="col-12 col-xl-4 d-flex flex-column gap-4">

                    {/* PAINEL DE QUICK TRADE */}
                    <div className="card border-0 shadow-sm rounded-4 bg-white">
                        <div className="card-header p-3 border-bottom d-flex align-items-center justify-content-between">
                            <h6 className="fw-bold m-0 text-dark d-flex align-items-center gap-2"><Target size={18} className="text-primary"/> Execução Rápida ({symbol})</h6>
                        </div>
                        <div className="card-body p-3">
                            <label className="form-label small fw-bold text-muted">Volume (Lotes)</label>
                            <div className="d-flex gap-2 mb-3">
                                <button className="btn btn-light border fw-bold" onClick={() => setTradeVolume(v => Math.max(0.01, Number((v - 0.01).toFixed(2))))}>-</button>
                                <input type="number" step="0.01" min="0.01" className="form-control text-center fw-bold fs-5 shadow-sm" value={tradeVolume} onChange={(e) => setTradeVolume(Number(e.target.value))} />
                                <button className="btn btn-light border fw-bold" onClick={() => setTradeVolume(v => Number((v + 0.01).toFixed(2)))}>+</button>
                            </div>
                            <div className="d-flex gap-2">
                                <button className="btn btn-danger w-100 fw-bold py-2 shadow-sm d-flex justify-content-center align-items-center gap-2" onClick={() => setConfirmTrade({show: true, type: 'SELL', processing: false})}>
                                    SELL <span className="small opacity-75">{ticker.bid.toFixed(5)}</span>
                                </button>
                                <button className="btn btn-success w-100 fw-bold py-2 shadow-sm d-flex justify-content-center align-items-center gap-2" onClick={() => setConfirmTrade({show: true, type: 'BUY', processing: false})}>
                                    BUY <span className="small opacity-75">{ticker.ask.toFixed(5)}</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* VISUALIZADOR APPEX MEMORY (ELLIOTT WAVE + CALCULADORA + LUCAS) */}
                    <ElliottWaveVisualizer memory={elliottMemory} currentBid={ticker.bid} candles={m1Candles} accountInfo={accountInfo} onApplyLots={setTradeVolume} />

                    {/* ASSISTENTE IA FINANCEIRO */}
                    <div className="card border-0 shadow-sm rounded-4 flex-grow-1 d-flex flex-column" style={{minHeight: '400px'}}>
                        <div className="card-header bg-info bg-opacity-10 p-3 border-info-subtle d-flex align-items-center gap-2">
                            <BrainCircuit size={20} className="text-info"/>
                            <h6 className="text-info-emphasis fw-bold m-0">Assistente Quantitativo</h6>
                        </div>
                        <div className="card-body p-3 overflow-auto custom-scrollbar d-flex flex-column gap-3 bg-body-tertiary">
                            {chatHistory.length === 0 ? (
                                <div className="text-center text-muted small my-auto">
                                    <Activity size={32} className="opacity-25 mb-2 text-info mx-auto"/>
                                    <p>Faz perguntas sobre o {symbol} ou pede análises de contexto macroeconómico.</p>
                                </div>
                            ) : (
                                chatHistory.map((msg, idx) => (
                                    <div key={idx} className={`d-flex flex-column ${msg.role === 'user' ? 'align-items-end' : 'align-items-start'}`}>
                                        <div className={`p-2 px-3 rounded-4 shadow-sm ${msg.role === 'user' ? 'bg-primary text-white' : 'bg-white border border-secondary-subtle'}`} style={{maxWidth: '90%'}}>
                                            {msg.role === 'ai' ? (
                                                <ReactMarkdown className="markdown-content m-0 small">{msg.content}</ReactMarkdown>
                                            ) : (
                                                <span className="fw-medium small">{msg.content}</span>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                            {isAiTyping && (
                                <div className="align-self-start p-2 px-3 rounded-4 bg-white border shadow-sm d-flex gap-2 align-items-center">
                                    <div className="spinner-grow spinner-grow-sm text-info" role="status"></div>
                                    <span className="small text-muted fw-bold fst-italic">A analisar...</span>
                                </div>
                            )}
                            <div ref={chatEndRef} />
                        </div>
                        <div className="card-footer bg-white p-2 border-top">
                            <div className="input-group">
                                <input type="text" className="form-control border-0 shadow-none bg-light rounded-pill px-3" placeholder={`Perguntar sobre ${symbol}...`} value={chatMessage} onChange={e => setChatMessage(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSendChat()} />
                                <button className="btn btn-link text-info" onClick={handleSendChat} disabled={!chatMessage.trim() || isAiTyping}><Send size={20}/></button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* --- ANÁLISE FRACTAL SMC (FIBO_DATA.JSON) --- */}
            {data && (
                <div className="mt-5 mb-5">
                    <h5 className="fw-bold text-dark mb-4 d-flex align-items-center gap-2">
                        <Database className="text-primary" /> Análise Fractal SMC e Liquidez Institucional
                    </h5>

                    {/* ROW: Heatmap & Correlação */}
                    <div className="row g-4 mb-4">
                        {/* Heatmap DOM */}
                        {data.heatmap_liquidez && data.heatmap_liquidez.status === 'ativo' && (
                            <div className="col-12 col-xl-8">
                                <div className="card border-0 shadow-sm rounded-4 h-100 bg-white">
                                    <div className="card-header bg-transparent border-bottom-0 p-3 d-flex align-items-center gap-2">
                                        <Layers size={18} className="text-primary" />
                                        <h6 className="fw-bold m-0">Radar DOM (Livro de Ofertas)</h6>
                                    </div>
                                    <div className="card-body p-3 pt-0">
                                        <div className="row g-3">
                                            {/* Muralhas de Venda */}
                                            <div className="col-12 col-md-6">
                                                <div className="p-3 bg-danger bg-opacity-10 border border-danger-subtle rounded-3 h-100">
                                                    <h6 className="text-danger fw-bold mb-3 small text-uppercase"><Shield size={14}/> Muralhas de Venda (Asks)</h6>
                                                    {data.heatmap_liquidez.muralhas_de_venda_topo?.map((ask: any, i: number) => (
                                                        <div key={i} className="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-danger-subtle">
                                                            <span className="font-monospace fw-bold text-dark">{ask.preco.toFixed(5)}</span>
                                                            <span className="badge bg-danger text-white">{ask.volume} L</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                            {/* Colchões de Compra */}
                                            <div className="col-12 col-md-6">
                                                <div className="p-3 bg-success bg-opacity-10 border border-success-subtle rounded-3 h-100">
                                                    <h6 className="text-success fw-bold mb-3 small text-uppercase"><Shield size={14}/> Colchões de Compra (Bids)</h6>
                                                    {data.heatmap_liquidez.colchoes_de_compra_fundo?.map((bid: any, i: number) => (
                                                        <div key={i} className="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-success-subtle">
                                                            <span className="font-monospace fw-bold text-dark">{bid.preco.toFixed(5)}</span>
                                                            <span className="badge bg-success text-white">{bid.volume} L</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Correlação Macro */}
                        {data.correlacao_macro_8y && Object.keys(data.correlacao_macro_8y).length > 0 && (
                            <div className="col-12 col-xl-4">
                                <div className="card border-0 shadow-sm rounded-4 h-100 bg-white">
                                    <div className="card-header bg-transparent border-bottom-0 p-3 d-flex align-items-center gap-2">
                                        <Zap size={18} className="text-warning" />
                                        <h6 className="fw-bold m-0">Matriz de Correlação (8Y)</h6>
                                    </div>
                                    <div className="card-body p-3 pt-0 overflow-auto custom-scrollbar">
                                        {Object.entries(data.correlacao_macro_8y)
                                            .filter(([k]) => k !== symbol)
                                            .sort(([, a]: any, [, b]: any) => Math.abs(b) - Math.abs(a))
                                            .map(([pair, value]: any) => (
                                                <div key={pair} className="d-flex justify-content-between align-items-center mb-2 p-2 bg-light rounded-3 border border-secondary-subtle">
                                                    <span className="fw-bold text-dark">{pair}</span>
                                                    <span className={`badge ${value > 0.8 ? 'bg-success' : value < -0.8 ? 'bg-danger' : 'bg-secondary'}`}>
                                                    {value > 0 ? '+' : ''}{(value * 100).toFixed(1)}%
                                                </span>
                                                </div>
                                            ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* TIMEFRAMES CARDS */}
                    <div className="row g-3">
                        {timeframes.map(tf => {
                            const info = data[tf];
                            if (!info) return null;

                            const isBull = info.tendencia === 'COMPRA';
                            const biasIcon = info.medias_moveis?.bias_macro === "ALTA" ? "🟢" : info.medias_moveis?.bias_macro === "BAIXA" ? "🔴" : "⚪";

                            return (
                                <div key={tf} className="col-12 col-md-6 col-xl-4">
                                    <div className="card border-0 shadow-sm rounded-4 h-100 bg-white hover-lift transition-all">
                                        {/* Cabeçalho do Card */}
                                        <div className="card-header bg-transparent border-bottom-0 pt-3 pb-2 d-flex justify-content-between align-items-center">
                                            <h5 className="fw-black m-0 d-flex align-items-center gap-2 text-dark">
                                                {tf} <span className="text-muted small fw-normal">@{info.preco_atual?.toFixed(5)}</span>
                                            </h5>
                                            <span className={`badge px-3 py-2 ${isBull ? 'bg-success' : 'bg-danger'} bg-opacity-10 ${isBull ? 'text-success' : 'text-danger'} border`}>
                                                {isBull ? <TrendingUp size={14} className="me-1"/> : <TrendingDown size={14} className="me-1"/>}
                                                {info.tendencia}
                                            </span>
                                        </div>

                                        <div className="card-body p-3 pt-0 d-flex flex-column gap-2">
                                            {/* Métricas Principais */}
                                            <div className="row g-2">
                                                <div className="col-6">
                                                    <div className="p-2 bg-light rounded-3 border border-secondary-subtle h-100">
                                                        <span className="text-muted d-block small mb-1" style={{fontSize: '0.65rem'}}>ALVO (1.618)</span>
                                                        <span className="fw-bold font-monospace text-dark">{info.alvo_1618?.toFixed(5)}</span>
                                                    </div>
                                                </div>
                                                <div className="col-6">
                                                    <div className="p-2 bg-light rounded-3 border border-secondary-subtle h-100">
                                                        <span className="text-muted d-block small mb-1" style={{fontSize: '0.65rem'}}>INVALIDAÇÃO</span>
                                                        <span className="fw-bold font-monospace text-dark">{info.nivel_critico?.toFixed(5)}</span>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Informações Secundárias */}
                                            <div className="d-flex justify-content-between align-items-center mt-2 px-2">
                                                <span className="text-muted small">Fair Value Gap:</span>
                                                <span className={`fw-bold small font-monospace ${info.gap_fvg !== "Nenhum" ? "text-primary" : "text-muted"}`}>{info.gap_fvg}</span>
                                            </div>
                                            <div className="d-flex justify-content-between align-items-center px-2">
                                                <span className="text-muted small">Bias Macro (200):</span>
                                                <span className="fw-bold small">{biasIcon} {info.medias_moveis?.bias_macro}</span>
                                            </div>
                                            <div className="d-flex justify-content-between align-items-center px-2 pb-2 border-bottom border-secondary-subtle">
                                                <span className="text-muted small">Tempo de Lucas:</span>
                                                <span className="fw-bold small text-primary">
                                                    {info.lucas_time?.candles_restantes !== "N/A"
                                                        ? `${info.lucas_time?.candles_restantes}c (Rácio: x${info.lucas_time?.racio_ativo})`
                                                        : "Expirado"}
                                                </span>
                                            </div>

                                            {/* Price Action e Oráculo */}
                                            <div className="mt-2">
                                                <span className="text-muted d-block mb-1 fw-bold" style={{fontSize: '0.65rem'}}>PSICOLOGIA PA:</span>
                                                <p className="small text-dark fw-medium lh-sm m-0">{info.price_action_atual}</p>
                                            </div>

                                            {info.resumo_ia && info.resumo_ia !== "IA Desativada neste TF para poupar tokens." && (
                                                <div className="mt-auto pt-3">
                                                    <div className="p-2 bg-info bg-opacity-10 border border-info-subtle rounded-3">
                                                        <span className="text-info-emphasis fw-black d-flex align-items-center gap-1 mb-1" style={{fontSize: '0.7rem'}}>
                                                            <BrainCircuit size={12}/> ORÁCULO IA
                                                        </span>
                                                        <p className="m-0 text-dark lh-sm" style={{fontSize: '0.75rem'}}>{info.resumo_ia}</p>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* MODAL DE CONFIRMAÇÃO DE TRADE */}
            {confirmTrade.show && (
                <div className="position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-75 d-flex justify-content-center align-items-center" style={{zIndex: 9999}}>
                    <div className="bg-white rounded-4 shadow-lg p-4 text-center" style={{maxWidth: '400px', width: '90%'}}>
                        <div className={`mx-auto mb-3 d-flex align-items-center justify-content-center rounded-circle ${confirmTrade.type === 'BUY' ? 'bg-success bg-opacity-10 text-success' : 'bg-danger bg-opacity-10 text-danger'}`} style={{width: '64px', height: '64px'}}>
                            {confirmTrade.type === 'BUY' ? <TrendingUp size={32}/> : <TrendingDown size={32}/>}
                        </div>
                        <h4 className="fw-bold mb-2">Confirmar {confirmTrade.type}</h4>
                        <p className="text-muted">Estás prestes a abrir uma ordem de mercado.</p>

                        <div className="bg-light rounded-3 p-3 mb-4 text-start border">
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted small fw-bold">Símbolo</span>
                                <span className="fw-bold">{symbol}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted small fw-bold">Volume</span>
                                <span className="fw-bold">{tradeVolume} Lotes</span>
                            </div>
                            <div className="d-flex justify-content-between border-top pt-2 mt-2">
                                <span className="text-muted small fw-bold">Preço Atual</span>
                                <span className={`fw-black ${confirmTrade.type === 'BUY' ? 'text-success' : 'text-danger'}`}>
                                    {confirmTrade.type === 'BUY' ? ticker.ask.toFixed(5) : ticker.bid.toFixed(5)}
                                </span>
                            </div>
                        </div>

                        <div className="d-flex gap-2">
                            <button className="btn btn-light fw-bold w-100 border" onClick={() => setConfirmTrade({show: false, type: null, processing: false})} disabled={confirmTrade.processing}>Cancelar</button>
                            <button className={`btn fw-bold w-100 d-flex align-items-center justify-content-center gap-2 ${confirmTrade.type === 'BUY' ? 'btn-success' : 'btn-danger'}`} onClick={handleExecuteTrade} disabled={confirmTrade.processing}>
                                {confirmTrade.processing ? <div className="spinner-border spinner-border-sm"></div> : <CheckCircle size={18}/>} Confirmar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* MODAL DE EDIÇÃO DO JSON DE NOTÍCIAS */}
            {showNewsEditor && (
                <div className="position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-75 d-flex justify-content-center align-items-center" style={{zIndex: 9999}}>
                    <div className="bg-white rounded-4 shadow-lg p-0 d-flex flex-column" style={{maxWidth: '700px', width: '90%', height: '80vh'}}>
                        <div className="p-3 border-bottom d-flex justify-content-between align-items-center bg-light rounded-top-4">
                            <h5 className="fw-bold m-0 d-flex align-items-center gap-2"><Edit2 size={18}/> Editor: news_calendar.json</h5>
                            <button className="btn-close" onClick={() => setShowNewsEditor(false)}></button>
                        </div>
                        <div className="p-3 flex-grow-1 d-flex flex-column bg-body-tertiary">
                            <p className="small text-muted mb-2">Edita o JSON bruto abaixo. Certifica-te que as aspas e vírgulas estão corretas antes de guardar.</p>
                            <textarea
                                className="form-control flex-grow-1 font-monospace text-light bg-dark"
                                style={{fontSize: '0.85rem'}}
                                value={newsJsonText}
                                onChange={e => setNewsJsonText(e.target.value)}
                            />
                        </div>
                        <div className="p-3 border-top d-flex gap-2 bg-light rounded-bottom-4 justify-content-end">
                            <button className="btn btn-outline-secondary fw-bold" onClick={() => setShowNewsEditor(false)}>Cancelar</button>
                            <button className="btn btn-primary fw-bold d-flex align-items-center gap-2" onClick={handleSaveNews}>
                                <Save size={16}/> Guardar e Aplicar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <style>{`
                .fw-black { font-weight: 900; }
                .ls-1 { letter-spacing: 1px; }
                .font-monospace { font-family: 'Courier New', Courier, monospace; }
                .spin-animation { animation: spin 1s linear infinite; }
                @keyframes spin { 100% { transform: rotate(360deg); } }
                
                .hover-lift:hover { transform: translateY(-5px); box-shadow: 0 .5rem 1rem rgba(0,0,0,.15)!important; }
                
                /* Nova animação para os minutos das notícias */
                .pulse-warning { animation: pulseWarning 1.5s infinite; }
                @keyframes pulseWarning { 
                    0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); } 
                    70% { transform: scale(1.05); box-shadow: 0 0 0 6px rgba(220, 53, 69, 0); } 
                    100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); } 
                }

                .invert-chart { filter: invert(0.92) hue-rotate(180deg) brightness(1.1) contrast(1.1); background-color: transparent; }
                [data-bs-theme="dark"] .bg-white { background-color: var(--bs-body-bg) !important; }
                [data-bs-theme="dark"] .bg-light { background-color: var(--bs-tertiary-bg) !important; }
            `}</style>
        </div>
    );
}

// --- COMPONENTE DO GRÁFICO ELLIOTT WAVE COM VELAS, CALCULADORA DE RISCO E NÚMEROS DE LUCAS ---
function ElliottWaveVisualizer({ memory, currentBid, candles, accountInfo, onApplyLots }: { memory: any, currentBid: number, candles: any[], accountInfo: any, onApplyLots: (lots: number) => void }) {
    const [targetPct, setTargetPct] = useState<number>(30);

    if (!memory || currentBid === 0 || memory.fase !== "ATIVA") return null;

    // EXTRAÇÃO DA ONDA ATUAL
    const { direcao, inicio, extremo, onda_atual = "PESQUISA" } = memory;
    const isBull = direcao === 'BULL';

    // Formatação visual da Badge da Onda
    let ondaClass = "bg-secondary text-secondary border-secondary-subtle";
    let ondaLabel = "PESQUISA";

    if (onda_atual === "RETRAÇÃO_2_4") {
        ondaClass = "bg-warning text-warning border-warning-subtle";
        ondaLabel = "Onda 2/4 (Retração)";
    } else if (onda_atual === "IMPULSO_3_5") {
        ondaClass = "bg-info text-info border-info-subtle";
        ondaLabel = "Onda 3/5 (Impulso)";
    } else if (onda_atual) {
        ondaLabel = onda_atual.replace(/_/g, ' ');
    }

    // --- Lógica de Cálculo de Risco ---
    const balance = accountInfo?.balance || 0;
    const priceDiff = Math.abs(extremo - currentBid);
    const targetProfit = (balance * targetPct) / 100;

    let calculatedLots = 0.01;
    if (priceDiff > 0 && balance > 0) {
        const rawLots = targetProfit / (100000 * priceDiff);
        calculatedLots = Math.max(0.01, Number(rawLots.toFixed(2)));
    }

    const leverage = 500;
    const requiredMargin = (calculatedLots * 100000 * currentBid) / leverage;

    // --- Lógica de Desenho do SVG e Lucas ---
    const hasCandles = candles && candles.length > 0;

    let minY = Math.min(inicio, extremo, currentBid);
    let maxY = Math.max(inicio, extremo, currentBid);

    if (hasCandles) {
        const lowestCandle = Math.min(...candles.map(c => c.low));
        const highestCandle = Math.max(...candles.map(c => c.high));
        minY = Math.min(minY, lowestCandle);
        maxY = Math.max(maxY, highestCandle);
    }

    const padding = (maxY - minY) * 0.1;
    minY -= padding;
    maxY += padding;
    const rangeY = maxY - minY;

    const getY = (price: number) => {
        if (rangeY === 0) return 50;
        return 100 - (((price - minY) / rangeY) * 100);
    };

    let pathData = "";
    let stepX = 1;
    const totalViewWidth = 240;

    // A Sequência de Lucas Clássica (para projeção temporal)
    const lucasNumbers = [1, 3, 4, 7, 11, 18, 29, 47, 76, 123, 199, 322, 521, 843];
    const currentCandleCount = hasCandles ? candles.length : 0;

    // Descobrir a próxima viragem
    const nextLucas = lucasNumbers.find(n => n > currentCandleCount) || 0;
    const candlesLeft = nextLucas > 0 ? nextLucas - currentCandleCount : 0;

    let lucasSVG = null;

    if (hasCandles) {
        stepX = totalViewWidth / Math.max(1, (candles.length - 1));
        pathData = candles.map((c, i) => {
            const x = i * stepX;
            const y = getY(c.close);
            return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
        }).join(" ");

        // Desenhar as linhas de Lucas que caem dentro da janela visível (até ao candle atual)
        lucasSVG = lucasNumbers.filter(L => L <= candles.length).map(L => {
            const xPos = L * stepX;
            return (
                <g key={`lucas-${L}`}>
                    <line x1={xPos} y1="0" x2={xPos} y2="100" stroke="#adb5bd" strokeWidth="0.5" strokeDasharray="2 2" opacity="0.4" />
                    <text x={xPos + 2} y="10" fontSize="5" fill="#adb5bd" fontWeight="bold">L{L}</text>
                </g>
            );
        });
    }

    const yInicio = getY(inicio);
    const yExtremo = getY(extremo);
    const yBid = getY(currentBid);

    return (
        <div className="card border-0 shadow-sm rounded-4 bg-white mb-2">
            <div className="card-header p-3 border-0 d-flex justify-content-between align-items-center">
                <h6 className="fw-bold m-0 d-flex align-items-center gap-2">
                    <Activity size={18} className={isBull ? "text-success" : "text-danger"}/>
                    Alvo da Estrutura (M1)
                </h6>
                <div className="d-flex gap-2">
                    <span className={`badge ${isBull ? 'bg-success' : 'bg-danger'} bg-opacity-10 ${isBull ? 'text-success' : 'text-danger'} border`}>
                        Dir: {direcao}
                    </span>
                    <span className={`badge ${ondaClass} bg-opacity-10 border`}>
                        {ondaLabel}
                    </span>
                </div>
            </div>

            <div className="card-body p-3 pt-0 position-relative">
                {/* GRÁFICO SVG NATIVO COM LINHAS DE LUCAS */}
                <div className="w-100 bg-light rounded-3 overflow-hidden position-relative border" style={{height: '180px'}}>
                    <svg viewBox={`0 0 ${totalViewWidth} 100`} preserveAspectRatio="none" className="w-100 h-100">
                        {/* Grelha de Lucas (Eixo X) */}
                        {lucasSVG}

                        <line x1="0" y1={yInicio} x2={totalViewWidth} y2={yInicio} stroke="#6c757d" strokeWidth="0.5" strokeDasharray="4 2" />
                        <line x1="0" y1={yExtremo} x2={totalViewWidth} y2={yExtremo} stroke={isBull ? "#198754" : "#dc3545"} strokeWidth="1" strokeDasharray="4 2" />
                        <line x1="0" y1={yBid} x2={totalViewWidth} y2={yBid} stroke="#0d6efd" strokeWidth="0.5" opacity="0.5" />
                        {hasCandles && <path d={pathData} fill="none" stroke="#212529" strokeWidth="1" vectorEffect="non-scaling-stroke" />}
                        {hasCandles && <circle cx={totalViewWidth} cy={yBid} r="3" fill="#0d6efd" className="pulse-circle" />}
                    </svg>

                    <div className="position-absolute small fw-bold text-muted bg-white px-1 rounded shadow-sm" style={{top: `${yInicio}%`, left: '5px', transform: 'translateY(-50%)', fontSize: '0.65rem'}}>
                        INÍCIO: {inicio.toFixed(5)}
                    </div>
                    <div className={`position-absolute small fw-bold text-white px-1 rounded shadow-sm ${isBull ? 'bg-success' : 'bg-danger'}`} style={{top: `${yExtremo}%`, left: '5px', transform: 'translateY(-50%)', fontSize: '0.65rem'}}>
                        ALVO: {extremo.toFixed(5)}
                    </div>
                    <div className="position-absolute small fw-black text-white bg-primary px-2 rounded shadow-sm" style={{top: `${yBid}%`, right: '5px', transform: 'translateY(-50%)', fontSize: '0.75rem'}}>
                        {currentBid.toFixed(5)}
                    </div>

                    {/* INDICADOR DE PRÓXIMA VIRAGEM (LUCAS) */}
                    {hasCandles && (
                        <div className="position-absolute bg-white px-2 py-1 rounded shadow-sm border border-secondary-subtle d-flex align-items-center gap-1" style={{bottom: '5px', left: '50%', transform: 'translateX(-50%)', fontSize: '0.65rem'}}>
                            <Clock size={12} className="text-primary" />
                            <span className="text-muted fw-bold">Viragem L{nextLucas}:</span>
                            <span className="text-dark fw-black">{candlesLeft} min</span>
                        </div>
                    )}
                </div>

                {/* PAINEL DE GESTÃO DE RISCO */}
                <div className="mt-3 p-3 bg-light rounded-3 border border-secondary-subtle">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                        <span className="small fw-bold text-muted d-flex align-items-center gap-1"><Calculator size={14}/> Gestão de Risco</span>
                        <span className="badge bg-primary bg-opacity-10 text-primary border border-primary-subtle">Calculadora</span>
                    </div>
                    <div className="row g-2 align-items-end">
                        <div className="col-4">
                            <label className="small text-muted" style={{fontSize: '0.7rem'}}>Alvo da Conta (%)</label>
                            <div className="input-group input-group-sm shadow-sm">
                                <input type="number" min="0" step="1" className="form-control fw-bold" value={targetPct} onChange={e => setTargetPct(Number(e.target.value))} />
                                <span className="input-group-text bg-white fw-bold">%</span>
                            </div>
                        </div>
                        <div className="col-4">
                            <label className="small text-muted" style={{fontSize: '0.7rem'}}>Lucro Previsto</label>
                            <div className="form-control form-control-sm bg-white fw-bold text-success text-end shadow-sm">
                                {targetProfit.toFixed(2)}€
                            </div>
                        </div>
                        <div className="col-4">
                            <label className="small text-muted" style={{fontSize: '0.7rem'}}>Lotes Necessários</label>
                            <button className="btn btn-sm btn-primary w-100 fw-bold shadow-sm" onClick={() => onApplyLots(calculatedLots)}>
                                Usar {calculatedLots}
                            </button>
                        </div>
                    </div>
                    <div className="text-muted mt-2 text-center" style={{fontSize: '0.65rem'}}>
                        Margem Mínima (1:500): <strong className="text-dark">{requiredMargin.toFixed(2)}€</strong> | Saldo: {balance.toFixed(2)}€
                    </div>
                </div>
            </div>
            <style>{`
                .pulse-circle { animation: pulse 1.5s infinite; transform-origin: center; }
                @keyframes pulse { 0% { r: 2; opacity: 1; } 50% { r: 6; opacity: 0.5; } 100% { r: 2; opacity: 1; } }
            `}</style>
        </div>
    );
}