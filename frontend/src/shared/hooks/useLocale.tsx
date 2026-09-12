import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { UiLocale } from "../i18n/strings";
import { t, type UiStringKey } from "../i18n/strings";

interface LocaleContextValue {
  locale: UiLocale;
  setLocale: (locale: UiLocale) => void;
  t: (key: UiStringKey) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

const STORAGE_KEY = "dhruva.locale";

function initialLocale(): UiLocale {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "hi" || saved === "ta") return saved;
  } catch {
    // localStorage unavailable (private mode, etc.) — fall through to default.
  }
  return "en";
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<UiLocale>(initialLocale);

  const setLocale = (next: UiLocale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // best-effort persistence only
    }
  };

  const value = useMemo<LocaleContextValue>(
    () => ({ locale, setLocale, t: (key: UiStringKey) => t(locale, key) }),
    [locale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within a LocaleProvider");
  return ctx;
}
