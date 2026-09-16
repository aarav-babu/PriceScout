"""Read current asking prices from public Cars24 listing pages, without a browser."""

import re
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

CITIES = {
    'delhi-ncr': 'Delhi NCR', 'bangalore': 'Bangalore', 'mumbai': 'Mumbai',
    'hyderabad': 'Hyderabad', 'pune': 'Pune', 'chennai': 'Chennai',
    'ahmedabad': 'Ahmedabad', 'kolkata': 'Kolkata', 'jaipur': 'Jaipur',
    'lucknow': 'Lucknow', 'surat': 'Surat',
}
BRANDS = {
    'maruti': 'Maruti Suzuki', 'hyundai': 'Hyundai', 'tata': 'Tata',
    'honda': 'Honda', 'mahindra': 'Mahindra', 'kia': 'Kia',
    'toyota': 'Toyota', 'renault': 'Renault', 'ford': 'Ford',
    'volkswagen': 'Volkswagen', 'skoda': 'Skoda', 'nissan': 'Nissan',
    'mg': 'MG',
}
CACHE_SECONDS = 300
_cache = OrderedDict()
_lock = threading.Lock()
_next_fetch = 0.0
_cooldown_until = 0.0


class SourceUnavailable(Exception):
    pass


class SearchBusy(Exception):
    pass


def source_url(brand, model, city, year=''):
    if brand not in BRANDS or city not in CITIES:
        raise ValueError('Choose a supported brand and city.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 .-]{0,39}', model):
        raise ValueError('Enter a model name such as Swift, i20, or Nexon (up to 40 characters).')
    if year and (not re.fullmatch(r'\d{4}', year) or not 1990 <= int(year) <= datetime.now().year):
        raise ValueError('Choose a valid model year.')
    model_slug = re.sub(r'[^a-z0-9]+', '-', model.lower()).strip('-')
    year_slug = f'-{year}' if year else ''
    return f'https://www.cars24.com/buy-used-{brand}-{model_slug}{year_slug}-cars-{city}/'


def parse_listings(html):
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    seen = set()
    for card in soup.select('a[href]'):
        url = urljoin('https://www.cars24.com', card['href'])
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.netloc != 'www.cars24.com'
                or not re.fullmatch(r'/buy-used-[a-z0-9-]+-\d{8,}/', parsed.path)
                or url in seen):
            continue
        text = card.get_text(' ', strip=True)
        title = re.search(r'\b((?:19|20)\d{2}\s+.*?)\s+([\d,]+)\s*km\b', text, re.I)
        # Scope prices to the price block: EMI and crossed-out prices must never
        # be mistaken for the current asking price. The current amount is last.
        price_block = card.select_one('[class*="priceWrap"]')
        if not title or price_block is None:
            continue
        prices = re.findall(r'₹\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr|l)?\b',
                            price_block.get_text(' ', strip=True), re.I)
        if not prices:
            continue
        amount, unit = prices[-1]
        multiplier = {'lakh': 100000, 'lac': 100000, 'l': 100000,
                      'crore': 10000000, 'cr': 10000000}.get(unit.lower(), 1)
        price = int(Decimal(amount.replace(',', '')) * multiplier)
        if not 10000 <= price <= 100000000:
            continue
        fuel = re.search(r'\b(Petrol\s*\+\s*CNG|Petrol|Diesel|CNG|Electric|Hybrid)\b', text, re.I)
        transmission = re.search(r'\b(Manual|Automatic|Auto)\b', text, re.I)
        address = card.select_one('[class*="hubAddress"]')
        listings.append({
            'title': title[1].strip(), 'year': int(title[1][:4]),
            'kilometers': int(title[2].replace(',', '')), 'price': price,
            'fuel': fuel[1].title() if fuel else 'Not listed',
            'transmission': ('Automatic' if transmission and transmission[1].lower().startswith('auto')
                             else 'Manual' if transmission else 'Not listed'),
            'location': address.get_text(' ', strip=True) if address else '',
            'url': url,
        })
        seen.add(url)
    return listings[:50]


def fetch_html(url):
    try:
        with requests.get(url, headers={'User-Agent': 'PriceScout/1.0 (used-car price comparison)',
                                       'Accept': 'text/html'},
                          timeout=(5, 20), allow_redirects=False, stream=True) as response:
            if response.status_code != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
                raise SourceUnavailable('The listing source could not be reached. Please try again later.')
            chunks = bytearray()
            for chunk in response.iter_content(65536):
                chunks.extend(chunk)
                if len(chunks) > 5_000_000:
                    raise SourceUnavailable('The listing source returned an unexpected page.')
            return chunks.decode('utf-8', errors='replace')
    except requests.RequestException as exc:
        raise SourceUnavailable('The listing source is taking too long or is unavailable. Please try again later.') from exc


def search(brand, model, city, year=''):
    """Bound memory and outbound requests; never substitute sample data on failure."""
    global _next_fetch, _cooldown_until
    url = source_url(brand, model, city, year)
    if not _lock.acquire(timeout=0.1):
        raise SearchBusy('Another search is fetching prices. Please try again in a few seconds.')
    try:
        now = time.monotonic()
        cached = _cache.get(url)
        if cached and now - cached[0] < CACHE_SECONDS:
            _cache.move_to_end(url)
            return {**cached[1], 'cached': True}
        if now < _cooldown_until:
            raise SourceUnavailable('The listing source is temporarily unavailable. Please try again in a minute.')
        if now < _next_fetch:
            raise SearchBusy('Please wait a few seconds between new searches.')
        _next_fetch = now + 3
        try:
            html = fetch_html(url)
            listings = parse_listings(html)
            if not listings:
                # Empty pages can also mean the retailer changed its layout or
                # blocked the request. Do not report zero market inventory.
                raise SourceUnavailable('No priced listings could be read for this search. Try a broader model or another city, or check Cars24 directly.')
        except SourceUnavailable:
            _cooldown_until = time.monotonic() + 15
            raise
        result = {'listings': listings, 'source_url': url,
                  'checked_at': datetime.now(timezone.utc), 'cached': False}
        _cache[url] = (time.monotonic(), result)
        _cache.move_to_end(url)
        while len(_cache) > 128:
            _cache.popitem(last=False)
        return result
    finally:
        _lock.release()
