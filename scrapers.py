"""Compatibility exports for the authorized provider layer.

PriceScout no longer ships browser automation for Cars24 or Facebook
Marketplace because their terms do not authorize this hosted commercial use.
Use documented provider APIs from ``marketplace_providers`` instead.
"""

from marketplace_providers import (
    EbayBrowseProvider,
    MarketObservation,
    NhtsaProvider,
    ProviderError,
    pricing_providers,
    provider_status,
)


def available_sources() -> list[str]:
    return [provider.name for provider in pricing_providers()]


def get_scraper(name: str):
    """Retained for callers migrating from the old scraper registry."""
    providers = {provider.name: provider for provider in pricing_providers()}
    try:
        return providers[name]
    except KeyError as exc:
        available = ", ".join(providers) or "none configured"
        raise ValueError(f"Unknown or unconfigured provider '{name}'. Available: {available}") from exc


__all__ = [
    "EbayBrowseProvider",
    "MarketObservation",
    "NhtsaProvider",
    "ProviderError",
    "available_sources",
    "get_scraper",
    "pricing_providers",
    "provider_status",
]
