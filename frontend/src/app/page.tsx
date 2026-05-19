"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Download, Upload } from "lucide-react";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";
import { cn, API_BASE } from "@/lib/utils";
import {
  ResultsTable,
  type VerificationRow,
} from "@/components/requirements/results-table";

type Req = {
  id: string;
  title: string;
  text: string;
  enabled: boolean;
};

async function poll<T>(fn: () => Promise<T>, ok: (d: T) => boolean, ms = 1500, max = 120): Promise<T> {
  for (let i = 0; i < max; i++) {
    const d = await fn();
    if (ok(d)) return d;
    await new Promise((r) => setTimeout(r, ms));
  }
  throw new Error("timeout");
}

export default function VerifyPage() {
  const locale = useAppStore((s) => s.locale);
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [autoDetect, setAutoDetect] = useState(false);
  const [product, setProduct] = useState("xdr");
  const [products, setProducts] = useState<{ id: string; chunk_count: number }[]>([]);
  const [phase, setPhase] = useState<"input" | "review" | "results">("input");
  const [loading, setLoading] = useState(false);
  const [extractJobId, setExtractJobId] = useState<string | null>(null);
  const [verifyJobId, setVerifyJobId] = useState<string | null>(null);
  const [requirements, setRequirements] = useState<Req[]>([]);
  const [results, setResults] = useState<VerificationRow[]>([]);
  const [verifyProgress, setVerifyProgress] = useState({ done: 0, total: 0 });
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/kb/products`)
      .then((r) => r.json())
      .then((d) => {
        const list = d.products || [];
        setProducts(list);
        if (list.length && !list.find((p: { id: string }) => p.id === product)) {
          setProduct(list[0].id);
        }
      })
      .catch(() => setProducts([{ id: "xdr", chunk_count: 0 }]));
  }, [product]);

  const handleExtract = useCallback(async () => {
    if (!text.trim() && !file) return;
    setLoading(true);
    try {
      let jobId: string;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("language", locale);
        fd.append("auto_detect_product", String(autoDetect));
        if (text.trim()) fd.append("pasted_text", text.trim());
        const res = await fetch(`${API_BASE}/api/requirements/extract/upload`, {
          method: "POST",
          body: fd,
        });
        const data = await res.json();
        jobId = data.job_id;
      } else {
        const res = await fetch(`${API_BASE}/api/requirements/extract`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text,
            language: locale,
            auto_detect_product: autoDetect,
          }),
        });
        const data = await res.json();
        jobId = data.job_id;
      }
      setExtractJobId(jobId);
      const final = await poll(
        () => fetch(`${API_BASE}/api/requirements/extract/${jobId}`).then((r) => r.json()),
        (d) => d.status === "completed" || d.status === "failed"
      );
      if (final.status === "failed") throw new Error(final.error || "extraction failed");
      setRequirements(
        (final.requirements || []).map((r: Req) => ({
          ...r,
          enabled: r.enabled !== false,
        }))
      );
      if (final.product_suggestion) setProduct(final.product_suggestion);
      setPhase("review");
    } finally {
      setLoading(false);
    }
  }, [text, file, locale, autoDetect]);

  const handleVerify = useCallback(async () => {
    if (!extractJobId) return;
    setLoading(true);
    setPhase("results");
    try {
      await fetch(`${API_BASE}/api/requirements/extract/${extractJobId}/requirements`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirements }),
      });
      const res = await fetch(`${API_BASE}/api/requirements/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: extractJobId,
          product,
          language: locale,
          requirement_ids: requirements.filter((r) => r.enabled).map((r) => r.id),
        }),
      });
      const { job_id } = await res.json();
      setVerifyJobId(job_id);
      const final = await poll(
        () => fetch(`${API_BASE}/api/requirements/verify/${job_id}`).then((r) => r.json()),
        (d) => d.status === "completed" || d.status === "failed",
        2000
      );
      if (final.status === "failed") throw new Error(final.error || "verify failed");
      setVerifyProgress({ done: final.progress, total: final.total });
      setResults(final.results || []);
    } finally {
      setLoading(false);
    }
  }, [extractJobId, requirements, product, locale]);

  const exportMd = () => {
    if (!verifyJobId) return;
    window.open(
      `${API_BASE}/api/requirements/verify/${verifyJobId}/report.md?language=${locale}&auto_detect_warning=${autoDetect}`,
      "_blank"
    );
  };

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t(locale, "verify.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground max-w-2xl">{t(locale, "verify.subtitle")}</p>
      </header>

      {autoDetect && (
        <div
          role="alert"
          className="flex gap-3 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          {t(locale, "verify.autoDetectWarning")}
        </div>
      )}

      {phase === "input" && (
        <>
          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-lg border border-border bg-card p-5 space-y-4">
              <label className="text-sm font-medium">{t(locale, "verify.upload")}</label>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.doc"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="flex w-full flex-col items-center justify-center rounded-md border border-dashed border-border py-10 text-muted-foreground hover:bg-muted/30"
              >
                <Upload className="h-8 w-8 mb-2 opacity-50" strokeWidth={1.5} />
                <span className="text-xs">{file?.name || "PDF, DOCX"}</span>
              </button>
            </div>
            <div className="rounded-lg border border-border bg-card p-5 space-y-4">
              <label className="text-sm font-medium" htmlFor="req-text">
                {t(locale, "verify.paste")}
              </label>
              <textarea
                id="req-text"
                rows={10}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={t(locale, "verify.pastePlaceholder")}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono resize-y min-h-[200px] focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </section>
          <div>
            <label className="text-sm font-medium">{t(locale, "verify.product")}</label>
            <select
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              className="mt-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} ({p.chunk_count})
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoDetect}
                onChange={(e) => setAutoDetect(e.target.checked)}
              />
              {t(locale, "verify.autoDetect")}
            </label>
            <button
              type="button"
              onClick={handleExtract}
              disabled={loading || (!text.trim() && !file)}
              className={cn(
                "rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
                "hover:opacity-90 disabled:opacity-50"
              )}
            >
              {loading ? t(locale, "common.loading") : t(locale, "verify.extract")}
            </button>
          </div>
        </>
      )}

      {phase === "review" && (
        <section className="rounded-lg border border-border overflow-hidden">
          <div className="border-b border-border bg-muted/40 px-4 py-3 flex justify-between items-center">
            <h2 className="text-sm font-medium">{t(locale, "verify.review")}</h2>
            <span className="text-xs text-muted-foreground">{requirements.length} items</span>
          </div>
          <ul className="divide-y divide-border max-h-[28rem] overflow-auto">
            {requirements.map((r) => (
              <li key={r.id} className="px-4 py-3 flex gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={r.enabled}
                  onChange={(e) =>
                    setRequirements((prev) =>
                      prev.map((x) => (x.id === r.id ? { ...x, enabled: e.target.checked } : x))
                    )
                  }
                />
                <div>
                  <div className="font-medium">{r.title}</div>
                  <p className="text-muted-foreground mt-1">{r.text}</p>
                </div>
              </li>
            ))}
          </ul>
          <div className="border-t border-border px-4 py-3 flex gap-3">
            <button
              type="button"
              onClick={() => setPhase("input")}
              className="rounded-md border border-border px-4 py-2 text-sm"
            >
              {t(locale, "common.cancel")}
            </button>
            <button
              type="button"
              onClick={handleVerify}
              disabled={loading}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              {loading ? t(locale, "common.loading") : t(locale, "verify.runVerification")}
            </button>
          </div>
        </section>
      )}

      {phase === "results" && (
        <section className="space-y-4">
          {loading && (
            <p className="text-sm text-muted-foreground">
              {t(locale, "common.loading")}{" "}
              {verifyProgress.total > 0 &&
                `(${verifyProgress.done}/${verifyProgress.total})`}
            </p>
          )}
          {!loading && results.length > 0 && (
            <>
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={exportMd}
                  className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted"
                >
                  <Download className="h-4 w-4" />
                  Markdown
                </button>
              </div>
              <ResultsTable rows={results} />
            </>
          )}
        </section>
      )}
    </div>
  );
}

