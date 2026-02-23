import logging
import os
import time
import re
import json
import threading
from dataclasses import dataclass, field
from functools import wraps

import pandas as pd
from playwright.sync_api import sync_playwright

import model as mo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiter — enforces minimum delay between outbound requests
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, min_delay=None):
        self.min_delay = min_delay or float(os.getenv('SCRAPE_RATE_LIMIT', '2'))
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self):
        with self._lock:
            elapsed = time.time() - self._last_call
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
            self._last_call = time.time()


rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# Retry decorator — exponential backoff (2/4/8 s, 3 attempts)
# ---------------------------------------------------------------------------

def retry_with_backoff(max_retries=3, base_delay=2):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Attempt %d/%d for %s failed: %s — retrying in %ds",
                        attempt, max_retries, fn.__name__, exc, delay,
                    )
                    time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# IngestionStats — tracks scrape run counters
# ---------------------------------------------------------------------------

@dataclass
class IngestionStats:
    listings_processed: int = 0
    listings_inserted: int = 0
    listings_deduped: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def duration_seconds(self):
        return round(time.time() - self.start_time, 2)

    @property
    def error_rate(self):
        if self.listings_processed == 0:
            return 0.0
        return round(self.errors / self.listings_processed, 4)


def to_csv(df):
    with open('new_cars.csv', 'w', encoding='utf-8', newline="") as cw:
        df.to_csv(cw, sep=',', index=False, encoding='utf-8')


def process_string(input_string):
    result = re.sub(r'\b\d+\s*STR\b', '', input_string)
    result = re.sub(r'\d+(\.\d+)?L?', '', result)

    strings_to_remove = ['petrol', 'diesel', 'cng', 'lpg']
    for string in strings_to_remove:
        result = re.sub(fr'\b{re.escape(string)}\b', '', result, flags=re.IGNORECASE)

    result = re.sub(r'\s+', ' ', result).strip()
    return result


# ---------------------------------------------------------------------------
# Browser management
# ---------------------------------------------------------------------------

SCREENSHOT_DIR = os.getenv('SCRAPE_SCREENSHOT_DIR', '/tmp/scrape_screenshots')


def start_browser():
    """Launch Playwright Chromium with stealth settings to avoid bot detection."""
    logger.info("[BROWSER] Launching Chromium (headless)...")
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ],
    )
    context = browser.new_context(
        user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        ),
        viewport={'width': 1920, 'height': 1080},
        locale='en-IN',
        timezone_id='Asia/Kolkata',
    )
    # Remove navigator.webdriver flag that bot detectors check
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    page = context.new_page()
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    logger.info("[BROWSER] Browser ready (stealth mode)")
    return pw, browser, page


def _screenshot(page, name):
    """Save a timestamped screenshot for debugging."""
    try:
        path = os.path.join(SCREENSHOT_DIR, f"{int(time.time())}_{name}.png")
        page.screenshot(path=path)
        logger.info("[SCREENSHOT] Saved: %s", path)
    except Exception as exc:
        logger.debug("Screenshot failed: %s", exc)


# ---------------------------------------------------------------------------
# Scrape — intercept API responses + DOM fallback
# ---------------------------------------------------------------------------

@retry_with_backoff(max_retries=3, base_delay=2)
def scrape(car, page):
    """Extract listing data from Cars24 search results.

    Primary: intercept XHR/fetch JSON responses containing listing data.
    Fallback: parse listing cards from the DOM using text-based selectors.
    """
    captured_listings = []

    def _handle_response(response):
        """Capture listing data from Cars24 API responses."""
        url = response.url
        if '/api/' not in url and '/buy-used-cars' not in url:
            return
        content_type = response.headers.get('content-type', '')
        if 'json' not in content_type:
            return
        logger.info("[API-INTERCEPT] JSON response from: %s (status %d)", url[:120], response.status)
        try:
            body = response.json()
        except Exception:
            return

        # Cars24 API returns listings under various keys
        results = None
        if isinstance(body, dict):
            for key in ('results', 'data', 'cars', 'content', 'classifiedList'):
                if key in body and isinstance(body[key], list):
                    results = body[key]
                    break
            # Sometimes nested: body.data.results
            if results is None and isinstance(body.get('data'), dict):
                for key in ('results', 'cars', 'content', 'classifiedList'):
                    if key in body['data'] and isinstance(body['data'][key], list):
                        results = body['data'][key]
                        break

        if not results:
            return

        for item in results:
            if not isinstance(item, dict):
                continue
            try:
                listing = _extract_from_api(item, car)
                if listing:
                    captured_listings.append(listing)
            except Exception as exc:
                logger.debug("Failed to parse API listing item: %s", exc)

    page.on("response", _handle_response)

    # Scroll to load more results
    logger.info("[SCRAPE] Scrolling page to trigger API calls (5 scrolls)...")
    for i in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        logger.info("[SCRAPE]   Scroll %d/5 — captured %d listings so far", i + 1, len(captured_listings))

    page.remove_listener("response", _handle_response)
    _screenshot(page, "05_after_scrolling")

    # If API interception captured data, use it
    if captured_listings:
        logger.info("Captured %d listings via API interception", len(captured_listings))
        df = pd.DataFrame(captured_listings[:50])
        to_csv(df)
        return df

    # Fallback: parse listing cards from the DOM
    logger.info("API interception yielded no data, falling back to DOM parsing")
    data_list = _scrape_dom_fallback(car, page)

    df = pd.DataFrame(data_list)
    to_csv(df)
    return df


def _extract_from_api(item, car):
    """Extract a single listing dict from an API response item."""
    # Cars24 API uses various field names — try common ones
    name = (
        item.get('car_name')
        or item.get('carName')
        or item.get('name')
        or item.get('title')
        or item.get('model')
        or ''
    )
    year = (
        item.get('modelYear')
        or item.get('model_year')
        or item.get('year')
        or item.get('make_year')
    )
    price_raw = (
        item.get('price')
        or item.get('fixedPrice')
        or item.get('fixed_price')
        or item.get('displayPrice')
        or item.get('onRoadPrice')
    )
    km = (
        item.get('odometerReading')
        or item.get('km')
        or item.get('kms_driven')
        or item.get('kilometerDriven')
        or item.get('kilometer')
    )
    fuel = (
        item.get('fuelType')
        or item.get('fuel_type')
        or item.get('fuel')
    )
    transmission = (
        item.get('transmission')
        or item.get('transmissionType')
        or item.get('transmission_type')
    )
    owner = (
        item.get('ownerType')
        or item.get('owner_type')
        or item.get('ownerNumber')
        or item.get('noOfOwners')
    )
    engine = (
        item.get('engineCapacity')
        or item.get('engine')
        or item.get('engineDisplacement')
        or item.get('displacement')
    )
    power_val = (
        item.get('power')
        or item.get('maxPower')
        or item.get('max_power')
    )
    seats = (
        item.get('seats')
        or item.get('seatingCapacity')
    )
    location = (
        item.get('city')
        or item.get('cityName')
        or item.get('location')
        or item.get('city_name')
    )

    if not name and not year:
        return None

    # Normalize price to integer (Cars24 may return in lakhs or absolute)
    price = _normalize_price(price_raw)

    # Normalize owner type to first character if it's a string like "First Owner"
    if isinstance(owner, str) and len(owner) > 1:
        owner = owner[0]

    # Normalize engine — strip "cc" suffix
    if isinstance(engine, str):
        engine = int(re.sub(r'[^\d]', '', engine) or 0) or None

    # Normalize km — strip commas and "km"
    if isinstance(km, str):
        km = int(re.sub(r'[^\d]', '', km) or 0) or None

    # Normalize power
    if isinstance(power_val, str):
        m = re.search(r'(\d+(?:\.\d+)?)', power_val)
        power_val = float(m.group(1)) if m else None

    return {
        'Name': str(year or '') + ' ' + str(name),
        'Location': location,
        'Year': int(year) if year else None,
        'Kilometers_Driven': int(km) if km else None,
        'Fuel_Type': fuel,
        'Transmission': transmission,
        'Owner_Type': owner,
        'Engine': int(engine) if engine else None,
        'Power': float(power_val) if power_val else None,
        'Price': price,
        'Seats': int(seats) if seats else None,
    }


def _normalize_price(raw):
    """Convert price to integer rupees."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        # If value is small, assume it's in lakhs
        if raw < 500:
            return int(raw * 100000)
        return int(raw)
    if isinstance(raw, str):
        m = re.search(r'(\d+(?:\.\d+)?)', raw.replace(',', ''))
        if m:
            val = float(m.group(1))
            if 'lakh' in raw.lower() or val < 500:
                return int(val * 100000)
            return int(val)
    return None


def _scrape_dom_fallback(car, page):
    """Parse listing cards from the DOM using text-based selectors."""
    data_list = []

    # Try to find listing cards using common patterns
    # Cars24 listing cards usually contain price with ₹ or Lakh
    cards = page.locator("a[href*='/buy-used-']").all()
    if not cards:
        cards = page.locator("[class*='card'], [class*='listing'], [class*='vehicle']").all()

    count = 0
    for card in cards:
        if count >= 50:
            break
        rate_limiter.wait()
        try:
            text = card.inner_text()
            if not text or str(car.get('Year', '')) not in text:
                continue

            # Extract price
            price_match = re.search(r'₹\s*([\d,.]+)\s*(lakh|lac)?', text, re.IGNORECASE)
            if not price_match:
                price_match = re.search(r'([\d,.]+)\s*(lakh|lac)', text, re.IGNORECASE)
            price = None
            if price_match:
                val = float(price_match.group(1).replace(',', ''))
                if price_match.group(2):
                    price = int(val * 100000)
                else:
                    price = int(val)

            # Extract km
            km_match = re.search(r'([\d,]+)\s*km', text, re.IGNORECASE)
            km = int(km_match.group(1).replace(',', '')) if km_match else None

            # Extract year
            year_match = re.search(r'(20\d{2})', text)
            year = int(year_match.group(1)) if year_match else None

            data_list.append({
                'Name': text.split('\n')[0].strip()[:80],
                'Location': car.get('Location'),
                'Year': year,
                'Kilometers_Driven': km,
                'Fuel_Type': car.get('Fuel_Type'),
                'Transmission': car.get('Transmission'),
                'Owner_Type': car.get('Owner_Type', '1')[0] if car.get('Owner_Type') else None,
                'Engine': car.get('Engine'),
                'Power': car.get('Power'),
                'Price': price,
                'Seats': car.get('Seats'),
            })
            count += 1
        except Exception as exc:
            logger.debug("Failed to parse DOM card: %s", exc)

    logger.info("DOM fallback extracted %d listings", len(data_list))
    return data_list


# ---------------------------------------------------------------------------
# Web scrape — navigate, search, apply filters
# ---------------------------------------------------------------------------

def web_scrape(item, page):
    """Navigate to Cars24 and search for a specific car with filters."""
    link = "https://www.cars24.com/buy-used-car/"
    logger.info("[SCRAPE] Navigating to %s", link)
    page.goto(link, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    _screenshot(page, "01_page_loaded")
    logger.info("[SCRAPE] Page loaded, current URL: %s", page.url)

    # Find search input — use placeholder or input type
    search_input = (
        page.get_by_placeholder("Search car")
        .or_(page.get_by_placeholder("Search"))
        .or_(page.get_by_placeholder("search"))
        .or_(page.locator("input[type='text']").first)
        .or_(page.locator("input[type='search']").first)
    )
    search_query = item['Brand'] + " " + item['Model'].split(" ")[0]
    logger.info("[SCRAPE] Typing search query: '%s'", search_query)
    search_input.fill(search_query)
    page.wait_for_timeout(3000)
    _screenshot(page, "02_search_typed")

    # Click first suggestion from autocomplete dropdown
    suggestion = (
        page.get_by_role("option").first
        .or_(page.locator("ul li label").first)
        .or_(page.locator("[class*='suggestion'] li, [class*='dropdown'] li, [class*='auto'] li").first)
    )
    try:
        suggestion.click(timeout=5000)
        logger.info("[SCRAPE] Clicked autocomplete suggestion")
        page.wait_for_timeout(2000)
    except Exception:
        logger.warning("[SCRAPE] No autocomplete suggestion found, pressing Enter")
        search_input.press("Enter")
        page.wait_for_timeout(3000)

    _screenshot(page, "03_after_search")
    logger.info("[SCRAPE] After search, URL: %s", page.url)

    # Apply fuel type filter
    fuel_type = item.get('Fuel_Type', '')
    if fuel_type:
        logger.info("[SCRAPE] Applying fuel filter: '%s'", fuel_type)
        _apply_filter(page, fuel_type)

    # Apply transmission filter
    trans_type = item.get('Transmission', '')
    if trans_type:
        logger.info("[SCRAPE] Applying transmission filter: '%s'", trans_type)
        _apply_filter(page, trans_type)

    _screenshot(page, "04_filters_applied")
    page.wait_for_timeout(2000)
    logger.info("[SCRAPE] Filters applied, starting data extraction...")
    df = scrape(item, page)
    logger.info("[SCRAPE] Extraction complete — %d listings found", len(df))
    return df


def _apply_filter(page, filter_text):
    """Click a filter label by its text content (e.g., 'Petrol', 'Automatic')."""
    try:
        label = page.get_by_text(filter_text, exact=True)
        if label.count() > 0:
            label.first.click(timeout=3000)
            page.wait_for_timeout(1000)
        else:
            logger.debug("Filter '%s' not visible on page", filter_text)
    except Exception as exc:
        logger.debug("Could not apply filter '%s': %s", filter_text, exc)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ui_scrape(car_details):
    """Scrape Cars24 for comparable listings and predict price.

    Creates browser internally and ensures cleanup.
    Returns (price, stats).
    """
    logger.info("=" * 60)
    logger.info("[UI_SCRAPE] Starting scrape for: %s %s (%s)", car_details.get('Brand'), car_details.get('Model'), car_details.get('Year'))
    logger.info("=" * 60)
    stats = IngestionStats()
    pw, browser, page = start_browser()
    try:
        df = web_scrape(car_details, page)
        stats.listings_processed = len(df)
        stats.listings_inserted = len(df)
        logger.info("[UI_SCRAPE] Calling ML model with %d listings...", len(df))
        price = mo.model_call(df, car_details)
        logger.info("[UI_SCRAPE] Predicted price: %s", price)
    except Exception as exc:
        stats.errors += 1
        logger.error("[UI_SCRAPE] Scrape failed: %s", exc)
        _screenshot(page, "error_state")
        raise
    finally:
        browser.close()
        pw.stop()
        logger.info("[BROWSER] Browser closed")
    elapsed = stats.duration_seconds
    logger.info("[UI_SCRAPE] Completed in %.1f secs (%.1f mins)", elapsed, elapsed / 60)
    logger.info("=" * 60)
    return int(price), stats
