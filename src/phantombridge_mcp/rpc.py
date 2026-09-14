"""Thin Solana JSON-RPC + public HTTP helpers."""

from __future__ import annotations

from typing import Any

import httpx

from phantombridge_mcp.config import Settings
from phantombridge_mcp.errors import PhantomBridgeError


class HttpClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.Client(
            timeout=settings.http_timeout,
            headers={"User-Agent": "phantombridge-mcp/0.1"},
        )

    def close(self) -> None:
        self._client.close()

    def rpc(self, method: str, params: list[Any] | None = None) -> Any:
        url = self.settings.resolved_rpc_url()
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or [],
        }
        try:
            response = self._client.post(url, json=body)
        except httpx.TimeoutException as exc:
            raise PhantomBridgeError(
                "RPC_TIMEOUT",
                f"Solana RPC timed out calling {method}.",
                details={"url": url},
            ) from exc
        except httpx.HTTPError as exc:
            raise PhantomBridgeError(
                "RPC_UNREACHABLE",
                f"Solana RPC is unreachable: {exc}",
                details={"url": url, "method": method},
            ) from exc

        if response.status_code >= 400:
            raise PhantomBridgeError(
                "RPC_HTTP_ERROR",
                f"Solana RPC returned HTTP {response.status_code} for {method}.",
                details={"url": url, "body_preview": response.text[:240]},
            )
        try:
            payload = response.json()
        except Exception as exc:
            raise PhantomBridgeError(
                "RPC_BAD_RESPONSE",
                "Solana RPC returned non-JSON.",
                details={"url": url},
            ) from exc
        if "error" in payload:
            err = payload["error"]
            raise PhantomBridgeError(
                "RPC_ERROR",
                f"Solana RPC error on {method}: {err.get('message', err)}",
                details={"error": err, "method": method},
            )
        return payload.get("result")

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        code: str = "HTTP_ERROR",
    ) -> Any:
        try:
            response = self._client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise PhantomBridgeError(
                "HTTP_TIMEOUT",
                f"Timed out fetching {url}",
            ) from exc
        except httpx.HTTPError as exc:
            raise PhantomBridgeError(code, f"HTTP request failed: {exc}", details={"url": url}) from exc
        if response.status_code >= 400:
            raise PhantomBridgeError(
                code,
                f"HTTP {response.status_code} from {url}",
                details={"body_preview": response.text[:300]},
            )
        try:
            return response.json()
        except Exception as exc:
            raise PhantomBridgeError(code, "Response was not JSON.", details={"url": url}) from exc
