export const SESSION_PREFIX = "PhantomBridge read-proof";

export type PreparedSession = {
  pubkey: string;
  issuedAt: number;
  expiresAt: number;
  nonce: string;
  message: string;
};

export function sessionTtlSeconds(): number {
  const raw = Number(import.meta.env.VITE_SESSION_TTL_SECONDS ?? "900");
  return Number.isFinite(raw) && raw > 30 ? Math.min(raw, 3600) : 900;
}

export function buildReadProofMessage(
  pubkey: string,
  issuedAt: number,
  expiresAt: number,
  nonce: string,
): string {
  return [
    SESSION_PREFIX,
    "v=1",
    `pubkey=${pubkey}`,
    `issued_at=${issuedAt}`,
    `expires_at=${expiresAt}`,
    `nonce=${nonce}`,
  ].join("\n");
}

export function encodeSessionToken(payload: Record<string, unknown>): string {
  const json = JSON.stringify(payload);
  const bytes = new TextEncoder().encode(json);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function randomNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function prepareSession(pubkey: string): PreparedSession {
  const issuedAt = Math.floor(Date.now() / 1000);
  const expiresAt = issuedAt + sessionTtlSeconds();
  const nonce = randomNonce();
  return {
    pubkey,
    issuedAt,
    expiresAt,
    nonce,
    message: buildReadProofMessage(pubkey, issuedAt, expiresAt, nonce),
  };
}

export function finalizeSession(prepared: PreparedSession, signatureB58: string): string {
  return encodeSessionToken({
    v: 1,
    pubkey: prepared.pubkey,
    issued_at: prepared.issuedAt,
    expires_at: prepared.expiresAt,
    nonce: prepared.nonce,
    message: prepared.message,
    signature: signatureB58,
  });
}
