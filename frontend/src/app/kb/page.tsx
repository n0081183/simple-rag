"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";
import { API_BASE, cn } from "@/lib/utils";

const PRODUCTS = ["xdr", "xsiam", "xsoar", "xpanse", "cortex_cloud", "agentix"];

const STEPS = [
  "bootstrap",
  "clone_docs_sync",
  "sync_docs",
  "chunk_html",
  "embed_gpu",
  "build_index",
  "export_snapshot",
  "download_local",
];

export default function KbPage() {
  const locale = useAppStore((s) => s.locale);
  const [selected, setSelected] = useState<string[]>(PRODUCTS);
  const [kbLoaded, setKbLoaded] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/kb/status`)
      .then((r) => r.json())
      .then((d) => setKbLoaded(d.loaded))
      .catch(() => setKbLoaded(false));
  }, []);

  function toggleProduct(p: string) {
    setSelected((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  async function handleStart() {
    setLogs([`[${new Date().toISOString()}] Starting sync (mock)…`]);
    try {
      const res = await fetch(`${API_BASE}/api/kb/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          products: selected,
          incremental: true,
          pod_id: "pod-placeholder",
        }),
      });
      const { job_id } = await res.json();
      const interval = setInterval(async () => {
        const st = await fetch(`${API_BASE}/api/kb/sync/${job_id}`);
        const data = await st.json();
        if (data.logs?.length) setLogs(data.logs);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
        }
      }, 1500);
    } catch (e) {
      setLogs((l) => [...l, `Error: ${e}`]);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t(locale, "kb.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground max-w-2xl">{t(locale, "kb.subtitle")}</p>
      </header>

      {!kbLoaded && (
        <div className="rounded-md border border-border bg-muted/30 px-4 py-3 text-sm">
          <span className="font-medium">{t(locale, "kb.noKb")}</span>
          <span className="text-muted-foreground"> — {t(locale, "kb.noKbHint")}</span>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-border bg-card p-5 space-y-4">
          <h2 className="text-sm font-medium">{t(locale, "kb.stepCredentials")}</h2>
          <input
            type="password"
            placeholder={t(locale, "kb.apiKey")}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder={t(locale, "kb.podId")}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono"
          />
          <button
            type="button"
            className="text-sm text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
          >
            {t(locale, "kb.testConnection")}
          </button>
        </section>

        <section className="rounded-lg border border-border bg-card p-5 space-y-4">
          <h2 className="text-sm font-medium">{t(locale, "kb.stepScope")}</h2>
          <div className="grid grid-cols-2 gap-2">
            {PRODUCTS.map((p) => (
              <label key={p} className="flex items-center gap-2 text-sm capitalize">
                <input
                  type="checkbox"
                  checked={selected.includes(p)}
                  onChange={() => toggleProduct(p)}
                  className="rounded border-border"
                />
                {p.replace("_", " ")}
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={handleStart}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            {t(locale, "kb.start")}
          </button>
        </section>
      </div>

      <section className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-sm font-medium mb-4">{t(locale, "kb.stepProgress")}</h2>
        <ul className="space-y-2 mb-4">
          {STEPS.map((step, i) => (
            <li key={step} className="flex items-center gap-2 text-sm font-mono">
              {i === 2 ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : i < 2 ? (
                <CheckCircle2 className="h-4 w-4 text-primary" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground" />
              )}
              {step.replace(/_/g, " ")}
            </li>
          ))}
        </ul>
        <pre
          className={cn(
            "rounded-md bg-muted/50 p-3 text-xs font-mono max-h-48 overflow-auto",
            "text-muted-foreground"
          )}
        >
          {logs.length ? logs.join("\n") : "—"}
        </pre>
      </section>
    </div>
  );
}
