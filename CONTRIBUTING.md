# Contributing to PhantomBridge

Thanks for helping keep this read-only.

## Principles

- **No custody.** Do not add key storage, seed import, or silent signing.
- **No execution in v1.** Quotes, drafts, and summaries only. No swap/send/revoke txs.
- **Public defaults.** Prefer public Solana RPC, Jupiter lite, and DexScreener. Document optional paid keys; never require invented secrets.
- **Structured failures.** Tools return `{ "ok": false, "error": { "code", "message" } }` — do not swallow RPC outages.

## Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q

cd web
cp .env.example .env
npm install
npm run dev
```

## Pull requests

1. Branch from `main`.
2. Add tests for helper changes (pubkey, session, risk, quote parsing).
3. Update README env vars if you add a setting.
4. Keep the security model section honest if behavior changes.

## Code of conduct (short)

Be kind. Do not file issues asking for auto-trading, key export, or ways to hide signatures from the user.
