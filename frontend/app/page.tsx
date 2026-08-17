"use client";

import { useEffect, useRef, useState } from "react";
import { Upload, Play, FileText, RotateCcw, Download } from "lucide-react";
import AgentTimeline from "@/components/AgentTimeline";
import {
  API,
  fetchSample,
  pdfUrl,
  resetDemo,
  streamProcess,
  type AgentState,
  type PipelineResult,
} from "@/lib/api";

const SAMPLES = [
  { kind: "default", label: "Standard PO" },
  { kind: "success", label: "Clean success" },
  { kind: "partial", label: "Stock warning" },
  { kind: "errors", label: "Validation errors" },
];

export default function ProcessPage() {
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [running, setRunning] = useState(false);
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [reasoning, setReasoning] = useState<string[]>([]);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [err, setErr] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [reasoning]);

  async function pickSample(kind: string, label: string) {
    setErr("");
    try {
      const f = await fetchSample(kind);
      setFile(f);
      setFileName(`${label} (sample)`);
      setResult(null);
      setAgents([]);
      setReasoning([]);
    } catch {
      setErr("Could not load sample. Is the backend URL configured?");
    }
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setFileName(f.name);
    setResult(null);
    setAgents([]);
    setReasoning([]);
    setErr("");
  }

  async function run() {
    if (!file || running) return;
    setRunning(true);
    setErr("");
    setResult(null);
    setAgents([]);
    setReasoning([]);
    try {
      await streamProcess(file, (ev) => {
        if (ev.error) setErr(ev.error);
        if (ev.agents?.length) setAgents(ev.agents);
        if (ev.reasoning?.length) setReasoning(ev.reasoning);
        if (ev.result) setResult(ev.result);
      });
    } catch {
      setErr("Processing failed. Check that the backend is reachable at " + API);
    } finally {
      setRunning(false);
    }
  }

  async function doReset() {
    await resetDemo().catch(() => {});
    setResult(null);
    setAgents([]);
    setReasoning([]);
    setFile(null);
    setFileName("");
  }

  const banner = (() => {
    if (!result) return null;
    if (result.success)
      return { tone: "ok", text: result.message };
    if (result.duplicate)
      return { tone: "warn", text: result.message };
    return { tone: "err", text: result.message };
  })();

  return (
    <div>
      <Header />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-6 mt-6">
        {/* left: input */}
        <section className="bg-white rounded-2xl shadow-soft border border-cardline p-6">
          <h2 className="text-base font-semibold text-ink mb-4">1 · Upload Purchase Order</h2>

          <label className="flex items-center gap-3 border-2 border-dashed border-cardline rounded-xl px-4 py-5 cursor-pointer hover:border-teal/50 transition-colors">
            <Upload size={20} className="text-teal" />
            <span className="text-sm text-slate-600">
              {fileName || "Choose a PO PDF (or use a sample below)"}
            </span>
            <input type="file" accept="application/pdf" className="hidden" onChange={onFile} />
          </label>

          <div className="mt-4">
            <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">
              Or use a sample
            </div>
            <div className="flex flex-wrap gap-2">
              {SAMPLES.map((s) => (
                <button
                  key={s.kind}
                  onClick={() => pickSample(s.kind, s.label)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-cardline hover:border-teal hover:text-teal-dark transition-colors flex items-center gap-1.5"
                >
                  <FileText size={13} /> {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={run}
              disabled={!file || running}
              className="flex-1 bg-teal hover:bg-teal-dark disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl px-4 py-3 flex items-center justify-center gap-2 transition-colors"
            >
              <Play size={16} /> {running ? "Running pipeline…" : "Run AI Agent Pipeline"}
            </button>
            <button
              onClick={doReset}
              title="Reset demo data"
              className="px-3 py-3 rounded-xl border border-cardline text-slate-500 hover:text-ink hover:border-slate-300 transition-colors"
            >
              <RotateCcw size={16} />
            </button>
          </div>

          {err && (
            <div className="mt-4 text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
              {err}
            </div>
          )}
        </section>

        {/* right: pipeline */}
        <section className="bg-white rounded-2xl shadow-soft border border-cardline p-6">
          <h2 className="text-base font-semibold text-ink mb-4">2 · Agent Pipeline</h2>
          {agents.length === 0 && !running ? (
            <div className="text-sm text-slate-400 py-10 text-center">
              Run the pipeline to watch the four agents work.
            </div>
          ) : (
            <AgentTimeline agents={agents} />
          )}

          {reasoning.length > 0 && (
            <div
              ref={logRef}
              className="mt-4 max-h-40 overflow-y-auto bg-slate-900 rounded-xl p-3 mono text-[11px] leading-relaxed text-slate-300"
            >
              {reasoning.map((r, i) => (
                <div key={i} className="fadein">
                  <span className="text-teal">›</span> {r}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* result */}
      {banner && (
        <div
          className={`mt-6 rounded-xl px-5 py-4 text-sm font-medium fadein ${
            banner.tone === "ok"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : banner.tone === "warn"
              ? "bg-amber-50 text-amber-700 border border-amber-200"
              : "bg-rose-50 text-rose-700 border border-rose-200"
          }`}
        >
          {banner.text}
        </div>
      )}

      {result && <ResultDetail result={result} />}
    </div>
  );
}

function Header() {
  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-teal-dark font-semibold">
        Order-to-Cash Automation
      </div>
      <h1 className="text-3xl font-bold text-ink mt-1">Purchase Order → Sales Order</h1>
      <p className="text-slate-500 mt-2 max-w-2xl">
        Upload a customer PO. The AI agents read it, validate it against master data, apply
        business rules, and create the Sales Order — no manual entry.
      </p>
    </div>
  );
}

function ResultDetail({ result }: { result: PipelineResult }) {
  const v = result.validation;
  const so = result.sales_order;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-6 mt-6">
      {/* validation */}
      {v && (
        <section className="bg-white rounded-2xl shadow-soft border border-cardline p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-ink">Validation</h3>
            <span className="text-sm text-slate-500">
              accuracy <b className="text-ink">{v.accuracy}%</b>
            </span>
          </div>
          <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto pr-1">
            {v.checks.map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span>{c.icon}</span>
                <span className={c.passed ? "text-slate-600" : "text-ink font-medium"}>
                  {c.name}
                  {!c.passed && c.message && (
                    <span className="text-slate-500 font-normal"> — {c.message}</span>
                  )}
                </span>
              </div>
            ))}
          </div>
          {v.customer_suggestions.length > 0 && (
            <div className="mt-4 text-sm bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              <div className="font-medium text-amber-800 mb-1">Did you mean:</div>
              <ul className="list-disc list-inside text-amber-700">
                {v.customer_suggestions.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* sales order */}
      <section className="bg-white rounded-2xl shadow-soft border border-cardline p-6">
        <h3 className="font-semibold text-ink mb-4">Sales Order</h3>
        {so ? (
          <>
            <div className="flex items-baseline justify-between">
              <div className="text-2xl font-bold text-teal-dark mono">{so.so_number}</div>
              <a
                href={pdfUrl(so.so_number)}
                target="_blank"
                className="text-sm text-teal-dark hover:underline flex items-center gap-1.5"
              >
                <Download size={15} /> PDF
              </a>
            </div>
            <div className="text-sm text-slate-600 mt-1">
              {so.customer_name} · {so.po_number}
            </div>
            <table className="w-full text-sm mt-4">
              <thead>
                <tr className="text-left text-slate-400 border-b border-cardline">
                  <th className="py-1.5 font-medium">Material</th>
                  <th className="py-1.5 font-medium text-right">Qty</th>
                  <th className="py-1.5 font-medium text-right">Price</th>
                  <th className="py-1.5 font-medium text-right">Net</th>
                </tr>
              </thead>
              <tbody>
                {so.items.map((it, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td className="py-1.5">
                      <div className="font-medium text-ink">{it.material}</div>
                      <div className="text-xs text-slate-400">{it.description}</div>
                    </td>
                    <td className="py-1.5 text-right">{it.qty}</td>
                    <td className="py-1.5 text-right">{it.unit_price.toLocaleString()}</td>
                    <td className="py-1.5 text-right">{it.net_value.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 text-sm flex flex-col gap-1 items-end">
              <div className="text-slate-500">
                Net <b className="text-ink">{so.currency} {so.net_value.toLocaleString()}</b>
              </div>
              <div className="text-slate-500">
                GST ({Math.round(so.tax_rate * 100)}%){" "}
                <b className="text-ink">{so.currency} {so.tax_amount.toLocaleString()}</b>
              </div>
              <div className="text-base">
                Total{" "}
                <b className="text-teal-dark">
                  {so.currency} {so.total_value.toLocaleString()}
                </b>
              </div>
            </div>
          </>
        ) : (
          <div className="text-sm text-slate-400 py-10 text-center">
            No Sales Order created — resolve the validation errors and re-run.
          </div>
        )}
      </section>
    </div>
  );
}
