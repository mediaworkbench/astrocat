import "@fontsource-variable/fraunces";
import "@fontsource-variable/nunito";
import "./styles.css";
import "./i18n";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="sky" aria-hidden="true">
      <span className="shooting-star" />
    </div>
    <App />
  </StrictMode>,
);
