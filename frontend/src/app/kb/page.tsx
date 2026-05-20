"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Gauge,
  Loader2,
  XCircle,
  Zap,
} from "lucide-react";
import { CortexLogo } from "@/components/brand/logo";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";
import { API_BASE, cn } from "@/lib/utils";

const PRODUCTS = ["xdr", "xsiam", "xsoar", "xpanse", "cortex_cloud", "agentix"];

const SYNC_PRESETS = [
  { key: "safe", rate: 0.5, workers: 2 },
  { key: "default", rate: 1.0, workers: 4 },
  { key: "fast", rate: 2.0, workers: 4 },
  { key: "aggressive", rate: 2.0, workers: 8 },
] as const;

const STORAGE_RATE = "cortex_workbench_kb_rate";
const STORAGE_WORKERS = "cortex_workbench_kb_workers";

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
  if (state === "running") return <Loader2 className="h-4 w-4 animate-spin text-soc" />;
  if (state === "done") return <CheckCircle2 className="h-4 w-4 text-soc" />;
  if (state === "failed") return <XCircle className="h-4 w-4 text-destructive" />;
  return <Circle className="h-4 w-4 text-muted-foreground" />;
}

function presetLabel(locale: string, key: (typeof SYNC_PRESETS)[number]["key"]) {
  const map = {
    safe: "kb.ratePresetSafe",
    default: "kb.ratePresetDefault",
    fast: "kb.ratePresetFast",
    aggressive: "kb.ratePresetAggressive",
  } as const;
  return t(locale as "pl" | "en", map[key]);
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
  const [rateLimit, setRateLimit] = useState(1.0);
  const [topicWorkers, setTopicWorkers] = useState(4);
  const [gpuInfo, setGpuInfo] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    const savedRate = localStorage.getItem(STORAGE_RATE);
    const savedWorkers = localStorage.getItem(STORAGE_WORKERS);
    if (savedRate) {
      const v = parseFloat(savedRate);
      if (!Number.isNaN(v) && v >= 0.1 && v <= 2) setRateLimit(v);
    }
    if (savedWorkers) {
      const w = parseInt(savedWorkers, 10);
      if (!Number.isNaN(w) && w >= 1 && w <= 8) setTopicWorkers(w);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_RATE, String(rateLimit));
    localStorage.setItem(STORAGE_WORKERS, String(topicWorkers));
  }, [rateLimit, topicWorkers]);

  const aggregateRps = rateLimit * topicWorkers;
  const rateHigh = rateLimit >= 1.5;
  const workersHigh = topicWorkers > 4;

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
      if (!res.ok) {
        const detail = data.detail;
        const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
        throw new Error(msg || "Connection failed");
      }
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
          rate_limit_rps: rateLimit,
          topic_workers: topicWorkers,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail?.toString?.() || res.statusText);
      }
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
      <header className="border-l-4 border-soc pl-4 flex gap-4 items-start">
        <CortexLogo size={48} className="hidden sm:block" />
        <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {t(locale, "kb.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground max-w-2xl">{t(locale, "kb.subtitle")}</p>
        </div>
      </header>

      {!kbLoaded && (
        <div className="soc-panel-accent px-4 py-3 text-sm">
          <span className="font-medium text-soc">{t(locale, "kb.noKb")}</span>
          <span className="text-muted-foreground"> — {t(locale, "kb.noKbHint")}</span>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="soc-panel soc-glow p-5 space-y-4">
          <h2 className="text-sm font-medium text-soc">{t(locale, "kb.stepCredentials")}</h2>
          <input
            type="password"
            placeholder={t(locale, "kb.apiKey")}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:border-soc focus:ring-1 focus:ring-soc/40"
            onBlur={(e) => saveRunPodKey(e.target.value)}
          />
          <input
            type="text"
            placeholder={t(locale, "kb.podId")}
            value={podId}
            onChange={(e) => setPodId(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono focus:border-soc focus:ring-1 focus:ring-soc/40"
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
          {gpuInfo && (
            <p className="text-xs text-soc font-mono bg-soc-muted/50 rounded px-2 py-1">{gpuInfo}</p>
          )}
          <button
            type="button"
            onClick={() => handleTestConnection()}
            className="text-sm text-soc-cyan hover:underline underline-offset-2"
          >
            {t(locale, "kb.testConnection")}
          </button>
        </section>

        <section className="soc-panel p-5 space-y-4">
          <h2 className="text-sm font-medium text-soc">{t(locale, "kb.stepScope")}</h2>
          <div className="grid grid-cols-2 gap-2">
            {PRODUCTS.map((p) => (
              <label
                key={p}
                className="flex items-center gap-2 text-sm capitalize rounded-md px-2 py-1 hover:bg-soc-muted/40"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(p)}
                  onChange={() => toggleProduct(p)}
                  disabled={syncing}
                  className="accent-[hsl(var(--soc))]"
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
              className="accent-[hsl(var(--soc))]"
            />
            {t(locale, "kb.incremental")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={!incremental}
              onChange={() => setIncremental(false)}
              className="accent-[hsl(var(--soc))]"
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
        </section>
      </div>

      <section className="soc-panel soc-glow p-5 space-y-5" data-testid="kb-download-settings">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-soc-cyan" />
          <h2 className="text-sm font-medium text-soc">{t(locale, "kb.stepDownload")}</h2>
        </div>
        <p className="text-sm text-muted-foreground">{t(locale, "kb.rateLimitHint")}</p>
        <p className="text-xs text-muted-foreground italic">{t(locale, "kb.estHint")}</p>

        <div className="flex flex-wrap gap-2">
          {SYNC_PRESETS.map(({ key, rate, workers }) => {
            const active =
              Math.abs(rateLimit - rate) < 0.01 && topicWorkers === workers;
            return (
              <button
                key={key}
                type="button"
                disabled={syncing}
                onClick={() => {
                  setRateLimit(rate);
                  setTopicWorkers(workers);
                }}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium border transition-colors inline-flex items-center gap-1",
                  active
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border text-muted-foreground hover:border-soc hover:text-foreground"
                )}
              >
                {key === "aggressive" && <Zap className="h-3 w-3" />}
                {presetLabel(locale, key)}
              </button>
            );
          })}
        </div>

        <p className="text-sm font-mono text-soc-cyan">
          {t(locale, "kb.aggregateRate")}: ≈ {aggregateRps.toFixed(1)} req/s
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-2">
            <span className="text-sm font-medium">
              {t(locale, "kb.rateLimit")}:{" "}
              <span className="font-mono text-soc">{rateLimit.toFixed(2)}</span>
            </span>
            <input
              type="range"
              min={0.1}
              max={4}
              step={0.05}
              value={rateLimit}
              onChange={(e) => setRateLimit(parseFloat(e.target.value))}
              disabled={syncing}
              className="w-full accent-[hsl(var(--soc))]"
              data-testid="kb-rate-slider"
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-medium">
              {t(locale, "kb.topicWorkers")}:{" "}
              <span className="font-mono text-soc-cyan">{topicWorkers}</span>
            </span>
            <input
              type="range"
              min={1}
              max={8}
              step={1}
              value={topicWorkers}
              onChange={(e) => setTopicWorkers(parseInt(e.target.value, 10))}
              disabled={syncing}
              className="w-full accent-[hsl(var(--soc-cyan))]"
              data-testid="kb-workers-slider"
            />
            <span className="text-xs text-muted-foreground">{t(locale, "kb.topicWorkersHint")}</span>
          </label>
        </div>

        {(rateHigh || workersHigh) && (
          <div
            className="flex gap-2 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-foreground"
            role="alert"
          >
            <AlertTriangle className="h-4 w-4 shrink-0 text-warning mt-0.5" />
            <div className="space-y-1">
              {rateHigh && <p>{t(locale, "kb.rateWarningHigh")}</p>}
              {workersHigh && <p>{t(locale, "kb.rateWarningWorkers")}</p>}
            </div>
          </div>
        )}

        <button
          type="button"
          data-testid="kb-start-btn"
          onClick={handleStart}
          disabled={syncing || (!dryRun && !podId)}
          className="rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-md hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {syncing ? t(locale, "common.loading") : t(locale, "kb.start")}
        </button>
      </section>

      <section className="soc-panel p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-soc">{t(locale, "kb.stepProgress")}</h2>
          {jobStatus && (
            <span className="text-xs font-mono text-soc-cyan">
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
            "rounded-md bg-muted/50 border border-border/80 p-3 text-xs font-mono max-h-64 overflow-auto",
            "text-muted-foreground"
          )}
        >
          {logs.length ? logs.join("\n") : "—"}
        </pre>
      </section>
    </div>
  );
}
