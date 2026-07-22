"""Pluggable live web-scraping sources for comparable market listings.

Live scraping is OPTIONAL. It only runs when ``ENABLE_LIVE_SCRAPING=true`` and
requires a machine with Firefox installed (it will not work on browserless
serverless hosts such as Vercel/Netlify). When disabled, the app estimates
prices from the bundled dataset instead - see ``app.predict_from_cache``.

Each scraper returns a ``pandas.DataFrame`` of comparable listings using the
same column schema the pricing model expects (matching ``new_cars.csv``):

    Name, Location, Year, Kilometers_Driven, Fuel_Type, Transmission,
    Owner_Type, Engine, Power, Seats, Price

Add a new source by subclassing ``BaseScraper`` and registering it in
``REGISTRY``. Select the active source with the ``SCRAPER_SOURCE`` env var.

IMPORTANT: Always review a site's Terms of Service and robots.txt before
enabling scraping against it. Facebook Marketplace in particular restricts
automated access and typically requires authentication; the scraper below is a
best-effort, experimental starting point.
"""

import os
import re
import time

import pandas as pd

# Columns the pricing model consumes (see model.clean / model.encode).
SCHEMA = [
    "Name", "Location", "Year", "Kilometers_Driven", "Fuel_Type",
    "Transmission", "Owner_Type", "Engine", "Power", "Seats", "Price",
]


class BaseScraper:
    """Common interface for all scraping sources."""

    name = "base"
    label = "Base"

    def scrape(self, item):
        """Return a DataFrame of comparable listings for the given item dict."""
        raise NotImplementedError

    @staticmethod
    def _empty():
        return pd.DataFrame(columns=SCHEMA)


class Cars24Scraper(BaseScraper):
    """Scrapes cars24.com via the existing Selenium routine in UserInput.py."""

    name = "cars24"
    label = "Cars24"

    def scrape(self, item):
        import UserInput as wsi  # lazy import: only needs selenium when used

        driver = wsi.start_driver()
        try:
            return wsi.web_scrape(item, driver)
        finally:
            try:
                driver.quit()
            except Exception:
                pass


class FacebookMarketplaceScraper(BaseScraper):
    """Experimental Facebook Marketplace source.

    Facebook requires login and actively restricts scraping, so this is a
    best-effort implementation intended as an extension point. It collects
    listing prices for a brand/model query and pairs them with the user's own
    specs so the pricing model has a usable training frame. Unverified against
    live Facebook; enable at your own risk and per Facebook's ToS.
    """

    name = "facebook_marketplace"
    label = "Facebook Marketplace"
    SEARCH_URL = "https://www.facebook.com/marketplace/search/?query={query}"

    def scrape(self, item):
        from selenium.webdriver.common.by import By
        import UserInput as wsi

        driver = wsi.start_driver()
        rows = []
        try:
            query = f"{item.get('Brand', '')} {str(item.get('Model', '')).split(' ')[0]}".strip()
            driver.get(self.SEARCH_URL.format(query=query.replace(" ", "%20")))
            time.sleep(6)

            cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/marketplace/item/']")
            for card in cards[:40]:
                text = (card.text or "").strip()
                match = re.search(r"[₹$€£]\s?([\d,]+)", text)
                if not match:
                    continue
                price = int(match.group(1).replace(",", ""))
                # Pair the listing price with the user's own specs so the model
                # has a coherent training row (FB titles are unstructured).
                rows.append({
                    "Name": f"{item.get('Year', '')} {item.get('Brand', '')} {str(item.get('Model', '')).split(' ')[0]}".strip(),
                    "Location": item.get("Location"),
                    "Year": item.get("Year"),
                    "Kilometers_Driven": item.get("Kilometers_Driven"),
                    "Fuel_Type": item.get("Fuel_Type"),
                    "Transmission": item.get("Transmission"),
                    "Owner_Type": item.get("Owner_Type"),
                    "Engine": item.get("Engine"),
                    "Power": item.get("Power"),
                    "Seats": item.get("Seats"),
                    "Price": price,
                })
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        return pd.DataFrame(rows, columns=SCHEMA)


REGISTRY = {
    Cars24Scraper.name: Cars24Scraper,
    FacebookMarketplaceScraper.name: FacebookMarketplaceScraper,
}


def available_sources():
    """Return the list of registered scraper source keys."""
    return list(REGISTRY.keys())


def get_scraper(name):
    """Instantiate a scraper by its source key (e.g. 'cars24')."""
    try:
        return REGISTRY[name]()
    except KeyError:
        raise ValueError(
            f"Unknown SCRAPER_SOURCE '{name}'. Available: {', '.join(available_sources())}"
        )
