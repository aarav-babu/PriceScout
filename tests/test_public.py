"""Public launch regression tests; no network or database required."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import live_prices
import public_app


def card(title='2018 Maruti Swift VXI', price='₹4.18 lakh', identity='10019270138'):
    return f'''<a href="https://www.cars24.com/buy-used-maruti-swift-2018-cars-gurgaon-{identity}/">
      <span>Cars24 Owned Stock</span><h3>{title}</h3>
      <p>52,541 km</p><p>Petrol</p><p>Manual</p><p>EMI ₹7,375/m*</p>
      <div class="styles_priceWrap__abc"><p>₹5.70L</p><p>{price}</p></div>
      <div class="styles_hubAddress__abc">Gurgaon</div></a>'''


class PublicTests(unittest.TestCase):
    def setUp(self):
        live_prices._cache.clear()
        live_prices._next_fetch = 0
        live_prices._cooldown_until = 0
        public_app._clients.clear()
        self.client = public_app.app.test_client()

    def result(self):
        return {'listings': live_prices.parse_listings(card()),
                'checked_at': datetime.now(timezone.utc), 'cached': False,
                'source_url': live_prices.source_url('maruti', 'Swift', 'delhi-ncr')}

    def test_current_price_not_emi_or_original_price(self):
        item = live_prices.parse_listings(card())[0]
        self.assertEqual(item['price'], 418000)
        self.assertEqual(item['kilometers'], 52541)
        self.assertEqual(item['title'], '2018 Maruti Swift VXI')

    def test_price_units(self):
        for text, expected in [('₹4,18,000', 418000), ('₹4.18L', 418000), ('₹1.25 crore', 12500000)]:
            with self.subTest(text=text):
                self.assertEqual(live_prices.parse_listings(card(price=text))[0]['price'], expected)

    def test_duplicate_listings_removed(self):
        self.assertEqual(len(live_prices.parse_listings(card() + card())), 1)

    def test_external_and_script_links_excluded(self):
        for host in ['https://evil.example', 'https://www.cars24.com.evil.example', 'javascript:alert(1)//']:
            self.assertEqual(live_prices.parse_listings(card().replace('https://www.cars24.com', host)), [])

    def test_missing_price_block_does_not_fall_back_to_emi(self):
        self.assertEqual(live_prices.parse_listings(card().replace('styles_priceWrap__abc', 'unknown')), [])

    def test_search_inputs_cannot_change_source_host(self):
        for model in ['../../', 'https://evil.example', '<script>', '', 'x' * 41]:
            with self.subTest(model=model), self.assertRaises(ValueError):
                live_prices.source_url('maruti', model, 'delhi-ncr')

    def test_year_is_used_in_source_url(self):
        self.assertEqual(live_prices.source_url('maruti', 'Swift', 'delhi-ncr', '2018'),
                         'https://www.cars24.com/buy-used-maruti-swift-2018-cars-delhi-ncr/')

    @patch('live_prices.fetch_html', return_value=card())
    def test_cache_preserves_fetch_time_and_avoids_second_request(self, fetch):
        first = live_prices.search('maruti', 'Swift', 'delhi-ncr')
        second = live_prices.search('maruti', 'Swift', 'delhi-ncr')
        self.assertFalse(first['cached'])
        self.assertTrue(second['cached'])
        self.assertEqual(first['checked_at'], second['checked_at'])
        fetch.assert_called_once()

    @patch('live_prices.fetch_html', return_value=card())
    def test_expired_cache_fetches_again(self, fetch):
        live_prices.search('maruti', 'Swift', 'delhi-ncr')
        url, (created, result) = next(iter(live_prices._cache.items()))
        live_prices._cache[url] = (created - 301, result)
        live_prices._next_fetch = 0
        self.assertFalse(live_prices.search('maruti', 'Swift', 'delhi-ncr')['cached'])
        self.assertEqual(fetch.call_count, 2)

    @patch('live_prices.fetch_html', return_value='<html>Access denied</html>')
    def test_blocked_or_changed_page_is_error_not_fake_prices(self, fetch):
        with self.assertRaises(live_prices.SourceUnavailable):
            live_prices.search('maruti', 'Swift', 'delhi-ncr')
        self.assertFalse(live_prices._cache)
        self.assertFalse(live_prices._lock.locked())

    def test_home_and_health_need_no_source(self):
        with patch('live_prices.search') as search:
            self.assertEqual(self.client.get('/').status_code, 200)
            self.assertEqual(self.client.get('/healthz').json['status'], 'ok')
            search.assert_not_called()

    def test_results_render_prices_and_source(self):
        with patch('live_prices.search', return_value=self.result()):
            response = self.client.get('/?brand=maruti&model=Swift&city=delhi-ncr')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('₹4,18,000', text)
        self.assertIn('Checked ', text)
        self.assertIn('View on Cars24', text)
        self.assertIn('first page', text)

    def test_filters_do_not_invent_attributes(self):
        with patch('live_prices.search', return_value=self.result()):
            response = self.client.get('/?brand=maruti&model=Swift&city=delhi-ncr&fuel=Diesel')
        self.assertIn('No matches in this sample', response.get_data(as_text=True))
        self.assertNotIn('Median asking price', response.get_data(as_text=True))

    def test_unrelated_model_is_not_shown(self):
        result = self.result()
        result['listings'][0]['title'] = '2018 Maruti Baleno VXI'
        with patch('live_prices.search', return_value=result):
            response = self.client.get('/?brand=maruti&model=Swift&city=delhi-ncr')
        self.assertIn('No matches in this sample', response.get_data(as_text=True))

    def test_unavailable_source_shows_retry_and_link(self):
        with patch('live_prices.search', side_effect=live_prices.SourceUnavailable('Try again later.')):
            response = self.client.get('/?brand=maruti&model=Swift&city=delhi-ncr')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers['Retry-After'], '60')
        self.assertIn('Check this search on Cars24', response.get_data(as_text=True))

    def test_invalid_input_rejected_before_fetch(self):
        with patch('live_prices.search') as search:
            response = self.client.get('/?brand=maruti&model=%3Cscript%3E&city=delhi-ncr')
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('<script>', response.get_data(as_text=True))
            search.assert_not_called()

    def test_rate_limit_stops_source_calls(self):
        with patch('live_prices.search', return_value=self.result()) as search:
            for _ in range(12):
                self.client.get('/?brand=maruti&model=Swift&city=delhi-ncr')
            response = self.client.get('/?brand=maruti&model=Swift&city=delhi-ncr')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(search.call_count, 12)


if __name__ == '__main__':
    unittest.main()
