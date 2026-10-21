import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { AccessibilityProvider } from "./hooks/useAccessibility";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/accessibility.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AccessibilityProvider>
      <App />
    </AccessibilityProvider>
  </StrictMode>,
);
