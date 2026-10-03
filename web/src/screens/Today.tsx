import { type CSSProperties, useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, CATEGORIES, type Me, type Today as TodayData } from "../api";
import { CategoryIcon, Icon, Mira, MiraLoading, PawRating } from "../components";
import { MoonPhaseIcon } from "../moon";
import { describeFactor } from "../why";

function formatDate(isoDate: string, language: string): string {
  return new Intl.DateTimeFormat(language, { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }).format(
    new Date(`${isoDate}T12:00:00Z`),
  );
}

type State =
  | { kind: "loading"; slow: boolean }
  | { kind: "ready"; data: TodayData; fetchedAt: number }
  | { kind: "error"; message: string };

export function Today({ me, onSettings, onNeedsOnboarding, onUnauthorized }: {
  me: Me;
  onSettings: () => void;
  onNeedsOnboarding: () => void;
  onUnauthorized: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [state, setState] = useState<State>({ kind: "loading", slow: false });
  const retryTimer = useRef<number | undefined>(undefined);
  const attempts = useRef(0);

  const load = useCallback(async () => {
    window.clearTimeout(retryTimer.current);
    try {
      const data = await api.today();
      attempts.current = 0;
      setState({ kind: "ready", data, fetchedAt: Date.now() });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return onUnauthorized();
      if (err instanceof ApiError && err.status === 409) return onNeedsOnboarding();
      if (err instanceof ApiError && err.status === 503) {
        // Another request is generating the reading: show Mira and ask again shortly.
        attempts.current += 1;
        setState({ kind: "loading", slow: attempts.current > 2 });
        retryTimer.current = window.setTimeout(load, (err.retryAfter ?? 5) * 1000);
        return;
      }
      setState({ kind: "error", message: err instanceof ApiError && err.status === 0 ? t("common.errorNetwork") : t("common.errorGeneric") });
    }
  }, [onNeedsOnboarding, onUnauthorized, t]);

  // Generation can take 10–20 s; after a while, tell the user it's still coming.
  useEffect(() => {
    if (state.kind !== "loading" || state.slow) return;
    const timer = window.setTimeout(() => setState((s) => (s.kind === "loading" ? { ...s, slow: true } : s)), 12000);
    return () => window.clearTimeout(timer);
  }, [state]);

  useEffect(() => {
    void load();
    return () => window.clearTimeout(retryTimer.current);
  }, [load]);

  // Coming back to the app the next morning: fetch the new day's reading.
  useEffect(() => {
    function onVisible() {
      if (document.visibilityState === "visible" && state.kind === "ready" && Date.now() - state.fetchedAt > 30 * 60 * 1000) {
        void load();
      }
    }
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load, state]);

  const settingsButton = (
    <button type="button" className="icon-button" onClick={onSettings} aria-label={t("today.settings")}>
      <Icon name="gear" />
    </button>
  );

  if (state.kind === "loading") {
    return (
      <main className="page">
        <div className="topbar">
          <span className="spacer" />
          {settingsButton}
        </div>
        <MiraLoading slow={state.slow} />
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main className="page">
        <div className="topbar">
          <span className="spacer" />
          {settingsButton}
        </div>
        <div className="center-screen">
          <Mira small />
          <p role="alert">{state.message}</p>
          <button type="button" className="button secondary" onClick={() => { setState({ kind: "loading", slow: false }); void load(); }}>
            {t("common.retry")}
          </button>
        </div>
      </main>
    );
  }

  const { data } = state;
  const { reading } = data;
  return (
    <main className="page stack fade-in">
      <div className="topbar">
        <span className="title">{formatDate(data.date, i18n.language)}</span>
        {settingsButton}
      </div>

      <section className="hero">
        <Mira pose={data.day.mira_pose} />
        <p className="eyebrow">{t("today.hello", { name: me.display_name })}</p>
        <h1 className="headline">{reading.headline}</h1>
        <p className="muted small moon-line">
          <MoonPhaseIcon phase={data.day.moon_phase} />
          {t("today.moonLine", { sign: t(`sign.${data.day.moon_sign}`), phase: t(`phase.${data.day.moon_phase}`) })}
        </p>
      </section>

      <p className="summary rise" style={{ "--i": 1 } as CSSProperties}>{reading.summary}</p>
      {data.status === "fallback" && <p className="note">{t("today.fallbackNote")}</p>}

      <section className="categories" aria-label={t("today.why")}>
        {CATEGORIES.map((c, i) => (
          <article key={c} className="card category rise" data-category={c} style={{ "--i": 2 + i } as CSSProperties}>
            <div className="category-head">
              <CategoryIcon category={c} />
              <h3>{t(`category.${c}`)}</h3>
              <PawRating score={data.categories[c].score} />
            </div>
            <p>{reading.sections[c]}</p>
          </article>
        ))}
      </section>

      <section className="card highlight stack-sm rise" style={{ "--i": 6 } as CSSProperties}>
        <span className="advice-label">
          <Icon name="star" />
          {t("today.advice")}
        </span>
        <p className="advice">{reading.advice}</p>
      </section>

      <details className="why rise" style={{ "--i": 7 } as CSSProperties}>
        <summary>
          {t("today.why")}
          <Icon name="chevron" />
        </summary>
        <div className="why-body">
          <p className="muted small">{t("today.whyIntro")}</p>
          <ul className="why-list">
            {data.factors.map((f) => {
              const text = describeFactor(t, f);
              return (
                <li key={f.id} className={`nature-${f.nature}`}>
                  <span className="why-title">{text.title}</span>
                  <br />
                  <span className="muted small">{text.details.join(" · ")}</span>
                </li>
              );
            })}
          </ul>
          {!data.birth_time_known && <p className="note" style={{ marginTop: 14 }}>{t("today.unknownTimeHint")}</p>}
        </div>
      </details>

      <p className="disclaimer">{t("today.disclaimer")}</p>
    </main>
  );
}
