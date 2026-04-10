import { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";

// ── Types ────────────────────────────────────────────────────────────────────

interface Transaction {
  TransactionAmt: number | null;
  ProductCD: string;
  card1: number | null;
  card4: string;
  card6: string;
  addr1: number | null;
  P_emaildomain: string;
  DeviceType: string;
  C1: number | null;
}

interface PredictResult {
  fraud_probability: number;
  is_fraud: boolean;
  threshold: number;
  error?: string;
}

interface HistoryRow {
  id: number;
  transaction_amt: number;
  product_cd: string;
  fraud_probability: number;
  is_fraud: boolean;
  created_at: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const PRODUCT_CD = ["W", "H", "C", "S", "R"];
const CARD4 = ["visa", "mastercard", "discover", "american express"];
const CARD6 = ["debit", "credit", "charge card", "debit or credit"];
const EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "unknown"];
const DEVICE_TYPES = ["desktop", "mobile"];

const DEFAULT_FORM: Transaction = {
  TransactionAmt: null,
  ProductCD: "W",
  card1: null,
  card4: "visa",
  card6: "debit",
  addr1: null,
  P_emaildomain: "gmail.com",
  DeviceType: "desktop",
  C1: null,
};

// ── Styles (inline, no external CSS) ────────────────────────────────────────

const css = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f0f2f5; color: #1a1a2e; }
  .wrap { max-width: 860px; margin: 40px auto; padding: 0 16px; }
  h1 { font-size: 1.6rem; margin-bottom: 24px; }
  .card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 24px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  label { display: block; font-size: .85rem; font-weight: 600; margin-bottom: 4px; color: #555; }
  input, select { width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: .95rem; }
  input:focus, select:focus { outline: 2px solid #6366f1; border-color: transparent; }
  .btn { padding: 10px 24px; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: 600; }
  .btn-primary { background: #6366f1; color: #fff; }
  .btn-primary:hover { background: #4f46e5; }
  .btn-secondary { background: #e5e7eb; color: #374151; margin-left: 8px; }
  .result { padding: 16px; border-radius: 10px; margin-top: 16px; }
  .fraud { background: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; }
  .legit { background: #dcfce7; border: 1px solid #86efac; color: #166534; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th, td { padding: 8px 10px; border-bottom: 1px solid #e5e7eb; text-align: left; }
  th { background: #f9fafb; font-weight: 600; }
  .badge-fraud { background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 99px; font-size: .78rem; }
  .badge-ok { background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 99px; font-size: .78rem; }
  .tabs { display: flex; gap: 8px; margin-bottom: 20px; }
  .tab { padding: 8px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; border: 2px solid transparent; color: #6b7280; }
  .tab.active { border-color: #6366f1; color: #6366f1; }
  .tab:hover:not(.active) { background: #f3f4f6; }
  .file-area { border: 2px dashed #d1d5db; border-radius: 10px; padding: 32px; text-align: center; cursor: pointer; color: #6b7280; }
  .file-area:hover { border-color: #6366f1; color: #6366f1; }
  .error { color: #dc2626; font-size: .9rem; margin-top: 8px; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 3px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; vertical-align: middle; margin-right: 6px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .mt { margin-top: 16px; }
  .row { display: flex; align-items: center; gap: 8px; margin-top: 20px; }
`;

// ── Field helpers ────────────────────────────────────────────────────────────

type FieldDef =
  | { name: keyof Transaction; label: string; kind: "number"; placeholder: string }
  | { name: keyof Transaction; label: string; kind: "select"; options: string[] };

const FIELDS: FieldDef[] = [
  { name: "TransactionAmt", label: "Сумма (USD)", kind: "number", placeholder: "49.00" },
  { name: "ProductCD",      label: "Тип продукта", kind: "select", options: PRODUCT_CD },
  { name: "card1",          label: "ID карты", kind: "number", placeholder: "3429" },
  { name: "card4",          label: "Платёжная система", kind: "select", options: CARD4 },
  { name: "card6",          label: "Тип счёта", kind: "select", options: CARD6 },
  { name: "addr1",          label: "Биллинговый регион", kind: "number", placeholder: "299" },
  { name: "P_emaildomain",  label: "Email домен", kind: "select", options: EMAIL_DOMAINS },
  { name: "DeviceType",     label: "Устройство", kind: "select", options: DEVICE_TYPES },
  { name: "C1",             label: "Транзакций по карте", kind: "number", placeholder: "1" },
];

// ── App ──────────────────────────────────────────────────────────────────────

function App() {
  const [tab, setTab] = useState<"single" | "batch" | "history">("single");
  const [form, setForm] = useState<Transaction>(DEFAULT_FORM);
  const [result, setResult] = useState<PredictResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [batchResults, setBatchResults] = useState<(Transaction & Partial<PredictResult>)[]>([]);

  useEffect(() => { loadHistory(); }, []);

  async function loadHistory() {
    try {
      const r = await fetch("/api/history?limit=20");
      setHistory(await r.json());
    } catch {}
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError(""); setResult(null);
    try {
      const r = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setResult(await r.json());
      loadHistory();
    } catch (err: unknown) {
      setError("Ошибка: " + (err instanceof Error ? err.message : String(err)));
    } finally { setLoading(false); }
  }

  async function handleBatch(e: React.FormEvent) {
    e.preventDefault();
    if (!csvFile) return;
    setLoading(true); setError(""); setBatchResults([]);
    try {
      const fd = new FormData();
      fd.append("file", csvFile);
      const r = await fetch("/api/predict/batch", { method: "POST", body: fd });
      setBatchResults(await r.json());
      loadHistory();
    } catch (err: unknown) {
      setError("Ошибка: " + (err instanceof Error ? err.message : String(err)));
    } finally { setLoading(false); }
  }

  function setField(name: keyof Transaction, value: string) {
    const numFields: (keyof Transaction)[] = ["TransactionAmt", "card1", "addr1", "C1"];
    setForm(f => ({
      ...f,
      [name]: numFields.includes(name) ? (value === "" ? null : parseFloat(value)) : value,
    }));
  }

  return (
    <>
      <style>{css}</style>
      <div className="wrap">
        <h1>🔍 Fraud Detector — Детектор банковского фрода</h1>

        <div className="tabs">
          {(["single", "batch", "history"] as const).map(t => (
            <div key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
              {t === "single" ? "Одиночная транзакция" : t === "batch" ? "CSV-файл" : "История"}
            </div>
          ))}
        </div>

        {tab === "single" && (
          <div className="card">
            <form onSubmit={handleSubmit}>
              <div className="grid">
                {FIELDS.map(f => (
                  <div key={f.name}>
                    <label>{f.label}</label>
                    {f.kind === "select"
                      ? <select value={String(form[f.name] ?? "")} onChange={e => setField(f.name, e.target.value)}>
                          {f.options.map(o => <option key={o}>{o}</option>)}
                        </select>
                      : <input type="number" step="any" placeholder={f.placeholder}
                          value={form[f.name] ?? ""}
                          onChange={e => setField(f.name, e.target.value)} />
                    }
                  </div>
                ))}
              </div>
              <div className="row">
                <button className="btn btn-primary" type="submit" disabled={loading}>
                  {loading && <span className="spinner" />}Проверить
                </button>
                <button className="btn btn-secondary" type="button"
                  onClick={() => { setForm(DEFAULT_FORM); setResult(null); setError(""); }}>
                  Сбросить
                </button>
              </div>
              {error && <div className="error">{error}</div>}
              {result && (
                <div className={`result ${result.is_fraud ? "fraud" : "legit"}`}>
                  {result.is_fraud ? "🚨 ФРОД" : "✅ Легитимная транзакция"}<br />
                  <small>P(фрод) = <b>{(result.fraud_probability * 100).toFixed(2)}%</b> (порог {(result.threshold * 100).toFixed(1)}%)</small>
                </div>
              )}
            </form>
          </div>
        )}

        {tab === "batch" && (
          <div className="card">
            <form onSubmit={handleBatch}>
              <label className="file-area" onClick={() => document.getElementById("csvInput")?.click()}>
                {csvFile ? `📄 ${csvFile.name}` : "Нажмите или перетащите CSV-файл"}
                <input id="csvInput" type="file" accept=".csv" style={{ display: "none" }}
                  onChange={e => setCsvFile(e.target.files?.[0] ?? null)} />
              </label>
              <div className="mt">
                <button className="btn btn-primary" type="submit" disabled={loading || !csvFile}>
                  {loading && <span className="spinner" />}Загрузить и проверить
                </button>
              </div>
              {error && <div className="error">{error}</div>}
            </form>
            {batchResults.length > 0 && (
              <div className="mt" style={{ overflowX: "auto" }}>
                <table>
                  <thead><tr><th>Сумма</th><th>Продукт</th><th>P(фрод)</th><th>Решение</th></tr></thead>
                  <tbody>
                    {batchResults.map((r, i) => (
                      <tr key={i}>
                        <td>${r.TransactionAmt}</td>
                        <td>{r.ProductCD}</td>
                        <td>{r.fraud_probability != null ? (r.fraud_probability * 100).toFixed(2) + "%" : "—"}</td>
                        <td>{r.is_fraud != null
                          ? <span className={r.is_fraud ? "badge-fraud" : "badge-ok"}>{r.is_fraud ? "ФРОД" : "OK"}</span>
                          : r.error}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === "history" && (
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <b>Последние 20 предсказаний</b>
              <button className="btn btn-secondary" onClick={loadHistory}>Обновить</button>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead><tr><th>Время</th><th>Сумма</th><th>Продукт</th><th>P(фрод)</th><th>Решение</th></tr></thead>
                <tbody>
                  {history.map((r, i) => (
                    <tr key={i}>
                      <td>{new Date(r.created_at).toLocaleString("ru")}</td>
                      <td>${r.transaction_amt}</td>
                      <td>{r.product_cd}</td>
                      <td>{(r.fraud_probability * 100).toFixed(2)}%</td>
                      <td><span className={r.is_fraud ? "badge-fraud" : "badge-ok"}>{r.is_fraud ? "ФРОД" : "OK"}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
