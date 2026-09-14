"""Structured, machine-readable failures for MCP tools."""

from __future__ import annotations

from typing import Any


class PhantomBridgeError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
            "read_only": True,
        }


def ok(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "read_only": True, **payload}


def fail_from_exception(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, PhantomBridgeError):
        return exc.to_dict()
    return PhantomBridgeError(
        "INTERNAL",
        f"{type(exc).__name__}: {exc}",
    ).to_dict()
