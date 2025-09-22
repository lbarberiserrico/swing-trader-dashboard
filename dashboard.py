import React, { useEffect, useMemo, useState } from "react";
// SwingTraderDashboard.jsx
// Single-file React component UI for swing trading logging & analytics
// - Tailwind CSS assumed available in host project
// - Recharts used for charts (install recharts)
// - Default export is the main component

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ResponsiveContainer,
  Legend,
} from "recharts";

// Helpers: math & metrics
const round = (n, d = 2) => Math.round((n + Number.EPSILON) * 10 ** d) / 10 ** d;

function calcPnL(entryPrice, exitPrice, qty, positionType, commission = 0) {
  const raw = positionType === "long" ? (exitPrice - entryPrice) * qty : (entryPrice - exitPrice) * qty;
  return raw - commission;
}

function calcReturnPct(entryPrice, exitPrice, positionType) {
  const ret = positionType === "long" ? (exitPrice - entryPrice) / entryPrice : (entryPrice - exitPrice) / entryPrice;
  return ret * 100;
}

function calculateEquityCurve(trades, startingCapital) {
  // Sort trades by exit date if present, else entry date
  const t = [...trades].sort((a, b) => new Date((a.exitDate || a.entryDate)) - new Date((b.exitDate || b.entryDate)));
  let equity = startingCapital;
  const points = [];
  // baseline point at start
  points.push({ date: null, equity });
  for (const tr of t) {
    const pnl = calcPnL(tr.entryPrice, tr.exitPrice, tr.quantity, tr.positionType, tr.commission || 0);
    equity += pnl;
    points.push({ date: tr.exitDate || tr.entryDate, equity: round(equity, 2) });
  }
  return points;
}

function calcSharpe(dailyReturns, riskFreeRate = 0) {
  if (!dailyReturns.length) return 0;
  const avg = dailyReturns.reduce((s, v) => s + v, 0) / dailyReturns.length;
  const std = Math.sqrt(dailyReturns.reduce((s, v) => s + (v - avg) ** 2, 0) / dailyReturns.length);
  if (std === 0) return 0;
  // Annualize using sqrt(252)
  return ((avg - riskFreeRate) / std) * Math.sqrt(252);
}

function calcDrawdowns(equitySeries) {
  let peak = -Infinity;
  let maxDD = 0;
  for (let i = 0; i < equitySeries.length; i++) {
    const val = equitySeries[i].equity;
    if (val > peak) peak = val;
    const dd = peak - val;
    if (dd > maxDD) maxDD = dd;
  }
  return maxDD;
}

function calcProfitFactor(trades) {
  const grossWins = trades.filter(t => t.pnl > 0).reduce((s, t) => s + t.pnl, 0);
  const grossLosses = Math.abs(trades.filter(t => t.pnl < 0).reduce((s, t) => s + t.pnl, 0));
  if (grossLosses === 0) return grossWins > 0 ? Infinity : 0;
  return grossWins / grossLosses;
}

function monthlyReturnsFromEquity(equitySeries) {
  // group by YYYY-MM
  const map = {};
  for (const p of equitySeries) {
    if (!p.date) continue;
    const d = new Date(p.date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    map[key] = p.equity; // last point of month will overwrite
  }
  const keys = Object.keys(map).sort();
  const out = [];
  let prev = null;
  for (const k of keys) {
    const val = map[k];
    if (prev == null) {
      out.push({ month: k, ret: 0 });
    } else {
      out.push({ month: k, ret: round(((val - prev) / prev) * 100, 2) });
    }
    prev = val;
  }
  return out;
}

// LocalStorage keys
const LS_TRADES = "swingtrader.trades.v1";
const LS_SETTINGS = "swingtrader.settings.v1";

// Default settings
const defaultSettings = {
  startingCapital: 10000,
  defaultCommission: 1.0,
  maxRiskPct: 2, // percent of capital
};

export default function SwingTraderDashboard() {
  const [trades, setTrades] = useState(() => {
    try {
      const raw = localStorage.getItem(LS_TRADES);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      console.warn("failed to parse trades", e);
      return [];
    }
  });
  const [settings, setSettings] = useState(() => {
    try {
      const raw = localStorage.getItem(LS_SETTINGS);
      return raw ? JSON.parse(raw) : defaultSettings;
    } catch (e) {
      return defaultSettings;
    }
  });

  useEffect(() => {
    localStorage.setItem(LS_TRADES, JSON.stringify(trades));
  }, [trades]);
  useEffect(() => {
    localStorage.setItem(LS_SETTINGS, JSON.stringify(settings));
  }, [settings]);

  // derived metrics
  const tradesWithPnL = useMemo(() => {
    return trades.map((t) => {
      const pnl = t.exitPrice != null ? calcPnL(t.entryPrice, t.exitPrice, t.quantity, t.positionType, t.commission || 0) : 0;
      const ret = t.exitPrice != null ? calcReturnPct(t.entryPrice, t.exitPrice, t.positionType) : 0;
      return { ...t, pnl: round(pnl, 2), ret: round(ret, 2) };
    });
  }, [trades]);

  const equitySeries = useMemo(() => calculateEquityCurve(tradesWithPnL, settings.startingCapital), [tradesWithPnL, settings.startingCapital]);

  const totalPnL = tradesWithPnL.reduce((s, t) => s + t.pnl, 0);
  const winTrades = tradesWithPnL.filter(t => t.exitPrice != null && t.pnl > 0);
  const lossTrades = tradesWithPnL.filter(t => t.exitPrice != null && t.pnl <= 0);
  const winRate = tradesWithPnL.filter(t => t.exitPrice != null).length ? round((winTrades.length / tradesWithPnL.filter(t => t.exitPrice != null).length) * 100, 2) : 0;
  const avgWin = winTrades.length ? round(winTrades.reduce((s, t) => s + t.pnl, 0) / winTrades.length, 2) : 0;
  const avgLoss = lossTrades.length ? round(lossTrades.reduce((s, t) => s + t.pnl, 0) / lossTrades.length, 2) : 0;
  const profitFactor = calcProfitFactor(tradesWithPnL);
  const maxDrawdown = calcDrawdowns(equitySeries);
  const currentEquity = equitySeries.length ? equitySeries[equitySeries.length - 1].equity : settings.startingCapital;

  // Sharpe: approximate by daily returns from equitySeries
  const dailyRets = [];
  for (let i = 1; i < equitySeries.length; i++) {
    const prev = equitySeries[i - 1].equity;
    const cur = equitySeries[i].equity;
    if (prev !== 0) dailyRets.push((cur - prev) / prev);
  }
  const sharpe = round(calcSharpe(dailyRets), 3);

  // handlers
  function addTrade(trade) {
    const id = cryptoRandomId();
    const computed = {
      id,
      ...trade,
      createdAt: new Date().toISOString(),
    };
    setTrades(prev => [ ...prev, computed ]);
  }

  function updateTrade(id, changes) {
    setTrades(prev => prev.map(t => t.id === id ? { ...t, ...changes } : t));
  }

  function deleteTrade(id) {
    setTrades(prev => prev.filter(t => t.id !== id));
  }

  function clearAll() {
    if (!confirm("Clear all trades? This cannot be undone.")) return;
    setTrades([]);
  }

  function exportJSON() {
    const payload = { trades, settings };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `swingtrader-backup-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function importJSON(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const obj = JSON.parse(e.target.result);
        if (obj.trades) setTrades(obj.trades);
        if (obj.settings) setSettings(obj.settings);
        alert('Imported successfully.');
      } catch (err) {
        alert('Invalid JSON');
      }
    };
    reader.readAsText(file);
  }

  // UI state
  const [filter, setFilter] = useState({ symbol: '', strategy: '', from: '', to: '', outcome: 'all' });
  const [sortBy, setSortBy] = useState({ key: 'createdAt', dir: 'desc' });
  const [editingTrade, setEditingTrade] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  const filteredTrades = tradesWithPnL.filter(t => {
    if (filter.symbol && !t.symbol.toLowerCase().includes(filter.symbol.toLowerCase())) return false;
    if (filter.strategy && !(t.strategy === filter.strategy)) return false;
    if (filter.from && new Date(t.entryDate) < new Date(filter.from)) return false;
    if (filter.to && new Date(t.exitDate || t.entryDate) > new Date(filter.to)) return false;
    if (filter.outcome === 'wins' && !(t.pnl > 0)) return false;
    if (filter.outcome === 'losses' && !(t.pnl <= 0)) return false;
    return true;
  });

  const sortedTrades = [...filteredTrades].sort((a, b) => {
    const dir = sortBy.dir === 'asc' ? 1 : -1;
    if (sortBy.key === 'symbol') return a.symbol.localeCompare(b.symbol) * dir;
    if (sortBy.key === 'entryDate') return (new Date(a.entryDate) - new Date(b.entryDate)) * dir;
    if (sortBy.key === 'pnl') return (a.pnl - b.pnl) * dir;
    return (new Date(a.createdAt) - new Date(b.createdAt)) * dir;
  });

  const filteredCount = filteredTrades.length;
  const totalCount = tradesWithPnL.length;

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl md:text-3xl font-bold">SwingTrader Dashboard</h1>
          <div className="space-x-2">
            <button
              onClick={() => setShowSettings(true)}
              className="px-3 py-2 bg-white border rounded shadow-sm hover:bg-gray-100"
            >Settings</button>
            <button onClick={exportJSON} className="px-3 py-2 bg-blue-600 text-white rounded shadow">Export</button>
            <label className="px-3 py-2 bg-gray-800 text-white rounded cursor-pointer">
              Import
              <input type="file" accept="application/json" className="hidden" onChange={(e) => e.target.files && importJSON(e.target.files[0])} />
            </label>
            <button onClick={clearAll} className="px-3 py-2 bg-red-600 text-white rounded">Clear</button>
          </div>
        </header>

        <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="lg:col-span-1 bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Add Trade</h2>
            <TradeForm onAdd={addTrade} defaultCommission={settings.defaultCommission} startingCapital={settings.startingCapital} maxRiskPct={settings.maxRiskPct} />

            <div className="mt-4">
              <h3 className="font-semibold mb-1">Filters</h3>
              <div className="space-y-2">
                <input placeholder="symbol" value={filter.symbol} onChange={(e) => setFilter({...filter, symbol: e.target.value})} className="w-full border rounded p-2" />
                <input placeholder="strategy" value={filter.strategy} onChange={(e) => setFilter({...filter, strategy: e.target.value})} className="w-full border rounded p-2" />
                <div className="flex gap-2">
                  <input type="date" value={filter.from} onChange={(e) => setFilter({...filter, from: e.target.value})} className="w-1/2 border rounded p-2" />
                  <input type="date" value={filter.to} onChange={(e) => setFilter({...filter, to: e.target.value})} className="w-1/2 border rounded p-2" />
                </div>
                <select value={filter.outcome} onChange={(e) => setFilter({...filter, outcome: e.target.value})} className="w-full border rounded p-2">
                  <option value="all">All</option>
                  <option value="wins">Wins</option>
                  <option value="losses">Losses</option>
                </select>
              </div>
            </div>

            <div className="mt-4 text-sm text-gray-600">
              <div>Starting capital: <strong>${settings.startingCapital}</strong></div>
              <div>Current Equity: <strong>${round(currentEquity,2)}</strong></div>
              <div>Open Trades: <strong>{tradesWithPnL.filter(t => !t.exitPrice).length}</strong></div>
            </div>
          </section>

          <section className="lg:col-span-2 bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-4">Analytics & Charts</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <StatCard title="Total Trades" value={totalCount} subtitle={`Filtered: ${filteredCount}`} />
              <StatCard title="Total P&L" value={`$${round(totalPnL, 2)}`} subtitle={`Profit Factor: ${isFinite(profitFactor) ? round(profitFactor,2) : '—'}`} />
              <StatCard title="Win Rate" value={`${winRate}%`} subtitle={`Avg Win: $${avgWin} • Avg Loss: $${avgLoss}`} />
            </div>

            <div className="h-64 bg-gray-50 rounded p-2">
              <h3 className="mb-2 font-medium">Equity Curve</h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={equitySeries.map((p, i) => ({ ...p, idx: i }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickFormatter={(d) => d ? d.split('T')[0] : 'start'} />
                  <YAxis />
                  <Tooltip formatter={(v) => `$${v}`} labelFormatter={(l) => l ? l.split('T')[0] : 'start'} />
                  <Line type="monotone" dataKey="equity" stroke="#2563eb" strokeWidth={2} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div className="bg-gray-50 rounded p-2 h-56">
                <h3 className="mb-2 font-medium">Monthly Returns</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={monthlyReturnsFromEquity(equitySeries)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip formatter={(v) => `${v}%`} />
                    <Bar dataKey="ret" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-gray-50 rounded p-2 h-56">
                <h3 className="mb-2 font-medium">Drawdown</h3>
                <div className="text-sm mb-2">Max Drawdown: <strong>${round(maxDrawdown,2)}</strong></div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={equitySeries.map((p, i) => ({ x: p.date || 'start', y: p.equity }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="x" />
                    <YAxis />
                    <Tooltip />
                    <Area dataKey="y" type="monotone" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="mt-4">
              <h3 className="font-semibold mb-2">Walkforward Stats</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-sm">
                <SmallStat label="Sharpe" value={sharpe} />
                <SmallStat label="Profit Factor" value={isFinite(profitFactor) ? round(profitFactor,2) : '—'} />
                <SmallStat label="Max Drawdown" value={`$${round(maxDrawdown,2)}`} />
                <SmallStat label="Avg Risk/Trade" value={`${settings.maxRiskPct}%`} />
              </div>
            </div>
          </section>

          <section className="lg:col-span-3 bg-white p-4 rounded shadow">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Trade History ({filteredCount}/{totalCount})</h2>
              <div className="flex gap-2 items-center">
                <label className="text-sm">Sort:</label>
                <select value={sortBy.key} onChange={(e) => setSortBy({...sortBy, key: e.target.value})} className="border rounded p-1">
                  <option value="createdAt">Date Added</option>
                  <option value="entryDate">Entry Date</option>
                  <option value="symbol">Symbol</option>
                  <option value="pnl">P&L</option>
                </select>
                <button onClick={() => setSortBy({...sortBy, dir: sortBy.dir === 'asc' ? 'desc' : 'asc'})} className="px-2 py-1 border rounded">{sortBy.dir === 'asc' ? '↑' : '↓'}</button>
              </div>
            </div>

            <TradeTable trades={sortedTrades} onDelete={deleteTrade} onEdit={(t) => setEditingTrade(t)} onUpdate={updateTrade} />
          </section>
        </main>
      </div>

      {editingTrade && (
        <EditTradeModal trade={editingTrade} onClose={() => setEditingTrade(null)} onSave={(id, changes) => { updateTrade(id, changes); setEditingTrade(null); }} />
      )}

      {showSettings && (
        <SettingsModal settings={settings} onClose={() => setShowSettings(false)} onSave={(s) => { setSettings(s); setShowSettings(false); }} />
      )}
    </div>
  );
}

// --- UI Subcomponents ---

function TradeForm({ onAdd, defaultCommission = 1.0, startingCapital = 10000, maxRiskPct = 2 }) {
  const [symbol, setSymbol] = useState('');
  const [entryDate, setEntryDate] = useState('');
  const [entryPrice, setEntryPrice] = useState('');
  const [exitDate, setExitDate] = useState('');
  const [exitPrice, setExitPrice] = useState('');
  const [positionType, setPositionType] = useState('long');
  const [quantity, setQuantity] = useState('');
  const [strategy, setStrategy] = useState('');
  const [notes, setNotes] = useState('');
  const [commission, setCommission] = useState(defaultCommission);
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');

  useEffect(() => { setCommission(defaultCommission); }, [defaultCommission]);

  function validate() {
    if (!symbol) return "symbol required";
    if (!entryDate || !entryPrice || !quantity) return "entry date/price/quantity required";
    if (exitPrice && !exitDate) return "exit date required if exit price set";
    return null;
  }

  function handleSubmit(e) {
    e.preventDefault();
    const err = validate();
    if (err) return alert(err);
    const trade = {
      symbol: symbol.toUpperCase(),
      entryDate,
      entryPrice: Number(entryPrice),
      exitDate: exitDate || null,
      exitPrice: exitPrice ? Number(exitPrice) : null,
      positionType,
      quantity: Number(quantity),
      strategy,
      notes,
      commission: Number(commission) || 0,
      stopLoss: stopLoss ? Number(stopLoss) : null,
      takeProfit: takeProfit ? Number(takeProfit) : null,
    };
    onAdd(trade);
    // clear form
    setSymbol(''); setEntryDate(''); setEntryPrice(''); setExitDate(''); setExitPrice(''); setQuantity(''); setStrategy(''); setNotes(''); setStopLoss(''); setTakeProfit('');
  }

  // risk calc
  const riskPerShare = stopLoss ? Math.abs(positionType==='long' ? (entryPrice - stopLoss) : (stopLoss - entryPrice)) : 0;
  const riskAmount = riskPerShare && quantity ? riskPerShare * quantity + Number(commission || 0) : 0;
  const riskPctOfCapital = startingCapital ? (riskAmount / startingCapital) * 100 : 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <input placeholder="Symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} className="w-full border rounded p-2" />
      <div className="grid grid-cols-2 gap-2">
        <input type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} className="border rounded p-2" />
        <input placeholder="entry price" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} className="border rounded p-2" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <input type="date" value={exitDate} onChange={(e) => setExitDate(e.target.value)} className="border rounded p-2" />
        <input placeholder="exit price (optional)" value={exitPrice} onChange={(e) => setExitPrice(e.target.value)} className="border rounded p-2" />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <select value={positionType} onChange={(e) => setPositionType(e.target.value)} className="border rounded p-2">
          <option value="long">Long</option>
          <option value="short">Short</option>
        </select>
        <input placeholder="quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="border rounded p-2" />
        <input placeholder="commission" value={commission} onChange={(e) => setCommission(e.target.value)} className="border rounded p-2" />
      </div>
      <input placeholder="strategy (e.g., breakout)" value={strategy} onChange={(e) => setStrategy(e.target.value)} className="w-full border rounded p-2" />
      <div className="grid grid-cols-2 gap-2">
        <input placeholder="stop loss (optional)" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} className="border rounded p-2" />
        <input placeholder="take profit (optional)" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)} className="border rounded p-2" />
      </div>
      <textarea placeholder="notes" value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full border rounded p-2" rows={3} />

      <div className="text-sm text-gray-600">
        <div>Risk / share: ${round(riskPerShare,4)} • Risk amount: ${round(riskAmount,2)}</div>
        <div className={`${riskPctOfCapital > maxRiskPct ? 'text-red-600 font-semibold' : ''}`}>Risk % of capital: {round(riskPctOfCapital,2)}% {riskPctOfCapital > maxRiskPct ? ' — exceeds limit' : ''}</div>
      </div>

      <div className="flex gap-2">
        <button type="submit" className="px-3 py-2 bg-green-600 text-white rounded">Add Trade</button>
        <button type="button" onClick={() => { /* quick fill example */ setSymbol('AAPL'); setEntryDate(new Date().toISOString().slice(0,10)); setEntryPrice('170'); setQuantity('10'); }} className="px-3 py-2 bg-gray-200 rounded">Example</button>
      </div>
    </form>
  );
}

function TradeTable({ trades, onDelete, onEdit, onUpdate }) {
  return (
    <div className="overflow-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-100">
          <tr>
            <th className="p-2 text-left">Symbol</th>
            <th className="p-2">Entry</th>
            <th className="p-2">Exit</th>
            <th className="p-2">Qty</th>
            <th className="p-2">P&L</th>
            <th className="p-2">Ret %</th>
            <th className="p-2">Strategy</th>
            <th className="p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {trades.map(t => (
            <tr key={t.id} className="border-b hover:bg-gray-50">
              <td className="p-2 font-medium">{t.symbol}</td>
              <td className="p-2 text-xs">{t.entryDate}<div className="text-xs text-gray-500">@ {t.entryPrice}</div></td>
              <td className="p-2 text-xs">{t.exitDate || '—'}<div className="text-xs text-gray-500">@ {t.exitPrice || '—'}</div></td>
              <td className="p-2">{t.quantity}</td>
              <td className={`p-2 ${t.pnl>0? 'text-green-600':'text-red-600'}`}>${t.pnl}</td>
              <td className="p-2">{t.ret}%</td>
              <td className="p-2">{t.strategy || '—'}</td>
              <td className="p-2">
                <div className="flex gap-1">
                  <button onClick={() => onEdit(t)} className="px-2 py-1 border rounded">Edit</button>
                  <button onClick={() => { if (confirm('Delete trade?')) onDelete(t.id); }} className="px-2 py-1 border rounded">Delete</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatCard({ title, value, subtitle }) {
  return (
    <div className="bg-white rounded p-3 shadow">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-xl font-bold">{value}</div>
      {subtitle && <div className="text-sm text-gray-500">{subtitle}</div>}
    </div>
  );
}

function SmallStat({ label, value }) {
  return (
    <div className="bg-white rounded p-2 shadow text-center">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}

function EditTradeModal({ trade, onClose, onSave }) {
  const [form, setForm] = useState({ ...trade });
  function save() {
    // basic validation
    if (!form.symbol) return alert('symbol required');
    onSave(trade.id, form);
  }
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl rounded p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold">Edit Trade</h3>
          <div className="space-x-2">
            <button onClick={onClose} className="px-3 py-1 border rounded">Close</button>
            <button onClick={save} className="px-3 py-1 bg-blue-600 text-white rounded">Save</button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input value={form.symbol} onChange={(e) => setForm({...form, symbol: e.target.value})} className="border rounded p-2" />
          <select value={form.positionType} onChange={(e) => setForm({...form, positionType: e.target.value})} className="border rounded p-2">
            <option value="long">Long</option>
            <option value="short">Short</option>
          </select>
          <input type="date" value={form.entryDate} onChange={(e) => setForm({...form, entryDate: e.target.value})} className="border rounded p-2" />
          <input type="date" value={form.exitDate || ''} onChange={(e) => setForm({...form, exitDate: e.target.value})} className="border rounded p-2" />
          <input value={form.entryPrice} onChange={(e) => setForm({...form, entryPrice: Number(e.target.value)})} className="border rounded p-2" />
          <input value={form.exitPrice || ''} onChange={(e) => setForm({...form, exitPrice: e.target.value ? Number(e.target.value) : null})} className="border rounded p-2" />
          <input value={form.quantity} onChange={(e) => setForm({...form, quantity: Number(e.target.value)})} className="border rounded p-2" />
          <input value={form.commission || 0} onChange={(e) => setForm({...form, commission: Number(e.target.value)})} className="border rounded p-2" />
          <input value={form.strategy || ''} onChange={(e) => setForm({...form, strategy: e.target.value})} className="border rounded p-2" />
          <input value={form.stopLoss || ''} onChange={(e) => setForm({...form, stopLoss: e.target.value ? Number(e.target.value) : null})} className="border rounded p-2" />
          <textarea value={form.notes || ''} onChange={(e) => setForm({...form, notes: e.target.value})} className="col-span-2 border rounded p-2" rows={4} />
        </div>
      </div>
    </div>
  );
}

function SettingsModal({ settings, onClose, onSave }) {
  const [local, setLocal] = useState({ ...settings });
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-lg rounded p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold">Settings</h3>
          <div className="space-x-2">
            <button onClick={onClose} className="px-3 py-1 border rounded">Close</button>
            <button onClick={() => onSave(local)} className="px-3 py-1 bg-blue-600 text-white rounded">Save</button>
          </div>
        </div>
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <label className="text-sm">Starting Capital</label>
            <input value={local.startingCapital} onChange={(e) => setLocal({...local, startingCapital: Number(e.target.value)})} className="border rounded p-2" />
            <label className="text-sm">Default Commission</label>
            <input value={local.defaultCommission} onChange={(e) => setLocal({...local, defaultCommission: Number(e.target.value)})} className="border rounded p-2" />
            <label className="text-sm">Max Risk % per Trade</label>
            <input value={local.maxRiskPct} onChange={(e) => setLocal({...local, maxRiskPct: Number(e.target.value)})} className="border rounded p-2" />
          </div>
        </div>
      </div>
    </div>
  );
}

// small util
function cryptoRandomId() {
  if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
  return Math.random().toString(36).slice(2, 9);
}
