/** Birth date/time and birth place inputs, shared by onboarding and settings. */

import { useTranslation } from "react-i18next";

import type { Birth, BirthUpdate } from "../api";
import { type ChosenPlace, Field, Icon, PlaceSearch, placeLabel } from "../components";

export interface BirthDraft {
  date: string;
  time: string;
  timeUnknown: boolean;
  place: ChosenPlace | null;
}

export function draftFrom(birth: Birth | null): BirthDraft {
  if (!birth) return { date: "", time: "", timeUnknown: false, place: null };
  const place: ChosenPlace = {
    kind: "manual",
    place: { name: birth.place_name, latitude: birth.latitude, longitude: birth.longitude, timezone: birth.timezone },
  };
  return { date: birth.date, time: birth.time ?? "", timeUnknown: birth.time === null, place };
}

export function dateTimeValid(d: BirthDraft): boolean {
  const today = new Date().toISOString().slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(d.date) && d.date >= "1900-01-01" && d.date <= today && (d.timeUnknown || /^\d{2}:\d{2}/.test(d.time));
}

export function toUpdate(d: BirthDraft, original?: Birth | null): BirthUpdate {
  const base = { date: d.date, time: d.timeUnknown ? null : d.time.slice(0, 5) };
  if (!d.place) throw new Error("place missing");
  if (d.place.kind === "search") return { ...base, place_id: d.place.place.id };
  // Unchanged place from the database: keep its GeoNames id if it had one.
  if (original?.place_id && original.place_name === d.place.place.name) return { ...base, place_id: original.place_id };
  return { ...base, place: d.place.place };
}

export function BirthDateTime({ draft, onChange }: { draft: BirthDraft; onChange: (d: BirthDraft) => void }) {
  const { t } = useTranslation();
  return (
    <div className="stack">
      <Field label={t("onboarding.birthDate")}>
        <input
          type="date"
          min="1900-01-01"
          max={new Date().toISOString().slice(0, 10)}
          value={draft.date}
          onChange={(e) => onChange({ ...draft, date: e.target.value })}
        />
      </Field>
      <Field label={t("onboarding.birthTime")}>
        <input
          type="time"
          value={draft.time}
          disabled={draft.timeUnknown}
          onChange={(e) => onChange({ ...draft, time: e.target.value })}
        />
      </Field>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={draft.timeUnknown}
          onChange={(e) => onChange({ ...draft, timeUnknown: e.target.checked })}
        />
        <span className="stack-sm">
          {t("onboarding.timeUnknown")}
          {draft.timeUnknown && <span className="field-hint">{t("onboarding.timeUnknownHint")}</span>}
        </span>
      </label>
    </div>
  );
}

export function BirthPlace({ draft, onChange }: { draft: BirthDraft; onChange: (d: BirthDraft) => void }) {
  const { t } = useTranslation();
  if (draft.place) {
    return (
      <div className="chosen">
        <Icon name="pin" />
        <span style={{ flex: 1 }}>{t("onboarding.placeChosen", { place: placeLabel(draft.place) })}</span>
        <button type="button" className="button ghost" onClick={() => onChange({ ...draft, place: null })}>
          {t("onboarding.placeChange")}
        </button>
      </div>
    );
  }
  return <PlaceSearch onChoose={(place) => onChange({ ...draft, place })} />;
}
