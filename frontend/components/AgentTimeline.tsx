"use client";

import { Check, Loader2, X, Circle } from "lucide-react";
import type { AgentState } from "@/lib/api";

function dot(status: string) {
  if (status === "success" || status === "completed")
    return <span className="w-7 h-7 rounded-full bg-teal text-white grid place-items-center"><Check size={16} /></span>;
  if (status === "running")
    return <span className="w-7 h-7 rounded-full bg-teal text-white grid place-items-center pulse"><Loader2 size={16} className="animate-spin" /></span>;
  if (status === "failed")
    return <span className="w-7 h-7 rounded-full bg-rose-500 text-white grid place-items-center"><X size={16} /></span>;
  return <span className="w-7 h-7 rounded-full bg-slate-200 text-slate-400 grid place-items-center"><Circle size={12} /></span>;
}

export default function AgentTimeline({ agents }: { agents: AgentState[] }) {
  if (!agents.length) return null;
  return (
    <div className="flex flex-col gap-0">
      {agents.map((a, i) => (
        <div key={a.key} className="flex gap-4">
          <div className="flex flex-col items-center">
            {dot(a.status)}
            {i < agents.length - 1 && (
              <span
                className={`w-0.5 grow my-1 ${
                  a.status === "success" || a.status === "completed"
                    ? "bg-teal/40"
                    : "bg-slate-200"
                }`}
                style={{ minHeight: 22 }}
              />
            )}
          </div>
          <div className="pb-4">
            <div
              className={`text-sm font-semibold ${
                a.status === "pending" ? "text-slate-400" : "text-ink"
              }`}
            >
              {a.label}
            </div>
            {a.detail && <div className="text-xs text-slate-500 mt-0.5">{a.detail}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
