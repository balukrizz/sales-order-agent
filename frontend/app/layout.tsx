import "./globals.css";
import type { Metadata } from "next";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "PO → Sales Order Agent",
  description: "Agentic AI that turns a Purchase Order PDF into an ERP Sales Order.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 px-8 py-8 max-w-[1200px]">{children}</main>
        </div>
      </body>
    </html>
  );
}
