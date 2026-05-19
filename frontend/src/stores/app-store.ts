import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Locale } from "@/i18n";

export type ThemeMode = "light" | "dark" | "system";

interface AppState {
  locale: Locale;
  theme: ThemeMode;
  setLocale: (locale: Locale) => void;
  setTheme: (theme: ThemeMode) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      locale: "pl",
      theme: "system",
      setLocale: (locale) => set({ locale }),
      setTheme: (theme) => set({ theme }),
    }),
    { name: "siwz-rag-lite" }
  )
);
