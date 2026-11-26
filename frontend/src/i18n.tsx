/* eslint-disable react-refresh/only-export-components --
   The provider and its hooks belong together; Fast Refresh still reloads the
   provider because the exported hooks are stable and live outside render. */
import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import {
  Lang,
  readStoredLang,
  setCurrentLang,
  storeLang,
  translate,
} from "./i18nTranslate";

export type LanguageContextValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => readStoredLang());

  useEffect(() => {
    setCurrentLang(lang);
    storeLang(lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang }), [lang]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("LanguageProvider is missing from the component tree.");
  }
  return context;
}

export function useLang(): Lang {
  return useLanguage().lang;
}

export function useSetLang(): (lang: Lang) => void {
  return useLanguage().setLang;
}

/** Returns `t(tr, vars?)`: Turkish is the key, English when selected, Turkish for unknown keys. */
export function useT(): (tr: string, vars?: Record<string, string | number>) => string {
  const { lang } = useLanguage();
  return useMemo(
    () => (tr: string, vars?: Record<string, string | number>) => translate(tr, vars, lang),
    [lang],
  );
}
