"use client";

import { useState } from "react";
import { Upload, AlertTriangle } from "lucide-react";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/utils";

export default function VerifyPage() {
  const locale = useAppStore((s) => s.locale);
  const [text, setText] = useState("");
  const [autoDetect, setAutoDetect] = useState(false);
  const [loading, setLoading] = useState(false);
  const [requirements, setRequirements] = useState<
    { id: string; title: string; text: string; enabled: boolean }[]
  >([]);

  async function handleExtract() {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/requirements/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          language: locale,
          auto_detect_product: autoDetect,
        }),
      });
      const { job_id } = await res.json();
      await new Promise((r) => setTimeout(r, 800));
      const poll = await fetch(`${API_BASE}/api/requirements/extract/${job_id}`);
      const data = await poll.json();
      setRequirements(data.requirements || []);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">
          {t(locale, "verify.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground max-w-2xl">
          {t(locale, "verify.subtitle")}
        </p>
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

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <label className="text-sm font-medium">{t(locale, "verify.upload")}</label>
          <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-border py-10 text-muted-foreground">
            <Upload className="h-8 w-8 mb-2 opacity-50" strokeWidth={1.5} />
            <span className="text-xs">PDF, DOCX — Milestone 1</span>
          </div>
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

      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={autoDetect}
            onChange={(e) => setAutoDetect(e.target.checked)}
            className="rounded border-border"
          />
          {t(locale, "verify.autoDetect")}
        </label>
        <button
          type="button"
          onClick={handleExtract}
          disabled={loading || !text.trim()}
          className={cn(
            "rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
            "hover:opacity-90 disabled:opacity-50"
          )}
        >
          {loading ? t(locale, "common.loading") : t(locale, "verify.extract")}
        </button>
      </div>

      {requirements.length === 0 ? (
        <div className="rounded-lg border border-border bg-muted/30 px-6 py-12 text-center">
          <p className="font-medium">{t(locale, "verify.emptyTitle")}</p>
          <p className="text-sm text-muted-foreground mt-1">
            {t(locale, "verify.emptyDescription")}
          </p>
        </div>
      ) : (
        <section className="rounded-lg border border-border overflow-hidden">
          <div className="border-b border-border bg-muted/40 px-4 py-3">
            <h2 className="text-sm font-medium">{t(locale, "verify.review")}</h2>
          </div>
          <ul className="divide-y divide-border max-h-96 overflow-auto">
            {requirements.map((r) => (
              <li key={r.id} className="px-4 py-3 text-sm">
                <div className="font-medium">{r.title}</div>
                <p className="text-muted-foreground mt-1 line-clamp-2">{r.text}</p>
              </li>
            ))}
          </ul>
          <div className="border-t border-border px-4 py-3">
            <button
              type="button"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              {t(locale, "verify.runVerification")}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
