import logging
import functools
import csv
import os
import hashlib
from datetime import datetime

import pandas as pd
import mysql.connector
from flask import Flask, render_template, request, redirect, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

import model as mo
import UserInput as wsi
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['STATIC_URL_PATH'] = '/static'
app.secret_key = Config.SECRET_KEY


# ---------------------------------------------------------------------------
# Database helpers (per-request connections via Flask's g object)
# ---------------------------------------------------------------------------

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
        )
    return g.db


def get_cursor():
    return get_db().cursor()


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Ingestion logging helper
# ---------------------------------------------------------------------------

def log_ingestion(run_type, stats=None, *, started_at=None, status='success', error_detail=None):
    now = datetime.utcnow()
    cursor = get_cursor()
    cursor.execute(
        """INSERT INTO ingestion_log
           (run_type, started_at, finished_at, listings_processed, listings_inserted,
            listings_deduped, errors, duration_seconds, status, error_detail)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            run_type,
            started_at or now,
            now,
            stats.listings_processed if stats else 1,
            stats.listings_inserted if stats else 1,
            stats.listings_deduped if stats else 0,
            stats.errors if stats else 0,
            stats.duration_seconds if stats else 0,
            status,
            error_detail,
        ),
    )
    get_db().commit()


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect('/userdata/login')
        # If the DB was recreated (common in Docker), the browser may still have an old session cookie.
        # Validate that the user still exists and cache their email for the request.
        cursor = get_cursor()
        cursor.execute("SELECT email FROM users WHERE username = %s", (session['user_id'],))
        row = cursor.fetchone()
        if row is None:
            session.clear()
            flash('Your session expired. Please log in again.', 'warning')
            return redirect('/userdata/login')
        g.current_user_email = row[0]
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Legacy password helpers (for backward-compatible migration)
# ---------------------------------------------------------------------------

def _is_legacy_hash(stored_hash):
    """Legacy SHA-256 hashes are 64 hex chars and don't contain method prefixes."""
    return len(stored_hash) == 64 and ':' not in stored_hash


def _legacy_sha256(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('errors/500.html'), 500


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/userdata/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = get_cursor()
        cursor.execute(
            "SELECT username, password FROM users WHERE username = %s",
            (username,),
        )
        user = cursor.fetchone()

        if user is None:
            return render_template('/userdata/loginsignup.html', alert_message_login=True)

        stored_hash = user[1]

        # Backward-compatible login: support legacy SHA-256 hashes
        if _is_legacy_hash(stored_hash):
            if _legacy_sha256(password) != stored_hash:
                return render_template('/userdata/loginsignup.html', alert_message_login=True)
            # Upgrade to werkzeug hash on successful legacy login
            new_hash = generate_password_hash(password)
            cursor.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (new_hash, username),
            )
            get_db().commit()
            logger.info("Upgraded password hash for user %s", username)
        else:
            if not check_password_hash(stored_hash, password):
                return render_template('/userdata/loginsignup.html', alert_message_login=True)

        session['user_id'] = user[0]
        session['post_type'] = None
        flash('Login successful', 'success')
        return redirect('/')

    return render_template('/userdata/loginsignup.html')


@app.route('/userdata/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        number = request.form['number']
        hashed_pass = generate_password_hash(password)

        try:
            cursor = get_cursor()
            cursor.execute(
                'INSERT INTO users (name, username, password, email, number) VALUES (%s, %s, %s, %s, %s)',
                (name, username, hashed_pass, email, number),
            )
            get_db().commit()
        except Exception as e:
            logger.error("Registration error: %s", e)
            return render_template('/userdata/loginsignup.html', error_message_register=str(e))

        flash('Account registered. Please login.', 'success')
        return redirect('/userdata/login')
    return render_template('/userdata/loginsignup.html', signupside=True)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect('/')


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('home.html')
    return render_template('index.html', user=session['user_id'])


@app.route('/postdata/cars', methods=['GET', 'POST'])
@login_required
def cars():
    if request.method == 'POST':
        vehicle_type = request.form['vehicle-type']
        brandcar = request.form['brand']
        name_model = request.form['name-model']
        model_year = int(request.form['model-year'])
        kilometers_driven = int(request.form['kilometers-driven'])
        fuel_type = request.form['fuel-type']
        transmission_type = request.form['transmission-type']
        owner_type = request.form['owner-type']
        engine_capacity = request.form['engine-capacity']
        power = float(request.form['power'])
        seats = int(request.form['seats'])
        color = request.form['color']
        description = request.form['description']
        location = request.form['location']
        mileage = request.form['mileage']

        user_email = g.current_user_email
        cursor = get_cursor()

        cursor.execute(
            """INSERT INTO vehicle(user_email, brand, name_model, location, vehicle_type, model_year, color, km_driven, mileage, fuel_type, transmission, owner_type, engine_capacity, power, seats, description)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 location=VALUES(location), vehicle_type=VALUES(vehicle_type), color=VALUES(color),
                 mileage=VALUES(mileage), fuel_type=VALUES(fuel_type), transmission=VALUES(transmission),
                 owner_type=VALUES(owner_type), engine_capacity=VALUES(engine_capacity),
                 power=VALUES(power), seats=VALUES(seats), description=VALUES(description)""",
            (user_email, brandcar, name_model, location, vehicle_type, model_year, color, kilometers_driven, mileage, fuel_type, transmission_type, owner_type, engine_capacity, power, seats, description),
        )
        get_db().commit()
        session['post_type'] = 'vehicle'

        cursor.execute("SELECT post_id FROM vehicle WHERE user_email = %s ORDER BY post_id DESC LIMIT 1;", (user_email,))
        post_id = cursor.fetchone()

        cursor.execute(
            'INSERT INTO price (email, post_id, post_type, brand, model, description) VALUES (%s, %s, %s, %s, %s, %s)',
            (user_email, post_id[0], 'vehicle', brandcar, name_model, description),
        )
        get_db().commit()

        log_ingestion('form_vehicle')
        create_csv()
        input_query()
        flash('Vehicle data submitted successfully.', 'success')
        return redirect('/')
    return render_template("/postdata/cars.html")


@app.route('/postdata/mobiles', methods=['GET', 'POST'])
@login_required
def mobiles():
    if request.method == 'POST':
        brand = request.form['brand']
        model_name = request.form['model-name']
        sim_slots = int(request.form['sim-slots'])
        processor = request.form['processor']
        ram = request.form['ram']
        storage_size = request.form['storage-size']
        battery_size = request.form['battery-size']
        display = request.form['display']
        camera = request.form['camera']
        description = request.form['description']

        user_email = g.current_user_email
        cursor = get_cursor()

        cursor.execute(
            """INSERT INTO mobiles (email, brand, model_name, sim_slots, processor, ram, storage_size, battery_size, display, camera, description)
               VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 sim_slots=VALUES(sim_slots), processor=VALUES(processor),
                 battery_size=VALUES(battery_size), display=VALUES(display),
                 camera=VALUES(camera), description=VALUES(description)""",
            (user_email, brand, model_name, sim_slots, processor, ram, storage_size, battery_size, display, camera, description),
        )
        get_db().commit()
        session['post_type'] = 'mobiles'

        cursor.execute("SELECT post_id FROM mobiles WHERE email = %s ORDER BY post_id DESC LIMIT 1;", (user_email,))
        post_id = cursor.fetchone()

        cursor.execute(
            'INSERT INTO price (email, brand, model, description, post_id, post_type) VALUES (%s, %s, %s, %s, %s, %s)',
            (user_email, brand, model_name, description, post_id[0], session['post_type']),
        )
        get_db().commit()

        log_ingestion('form_mobile')
        create_csv()
        flash('Mobile data submitted successfully.', 'success')
        return redirect('/')
    return render_template('/postdata/mobiles.html')


@app.route('/postdata/laptops', methods=['GET', 'POST'])
@login_required
def laptops():
    if request.method == 'POST':
        brandlap = request.form['brand']
        model = request.form['model']
        processor = request.form['processor']
        ram_size = request.form['ram-size']
        memory_type = request.form['memory-type']
        memory_size = request.form['memory-size']
        display_size = request.form['display-size']
        refresh_rate = request.form['refresh-rate']
        battery = request.form['battery']
        laptop_type = request.form['laptop-type']
        description = request.form['description']

        user_email = g.current_user_email
        cursor = get_cursor()

        cursor.execute(
            """INSERT INTO laptops (email, brandlap, model, processor, ram_size, memory_type, memory_size, display_size, refresh_rate, battery, laptop_type, description)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 memory_type=VALUES(memory_type), memory_size=VALUES(memory_size),
                 display_size=VALUES(display_size), refresh_rate=VALUES(refresh_rate),
                 battery=VALUES(battery), laptop_type=VALUES(laptop_type), description=VALUES(description)""",
            (user_email, brandlap, model, processor, ram_size, memory_type, memory_size, display_size, refresh_rate, battery, laptop_type, description),
        )
        get_db().commit()
        session['post_type'] = 'laptops'

        cursor.execute("SELECT post_id FROM laptops WHERE email = %s ORDER BY post_id DESC LIMIT 1;", (user_email,))
        post_id = cursor.fetchone()

        cursor.execute(
            'INSERT INTO price (email, brand, model, description, post_id, post_type) VALUES (%s, %s, %s, %s, %s, %s)',
            (user_email, brandlap, model, description, post_id[0], session['post_type']),
        )
        get_db().commit()

        log_ingestion('form_laptop')
        create_csv()
        flash('Laptop data submitted successfully.', 'success')
        return redirect('/')
    return render_template('/postdata/laptops.html')


@app.route('/postdata/price', methods=['GET', 'POST'])
@login_required
def pricing():
    if session.get('post_type') is None:
        flash('Please enter data to view a price. To view already retrieved price, go to User Profile.', 'warning')
        return redirect('/')

    call_webscraper()
    cursor = get_cursor()
    cursor.execute(
        "SELECT CONCAT(Brand, ' ', Model) AS Name, post_type, price FROM price WHERE email = %s ORDER BY post_id DESC LIMIT 1;",
        (g.current_user_email,),
    )
    result = cursor.fetchone()
    if result is None:
        flash('No recent price request found for your account yet.', 'warning')
        return redirect('/')

    img_data = '/static/images/defaultprice.jpg'
    if session['post_type'] == 'vehicle':
        img_data = '/static/images/vehicleicon.jpg'
    elif session['post_type'] == 'mobiles':
        img_data = '/static/images/mobilesicon.jpg'
    elif session['post_type'] == 'laptops':
        img_data = '/static/images/laptopsicon.jpg'

    if result[2] is None:
        Price = 'Calculating Price - Please check in a while'
    else:
        Price = result[2]

    return render_template('/postdata/price.html', Name=result[0], Type=result[1], Price=Price, img_data=img_data)


@app.route('/userdata/userprofile', methods=['GET', 'POST'])
@login_required
def userprofile():
    data = get_user_data(session['user_id'])

    cursor = get_cursor()
    cursor.execute(
        "SELECT * FROM price WHERE email IN (SELECT email FROM users WHERE username = %s)",
        (session['user_id'],),
    )
    result = cursor.fetchall()

    return render_template(
        '/userdata/userprofile.html',
        username=data[0],
        name=data[1],
        email=data[2],
        number=data[3],
        items=result,
    )


@app.route('/misc/about', methods=['GET', 'POST'])
def about():
    data = ret_session()
    return render_template('/misc/about.html', user_is_signed_in=data)


@app.route('/misc/contact', methods=['GET', 'POST'])
def contact():
    data = ret_session()
    return render_template('/misc/contact.html', user_is_signed_in=data)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def ret_session():
    return 'user_id' in session


def get_user_data(user_id):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (user_id,))
    return cursor.fetchone()


def ret_db_data():
    cursor = get_cursor()
    if session['post_type'] == 'vehicle':
        cursor.execute(
            "SELECT * FROM vehicle WHERE user_email IN (SELECT email FROM users WHERE username = %s)",
            (session['user_id'],),
        )
    elif session['post_type'] == 'mobiles':
        cursor.execute(
            "SELECT * FROM mobiles WHERE email IN (SELECT email FROM users WHERE username = %s)",
            (session['user_id'],),
        )
    elif session['post_type'] == 'laptops':
        cursor.execute(
            "SELECT * FROM laptops WHERE email IN (SELECT email FROM users WHERE username = %s)",
            (session['user_id'],),
        )
    return cursor.fetchall()


def ret_single_data():
    cursor = get_cursor()
    if session['post_type'] == 'vehicle':
        cursor.execute(
            "SELECT brand, location, model_year, km_driven, fuel_type, transmission, owner_type, mileage, engine_capacity, power, seats, description, name_model FROM vehicle WHERE user_email IN (SELECT email FROM users WHERE username = %s) ORDER BY post_id DESC LIMIT 1",
            (session['user_id'],),
        )
    elif session['post_type'] == 'mobiles':
        cursor.execute(
            "SELECT * FROM mobiles WHERE email IN (SELECT email FROM users WHERE username = %s) ORDER BY post_id DESC LIMIT 1",
            (session['user_id'],),
        )
    elif session['post_type'] == 'laptops':
        cursor.execute(
            "SELECT * FROM laptops WHERE email IN (SELECT email FROM users WHERE username = %s) ORDER BY post_id DESC LIMIT 1",
            (session['user_id'],),
        )
    return cursor.fetchall()


def create_csv():
    data = ret_db_data()
    if session['post_type'] == 'vehicle':
        if not os.path.exists('vehicles.csv'):
            with open('vehicles.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'post_id', 'user_email', 'brand', 'model', 'location', 'vehicle_type',
                    'model_year', 'color', 'km_driven', 'mileage', 'fuel_type', 'transmission',
                    'owner_type', 'engine_capacity', 'power', 'seats', 'description',
                ])
        with open('vehicles.csv', 'a', newline='') as g:
            writer = csv.writer(g)
            writer.writerow(data[len(data) - 1])

    elif session['post_type'] == 'mobiles':
        if not os.path.exists('mobiles.csv'):
            with open('mobiles.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'post_id', 'email', 'brand', 'model_name', 'sim_slots', 'processor',
                    'ram', 'storage_size', 'battery_size', 'display', 'camera', 'description',
                ])
        with open('mobiles.csv', 'a', newline='') as g:
            writer = csv.writer(g)
            writer.writerow(data[len(data) - 1])

    elif session['post_type'] == 'laptops':
        if not os.path.exists('laptops.csv'):
            with open('laptops.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'post_id', 'email', 'brandlap', 'model', 'processor', 'ram_size',
                    'memory_type', 'memory_size', 'display_size', 'refresh_rate', 'battery',
                    'laptop_type', 'description',
                ])
        with open('laptops.csv', 'a', newline='') as g:
            writer = csv.writer(g)
            writer.writerow(data[len(data) - 1])


def input_query():
    if session['post_type'] == "vehicle":
        df = pd.read_csv("vehicles.csv")
        queries = df.query("brand != '' and model != ''").apply(lambda row: f"{row['brand']} {row['model']}", axis=1)
    elif session['post_type'] == "mobiles":
        df = pd.read_csv("mobiles.csv")
        queries = df.query("brand != '' and model_name != ''").apply(lambda row: f"{row['brand']} {row['model_name']}", axis=1)
    elif session['post_type'] == "laptops":
        df = pd.read_csv("laptops.csv")
        queries = df.query("brandlap != '' and model != ''").apply(lambda row: f"{row['brandlap']} {row['model']}", axis=1)
    x = len(queries)
    return queries[x - 1]


def call_webscraper():
    if session['post_type'] == 'vehicle':
        keys = ['Brand', 'Location', 'Year', 'Kilometers_Driven', 'Fuel_Type', 'Transmission', 'Owner_Type', 'Mileage', 'Engine', 'Power', 'Seats', 'Seller_Comments', 'Model']
        car_details = {}
        data = ret_single_data()
        row = data[0]
        for i, key in enumerate(keys):
            car_details[key] = row[i]

    logger.info(">>> call_webscraper() triggered for: %s", car_details)
    started = datetime.utcnow()
    try:
        price, stats = wsi.ui_scrape(car_details)
        logger.info(">>> Scraper returned price=%s, listings=%d", price, stats.listings_processed)
        pid = get_postid()
        email = get_email()
        enter_price(price, pid, email)
        log_ingestion('scrape', stats, started_at=started)
    except Exception as exc:
        logger.error(">>> Scraper failed: %s", exc)
        log_ingestion('scrape', started_at=started, status='failed', error_detail=str(exc))
        raise


def enter_price(price, pid, email):
    cursor = get_cursor()
    if session['post_type'] == 'vehicle':
        cursor.execute(
            'UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;',
            (price, email[0], session['post_type'], pid[0]),
        )
    elif session['post_type'] == 'laptops':
        cursor.execute(
            'UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;',
            (price, email, session['post_type'], pid),
        )
    elif session['post_type'] == 'mobiles':
        cursor.execute(
            'UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;',
            (price, email, session['post_type'], pid),
        )
    get_db().commit()


def get_email():
    cursor = get_cursor()
    cursor.execute("SELECT email FROM users WHERE username = %s", (session['user_id'],))
    return cursor.fetchone()


def get_postid():
    email = get_email()
    cursor = get_cursor()
    cursor.execute(
        "SELECT post_id FROM vehicle WHERE user_email = %s ORDER BY post_id DESC LIMIT 1",
        (email,),
    )
    return cursor.fetchone()


if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes', 'y', 'on')
    app.run(host=host, port=port, debug=debug)
