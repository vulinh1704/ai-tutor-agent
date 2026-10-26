"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { detectLanguage, translate, type MessageKey } from "@/lib/i18n";
import type { Language } from "@/lib/types";

interface I18n {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: MessageKey, values?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18n | null>(null);

function browserLanguage(): Language {
  return typeof navigator === "undefined" ? "en" : detectLanguage(navigator.languages);
}

/** UI language: the browser's at first, then the learner's choice. Client-only. */
export function I18nProvider({
  children,
  initialLanguage,
}: {
  children: React.ReactNode;
  initialLanguage?: Language;
}) {
  const [language, setLanguage] = useState<Language>(() => initialLanguage ?? browserLanguage());

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<I18n>(
    () => ({
      language,
      setLanguage,
      t: (key, values) => translate(language, key, values),
    }),
    [language],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside <I18nProvider>");
  return context;
}
