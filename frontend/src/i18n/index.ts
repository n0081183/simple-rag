import { en } from "./en";
import { pl } from "./pl";

export type Locale = "pl" | "en";

const dictionaries = { pl, en };

export function t(locale: Locale, key: string): string {
  const parts = key.split(".");
  let node: unknown = dictionaries[locale];
  for (const p of parts) {
    if (node && typeof node === "object" && p in node) {
      node = (node as Record<string, unknown>)[p];
    } else {
      return key;
    }
  }
  return typeof node === "string" ? node : key;
}

export { en, pl };
