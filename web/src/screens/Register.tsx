import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, type Me } from "../api";
import { Field, Mira, browserTimezone } from "../components";
import i18n, { isLanguage } from "../i18n";

const USERNAME = /^[a-z0-9][a-z0-9._-]{2,31}$/;

/** Self-registration with an invite code (concept §9). Afterwards the user continues with onboarding. */
export function Register({ onRegistered, onLogin }: { onRegistered: (me: Me) => void; onLogin: () => void }) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalized = username.trim().toLowerCase();

  /** Says which field is wrong, instead of a silently disabled button. */
  function problem(): string | null {
    if (!USERNAME.test(normalized)) return t("register.invalidUsername");
    if (password.length < 8) return t("register.passwordShort");
    if (!code.trim()) return t("register.codeMissing");
    return null;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const invalid = problem();
    if (invalid) {
      setError(invalid);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const language = isLanguage(i18n.language) ? i18n.language : "en";
      onRegistered(await api.register({ username: username.trim(), password, invite_code: code, language, timezone: browserTimezone() }));
    } catch (err) {
      const status = err instanceof ApiError ? err.status : -1;
      const messages: Record<number, string> = {
        0: t("common.errorNetwork"),
        403: t("register.wrongCode"),
        404: t("register.closed"),
        409: t("register.taken"),
        422: t("register.invalidUsername"),
      };
      if (status === 429 && err instanceof ApiError) {
        setError(t("register.tooMany", { minutes: Math.max(1, Math.ceil((err.retryAfter ?? 60) / 60)) }));
      } else {
        setError(messages[status] ?? t("common.errorGeneric"));
      }
      setBusy(false);
    }
  }

  return (
    <main className="page stack fade-in">
      <div className="hero" style={{ marginTop: 16 }}>
        <Mira small />
        <h1>{t("register.title")}</h1>
        <p className="muted">{t("register.intro")}</p>
      </div>
      <form className="card stack" onSubmit={submit}>
        <Field label={t("register.username")} hint={t("register.usernameHint")}>
          <input
            type="text"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            maxLength={32}
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </Field>
        <Field label={t("register.password")} hint={t("register.passwordHint")}>
          <input
            type="password"
            name="new-password"
            autoComplete="new-password"
            minLength={8}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        <Field label={t("register.inviteCode")}>
          <input
            type="text"
            name="invite-code"
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        </Field>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="button primary block" type="submit" disabled={busy}>
          {busy ? t("register.submitting") : t("register.submit")}
        </button>
      </form>
      <button type="button" className="button ghost" onClick={onLogin}>
        {t("register.haveAccount")}
      </button>
    </main>
  );
}
