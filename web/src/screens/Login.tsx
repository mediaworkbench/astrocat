import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, type Me } from "../api";
import { Field, Mira } from "../components";

export function Login({ onLogin, onRegister }: { onLogin: (me: Me) => void; onRegister?: () => void }) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onLogin(await api.login(username, password));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError(t("login.wrong"));
      else if (err instanceof ApiError && err.status === 429)
        setError(t("login.tooMany", { minutes: Math.max(1, Math.ceil((err.retryAfter ?? 60) / 60)) }));
      else if (err instanceof ApiError && err.status === 0) setError(t("common.errorNetwork"));
      else setError(t("common.errorGeneric"));
      setBusy(false);
    }
  }

  return (
    <main className="page stack fade-in">
      <div className="hero" style={{ marginTop: 24 }}>
        <Mira small />
        <h1 className="brand">AstroCat</h1>
        <p className="muted">{t("common.tagline")}</p>
      </div>
      <form className="card stack" onSubmit={submit}>
        <h2>{t("login.title")}</h2>
        <Field label={t("login.username")}>
          <input
            type="text"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </Field>
        <Field label={t("login.password")}>
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="button primary block" type="submit" disabled={busy}>
          {busy ? t("login.submitting") : t("login.submit")}
        </button>
      </form>
      {onRegister && (
        <p className="muted" style={{ textAlign: "center" }}>
          {t("login.noAccount")}{" "}
          <button type="button" className="button ghost" onClick={onRegister}>
            {t("login.createAccount")}
          </button>
        </p>
      )}
    </main>
  );
}
