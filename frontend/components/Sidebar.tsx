"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileUp, ListChecks, LayoutDashboard, Workflow } from "lucide-react";

const NAV = [
  { href: "/", label: "Upload & Process", icon: FileUp },
  { href: "/sales-orders", label: "Sales Orders", icon: ListChecks },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/architecture", label: "Architecture", icon: Workflow },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-64 shrink-0 border-r border-cardline bg-white min-h-screen px-4 py-6 flex flex-col">
      <div className="px-2 mb-8">
        <div className="text-lg font-bold text-ink flex items-center gap-2">
          <span className="inline-block w-7 h-7 rounded-lg bg-teal text-white grid place-items-center text-sm">
            SO
          </span>
          Sales Order Agent
        </div>
        <div className="text-xs text-slate-400 mt-1 pl-9">Agentic AI · PO → SO</div>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-teal/10 text-teal-dark"
                  : "text-slate-600 hover:bg-slate-50 hover:text-ink"
              }`}
            >
              <Icon size={18} strokeWidth={2} />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
