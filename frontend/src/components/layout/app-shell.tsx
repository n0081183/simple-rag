"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  Database,
  FileCheck,
  Settings,
  Moon,
  Sun,
  Monitor,
} from "lucide-react";
import { useAppStore, type ThemeMode } from "@/stores/app-store";
import { t, type Locale } from "@/i18n";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", icon: FileCheck, key: "nav.verify" },
  { href: "/kb/", icon: Database, key: "nav.kb" },
  { href: "/settings/", icon: Settings, key: "nav.settings" },
];

function ThemeSync({ theme }: { theme: ThemeMode }) {
  useEffect(() => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = theme === "dark" || (theme === "system" && prefersDark);
    root.classList.toggle("dark", dark);
  }, [theme]);
  return null;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { locale, theme, setLocale, setTheme } = useAppStore();

  return (
    <>
      <ThemeSync theme={theme} />
      <div className="flex min-h-screen bg-background text-foreground">
        <aside className="flex w-56 shrink-0 flex-col border-r border-[hsl(var(--soc)/0.25)] bg-sidebar text-sidebar-foreground">
          <div className="border-b border-[hsl(var(--soc)/0.2)] px-4 py-4">
            <div className="text-sm font-semibold tracking-tight text-[hsl(var(--soc))]">
              {t(locale, "app.name")}
            </div>
            <div className="text-xs text-muted-foreground mt-0.5">
              {t(locale, "app.tagline")}
            </div>
          </div>
          <nav className="flex-1 space-y-0.5 p-3">
            {navItems.map(({ href, icon: Icon, key }) => {
              const testId =
                href === "/" ? "nav-verify" : href.startsWith("/kb") ? "nav-kb" : "nav-settings";
              const active =
                href === "/"
                  ? pathname === "/" || pathname === ""
                  : pathname.startsWith(href.replace(/\/$/, ""));
              return (
                <Link
                  key={href}
                  href={href}
                  data-testid={testId}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary/15 text-[hsl(var(--soc))] border border-[hsl(var(--soc)/0.3)]"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                  {t(locale, key)}
                </Link>
              );
            })}
          </nav>
          <SidebarFooter locale={locale} theme={theme} setLocale={setLocale} setTheme={setTheme} />
        </aside>
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
        </main>
      </div>
    </>
  );
}

function SidebarFooter({
  locale,
  theme,
  setLocale,
  setTheme,
}: {
  locale: Locale;
  theme: ThemeMode;
  setLocale: (l: Locale) => void;
  setTheme: (t: ThemeMode) => void;
}) {
  return (
    <div className="border-t border-border p-3 space-y-2">
      <div className="flex gap-1">
        {(["pl", "en"] as Locale[]).map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setLocale(l)}
            className={cn(
              "flex-1 rounded px-2 py-1 text-xs font-medium uppercase",
              locale === l
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            )}
          >
            {l}
          </button>
        ))}
      </div>
      <div className="flex gap-1">
        {(
          [
            ["light", Sun],
            ["dark", Moon],
            ["system", Monitor],
          ] as const
        ).map(([mode, Icon]) => (
          <button
            key={mode}
            type="button"
            onClick={() => setTheme(mode)}
            className={cn(
              "flex-1 flex justify-center rounded p-1.5",
              theme === mode
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:bg-muted/50"
            )}
            aria-label={mode}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        ))}
      </div>
    </div>
  );
}
