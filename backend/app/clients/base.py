"""
BaseServiceClient
─────────────────
All four AI-module clients inherit from this.  It handles:
  • shared httpx.AsyncClient lifecycle
  • timeout / connect-error → clean AppException
  • non-2xx response → ServiceResponseError with logged detail
  • structured logging of every outbound call
"""
from __future__ import annotations

import json
from typing import Any, Dict

import httpx

from app.core.config import get_settings
from app.core.exceptions import (
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class BaseServiceClient:
    """
    Thin async HTTP wrapper.  Subclasses declare:
        service_name  – used in log messages and exceptions
        base_url_key  – name of the Settings attribute holding the URL
    """

    service_name: str = "external-service"
    base_url: str = ""

    def __init__(self) -> None:
        timeout = httpx.Timeout(
            timeout=settings.SERVICE_TIMEOUT,
            connect=settings.SERVICE_CONNECT_TIMEOUT,
        )
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "BaseServiceClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ── Internal request helper ───────────────────────────────────────────

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST JSON to *path*, return parsed JSON body.
        Raises clean AppExceptions on all failure modes.
        """
        url = f"{self.base_url}{path}"
        logger.info("[%s] POST %s payload_keys=%s", self.service_name, url, list(payload.keys()))

        try:
            response = await self._client.post(path, json=payload)
        except httpx.ConnectError as exc:
            logger.error("[%s] Connection refused: %s", self.service_name, exc)
            raise ServiceUnavailableError(
                f"{self.service_name} is unavailable (connection refused)."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("[%s] Request timed out: %s", self.service_name, exc)
            raise ServiceTimeoutError(
                f"{self.service_name} did not respond within the timeout window."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("[%s] Request error: %s", self.service_name, exc)
            raise ServiceUnavailableError(
                f"{self.service_name} request failed: {exc}"
            ) from exc

        return self._handle_response(response)

    async def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        logger.info("[%s] GET %s params=%s", self.service_name, url, params)

        try:
            response = await self._client.get(path, params=params)
        except httpx.ConnectError as exc:
            logger.error("[%s] Connection refused: %s", self.service_name, exc)
            raise ServiceUnavailableError(
                f"{self.service_name} is unavailable (connection refused)."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("[%s] Request timed out: %s", self.service_name, exc)
            raise ServiceTimeoutError(
                f"{self.service_name} did not respond within the timeout window."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("[%s] Request error: %s", self.service_name, exc)
            raise ServiceUnavailableError(
                f"{self.service_name} request failed: {exc}"
            ) from exc

        return self._handle_response(response)

    # ── Response processing ───────────────────────────────────────────────

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        logger.info(
            "[%s] Response status=%d", self.service_name, response.status_code
        )

        if response.is_success:
            try:
                return response.json()
            except json.JSONDecodeError as exc:
                logger.error(
                    "[%s] Non-JSON response body: %s", self.service_name, response.text[:200]
                )
                raise ServiceResponseError(
                    f"{self.service_name} returned a non-JSON response."
                ) from exc

        # Non-2xx
        logger.error(
            "[%s] Error response status=%d body=%s",
            self.service_name,
            response.status_code,
            response.text[:500],
        )
        raise ServiceResponseError(
            f"{self.service_name} returned HTTP {response.status_code}."
        )
