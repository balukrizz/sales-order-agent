"use client";

import { ArrowRight } from "lucide-react";

const STEPS = [
  { n: 1, title: "Document Extraction Agent", desc: "Reads the PO PDF (pdfplumber → PyMuPDF → OCR) and the LLM returns schema-validated fields.", tag: "Agentic (LLM)" },
  { n: 2, title: "Validation Agent", desc: "Checks customer, materials, quantities, prices, GST and dates against master data.", tag: "Rule-based" },
  { n: 3, title: "Business Rules Agent", desc: "Duplicate-PO block, stock / partial-delivery, past-dated delivery, customer suggestions.", tag: "Rule-based" },
  { n: 4, title: "Sales Order Creation Agent", desc: "Assigns the SO number, persists to the ERP, and generates the Sales Order PDF.", tag: "Rule-based" },
];

const RULES = [
  "Customer must exist in the customer master (else top-3 suggestions).",
  "Every material must exist in the material master.",
  "Quantity > 0 and a price must be available for each line.",
  "GST number present (warning if missing).",
  "Delivery date cannot be in the past.",
  "Duplicate PO numbers never create a second Sales Order.",
  "Stock shortfall raises a “Partial Delivery Possible” warning (non-blocking).",
];

export default function ArchitecturePage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-ink">Architecture</h1>
      <p className="text-slate-500 mt-1">
        A four-agent LangChain pipeline. Schema-validated objects flow between agents — never raw LLM text.
      </p>

      <div className="bg-white rounded-2xl shadow-soft border border-cardline p-6 mt-6">
        <div className="flex flex-col gap-3">
          {STEPS.map((s, i) => (
            <div key={s.n}>
              <div className="flex items-start gap-4">
                <div className="w-9 h-9 shrink-0 rounded-full bg-teal text-white grid place-items-center font-bold">
                  {s.n}
                </div>
                <div className="flex-1 bg-slate-50 rounded-xl px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-ink">{s.title}</div>
                    <span
                      className={`text-[11px] px-2 py-0.5 rounded-full ${
                        s.tag.startsWith("Agentic")
                          ? "bg-teal/10 text-teal-dark"
                          : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {s.tag}
                    </span>
                  </div>
                  <div className="text-sm text-slate-500 mt-1">{s.desc}</div>
                </div>
              </div>
              {i < STEPS.length - 1 && (
                <div className="ml-4 my-1 text-slate-300">
                  <ArrowRight size={16} className="rotate-90" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-soft border border-cardline p-6 mt-6">
        <h3 className="font-semibold text-ink mb-3">Business rules enforced</h3>
        <ul className="grid md:grid-cols-2 gap-x-8 gap-y-2 text-sm text-slate-600">
          {RULES.map((r) => (
            <li key={r} className="flex gap-2">
              <span className="text-teal">•</span>
              <span dangerouslySetInnerHTML={{ __html: r }} />
            </li>
          ))}
        </ul>
        <p className="text-xs text-slate-400 mt-4">
          Blocking errors stop Sales Order creation; warnings are surfaced but allow the order
          through. The ERP is a local SQLite stand-in — swap the persistence call for a real
          ERP API (SAP / Oracle / Dynamics) to go live.
        </p>
      </div>
    </div>
  );
}
