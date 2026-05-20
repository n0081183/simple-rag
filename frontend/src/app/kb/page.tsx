"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
} from "lucide-react";
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
  "atomic_swap",
];

type StepState = "pending" | "running" | "done" | "failed";

function StepIcon({ state }: { state: StepState }) {
  if (state === "running") return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  if (state === "done") return <CheckCircle2 className="h-4 w-4 text-primary" />;
  if (state === "failed") return <XCircle className="h-4 w-4 text-destructive" />;
  return <Circle className="h-4 w-4 text-muted-foreground" />;
}

export default function KbPage() {
  const locale = useAppStore((s) => s.locale);
  const [selected, setSelected] = useState<string[]>(PRODUCTS);
  const [kbLoaded, setKbLoaded] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [steps, setSteps] = useState<Record<string, StepState>>({});
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [progressPct, setProgressPct] = useState(0);
  const [podId, setPodId] = useState("");
  const [sshHost, setSshHost] = useState("");
  const [sshPort, setSshPort] = useState("22");
  const [incremental, setIncremental] = useState(true);
  const [dryRun, setDryRun] = useState(false);
  const [releaseNotes, setReleaseNotes] = useState(false);
  const [gpuInfo, setGpuInfo] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const refreshKb = useCallback(() => {
    fetch(`${API_BASE}/api/kb/status`)
      .then((r) => r.json())
      .then((d) => setKbLoaded(d.loaded))
      .catch(() => setKbLoaded(false));
  }, []);

  useEffect(() => {
    refreshKb();
  }, [refreshKb, jobStatus]);

  function toggleProduct(p: string) {
    setSelected((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  async function saveRunPodKey(key: string) {
    if (!key.trim()) return;
    await fetch(`${API_BASE}/api/settings/secrets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "runpod_api_key", value: key }),
    });
  }

  async function handleTestConnection(apiKey?: string) {
    if (apiKey) await saveRunPodKey(apiKey);
    try {
      const res = await fetch(`${API_BASE}/api/kb/test-connection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pod_id: podId,
          ssh_host: sshHost || null,
          ssh_port: parseInt(sshPort, 10) || 22,
          dry_run: dryRun,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Connection failed");
      setGpuInfo(data.gpu || data.message || "OK");
    } catch (e) {
      setGpuInfo(`Error: ${e}`);
    }
  }

  async function handleStart() {
    setSyncing(true);
    setLogs([]);
    setSteps({});
    setJobStatus("queued");
    try {
      const res = await fetch(`${API_BASE}/api/kb/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          products: selected,
          incremental,
          pod_id: podId,
          ssh_host: sshHost || null,
          ssh_port: parseInt(sshPort, 10) || 22,
          include_release_notes: releaseNotes,
          dry_run: dryRun,
        }),
      });
      const { job_id } = await res.json();
      const interval = setInterval(async () => {
        const st = await fetch(`${API_BASE}/api/kb/sync/${job_id}`);
        const data = await st.json();
        if (data.logs?.length) setLogs(data.logs);
        if (data.steps) setSteps(data.steps);
        if (data.progress_pct != null) setProgressPct(data.progress_pct);
        setJobStatus(data.status);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
          setSyncing(false);
          refreshKb();
        }
      }, 1200);
    } catch (e) {
      setLogs((l) => [...l, `Error: ${e}`]);
      setSyncing(false);
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
            onBlur={(e) => saveRunPodKey(e.target.value)}
          />
          <input
            type="text"
            placeholder={t(locale, "kb.podId")}
            value={podId}
            onChange={(e) => setPodId(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono"
          />
          <div className="flex gap-2">
            <input
              type="text"
              placeholder={t(locale, "kb.sshHost")}
              value={sshHost}
              onChange={(e) => setSshHost(e.target.value)}
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm font-mono"
            />
            <input
              type="text"
              value={sshPort}
              onChange={(e) => setSshPort(e.target.value)}
              className="w-20 rounded-md border border-border bg-background px-3 py-2 text-sm font-mono"
              title={t(locale, "kb.sshPort")}
              aria-label={t(locale, "kb.sshPort")}
            />
          </div>
          {gpuInfo && <p className="text-xs text-muted-foreground font-mono">{gpuInfo}</p>}
          <button
            type="button"
            onClick={() => handleTestConnection()}
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
                  disabled={syncing}
                />
                {p.replace("_", " ")}
              </label>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={incremental}
              onChange={() => setIncremental(true)}
            />
            {t(locale, "kb.incremental")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={!incremental}
              onChange={() => setIncremental(false)}
            />
            {t(locale, "kb.fullRebuild")}
          </label>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={releaseNotes}
              onChange={(e) => setReleaseNotes(e.target.checked)}
            />
            {t(locale, "kb.releaseNotes")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            {t(locale, "kb.dryRun")}
          </label>
          <button
            type="button"
            data-testid="kb-start-btn"
            onClick={handleStart}
            disabled={syncing || (!dryRun && !podId)}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {syncing ? t(locale, "common.loading") : t(locale, "kb.start")}
          </button>
        </section>
      </div>

      <section className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium">{t(locale, "kb.stepProgress")}</h2>
          {jobStatus && (
            <span className="text-xs font-mono text-muted-foreground">
              {jobStatus} {progressPct > 0 && `· ${progressPct}%`}
            </span>
          )}
        </div>
        <ul className="space-y-2 mb-4">
          {STEPS.map((step) => (
            <li key={step} className="flex items-center gap-2 text-sm font-mono">
              <StepIcon state={(steps[step] as StepState) || "pending"} />
              {step.replace(/_/g, " ")}
            </li>
          ))}
        </ul>
        <pre
          className={cn(
            "rounded-md bg-muted/50 p-3 text-xs font-mono max-h-64 overflow-auto",
            "text-muted-foreground"
          )}
        >
          {logs.length ? logs.join("\n") : "—"}
        </pre>
      </section>
    </div>
  );
}
