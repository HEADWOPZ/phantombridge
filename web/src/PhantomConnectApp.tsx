import {
  useAccounts,
  useConnect,
  useDisconnect,
  useIsExtensionInstalled,
  usePhantom,
  useSolana,
} from "@phantom/react-sdk";
import { useCallback, useEffect, useState } from "react";
import { fetchBalanceSummary, shortKey, type BalanceSummary } from "./balances";
import { toBase58 } from "./injected";
import { finalizeSession, prepareSession, sessionTtlSeconds } from "./session";

const appId = (import.meta.env.VITE_PHANTOM_APP_ID ?? "").trim();

export function PhantomConnectApp() {
  const { connect, isConnecting } = useConnect();
  const { isConnected, isLoading } = usePhantom();
  const addresses = useAccounts();
  const { disconnect } = useDisconnect();
  const { solana } = useSolana();
  const { isInstalled, isLoading: extLoading } = useIsExtensionInstalled();

  const pubkey = addresses?.[0]?.address ?? null;
  const [balances, setBalances] = useState<BalanceSummary | null>(null);
  const [token, setToken] = useState("");
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!pubkey) return;
    void fetchBalanceSummary(pubkey)
      .then(setBalances)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [pubkey]);

  const signProof = useCallback(async () => {
    if (!pubkey) return;
    setBusy("sign");
    setError(null);
    try {
      const prepared = prepareSession(pubkey);
      const result = await solana.signMessage(prepared.message);
      const bytes = extractSignatureBytes(result);
      setToken(finalizeSession(prepared, toBase58(bytes)));
      setExpiresAt(prepared.expiresAt);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }, [pubkey, solana]);

  return (
    <div className="app">
      <header className="hero">
        <div className="brand">
          <div className="mark">P</div>
          <div>
            <h1>PhantomBridge</h1>
            <p className="sub">Phantom Connect session desk — still read-only.</p>
          </div>
        </div>
        <div className="badge">connect sdk</div>
      </header>
      <div className="grid">
        <section className="card">
          <h2>Connect</h2>
          {isLoading || extLoading ? <p className="note">Checking Phantom…</p> : null}
          {!isConnected && (
            <div className="row">
              <button
                type="button"
                disabled={isConnecting || isInstalled === false}
                onClick={() => void connect({ provider: "injected" })}
              >
                {isConnecting ? "Connecting…" : "Connect extension"}
              </button>
              {appId && (
                <>
                  <button
                    type="button"
                    className="secondary"
                    disabled={isConnecting}
                    onClick={() => void connect({ provider: "google" })}
                  >
                    Google
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    disabled={isConnecting}
                    onClick={() => void connect({ provider: "apple" })}
                  >
                    Apple
                  </button>
                </>
              )}
              {isInstalled === false && (
                <a href="https://phantom.app/download" target="_blank" rel="noreferrer">
                  Install Phantom
                </a>
              )}
            </div>
          )}
          {isConnected && pubkey && (
            <div className="row">
              <div className="pubkey mono">{pubkey}</div>
              <button type="button" className="secondary" onClick={() => void disconnect()}>
                Disconnect
              </button>
            </div>
          )}
          {error && <p className="err">{error}</p>}
        </section>
        <section className="card">
          <h2>Balances</h2>
          <p>
            <strong>{balances ? `${balances.sol.toFixed(4)} SOL` : "—"}</strong>
          </p>
          <ul className="tokens">
            {(balances?.tokens ?? []).slice(0, 12).map((t) => (
              <li key={t.account}>
                <span className="mono">{shortKey(t.mint)}</span>
                <span>{t.uiAmount ?? t.amount}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2>MCP read-proof</h2>
          <p className="note">
            TTL {sessionTtlSeconds()}s. Agent tools verify this signature against your pubkey.
          </p>
          <div className="row">
            <button type="button" disabled={!pubkey || busy === "sign"} onClick={() => void signProof()}>
              {busy === "sign" ? "Sign in Phantom…" : "Sign read-proof"}
            </button>
            {token && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  void navigator.clipboard.writeText(token);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1200);
                }}
              >
                {copied ? "Copied" : "Copy token"}
              </button>
            )}
            {expiresAt && (
              <span className="ok">expires {new Date(expiresAt * 1000).toLocaleTimeString()}</span>
            )}
          </div>
          <textarea readOnly value={token} placeholder="Session token appears here after you sign." />
        </section>
      </div>
    </div>
  );
}

function extractSignatureBytes(result: unknown): Uint8Array {
  if (result instanceof Uint8Array) return result;
  if (result && typeof result === "object") {
    const rec = result as { rawSignature?: unknown; signature?: unknown };
    if (rec.rawSignature instanceof Uint8Array) return rec.rawSignature;
    if (rec.signature instanceof Uint8Array) return rec.signature;
    if (typeof rec.signature === "string") {
      try {
        const bin = atob(rec.signature);
        return Uint8Array.from(bin, (c) => c.charCodeAt(0));
      } catch {
        return new TextEncoder().encode(rec.signature);
      }
    }
  }
  throw new Error("Phantom did not return a signature.");
}
