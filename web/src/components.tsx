import { type ReactNode, useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type CategoryName, type ManualPlace, type Place } from "./api";

// --- icons ---------------------------------------------------------------------------------

const ICONS = {
  love: "M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.5 1.1 4.3 2.4.8-1.3 2.2-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z",
  work: "M9 4h6a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h3V6a2 2 0 0 1 2-2zm0 3h6V6H9v1zm-5 5v6h16v-6h-6v1h-4v-1H4z",
  energy: "M13.5 2 4 13.5h6.5L9.5 22 20 9.5h-6.5L13.5 2z",
  mood: "M20.3 14.6A8.5 8.5 0 0 1 9.4 3.7 8.5 8.5 0 1 0 20.3 14.6z",
  gear: "M19.4 13a7.6 7.6 0 0 0 0-2l2-1.6-2-3.4-2.4 1a7.4 7.4 0 0 0-1.7-1L15 3.5h-4l-.4 2.5a7.4 7.4 0 0 0-1.7 1l-2.4-1-2 3.4 2 1.6a7.6 7.6 0 0 0 0 2l-2 1.6 2 3.4 2.4-1a7.4 7.4 0 0 0 1.7 1l.4 2.5h4l.4-2.5a7.4 7.4 0 0 0 1.7-1l2.4 1 2-3.4-2-1.6zM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7z",
  back: "M15.5 4.5 8 12l7.5 7.5-1.6 1.6L4.8 12l9.1-9.1z",
  chevron: "M5.6 8.6 12 15l6.4-6.4L20 10.2l-8 8-8-8z",
  star: "M12 2.5l2.6 6.4 6.9.5-5.3 4.4 1.7 6.7L12 16.8l-5.9 3.7 1.7-6.7-5.3-4.4 6.9-.5z",
  pin: "M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7zm0 4.5A2.5 2.5 0 1 0 12 11.5 2.5 2.5 0 0 0 12 6.5z",
} as const;

export type IconName = keyof typeof ICONS;

export function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="currentColor" width="1.25em" height="1.25em">
      <path d={ICONS[name]} />
    </svg>
  );
}

function Paw({ on }: { on: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={on ? "on" : undefined}>
      <ellipse cx="12" cy="16.2" rx="5.2" ry="4.4" />
      <ellipse cx="5.4" cy="10.6" rx="2.2" ry="2.8" />
      <ellipse cx="9.4" cy="6.6" rx="2.2" ry="2.9" />
      <ellipse cx="14.6" cy="6.6" rx="2.2" ry="2.9" />
      <ellipse cx="18.6" cy="10.6" rx="2.2" ry="2.8" />
    </svg>
  );
}

export function PawRating({ score }: { score: number }) {
  const { t } = useTranslation();
  return (
    <span className="paws" role="img" aria-label={t("today.paws", { score })}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Paw key={n} on={n <= score} />
      ))}
    </span>
  );
}

export function CategoryIcon({ category }: { category: CategoryName }) {
  return (
    <span className="category-icon">
      <Icon name={category} />
    </span>
  );
}

// --- Mira ------------------------------------------------------------------------------------

export { Mira, MiraLoading } from "./mira";

// --- form controls ---------------------------------------------------------------------------

export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <div className="stack-sm">
      <span className="field" id={id}>
        {label}
      </span>
      <div className="segmented" role="group" aria-labelledby={id}>
        {options.map((o) => (
          <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function RadioCards<T extends string>({
  label,
  hint,
  options,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <div className="stack-sm">
      <span className="field" id={id}>
        {label}
      </span>
      {hint && <span className="field-hint">{hint}</span>}
      <div className="radio-cards" role="group" aria-labelledby={id}>
        {options.map((o) => (
          <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      {label}
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Progress({ current, total }: { current: number; total: number }) {
  return (
    <div className="progress" aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={i < current ? "done" : undefined} />
      ))}
    </div>
  );
}

/** All IANA zones the browser knows, for timezone inputs. */
export const TIMEZONES: string[] =
  typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : ["UTC"];

export function browserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

export function TimezoneInput({ label, hint, value, onChange }: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const listId = useId();
  return (
    <Field label={label} hint={hint}>
      <input
        type="text"
        list={listId}
        value={value}
        autoComplete="off"
        spellCheck={false}
        onChange={(e) => onChange(e.target.value)}
      />
      <datalist id={listId}>
        {TIMEZONES.map((tz) => (
          <option key={tz} value={tz} />
        ))}
      </datalist>
    </Field>
  );
}

// --- place search ------------------------------------------------------------------------------

export type ChosenPlace = { kind: "search"; place: Place } | { kind: "manual"; place: ManualPlace };

export function placeLabel(chosen: ChosenPlace): string {
  return chosen.kind === "search" ? `${chosen.place.name}, ${chosen.place.country_code}` : chosen.place.name;
}

export function PlaceSearch({ onChoose }: { onChoose: (place: ChosenPlace) => void }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [manual, setManual] = useState(false);
  const [m, setM] = useState({ name: "", latitude: "", longitude: "", timezone: browserTimezone() });

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      api
        .searchPlaces(q)
        .then((places) => !cancelled && (setResults(places), setFailed(false)))
        .catch(() => !cancelled && setFailed(true));
    }, 220);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  if (manual) {
    const lat = Number(m.latitude.replace(",", "."));
    const lon = Number(m.longitude.replace(",", "."));
    const valid =
      m.name.trim() !== "" &&
      m.latitude !== "" &&
      m.longitude !== "" &&
      Math.abs(lat) <= 90 &&
      Math.abs(lon) <= 180 &&
      TIMEZONES.includes(m.timezone);
    return (
      <div className="stack">
        <h3>{t("onboarding.placeManualTitle")}</h3>
        <Field label={t("onboarding.placeName")}>
          <input type="text" value={m.name} onChange={(e) => setM({ ...m, name: e.target.value })} />
        </Field>
        <div className="row">
          <Field label={t("onboarding.latitude")}>
            <input type="text" inputMode="decimal" placeholder="48.137" value={m.latitude}
              onChange={(e) => setM({ ...m, latitude: e.target.value })} />
          </Field>
          <Field label={t("onboarding.longitude")}>
            <input type="text" inputMode="decimal" placeholder="11.575" value={m.longitude}
              onChange={(e) => setM({ ...m, longitude: e.target.value })} />
          </Field>
        </div>
        <TimezoneInput label={t("onboarding.timezone")} value={m.timezone} onChange={(tz) => setM({ ...m, timezone: tz })} />
        <div className="row">
          <button type="button" className="button ghost" onClick={() => setManual(false)}>
            {t("common.back")}
          </button>
          <span className="spacer" />
          <button
            type="button"
            className="button secondary"
            disabled={!valid}
            onClick={() => onChoose({ kind: "manual", place: { name: m.name.trim(), latitude: lat, longitude: lon, timezone: m.timezone } })}
          >
            {t("common.next")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="stack-sm">
      <label className="field">
        {t("onboarding.placeSearch")}
        <input
          type="search"
          value={query}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="search"
          placeholder="München, Sevilla, Bristol …"
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      {failed && <p className="error">{t("common.errorNetwork")}</p>}
      {results && results.length > 0 && (
        <ul className="results">
          {results.map((p) => (
            <li key={p.id}>
              <button type="button" onClick={() => onChoose({ kind: "search", place: p })}>
                <Icon name="pin" className="muted" />
                <span>{p.name}</span>
                <span className="country">{p.country_code}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {results && results.length === 0 && <p className="muted small">{t("onboarding.placeNoResults")}</p>}
      <button type="button" className="button ghost" onClick={() => setManual(true)}>
        {t("onboarding.placeManual")}
      </button>
    </div>
  );
}
