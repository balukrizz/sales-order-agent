"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { getSalesOrder, getSalesOrders, pdfUrl, type SalesOrder } from "@/lib/api";

export default function SalesOrdersPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [sel, setSel] = useState<SalesOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    getSalesOrders()
      .then((r) => {
        setRows(r);
        if (r.length) getSalesOrder(r[0].so_number).then(setSel).catch(() => {});
      })
      .catch(() => setErr("Could not reach the backend."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-ink">Sales Orders</h1>
      <p className="text-slate-500 mt-1">Every order the agent has created, stored in the simulated ERP.</p>

      {err && <p className="mt-6 text-rose-600">{err}</p>}
      {!err && loading && <p className="mt-6 text-slate-400">Loading…</p>}
      {!err && !loading && rows.length === 0 && (
        <p className="mt-6 text-slate-400">No Sales Orders yet. Process a PO first.</p>
      )}

      {rows.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 mt-6">
          <div className="bg-white rounded-2xl shadow-soft border border-cardline overflow-hidden">
            {rows.map((r) => (
              <button
                key={r.so_number}
                onClick={() => getSalesOrder(r.so_number).then(setSel).catch(() => {})}
                className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors ${
                  sel?.so_number === r.so_number ? "bg-teal/5" : ""
                }`}
              >
                <div className="font-semibold text-ink mono">{r.so_number}</div>
                <div className="text-xs text-slate-500">
                  {r.customer_name} · {r.currency} {Number(r.total_value).toLocaleString()}
                </div>
              </button>
            ))}
          </div>

          <div className="bg-white rounded-2xl shadow-soft border border-cardline p-6">
            {sel ? (
              <>
                <div className="flex items-baseline justify-between">
                  <div>
                    <div className="text-2xl font-bold text-teal-dark mono">{sel.so_number}</div>
                    <div className="text-sm text-slate-600 mt-0.5">
                      {sel.customer_name} · PO {sel.po_number}
                    </div>
                  </div>
                  <a
                    href={pdfUrl(sel.so_number)}
                    target="_blank"
                    className="text-sm text-teal-dark hover:underline flex items-center gap-1.5"
                  >
                    <Download size={15} /> PDF
                  </a>
                </div>
                <table className="w-full text-sm mt-5">
                  <thead>
                    <tr className="text-left text-slate-400 border-b border-cardline">
                      <th className="py-1.5 font-medium">Material</th>
                      <th className="py-1.5 font-medium text-right">Qty</th>
                      <th className="py-1.5 font-medium text-right">Price</th>
                      <th className="py-1.5 font-medium text-right">Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sel.items.map((it, i) => (
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
                    Net <b className="text-ink">{sel.currency} {sel.net_value.toLocaleString()}</b>
                  </div>
                  <div className="text-slate-500">
                    GST ({Math.round(sel.tax_rate * 100)}%){" "}
                    <b className="text-ink">{sel.currency} {sel.tax_amount.toLocaleString()}</b>
                  </div>
                  <div className="text-base">
                    Total{" "}
                    <b className="text-teal-dark">
                      {sel.currency} {sel.total_value.toLocaleString()}
                    </b>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-slate-400 text-sm py-10 text-center">Select a Sales Order.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
