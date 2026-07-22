import os
import unittest
from unittest.mock import patch

import pandas as pd

import model
from market_model import predict_price, train_model
from marketplace_providers import EbayBrowseProvider


class MarketModelTests(unittest.TestCase):
    def test_versioned_model_round_trip(self):
        rows = []
        items = [
            ("vehicle", "Honda", "City", 500_000),
            ("mobiles", "Apple", "iPhone 14", 45_000),
            ("laptops", "Dell", "XPS 13", 70_000),
        ]
        for category, brand, item_model, base_price in items:
            for index in range(12):
                rows.append(
                    {
                        "category": category,
                        "brand": brand,
                        "model": item_model,
                        "condition": "used",
                        "price": base_price + index * 100,
                    }
                )
        result = train_model(rows, minimum_rows=25)
        prediction = predict_price(
            result.artifact,
            {
                "category": "mobiles",
                "brand": "Apple",
                "model": "iPhone 14",
                "condition": "used",
            },
        )
        self.assertGreater(prediction, 40_000)
        self.assertLess(prediction, 50_000)

    def test_bundled_vehicle_model_is_cached(self):
        rows = pd.read_csv("new_cars.csv")
        item = {
            "Model": "City",
            "Year": 2015,
            "Kilometers_Driven": 50_000,
            "Fuel_Type": "Petrol",
            "Transmission": "Manual",
            "Owner_Type": "1",
            "Engine": 1497,
            "Power": 117,
            "Seats": 5,
        }
        model._MODEL_CACHE.clear()
        first = model.model_call(rows, item)
        second = model.model_call(rows, item)
        self.assertGreater(first, 0)
        self.assertEqual(first, second)
        self.assertEqual(len(model._MODEL_CACHE), 1)


class EbayProviderTests(unittest.TestCase):
    def test_search_accepts_only_target_currency(self):
        environment = {
            "EBAY_CLIENT_ID": "client",
            "EBAY_CLIENT_SECRET": "secret",
            "TARGET_CURRENCY": "USD",
        }
        response = {
            "itemSummaries": [
                {
                    "itemId": "1",
                    "title": "Apple iPhone",
                    "condition": "Used",
                    "price": {"value": "399.99", "currency": "USD"},
                    "itemWebUrl": "https://example.test/1",
                },
                {
                    "itemId": "2",
                    "title": "Wrong currency",
                    "price": {"value": "100", "currency": "EUR"},
                },
            ]
        }
        with patch.dict(os.environ, environment, clear=False):
            provider = EbayBrowseProvider()
            with (
                patch.object(provider, "_access_token", return_value="token"),
                patch.object(provider, "_request_json", return_value=response),
            ):
                observations = provider.search("Apple iPhone")
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].price, 399.99)


if __name__ == "__main__":
    unittest.main()
