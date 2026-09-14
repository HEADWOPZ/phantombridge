import { AddressType } from "@phantom/browser-sdk";
import { PhantomProvider, darkTheme } from "@phantom/react-sdk";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { App } from "./App";
import { Callback } from "./Callback";
import { PhantomConnectApp } from "./PhantomConnectApp";
import "./styles.css";

const appId = (import.meta.env.VITE_PHANTOM_APP_ID ?? "").trim();
const redirectUrl =
  import.meta.env.VITE_PHANTOM_REDIRECT_URL ??
  (typeof window !== "undefined" ? `${window.location.origin}/callback` : "http://localhost:5173/callback");

function Root() {
  if (!appId) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route
            path="/callback"
            element={
              <div className="app">
                <p className="note">Social callback is unused in injected-only mode (no VITE_PHANTOM_APP_ID).</p>
              </div>
            }
          />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <PhantomProvider
      config={{
        providers: ["injected", "google", "apple"],
        appId,
        addressTypes: [AddressType.solana],
        authOptions: { redirectUrl },
      }}
      theme={darkTheme}
      appName="PhantomBridge"
    >
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PhantomConnectApp />} />
          <Route path="/callback" element={<Callback />} />
        </Routes>
      </BrowserRouter>
    </PhantomProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
