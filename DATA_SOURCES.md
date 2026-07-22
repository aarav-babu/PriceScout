# Market data policy and source review

This document is an engineering compliance screen, not legal advice. Provider
terms and product access change; re-check the linked terms before production
launch and record written approvals in the deployment runbook.

## Sources enabled in this repository

| Source | Use | Price meaning | Access |
| --- | --- | --- | --- |
| [eBay Browse API](https://developer.ebay.com/api-docs/buy/browse/overview.html) | Active comparables for vehicles, phones, and laptops | Seller asking price, not a completed sale | Official OAuth API; production approval may be required |
| [NHTSA vPIC](https://vpic.nhtsa.dot.gov/api/) | VIN decoding and vehicle metadata | No price data | Public government API |

The eBay provider is disabled until `EBAY_CLIENT_ID` and
`EBAY_CLIENT_SECRET` are configured. Before enabling it, confirm that the
current [eBay API License Agreement](https://developer.ebay.com/join/api-license-agreement)
allows this app's display, retention, derived statistics, and model-training
use. Restricted/historical eBay APIs are not assumed to be available.

NHTSA data can normalize vehicle identity and add recall or specification
features, but it cannot supply a resale target. `NhtsaProvider` is therefore an
enrichment provider rather than a pricing provider.

## Sources deliberately excluded

| Site | Reason |
| --- | --- |
| Cars24 | Its [terms](https://www.cars24.com/terms-and-conditions/) prohibit automated scraping and commercial extraction without written permission. |
| Facebook Marketplace | General commercial read access is unavailable. The [Content Library API](https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/fb-marketplace/) is limited to eligible public-interest researchers; partner APIs manage a partner's own inventory. |
| Craigslist | Its [terms](https://www.craigslist.org/about/terms.of.use) prohibit collection by robots, scripts, scrapers, and crawlers without a separate license. Its Bulkpost API is for managing one's own postings. |
| Swappa and Back Market | No general market-wide read API or data license has been identified. Seller APIs do not authorize collection of everyone else's listings. |

Robots.txt is a crawler instruction, not a grant of copyright, database,
contract, privacy, or commercial-reuse rights. A third-party scraping proxy
also does not grant rights to the upstream data. PriceScout does not include
login automation, CAPTCHA bypass, proxy rotation, browser fingerprinting, or
undocumented endpoint access.

## Recommended licensed additions

These are integration candidates, not pre-approved dependencies:

- Vehicles: [MarketCheck](https://www.marketcheck.com/apis/),
  [Auto.dev](https://docs.auto.dev/v2/products/vehicle-listings), KBB
  InfoDriver, or J.D. Power Consumer Pricing.
- Phones and laptops: RecommerceIQ or Apkudo for resale/trade-in values.
- Catalog normalization: Open Icecat for electronics and GSMA Device Database
  for TAC/IMEI identity.

For each provider, obtain written answers covering public display, attribution,
raw-data retention, historical storage, model training, survival of derived
model parameters after termination, redistribution, regions, deletion, audit,
and rate limits.

## Price semantics and geography

The current API model learns active asking prices. It must not be presented as
a completed-sale or guaranteed trade-in price. `EBAY_MARKETPLACE_ID` and
`TARGET_CURRENCY` must describe the same market; the pipeline rejects listings
in another currency rather than silently applying an exchange rate. Geographic
market differences cannot be corrected by currency conversion alone.

The default observation retention is seven days. Lower
`OBSERVATION_RETENTION_DAYS` if the provider agreement requires it. Do not
increase retention merely to improve model volume without confirming rights.
