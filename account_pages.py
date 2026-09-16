"""Account and saved electronics pages for the public application."""

import functools
import json
import re
import secrets
import threading
import time
from collections import OrderedDict

from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, session, url_for)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from account_store import AccountStore

pages = Blueprint('accounts', __name__)
_store_lock = threading.Lock()
_attempt_lock = threading.Lock()
_attempts = OrderedDict()
# Used when an email is absent to keep password checks comparable in cost.
_dummy_hash = generate_password_hash(secrets.token_urlsafe(32))
CATEGORIES = {'mobiles': 'Phone', 'laptops': 'Laptop'}


def store():
    if not current_app.config.get('DATABASE_URL'):
        abort(503, description='Accounts are temporarily unavailable. Please try again later.')
    if 'account_store' not in current_app.extensions:
        with _store_lock:
            if 'account_store' not in current_app.extensions:
                current_app.extensions['account_store'] = AccountStore(current_app.config['DATABASE_URL'])
    return current_app.extensions['account_store']


@pages.app_context_processor
def account_context():
    # Navigation can render without connecting to the database.
    return {'signed_in': bool(session.get('account_id')),
            'account_name': session.get('account_name', ''), 'categories': CATEGORIES}


def login_required(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('account_id'):
            flash('Sign in to save products and view your collection.', 'info')
            return redirect(url_for('accounts.login', next=request.path))
        user = store().find_user(user_id=session['account_id'])
        if not user:
            session.clear()
            return redirect(url_for('accounts.login'))
        g.account = user
        return fn(*args, **kwargs)
    return wrapped


def check_auth_limit():
    now = time.monotonic()
    key = request.remote_addr or 'unknown'
    with _attempt_lock:
        start, count = _attempts.get(key, (now, 0))
        if now - start >= 300:
            start, count = now, 0
        _attempts[key] = (start, count + 1)
        _attempts.move_to_end(key)
        while len(_attempts) > 2048:
            _attempts.popitem(last=False)
    if count >= 10:
        abort(429, description='Too many sign-in attempts. Please try again in five minutes.')


def safe_next(value):
    # Only known local destinations, never a caller-controlled redirect URL.
    return value if value in ('/products', '/postdata/mobiles', '/postdata/laptops', '/userdata/userprofile') else '/products'


def sign_in(user):
    session.clear()
    session['account_id'] = user['id']
    session['account_name'] = user['name']
    session.permanent = True


@pages.route('/userdata/register', methods=['GET', 'POST'])
def register():
    error = None
    status = 200
    if request.method == 'POST':
        check_auth_limit()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not 1 <= len(name) <= 80:
            error = 'Enter your name (up to 80 characters).'
        elif len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            error = 'Enter a valid email address.'
        elif not 10 <= len(password) <= 128:
            error = 'Choose a password between 10 and 128 characters.'
        else:
            try:
                user = store().create_user(name, email, generate_password_hash(password))
                sign_in(user)
                flash('Your account is ready. Add your first product.', 'success')
                return redirect('/products', code=303)
            except IntegrityError:
                error = 'An account with these details could not be created. Try signing in instead.'
        status = 400
    return render_template('public/auth.html', mode='register', error=error), status


@pages.route('/userdata/login', methods=['GET', 'POST'])
def login():
    error = None
    status = 200
    next_page = safe_next(request.values.get('next', ''))
    if request.method == 'POST':
        check_auth_limit()
        email = request.form.get('email', '').strip().lower()[:254]
        password = request.form.get('password', '')
        user = store().find_user(email=email)
        valid = len(password) <= 128 and check_password_hash(user['password_hash'] if user else _dummy_hash, password)
        if user and valid:
            sign_in(user)
            return redirect(next_page, code=303)
        error, status = 'Email or password is incorrect.', 400
    return render_template('public/auth.html', mode='login', error=error, next_page=next_page), status


@pages.post('/logout')
def logout():
    session.clear()
    flash('You have signed out.', 'info')
    return redirect('/', code=303)


@pages.get('/products')
def products_home():
    return render_template('public/products.html')


@pages.get('/misc/about')
def about():
    return render_template('public/about.html')


@pages.get('/misc/contact')
def contact():
    return render_template('public/contact.html')


def product_form(category):
    error = None
    values = request.form if request.method == 'POST' else {}
    if request.method == 'POST':
        brand = values.get('brand', '').strip()
        model = values.get('model', '').strip()
        details = {key: values.get(key, '').strip() for key in
                   ('condition', 'ram', 'storage', 'processor', 'age', 'description')}
        if not 1 <= len(brand) <= 60 or not 1 <= len(model) <= 100:
            error = 'Enter a brand and model within the displayed character limits.'
        elif details['condition'] not in ('Like new', 'Good', 'Fair', 'Needs repair'):
            error = 'Choose the condition of your product.'
        elif any(len(details[key]) > 80 for key in ('ram', 'storage', 'processor', 'age')) or len(details['description']) > 1000:
            error = 'Keep specifications under 80 characters and notes under 1,000 characters.'
        else:
            product = store().save_product(g.account['id'], category, brand, model, json.dumps(details))
            flash('Product saved to your collection.', 'success')
            return redirect(url_for('accounts.product_detail', product_id=product['id']), code=303)
    return render_template('public/product_form.html', category=category, values=values, error=error), (400 if error else 200)


@pages.route('/postdata/mobiles', methods=['GET', 'POST'])
@login_required
def mobiles():
    return product_form('mobiles')


@pages.route('/postdata/laptops', methods=['GET', 'POST'])
@login_required
def laptops():
    return product_form('laptops')


@pages.get('/postdata/cars')
def cars():
    return redirect('/')


@pages.get('/userdata/userprofile')
@login_required
def profile():
    items = store().list_products(g.account['id'])
    return render_template('public/profile.html', user=g.account, items=items)


@pages.get('/products/<product_id>')
@login_required
def product_detail(product_id):
    product = store().get_product(product_id, g.account['id'])
    if not product:
        abort(404)
    return render_template('public/product_detail.html', product=product, details=json.loads(product['details']))


@pages.get('/postdata/price')
@login_required
def legacy_price():
    items = store().list_products(g.account['id'])
    if not items:
        return redirect('/products')
    return redirect(url_for('accounts.product_detail', product_id=items[0]['id']))


def database_error(exc):
    # Do not log SQL parameters, credentials, email addresses, or password hashes.
    current_app.logger.error('Account database unavailable (%s)', type(exc).__name__)
    return render_template('public/error.html', title='Please try again shortly',
                           message='Accounts and saved products are temporarily unavailable. Car search is still available.'), 503


def init_accounts(app):
    app.register_blueprint(pages)
    app.register_error_handler(SQLAlchemyError, database_error)
