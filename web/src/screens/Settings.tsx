import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, type Gender, type Me } from "../api";
import { Field, Icon, RadioCards, Segmented, TIMEZONES, TimezoneInput } from "../components";
import { LANGUAGE_NAMES, LANGUAGES, type Language, setLanguage } from "../i18n";
import { BirthDateTime, type BirthDraft, BirthPlace, dateTimeValid, draftFrom, toUpdate } from "./BirthFields";

const SOURCE_URL: string | undefined = import.meta.env.VITE_SOURCE_URL;

type Status = { kind: "idle" | "busy" | "saved" } | { kind: "error"; message: string };

function useAction(onUnauthorized: () => void) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  async function run(action: () => Promise<void>, errors: Record<number, string> = {}) {
    setStatus({ kind: "busy" });
    try {
      await action();
      setStatus({ kind: "saved" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return onUnauthorized();
      const message =
        (err instanceof ApiError && errors[err.status]) ||
        (err instanceof ApiError && err.status === 0 ? t("common.errorNetwork") : t("common.errorGeneric"));
      setStatus({ kind: "error", message });
    }
  }
  return { status, run, reset: () => setStatus({ kind: "idle" }) };
}

function StatusLine({ status, saved }: { status: Status; saved: string }) {
  if (status.kind === "saved") return <p className="success" role="status">{saved}</p>;
  if (status.kind === "error") return <p className="error" role="alert">{status.message}</p>;
  return null;
}

function formatBirth(me: Me, language: string, unknown: string): string {
  if (!me.birth) return "";
  const date = new Intl.DateTimeFormat(language, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${me.birth.date}T12:00:00Z`),
  );
  return `${date}, ${me.birth.time ?? unknown} · ${me.birth.place_name}`;
}

export function Settings({ me, onChange, onBack, onLogout, onUnauthorized }: {
  me: Me;
  onChange: (me: Me) => void;
  onBack: () => void;
  onLogout: () => void;
  onUnauthorized: () => void;
}) {
  const { t, i18n } = useTranslation();

  // --- profile
  const [name, setName] = useState(me.display_name);
  const [language, setLang] = useState<Language>(me.language);
  const [gender, setGender] = useState<Gender>(me.grammatical_gender);
  const [timezone, setTimezone] = useState(me.timezone);
  const profile = useAction(onUnauthorized);
  const profileValid = name.trim().length > 0 && TIMEZONES.includes(timezone);

  function saveProfile(e: FormEvent) {
    e.preventDefault();
    void profile.run(async () => {
      const updated = await api.updateSettings({ display_name: name.trim(), language, grammatical_gender: gender, timezone });
      setLanguage(updated.language);
      onChange(updated);
    });
  }

  // --- birth data
  const [editingBirth, setEditingBirth] = useState(false);
  const [birth, setBirth] = useState<BirthDraft>(draftFrom(me.birth));
  const birthAction = useAction(onUnauthorized);

  function saveBirth() {
    void birthAction.run(async () => {
      onChange(await api.updateBirth(toUpdate(birth, me.birth)));
      setEditingBirth(false);
    });
  }

  // --- password
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const password = useAction(onUnauthorized);

  function changePassword(e: FormEvent) {
    e.preventDefault();
    void password.run(
      async () => {
        await api.changePassword(current, next);
        setCurrent("");
        setNext("");
      },
      { 403: t("settings.passwordWrong"), 422: t("settings.passwordShort") },
    );
  }

  async function logout() {
    try {
      await api.logout();
    } finally {
      onLogout();
    }
  }

  return (
    <main className="page stack fade-in">
      <div className="topbar">
        <button type="button" className="icon-button" onClick={onBack} aria-label={t("common.back")}>
          <Icon name="back" />
        </button>
        <h1 style={{ fontSize: "1.5rem", flex: 1 }}>{t("settings.title")}</h1>
      </div>

      <h2 className="section-title">{t("settings.profile")}</h2>
      <form className="card stack" onSubmit={saveProfile}>
        <Field label={t("onboarding.displayName")}>
          <input type="text" maxLength={80} value={name} onChange={(e) => { setName(e.target.value); profile.reset(); }} />
        </Field>
        <Segmented
          label={t("onboarding.language")}
          value={language}
          onChange={(l) => { setLang(l); profile.reset(); }}
          options={LANGUAGES.map((l) => ({ value: l, label: LANGUAGE_NAMES[l] }))}
        />
        <RadioCards
          label={t("onboarding.address")}
          hint={t("onboarding.addressHint")}
          value={gender}
          onChange={(g) => { setGender(g); profile.reset(); }}
          options={(["feminine", "masculine", "neutral"] as Gender[]).map((g) => ({ value: g, label: t(`address.${g}`) }))}
        />
        <TimezoneInput
          label={t("onboarding.currentTimezone")}
          hint={t("onboarding.currentTimezoneHint")}
          value={timezone}
          onChange={(tz) => { setTimezone(tz); profile.reset(); }}
        />
        <StatusLine status={profile.status} saved={t("common.saved")} />
        <button type="submit" className="button primary" disabled={!profileValid || profile.status.kind === "busy"}>
          {profile.status.kind === "busy" ? t("common.saving") : t("common.save")}
        </button>
      </form>

      <h2 className="section-title">{t("settings.birth")}</h2>
      <div className="card stack">
        {!editingBirth ? (
          <>
            <p>{formatBirth(me, i18n.language, t("settings.unknownTime"))}</p>
            <StatusLine status={birthAction.status} saved={t("common.saved")} />
            <button type="button" className="button secondary" onClick={() => { setBirth(draftFrom(me.birth)); setEditingBirth(true); birthAction.reset(); }}>
              {t("settings.editBirth")}
            </button>
          </>
        ) : (
          <>
            <BirthDateTime draft={birth} onChange={setBirth} />
            <BirthPlace draft={birth} onChange={setBirth} />
            <StatusLine status={birthAction.status} saved={t("common.saved")} />
            <div className="row">
              <button type="button" className="button ghost" onClick={() => setEditingBirth(false)}>
                {t("common.back")}
              </button>
              <span className="spacer" />
              <button
                type="button"
                className="button primary"
                disabled={!dateTimeValid(birth) || !birth.place || birthAction.status.kind === "busy"}
                onClick={saveBirth}
              >
                {birthAction.status.kind === "busy" ? t("common.saving") : t("common.save")}
              </button>
            </div>
          </>
        )}
      </div>

      <h2 className="section-title">{t("settings.password")}</h2>
      <form className="card stack" onSubmit={changePassword}>
        <input type="text" name="username" autoComplete="username" value={me.username} readOnly hidden />
        <Field label={t("settings.currentPassword")}>
          <input type="password" autoComplete="current-password" value={current} onChange={(e) => { setCurrent(e.target.value); password.reset(); }} />
        </Field>
        <Field label={t("settings.newPassword")}>
          <input type="password" autoComplete="new-password" minLength={8} value={next} onChange={(e) => { setNext(e.target.value); password.reset(); }} />
        </Field>
        <StatusLine status={password.status} saved={t("settings.passwordChanged")} />
        <button type="submit" className="button secondary" disabled={!current || next.length < 8 || password.status.kind === "busy"}>
          {t("settings.changePassword")}
        </button>
      </form>

      <button type="button" className="button danger block" onClick={logout}>
        {t("settings.logout")}
      </button>

      <h2 className="section-title">{t("settings.about")}</h2>
      <div className="card stack-sm small muted">
        <p>{t("common.tagline")}</p>
        <p>{t("settings.license")}</p>
        {SOURCE_URL && (
          <p>
            <a href={SOURCE_URL} target="_blank" rel="noreferrer">
              {t("settings.sourceCode")}
            </a>
          </p>
        )}
        <p>
          <a href="https://www.geonames.org/" target="_blank" rel="noreferrer">
            {t("settings.geonames")}
          </a>
        </p>
        <p>{t("today.disclaimer")}</p>
      </div>
    </main>
  );
}
