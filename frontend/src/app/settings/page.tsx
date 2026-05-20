"use client";

import { useCallback, useEffect, useState } from "react";
import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";
import { API_BASE } from "@/lib/utils";

type LlmProvider = "ollama" | "anthropic";

export default function SettingsPage() {
  const { locale, setLocale } = useAppStore();
  const [provider, setProvider] = useState<LlmProvider>("ollama");
  const [hasAnthropicKey, setHasAnthropicKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/llm`);
      if (!res.ok) return;
      const data = await res.json();
      setProvider(data.provider === "anthropic" ? "anthropic" : "ollama");
      setHasAnthropicKey(Boolean(data.has_anthropic_key));
    } catch {
      /* backend offline */
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  async function saveAnthropicKey(value: string) {
    if (!value.trim()) return;
    await fetch(`${API_BASE}/api/settings/secrets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "anthropic_api_key", value: value.trim() }),
    });
    setHasAnthropicKey(true);
  }

  async function handleProviderChange(next: LlmProvider) {
    setError(null);
    setMessage(null);
    if (next === "anthropic" && !hasAnthropicKey) {
      setError(t(locale, "settings.anthropicKeyRequired"));
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings/llm`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: next }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || res.statusText);
      }
      const data = await res.json();
      setProvider(data.provider === "anthropic" ? "anthropic" : "ollama");
      setMessage(t(locale, "settings.saved"));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-8 max-w-lg">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t(locale, "settings.title")}</h1>
      </header>

      <section className="rounded-lg border border-border bg-card p-5 space-y-3">
        <h2 className="text-sm font-medium">{t(locale, "settings.language")}</h2>
        <div className="flex gap-2">
          {(["pl", "en"] as const).map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => setLocale(l)}
              className={`rounded-md px-3 py-1.5 text-sm uppercase ${
                locale === l
                  ? "bg-primary text-primary-foreground"
                  : "border border-border text-muted-foreground"
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-5 space-y-3">
        <h2 className="text-sm font-medium">{t(locale, "settings.llm")}</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="llm"
            data-testid="settings-llm-ollama"
            checked={provider === "ollama"}
            disabled={saving}
            onChange={() => handleProviderChange("ollama")}
            className="border-border"
          />
          {t(locale, "settings.llmLocal")}
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="llm"
            data-testid="settings-llm-anthropic"
            checked={provider === "anthropic"}
            disabled={saving}
            onChange={() => handleProviderChange("anthropic")}
            className="border-border"
          />
          {t(locale, "settings.llmCloud")}
        </label>
        <input
          type="password"
          placeholder="Anthropic API key"
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          onBlur={(e) => saveAnthropicKey(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">{t(locale, "settings.keychainNote")}</p>
        {message && <p className="text-xs text-primary">{message}</p>}
        {error && <p className="text-xs text-destructive">{error}</p>}
      </section>
    </div>
  );
}
