"""Public car-price search with persistent accounts and saved electronics."""

import logging
import os
import statistics
import threading
import time
import secrets
from pathlib import Path
from collections import OrderedDict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect, CSRFError

from account_pages import init_accounts

import live_prices

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=16384,
                  SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
                  SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SECURE=bool(os.environ.get('RENDER')),
                  SESSION_COOKIE_SAMESITE='Lax',
                  PERMANENT_SESSION_LIFETIME=timedelta(days=7),
                  DATABASE_URL=os.environ.get('DATABASE_URL'))
if os.environ.get('RENDER'):
    if not os.environ.get('SECRET_KEY'):
        # Keep public search alive, but do not enable persistent accounts with
        # a session key that would rotate whenever the instance restarts.
        app.config['DATABASE_URL'] = None
elif not app.config['DATABASE_URL']:
    Path(app.instance_path).mkdir(exist_ok=True)
    app.config['DATABASE_URL'] = 'sqlite:///' + str(Path(app.instance_path) / 'accounts.db')
CSRFProtect(app)
init_accounts(app)
if os.environ.get('TRUST_PROXY') == '1':
    # Render has one trusted proxy in front of this service. Do not enable this
    # for a directly exposed development server.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
logging.basicConfig(level=logging.INFO)
_clients = OrderedDict()
_client_lock = threading.Lock()


@app.template_filter('rupees')
def rupees(value):
    digits = str(int(value))
    tail = digits[-3:]
    digits = digits[:-3]
    while digits:
        tail = digits[-2:] + ',' + tail
        digits = digits[:-2]
    return '₹' + tail


def rate_limited():
    now = time.monotonic()
    key = request.remote_addr or 'unknown'
    with _client_lock:
        start, count = _clients.get(key, (now, 0))
        if now - start >= 60:
            start, count = now, 0
        _clients[key] = (start, count + 1)
        _clients.move_to_end(key)
        while len(_clients) > 2048:
            _clients.popitem(last=False)
        return count >= 12


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/healthz')
def health():
    return {'status': 'ok', 'revision': os.environ.get('RENDER_GIT_COMMIT', 'local')}


@app.errorhandler(CSRFError)
def csrf_error(error):
    return render_template('public/error.html', title='This form has expired',
                           message='Go back, reload the page, and submit the form again.'), 400


@app.errorhandler(404)
@app.errorhandler(429)
@app.errorhandler(503)
def page_error(error):
    title = {404: 'Page not found', 429: 'A short pause', 503: 'Please try again shortly'}[error.code]
    return render_template('public/error.html', title=title, message=error.description), error.code


@app.get('/')
def index():
    values = {k: request.args.get(k, '').strip() for k in
              ('brand', 'model', 'city', 'year', 'fuel', 'transmission')}
    if not request.args:
        values.update(brand='maruti', model='', city='delhi-ncr')
    result = None
    summary = None
    error = None
    status = 200
    source_url = None
    if request.args:
        try:
            if rate_limited():
                raise live_prices.SearchBusy('You have made several searches. Please try again in a minute.')
            source_url = live_prices.source_url(values['brand'], values['model'], values['city'], values['year'])
            if values['fuel'] not in ('', 'Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid'):
                raise ValueError('Choose a supported fuel type.')
            if values['transmission'] not in ('', 'Manual', 'Automatic'):
                raise ValueError('Choose a supported transmission.')
            result = live_prices.search(values['brand'], values['model'], values['city'], values['year'])
            # Filter the sampled listings, never relabel retailer data using the
            # visitor's inputs. Search pages sometimes include related vehicles.
            words = values['model'].lower().replace('-', ' ').split()
            filtered = [item for item in result['listings']
                        if all(word in item['title'].lower().replace('-', ' ').split() for word in words)
                        and values['brand'] in item['title'].lower().split()
                        and (not values['year'] or item['year'] == int(values['year']))
                        and (not values['fuel'] or values['fuel'] in item['fuel'])
                        and (not values['transmission'] or values['transmission'] == item['transmission'])]
            result = {**result, 'listings': sorted(filtered, key=lambda x: x['price']),
                      'sample_count': len(result['listings']),
                      'checked_at_label': result['checked_at'].astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y, %I:%M %p IST')}
            if filtered:
                prices = [item['price'] for item in filtered]
                summary = {'lowest': min(prices), 'median': statistics.median(prices), 'highest': max(prices)}
        except ValueError as exc:
            error, status = str(exc), 400
        except live_prices.SearchBusy as exc:
            error, status = str(exc), 429
        except live_prices.SourceUnavailable as exc:
            app.logger.warning('Listing source unavailable: %s', exc)
            error, status = str(exc), 503
    response = app.make_response((render_template(
        'public/search.html', values=values, result=result, summary=summary,
        error=error, source_url=source_url, brands=live_prices.BRANDS,
        cities=live_prices.CITIES, years=range(datetime.now().year, 1999, -1)), status))
    if status in (429, 503):
        response.headers['Retry-After'] = '60'
    return response


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5002')), debug=False)
