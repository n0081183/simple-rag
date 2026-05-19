"use client";

import { useAppStore } from "@/stores/app-store";
import { t } from "@/i18n";

export default function SettingsPage() {
  const { locale, setLocale } = useAppStore();

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
          <input type="radio" name="llm" defaultChecked className="border-border" />
          {t(locale, "settings.llmLocal")}
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="radio" name="llm" className="border-border" />
          {t(locale, "settings.llmCloud")}
        </label>
        <p className="text-xs text-muted-foreground">
          API keys are stored in the OS keychain, not in project files.
        </p>
      </section>
    </div>
  );
}
