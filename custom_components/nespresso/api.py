"""Nespresso API client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import MACHINE_STATUS_MAP, COFFEE_FAMILY_MAP

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.nespresso.com/ecapi"
REFRESH_URL = "https://www.nespresso.com/ecapi/identityprovider/v2/{market}/b2c/token/refresh"
USER_AGENT = "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36"


class NespressoAuthError(Exception):
    """Authentication error."""


class NespressoApiError(Exception):
    """Generic API error."""


class NespressoClient:
    """Async client for the Nespresso API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        refresh_token: str | None = None,
        market: str = "it",
    ) -> None:
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._market = market
        self._customer_id: str | None = None

    async def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh_token cookie. Returns True if successful."""
        if not self._refresh_token:
            _LOGGER.warning("No refresh token available")
            return False
        url = REFRESH_URL.format(market=self._market)
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Origin": "https://www.nespresso.com",
            "Referer": f"https://www.nespresso.com/{self._market}/{self._market}/",
        }
        cookies = {
            "access-token": self._access_token,
            "refresh-token": self._refresh_token,
        }
        try:
            async with self._session.post(url, headers=headers, cookies=cookies) as resp:
                _LOGGER.debug("Token refresh status: %s", resp.status)
                if resp.status != 200:
                    _LOGGER.warning("Token refresh failed with status %s", resp.status)
                    return False
                for cookie in resp.cookies.values():
                    if cookie.key == "access-token":
                        self._access_token = cookie.value
                        _LOGGER.info("Access token refreshed successfully")
                    elif cookie.key == "refresh-token":
                        self._refresh_token = cookie.value
                return bool(self._access_token)
        except aiohttp.ClientError as err:
            _LOGGER.warning("Token refresh network error: %s", err)
            return False

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    @property
    def _headers(self) -> dict:
        return {
            "content-type": "application/json;charset=utf-8",
            "accept": "application/json, text/plain, */*",
            "user-agent": USER_AGENT,
            "accept-language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://www.nespresso.com",
            "referer": f"https://www.nespresso.com/{self._market}/{self._market}/",
        }

    @property
    def _cookies(self) -> dict:
        return {"access-token": self._access_token}

    async def _get(self, path: str, ignore_errors: bool = False) -> Any:
        url = f"{BASE_URL}/{path}"
        try:
            async with self._session.get(
                url, headers=self._headers, cookies=self._cookies
            ) as resp:
                _LOGGER.debug("GET %s → %s", url, resp.status)
                if resp.status == 401:
                    raise NespressoAuthError("Token expired (401)")
                if resp.status == 403:
                    raise NespressoAuthError("Access denied (403)")
                if resp.status == 404:
                    raise NespressoApiError(f"Not found (404): {path}")
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (NespressoAuthError, NespressoApiError):
            if ignore_errors:
                return None
            raise
        except aiohttp.ClientResponseError as err:
            if ignore_errors:
                return None
            raise NespressoApiError(f"HTTP {err.status}: {err.message}") from err

    async def get_customer_id(self) -> str:
        if self._customer_id:
            return self._customer_id
        data = await self._get(f"customers/v7/{self._market}/b2c/me")
        cid = (
            data.get("memberNumber")
            or data.get("customerId")
            or data.get("id")
            or data.get("customerNumber")
        )
        if not cid:
            raise NespressoApiError(f"Cannot find customer ID. Keys: {list(data.keys())}")
        self._customer_id = str(cid)
        return self._customer_id

    async def get_machines(self) -> list[dict]:
        customer_id = await self.get_customer_id()
        data = await self._get(f"machines/v1/{self._market}/b2c/{customer_id}")
        if isinstance(data, list):
            machines = data
        else:
            machines = data.get("machines", data.get("items", []))
        return [m for m in machines if m.get("modules") or m.get("macAddress") or m.get("id")]

    async def get_machine_status(self, customer_id: str, machine_id: str) -> dict:
        try:
            return await self._get(
                f"machines/v1/{self._market}/b2c/{customer_id}/{machine_id}/status"
            )
        except NespressoApiError as err:
            _LOGGER.warning("Status error for %s: %s", machine_id, err)
            return {}

    async def get_machine_presence(self, customer_id: str, machine_id: str) -> dict:
        try:
            return await self._get(
                f"machines/v1/{self._market}/b2c/{customer_id}/{machine_id}/presence"
            )
        except NespressoApiError as err:
            _LOGGER.warning("Presence error for %s: %s", machine_id, err)
            return {}

    @staticmethod
    def parse_status(status_code: int) -> str:
        return MACHINE_STATUS_MAP.get(status_code, f"unknown ({status_code})")

    @staticmethod
    def parse_coffee_family(family_id: int | None) -> str | None:
        if family_id is None:
            return None
        return COFFEE_FAMILY_MAP.get(int(family_id), f"family_{family_id}")
