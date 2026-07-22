"""Authorized market-data providers used by the pricing pipeline.

The production pipeline intentionally uses documented APIs. It does not automate
consumer websites, logins, CAPTCHAs, or undocumented endpoints.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


class ProviderError(RuntimeError):
    """A provider request failed or returned unusable data."""


@dataclass(frozen=True)
class MarketObservation:
    provider: str
    external_id: str
    title: str
    condition: str
    price: float
    currency: str
    url: str
    observed_at: datetime

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["observed_at"] = self.observed_at.astimezone(timezone.utc).replace(tzinfo=None)
        return record


class EbayBrowseProvider:
    """Read active asking prices through eBay's official Browse API."""

    name = "ebay"
    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    search_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    scope = "https://api.ebay.com/oauth/api_scope"

    def __init__(self) -> None:
        self.client_id = os.getenv("EBAY_CLIENT_ID", "")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
        self.marketplace_id = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")
        self.target_currency = os.getenv("TARGET_CURRENCY", "USD").upper()
        self.timeout = float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "15"))
        self.max_results = min(int(os.getenv("EBAY_RESULTS_PER_QUERY", "50")), 200)
        self._token: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> dict[str, Any]:
        request = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderError(f"eBay API returned HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"eBay API request failed: {exc}") from exc

    def _access_token(self) -> str:
        if self._token:
            return self._token
        if not self.configured:
            raise ProviderError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required")
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("ascii")
        payload = urllib.parse.urlencode(
            {"grant_type": "client_credentials", "scope": self.scope}
        ).encode("ascii")
        response = self._request_json(
            self.token_url,
            method="POST",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=payload,
        )
        try:
            self._token = response["access_token"]
        except KeyError as exc:
            raise ProviderError("eBay token response did not include access_token") from exc
        return self._token

    def search(self, query: str) -> list[MarketObservation]:
        params = urllib.parse.urlencode({"q": query, "limit": self.max_results})
        response = self._request_json(
            f"{self.search_url}?{params}",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            },
        )
        observed_at = datetime.now(timezone.utc)
        observations = []
        for item in response.get("itemSummaries", []):
            price = item.get("price") or {}
            if price.get("currency", "").upper() != self.target_currency:
                continue
            try:
                amount = float(price["value"])
            except (KeyError, TypeError, ValueError):
                continue
            if amount <= 0:
                continue
            observations.append(
                MarketObservation(
                    provider=self.name,
                    external_id=str(item.get("itemId", "")),
                    title=str(item.get("title", "")),
                    condition=str(item.get("condition", "used")),
                    price=amount,
                    currency=self.target_currency,
                    url=str(item.get("itemWebUrl", "")),
                    observed_at=observed_at,
                )
            )
        return observations


class NhtsaProvider:
    """Vehicle metadata enrichment through the public NHTSA vPIC API."""

    name = "nhtsa"
    decode_url = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"

    def __init__(self) -> None:
        self.timeout = float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "15"))

    @property
    def configured(self) -> bool:
        return True

    def decode_vin(self, vin: str) -> dict[str, str]:
        normalized = "".join(ch for ch in vin.upper() if ch.isalnum())
        if len(normalized) != 17:
            raise ValueError("VIN must contain exactly 17 letters and digits")
        request = urllib.request.Request(self.decode_url.format(vin=normalized))
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"NHTSA request failed: {exc}") from exc
        results = payload.get("Results") or []
        if not results:
            raise ProviderError("NHTSA returned no VIN result")
        result = results[0]
        return {
            key: str(result.get(key, ""))
            for key in ("Make", "Model", "ModelYear", "BodyClass", "FuelTypePrimary", "EngineCylinders")
        }


def pricing_providers() -> list[EbayBrowseProvider]:
    """Return configured providers that supply listing prices."""
    providers = [EbayBrowseProvider()]
    return [provider for provider in providers if provider.configured]


def provider_status() -> dict[str, bool]:
    """Expose configuration state without making network requests."""
    return {
        "ebay": EbayBrowseProvider().configured,
        "nhtsa": NhtsaProvider().configured,
    }
