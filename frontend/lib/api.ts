// Thin client for the FastAPI backend. Base URL comes from NEXT_PUBLIC_API_URL.

export const API =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export type AgentState = {
  key: string;
  label: string;
  status: "pending" | "running" | "completed" | "success" | "failed" | string;
  detail: string;
};

export type ValidationCheck = {
  name: string;
  passed: boolean;
  level: string;
  message: string;
  icon: string;
};

export type Validation = {
  accuracy: number;
  has_blocking_errors: boolean;
  customer_suggestions: string[];
  checks: ValidationCheck[];
  warnings: { name: string; message: string }[];
};

export type SalesOrderItem = {
  material: string;
  description: string;
  qty: number;
  unit_price: number;
  net_value: number;
};

export type SalesOrder = {
  so_number: string;
  customer_code: string;
  customer_name: string;
  po_number: string;
  currency: string;
  shipping_address: string;
  gst_number: string;
  payment_terms: string;
  status: string;
  created_at: string;
  net_value: number;
  tax_rate: number;
  tax_amount: number;
  total_value: number;
  items: SalesOrderItem[];
};

export type PipelineResult = {
  success: boolean;
  message: string;
  duplicate: boolean;
  extraction_conf: number;
  processing_time: number;
  purchase_order: any;
  validation: Validation | null;
  sales_order: SalesOrder | null;
};

export type StreamEvent = {
  agents: AgentState[];
  reasoning: string[];
  result: PipelineResult | null;
  error?: string;
};

export async function getConfig() {
  const r = await fetch(`${API}/api/config`, { cache: "no-store" });
  if (!r.ok) throw new Error("config failed");
  return r.json() as Promise<{ provider: string; model: string | null; ocr: boolean }>;
}

export async function fetchSample(kind: string): Promise<File> {
  const r = await fetch(`${API}/api/sample-po?kind=${encodeURIComponent(kind)}`, {
    cache: "no-store",
  });
  if (!r.ok) throw new Error("sample fetch failed");
  const blob = await r.blob();
  return new File([blob], `sample_${kind}.pdf`, { type: "application/pdf" });
}

export async function getKpis() {
  const r = await fetch(`${API}/api/kpis`, { cache: "no-store" });
  if (!r.ok) throw new Error("kpis failed");
  return r.json();
}

export async function getSalesOrders() {
  const r = await fetch(`${API}/api/sales-orders`, { cache: "no-store" });
  if (!r.ok) throw new Error("list failed");
  return r.json() as Promise<any[]>;
}

export async function getSalesOrder(so: string) {
  const r = await fetch(`${API}/api/sales-orders/${so}`, { cache: "no-store" });
  if (!r.ok) throw new Error("detail failed");
  return r.json() as Promise<SalesOrder>;
}

export async function resetDemo() {
  const r = await fetch(`${API}/api/reset`, { method: "POST" });
  if (!r.ok) throw new Error("reset failed");
  return r.json();
}

export function pdfUrl(so: string) {
  return `${API}/api/sales-orders/${so}/pdf`;
}

// Stream the pipeline (SSE over a POST fetch). Calls onEvent for each update.
export async function streamProcess(
  file: File,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${API}/api/process/stream`, { method: "POST", body: form });
  if (!resp.ok || !resp.body) {
    // fall back to non-streaming
    const r = await fetch(`${API}/api/process`, { method: "POST", body: form });
    const result = (await r.json()) as PipelineResult;
    onEvent({ agents: [], reasoning: [], result });
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice(6).trim();
      if (!payload || payload === "{}") continue;
      try {
        onEvent(JSON.parse(payload) as StreamEvent);
      } catch {
        /* ignore keep-alive / non-JSON frames */
      }
    }
  }
}
