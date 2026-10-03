import { useCallback, useEffect, useState } from "react";

import { api, type Me } from "./api";
import { MiraLoading } from "./components";
import { PoseGallery } from "./mira";
import { setLanguage } from "./i18n";
import { Login } from "./screens/Login";
import { Onboarding } from "./screens/Onboarding";
import { Settings } from "./screens/Settings";
import { Today } from "./screens/Today";

type Route = "today" | "settings";

function currentRoute(): Route {
  return window.location.hash === "#/settings" ? "settings" : "today";
}

export function App() {
  const [me, setMe] = useState<Me | null | undefined>(undefined); // undefined = still checking the session
  const [route, setRoute] = useState<Route>(currentRoute);

  useEffect(() => {
    // Not logged in (401) or server unreachable: the login screen explains the rest.
    api.me().then(setMe).catch(() => setMe(null));
    const onHash = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (me) setLanguage(me.language);
  }, [me]);

  const navigate = useCallback((to: Route) => {
    window.location.hash = to === "settings" ? "#/settings" : "";
    window.scrollTo(0, 0);
  }, []);

  const loggedOut = useCallback(() => setMe(null), []);
  const refreshMe = useCallback(() => {
    api.me().then(setMe).catch(() => setMe(null));
  }, []);

  if (import.meta.env.DEV && window.location.hash === "#/poses") return <PoseGallery />;
  if (me === undefined) return <div className="page"><MiraLoading /></div>;
  if (me === null) return <Login onLogin={setMe} />;
  if (!me.onboarding_complete) {
    return <Onboarding me={me} onDone={(updated) => { setMe(updated); navigate("today"); }} onUnauthorized={loggedOut} />;
  }
  if (route === "settings") {
    return (
      <Settings
        me={me}
        onChange={setMe}
        onBack={() => (window.history.length > 1 ? window.history.back() : navigate("today"))}
        onLogout={() => { navigate("today"); setMe(null); }}
        onUnauthorized={loggedOut}
      />
    );
  }
  // The key makes Today reload when language or birth data change in the settings.
  const key = `${me.language}|${me.grammatical_gender}|${me.timezone}|${JSON.stringify(me.birth)}`;
  return (
    <Today key={key} me={me} onSettings={() => navigate("settings")} onNeedsOnboarding={refreshMe} onUnauthorized={loggedOut} />
  );
}
