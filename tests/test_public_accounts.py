import re
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import check_password_hash

import account_pages
from account_store import AccountStore
from public_app import app


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_config = {key: app.config[key] for key in ('TESTING', 'DATABASE_URL', 'SESSION_COOKIE_SECURE')}
        app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False,
                          DATABASE_URL='sqlite:///' + str(Path(self.temp.name) / 'test.db'))
        self.previous_store = app.extensions.pop('account_store', None)
        account_pages._attempts.clear()
        self.client = app.test_client()

    def tearDown(self):
        store = app.extensions.pop('account_store', None)
        if store:
            store.engine.dispose()
        if self.previous_store:
            app.extensions['account_store'] = self.previous_store
        app.config.update(self.previous_config)
        self.temp.cleanup()

    def token(self, client, path):
        response = client.get(path)
        return re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))[1]

    def register(self, client=None, email='one@example.test'):
        client = client or self.client
        token = self.token(client, '/userdata/register')
        return client.post('/userdata/register', data={'csrf_token': token,
                           'name': 'Test User', 'email': email, 'password': 'a long test passphrase'})

    def add_product(self, category='mobiles', model='iPhone 14'):
        path = '/postdata/' + category
        token = self.token(self.client, path)
        return self.client.post(path, data={'csrf_token': token, 'brand': 'Apple',
                                'model': model, 'condition': 'Good', 'storage': '256 GB'})

    def test_informational_pages_do_not_need_database(self):
        app.config['DATABASE_URL'] = None
        for path in ['/', '/products', '/misc/about', '/misc/contact', '/userdata/login', '/userdata/register']:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_registration_hashes_password_and_signs_in(self):
        response = self.register()
        self.assertEqual(response.status_code, 303)
        user = app.extensions['account_store'].find_user(email='one@example.test')
        self.assertNotEqual(user['password_hash'], 'a long test passphrase')
        self.assertTrue(check_password_hash(user['password_hash'], 'a long test passphrase'))
        self.assertEqual(self.client.get('/userdata/userprofile').status_code, 200)

    def test_registration_requires_valid_csrf(self):
        response = self.client.post('/userdata/register', data={'name': 'Test', 'email': 't@example.test', 'password': 'long password'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('This form has expired', response.get_data(as_text=True))

    def test_duplicate_email_rejected(self):
        self.register()
        other = app.test_client()
        response = self.register(other, email='ONE@example.test')
        self.assertEqual(response.status_code, 400)

    def test_signed_out_forms_redirect_to_sign_in(self):
        for path in ['/postdata/mobiles', '/postdata/laptops', '/userdata/userprofile']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/userdata/login', response.location)

    def test_phone_and_laptop_save_to_profile(self):
        self.register()
        for category, model in [('mobiles', 'iPhone 14'), ('laptops', 'MacBook Air')]:
            response = self.add_product(category, model)
            self.assertEqual(response.status_code, 303)
            detail = self.client.get(response.location).get_data(as_text=True)
            self.assertIn(model, detail)
            self.assertIn('Pricing unavailable', detail)
            self.assertIn('256 GB', detail)
        profile = self.client.get('/userdata/userprofile').get_data(as_text=True)
        self.assertIn('2 saved products', profile)

    def test_saved_data_survives_a_new_database_connection(self):
        self.register()
        response = self.add_product()
        old = app.extensions.pop('account_store')
        old.engine.dispose()
        self.assertIn('iPhone 14', self.client.get(response.location).get_data(as_text=True))

    def test_another_account_cannot_read_product(self):
        self.register()
        location = self.add_product().location
        second = app.test_client()
        self.register(second, 'two@example.test')
        self.assertEqual(second.get(location).status_code, 404)
        self.assertNotIn('iPhone 14', second.get('/userdata/userprofile').get_data(as_text=True))

    def test_product_notes_are_escaped(self):
        self.register()
        path = '/postdata/mobiles'
        response = self.client.post(path, data={'csrf_token': self.token(self.client, path),
                                    'brand': 'Apple', 'model': '<script>alert(1)</script>', 'condition': 'Good'})
        html = self.client.get(response.location).get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_logout_requires_post_and_csrf(self):
        self.register()
        self.assertEqual(self.client.get('/logout').status_code, 405)
        self.assertEqual(self.client.post('/logout').status_code, 400)
        token = self.token(self.client, '/products')
        self.assertEqual(self.client.post('/logout', data={'csrf_token': token}).status_code, 303)
        self.assertEqual(self.client.get('/userdata/userprofile').status_code, 302)

    def test_login_and_redirect_validation(self):
        self.register()
        second = app.test_client()
        response = second.post('/userdata/login', data={
            'csrf_token': self.token(second, '/userdata/login'), 'email': 'one@example.test',
            'password': 'a long test passphrase', 'next': 'https://evil.example'})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, '/products')

    def test_incorrect_password_does_not_create_session(self):
        self.register()
        second = app.test_client()
        response = second.post('/userdata/login', data={
            'csrf_token': self.token(second, '/userdata/login'), 'email': 'one@example.test', 'password': 'wrong'})
        self.assertEqual(response.status_code, 400)
        with second.session_transaction() as session:
            self.assertNotIn('account_id', session)

    def test_unconfigured_hosted_database_rejects_registration(self):
        app.config['DATABASE_URL'] = None
        response = self.register()
        self.assertEqual(response.status_code, 503)
        self.assertIn('temporarily unavailable', response.get_data(as_text=True))

    def test_invalid_product_not_saved(self):
        self.register()
        response = self.add_product(model='')
        self.assertEqual(response.status_code, 400)
        self.assertIn('0 saved products', self.client.get('/userdata/userprofile').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
