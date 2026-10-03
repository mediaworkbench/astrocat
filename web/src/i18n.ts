import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import de from "./locales/de.json";
import en from "./locales/en.json";
import es from "./locales/es.json";

export const LANGUAGES = ["en", "es", "de"] as const;
export type Language = (typeof LANGUAGES)[number];

/** Language names in their own language, so everyone finds theirs. */
export const LANGUAGE_NAMES: Record<Language, string> = { en: "English", es: "Español", de: "Deutsch" };

export const resources = {
  en: { translation: en },
  es: { translation: es },
  de: { translation: de },
};

export function isLanguage(value: string): value is Language {
  return (LANGUAGES as readonly string[]).includes(value);
}

/** Before login: the browser's language if we have it, else English. */
export function browserLanguage(): Language {
  for (const tag of navigator.languages ?? [navigator.language]) {
    const base = tag.slice(0, 2).toLowerCase();
    if (isLanguage(base)) return base;
  }
  return "en";
}

export function setLanguage(language: Language): void {
  if (i18n.language !== language) void i18n.changeLanguage(language);
  document.documentElement.lang = language;
}

void i18n.use(initReactI18next).init({
  resources,
  lng: browserLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false }, // React escapes already
});
document.documentElement.lang = i18n.language;

export default i18n;
