import "@fontsource-variable/fraunces/index.css";
import "@fontsource-variable/space-grotesk/index.css";
import "@fontsource/dm-mono/400.css";
import "@fontsource/dm-mono/500.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
