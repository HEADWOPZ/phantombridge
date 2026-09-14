export const DEFAULT_RPC =
  import.meta.env.VITE_SOLANA_RPC_URL ?? "https://api.mainnet-beta.solana.com";

const TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb";

export type TokenRow = {
  mint: string;
  account: string;
  uiAmount: number | null;
  decimals: number;
  amount: string;
};

export type BalanceSummary = {
  lamports: number;
  sol: number;
  tokens: TokenRow[];
};

async function rpc<T>(method: string, params: unknown[]): Promise<T> {
  const res = await fetch(DEFAULT_RPC, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!res.ok) {
    throw new Error(`RPC HTTP ${res.status} from ${DEFAULT_RPC}`);
  }
  const body = (await res.json()) as { result?: T; error?: { message?: string } };
  if (body.error) {
    throw new Error(body.error.message ?? "Solana RPC error");
  }
  return body.result as T;
}

async function tokenAccounts(owner: string, programId: string): Promise<TokenRow[]> {
  const result = await rpc<{
    value: Array<{
      pubkey: string;
      account: {
        data: {
          parsed?: {
            info?: {
              mint?: string;
              tokenAmount?: { uiAmount: number | null; decimals: number; amount: string };
            };
          };
        };
      };
    }>;
  }>("getTokenAccountsByOwner", [
    owner,
    { programId },
    { encoding: "jsonParsed" },
  ]);

  return (result?.value ?? [])
    .map((item) => {
      const info = item.account.data.parsed?.info;
      const amt = info?.tokenAmount;
      return {
        mint: info?.mint ?? "",
        account: item.pubkey,
        uiAmount: amt?.uiAmount ?? null,
        decimals: amt?.decimals ?? 0,
        amount: amt?.amount ?? "0",
      };
    })
    .filter((row) => row.mint && row.amount !== "0");
}

export async function fetchBalanceSummary(pubkey: string): Promise<BalanceSummary> {
  const balance = await rpc<{ value: number } | number>("getBalance", [pubkey]);
  const lamports = typeof balance === "number" ? balance : (balance?.value ?? 0);
  const [spl, t22] = await Promise.all([
    tokenAccounts(pubkey, TOKEN_PROGRAM),
    tokenAccounts(pubkey, TOKEN_2022),
  ]);
  return {
    lamports,
    sol: lamports / 1_000_000_000,
    tokens: [...spl, ...t22],
  };
}

export function shortKey(key: string): string {
  if (key.length <= 10) return key;
  return `${key.slice(0, 4)}…${key.slice(-4)}`;
}
