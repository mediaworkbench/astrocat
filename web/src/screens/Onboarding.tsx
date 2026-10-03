import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, type Gender, type Me } from "../api";
import { Mira, Progress, RadioCards, Segmented, TIMEZONES, TimezoneInput, browserTimezone, Field } from "../components";
import { LANGUAGE_NAMES, LANGUAGES, type Language, setLanguage } from "../i18n";
import { BirthDateTime, type BirthDraft, BirthPlace, dateTimeValid, draftFrom, toUpdate } from "./BirthFields";

const STEPS = 3;

export function Onboarding({ me, onDone, onUnauthorized }: {
  me: Me;
  onDone: (me: Me) => void;
  onUnauthorized: () => void;
}) {
  const { t } = useTranslation();
  const [step, setStep] = useState(1);
  const [name, setName] = useState(me.display_name);
  const [language, setLang] = useState<Language>(me.language);
  const [gender, setGender] = useState<Gender>(me.grammatical_gender);
  const [timezone, setTimezone] = useState(TIMEZONES.includes(me.timezone) && me.timezone !== "UTC" ? me.timezone : browserTimezone());
  const [birth, setBirth] = useState<BirthDraft>(draftFrom(me.birth));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function chooseLanguage(l: Language) {
    setLang(l);
    setLanguage(l); // the UI switches right away
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return onUnauthorized();
      setError(err instanceof ApiError && err.status === 0 ? t("common.errorNetwork") : t("common.errorGeneric"));
    } finally {
      setBusy(false);
    }
  }

  const next = () =>
    run(async () => {
      if (step === 1) await api.updateSettings({ display_name: name.trim(), language, grammatical_gender: gender });
      setStep(step + 1);
      window.scrollTo(0, 0);
    });

  const finish = () =>
    run(async () => {
      await api.updateSettings({ timezone });
      onDone(await api.updateBirth(toUpdate(birth, me.birth)));
    });

  const canContinue =
    step === 1 ? name.trim().length > 0 : step === 2 ? dateTimeValid(birth) : birth.place !== null && TIMEZONES.includes(timezone);

  return (
    <main className="page stack fade-in">
      <div className="stack-sm" style={{ marginTop: 8 }}>
        <Progress current={step} total={STEPS} />
        <span className="muted small">{t("onboarding.step", { current: step, total: STEPS })}</span>
      </div>

      {step === 1 && (
        <>
          <div className="hero">
            <Mira small />
            <h1>{t("onboarding.aboutTitle")}</h1>
            <p className="muted">{t("onboarding.aboutIntro")}</p>
          </div>
          <div className="card stack">
            <Field label={t("onboarding.displayName")}>
              <input type="text" autoComplete="given-name" maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Segmented
              label={t("onboarding.language")}
              value={language}
              onChange={chooseLanguage}
              options={LANGUAGES.map((l) => ({ value: l, label: LANGUAGE_NAMES[l] }))}
            />
            <RadioCards
              label={t("onboarding.address")}
              hint={t("onboarding.addressHint")}
              value={gender}
              onChange={setGender}
              options={(["feminine", "masculine", "neutral"] as Gender[]).map((g) => ({ value: g, label: t(`address.${g}`) }))}
            />
          </div>
        </>
      )}

      {step === 2 && (
        <>
          <div className="stack-sm">
            <h1>{t("onboarding.birthTitle")}</h1>
            <p className="muted">{t("onboarding.birthIntro")}</p>
          </div>
          <div className="card">
            <BirthDateTime draft={birth} onChange={setBirth} />
          </div>
        </>
      )}

      {step === 3 && (
        <>
          <div className="stack-sm">
            <h1>{t("onboarding.placeTitle")}</h1>
            <p className="muted">{t("onboarding.placeIntro")}</p>
          </div>
          <div className="card stack">
            <BirthPlace draft={birth} onChange={setBirth} />
          </div>
          {birth.place && (
            <div className="card">
              <TimezoneInput
                label={t("onboarding.currentTimezone")}
                hint={t("onboarding.currentTimezoneHint")}
                value={timezone}
                onChange={setTimezone}
              />
            </div>
          )}
        </>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <div className="row">
        {step > 1 && (
          <button type="button" className="button ghost" onClick={() => setStep(step - 1)} disabled={busy}>
            {t("common.back")}
          </button>
        )}
        <span className="spacer" />
        {step < STEPS ? (
          <button type="button" className="button primary" disabled={!canContinue || busy} onClick={next}>
            {busy ? t("common.saving") : t("common.next")}
          </button>
        ) : (
          <button type="button" className="button primary" disabled={!canContinue || busy} onClick={finish}>
            {busy ? t("common.saving") : t("onboarding.finish")}
          </button>
        )}
      </div>
    </main>
  );
}
