"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getKpis, getSalesOrders } from "@/lib/api";

type Kpis = {
  orders: number;
  avg_time: number;
  avg_val: number;
  avg_conf: number;
  total_value: number;
  today: number;
};

export default function DashboardPage() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([getKpis(), getSalesOrders()])
      .then(([k, r]) => {
        setKpis(k);
        setRows(r);
      })
      .catch(() => setErr("Could not reach the backend."));
  }, []);

  const chartData = rows.map((r) => ({
    name: (r.customer_name || "").split(" ").slice(0, 2).join(" "),
    value: Number(r.total_value),
  }));

  const cards = kpis
    ? [
        { label: "Sales Orders", value: kpis.orders },
        { label: "Created Today", value: kpis.today },
        { label: "Avg Confidence", value: `${kpis.avg_conf}%` },
        { label: "Avg Validation", value: `${kpis.avg_val}%` },
        { label: "Avg Time", value: `${kpis.avg_time}s` },
        { label: "Total Value", value: `₹${Number(kpis.total_value).toLocaleString()}` },
      ]
    : [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-ink">Dashboard</h1>
      <p className="text-slate-500 mt-1">Live metrics from the simulated ERP.</p>

      {err && <p className="mt-6 text-rose-600">{err}</p>}

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-6">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-2xl shadow-soft border border-cardline p-5">
            <div className="text-xs uppercase tracking-wide text-slate-400">{c.label}</div>
            <div className="text-2xl font-bold text-ink mt-1">{c.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-2xl shadow-soft border border-cardline p-6 mt-6">
        <h3 className="font-semibold text-ink mb-4">Order Value by Customer</h3>
        {chartData.length === 0 ? (
          <div className="text-sm text-slate-400 py-10 text-center">
            No orders yet — process a PO to populate the dashboard.
          </div>
        ) : (
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} />
                <Tooltip
                  formatter={(v: number) => `₹${v.toLocaleString()}`}
                  contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
                />
                <Bar dataKey="value" fill="#0EA5A5" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {rows.length > 0 && (
        <div className="bg-white rounded-2xl shadow-soft border border-cardline p-6 mt-6">
          <h3 className="font-semibold text-ink mb-4">Recent Orders</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 border-b border-cardline">
                <th className="py-2 font-medium">SO</th>
                <th className="py-2 font-medium">Customer</th>
                <th className="py-2 font-medium">PO</th>
                <th className="py-2 font-medium text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 12).map((r) => (
                <tr key={r.so_number} className="border-b border-slate-50">
                  <td className="py-2 mono text-ink">{r.so_number}</td>
                  <td className="py-2 text-slate-600">{r.customer_name}</td>
                  <td className="py-2 text-slate-500">{r.po_number}</td>
                  <td className="py-2 text-right">
                    {r.currency} {Number(r.total_value).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
