import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchBalanceSummary, shortKey, type BalanceSummary } from "./balances";
import { getInjectedProvider, signBytes, toBase58 } from "./injected";
import { finalizeSession, prepareSession, sessionTtlSeconds } from "./session";

const appId = (import.meta.env.VITE_PHANTOM_APP_ID ?? "").trim();
const socialEnabled = Boolean(appId);

type WalletMode = "injected" | "connect-sdk";

export function App() {
  const [pubkey, setPubkey] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [balances, setBalances] = useState<BalanceSummary | null>(null);
  const [token, setToken] = useState<string>("");
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [extensionPresent, setExtensionPresent] = useState<boolean | null>(null);

  const mode: WalletMode = socialEnabled ? "connect-sdk" : "injected";

  useEffect(() => {
    setExtensionPresent(Boolean(getInjectedProvider()));
  }, []);

  const loadBalances = useCallback(async (key: string) => {
    setBusy("balances");
    try {
      setBalances(await fetchBalanceSummary(key));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }, []);

  const connectInjected = useCallback(async () => {
    setError(null);
    const provider = getInjectedProvider();
    if (!provider) {
      setError("Phantom extension not found. Install it or set VITE_PHANTOM_APP_ID for social login.");
      return;
    }
    setBusy("connect");
    try {
      const res = await provider.connect();
      const key = res.publicKey.toString();
      setPubkey(key);
      await loadBalances(key);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }, [loadBalances]);

  const disconnect = useCallback(async () => {
    const provider = getInjectedProvider();
    try {
      await provider?.disconnect();
    } catch {
      /* ignore */
    }
    setPubkey(null);
    setBalances(null);
    setToken("");
    setExpiresAt(null);
  }, []);

  const signProof = useCallback(async () => {
    if (!pubkey) return;
    const provider = getInjectedProvider();
    if (!provider) {
      setError("No injected Phantom provider available to sign the read-proof.");
      return;
    }
    setBusy("sign");
    setError(null);
    try {
      const prepared = prepareSession(pubkey);
      const sig = await signBytes(provider, prepared.message);
      setToken(finalizeSession(prepared, toBase58(sig)));
      setExpiresAt(prepared.expiresAt);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }, [pubkey]);

  const expiryLabel = useMemo(() => {
    if (!expiresAt) return null;
    return new Date(expiresAt * 1000).toLocaleTimeString();
  }, [expiresAt]);

  return (
    <div className="app">
      <header className="hero">
        <div className="brand">
          <div className="mark">P</div>
          <div>
            <h1>PhantomBridge</h1>
            <p className="sub">Read-only Solana session for MCP agents. No custody. No auto-swaps.</p>
          </div>
        </div>
        <div className="badge">v1 read-only</div>
      </header>

      <div className="grid">
        <section className="card">
          <h2>Connect</h2>
          <p className="mode">
            Mode: {mode === "connect-sdk" ? "Phantom Connect (appId + injected/social)" : "injected Phantom only"}
            {extensionPresent === false && " · extension not detected"}
          </p>
          {!pubkey ? (
            <div className="row">
              <button type="button" onClick={connectInjected} disabled={busy === "connect"}>
                {busy === "connect" ? "Connecting…" : "Connect Phantom"}
              </button>
              {socialEnabled && (
                <ConnectSdkNote />
              )}
              {!extensionPresent && (
                <a href="https://phantom.app/download" target="_blank" rel="noreferrer">
                  Install Phantom
                </a>
              )}
            </div>
          ) : (
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
          {!pubkey && <p className="note">Connect a wallet to load a public-RPC summary.</p>}
          {pubkey && (
            <>
              <div className="row">
                <strong>{balances ? `${balances.sol.toFixed(4)} SOL` : "—"}</strong>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void loadBalances(pubkey)}
                  disabled={busy === "balances"}
                >
                  {busy === "balances" ? "Refreshing…" : "Refresh"}
                </button>
              </div>
              {balances && (
                <ul className="tokens">
                  {balances.tokens.length === 0 && <li>No non-zero SPL accounts</li>}
                  {balances.tokens.slice(0, 12).map((t) => (
                    <li key={t.account}>
                      <span className="mono">{shortKey(t.mint)}</span>
                      <span>{t.uiAmount ?? t.amount}</span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>

        <section className="card">
          <h2>MCP read-proof session</h2>
          <p className="note">
            Signs a short-lived, pubkey-bound message ({sessionTtlSeconds()}s). The MCP verifies Ed25519 —
            it never receives a private key. Optional: pass the token as <span className="mono">session_token</span>.
          </p>
          <div className="row">
            <button type="button" onClick={() => void signProof()} disabled={!pubkey || busy === "sign"}>
              {busy === "sign" ? "Waiting for Phantom…" : "Sign read-proof"}
            </button>
            {token && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  void navigator.clipboard.writeText(token);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? "Copied" : "Copy token"}
              </button>
            )}
            {expiryLabel && <span className="ok">expires {expiryLabel}</span>}
          </div>
          <textarea readOnly value={token} placeholder="Session token appears here after you sign." />
        </section>

        <section className="card">
          <h2>Safety</h2>
          <p className="note">
            PhantomBridge never asks for seed phrases, never stores keys, and will not send swaps or
            revokes. Paste this pubkey (or session token) into Claude Desktop / Cursor MCP tools.
            Social login (Google/Apple) is available when <span className="mono">VITE_PHANTOM_APP_ID</span>{" "}
            from <a href="https://phantom.com/portal">phantom.com/portal</a> is set.
          </p>
        </section>
      </div>
    </div>
  );
}

function ConnectSdkNote() {
  return (
    <span className="note">
      App ID detected. Google/Apple need a Portal-allowlisted redirect; this demo still prefers injected connect.
    </span>
  );
}
