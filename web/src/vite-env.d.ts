/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PHANTOM_APP_ID?: string;
  readonly VITE_PHANTOM_REDIRECT_URL?: string;
  readonly VITE_SOLANA_RPC_URL?: string;
  readonly VITE_SESSION_TTL_SECONDS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface PhantomProviderLike {
  isPhantom?: boolean;
  publicKey?: { toString(): string };
  connect: () => Promise<{ publicKey: { toString(): string } }>;
  disconnect: () => Promise<void>;
  signMessage: (
    message: Uint8Array,
    encoding?: string,
  ) => Promise<{ signature: Uint8Array } | Uint8Array>;
  on?: (event: string, handler: (...args: unknown[]) => void) => void;
}

interface Window {
  solana?: PhantomProviderLike;
  phantom?: { solana?: PhantomProviderLike };
}
