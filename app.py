from flask import Flask, render_template, request, redirect, session, flash
import pandas as pd
import csv
import os
import mysql.connector
import hashlib

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import model as mo
import UserInput as wsi
# from celery import Celery
# from celery_worker import call_webscraper 
# import threading


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# Database configuration is read from the environment so the app can point at a
# local MySQL for development or a managed/hosted MySQL in production.
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "capstone"),
}

# Absolute base dir of the app so bundled data (datasets, templates) resolve
# correctly regardless of the current working directory (e.g. on serverless).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Writable directory for the per-post CSV logs. On platforms with a read-only
# app filesystem (Vercel/Netlify functions) point this at a writable path such
# as /tmp via the DATA_DIR env var.
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)


def _data_path(name):
    return os.path.join(DATA_DIR, name)


# When live scraping is disabled (the default for hosted deployments), the price
# estimate is produced by training the model on the bundled market dataset.
ENABLE_LIVE_SCRAPING = _env_bool("ENABLE_LIVE_SCRAPING", False)
_cached_dataset = os.getenv("CACHED_CARS_DATASET", "new_cars.csv")
CACHED_CARS_DATASET = _cached_dataset if os.path.isabs(_cached_dataset) else os.path.join(BASE_DIR, _cached_dataset)

# Scraper source used when ENABLE_LIVE_SCRAPING is true (see scrapers.py).
SCRAPER_SOURCE = os.getenv("SCRAPER_SOURCE", "cars24")


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password,hashed_text):
  if make_hashes(password) == hashed_text:
      return hashed_text
  return False


# The connection is created lazily and re-established when needed so that the
# app can boot (and serve the health check) even if the database is temporarily
# unavailable, which is common on hosted platforms during cold starts.
mydb = None
cursor = None


def init_db():
    global mydb, cursor
    mydb = mysql.connector.connect(**DB_CONFIG)
    cursor = mydb.cursor()
    return mydb


def ensure_db():
    global mydb, cursor
    if mydb is None:
        init_db()
        return
    try:
        mydb.ping(reconnect=True, attempts=3, delay=1)
        if cursor is None:
            cursor = mydb.cursor()
    except mysql.connector.Error:
        init_db()


try:
    init_db()
except mysql.connector.Error as exc:
    print(f"[startup] Database not reachable yet: {exc}. Will retry on first request.")

app = Flask(__name__)

# app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
# app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
# celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
# celery.conf.update(app.config)



app.config['STATIC_URL_PATH'] = '/static'

app.secret_key = os.getenv("SECRET_KEY", "dev-insecure-change-me")


@app.route('/health')
def health():
  db_ok = True
  try:
    ensure_db()
    cursor.execute("SELECT 1")
    cursor.fetchone()
  except Exception:
    db_ok = False
  return {"status": "ok", "database": "up" if db_ok else "down"}, (200 if db_ok else 503)


@app.before_request
def _ensure_db_connection():
  if request.endpoint == 'health':
    return
  try:
    ensure_db()
  except mysql.connector.Error:
    pass

@app.route('/userdata/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    hashed_pass = make_hashes(password)
    # Query the database for the user with the given username
    cursor.execute("SELECT username,password FROM users WHERE username = %s AND password = %s",(username,hashed_pass))
    user = cursor.fetchone()
    # If the user is not found or the password is incorrect, return an error

    if user is None or user[1] != hashed_pass:
      return render_template('/userdata/loginsignup.html',alert_message_login = True)

    # Otherwise, the login is successful. Set the user session and redirect to the home page
    session['user_id'] = user[0]
    session['post_type'] = None
    flash('Login successful', 'success')  # 'success' is the category for the message
    return redirect('/')

  # If the request is a GET, render the login page
  return render_template('/userdata/loginsignup.html')

@app.route('/userdata/register', methods = ['GET','POST'])
def register():
  if request.method == 'POST':
    session['error_message'] = ''
    # Get the user's registration information
    name = request.form['name']
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']
    number = request.form['number']
    hashed_pass = make_hashes(password)
    # Create a new user account
    try:
      cursor.execute('INSERT INTO users (name, username, password, email, number) VALUES (%s, %s, %s, %s, %s)', (name, username, hashed_pass, email, number))
      mydb.commit()
    except Exception as e:
      session['error_message'] = str(e)
      return render_template('/userdata/loginsignup.html',error_message_register = session['error_message'])

    # Redirect the user to the register page to display alert
    return redirect('/userdata/login')
  # Otherwise, render the register page
  return render_template('/userdata/loginsignup.html',signupside = True)

@app.route('/')
def index():
  # Check if the user is logged in
  alert_message = ''
  if 'user_id' not in session:
    return render_template('home.html')
  else:
    user_id = session['user_id']
  # Otherwise, render the home page
  return render_template('index.html', user=user_id,alert_message = alert_message)

@app.route('/postdata/cars',methods = ['GET','POST'])
def cars():
    # Add logic for the Cars page here
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

    cursor.execute("SELECT email FROM users WHERE username = %s",(session['user_id'],))
    data = cursor.fetchone()

    cursor.execute('INSERT INTO vehicle( user_email,brand,name_model,location,vehicle_type, model_year, color, km_driven, mileage,fuel_type, transmission, owner_type, engine_capacity, power, seats, description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(data[0],brandcar, name_model,location,vehicle_type, model_year, color, kilometers_driven,mileage, fuel_type, transmission_type, owner_type, engine_capacity, power, seats, description))
    mydb.commit()
    session['post_type'] = 'vehicle'

    cursor.execute("SELECT post_id FROM vehicle where user_email = %s ORDER BY post_id DESC LIMIT 1;",(data[0],))
    post_id = cursor.fetchone()

    #add post type as v
    cursor.execute('INSERT INTO price (email,post_id, post_type, brand, model, description) VALUES (%s, %s, %s, %s, %s, %s)', (data[0], post_id[0],'vehicle', brandcar, name_model, description))
    mydb.commit()

    create_csv()
    input_query()
    #run_pipeline()
    return render_template('index.html')
  return render_template("/postdata/cars.html")

@app.route('/postdata/price',methods = ['GET','POST'])
def pricing():
  if session['post_type'] == None:
    return render_template('index.html', alert_message = True)
  else:
    call_webscraper()
    cursor.execute("SELECT CONCAT(Brand, ' ', Model) AS Name, post_type, price FROM price WHERE email IN (SELECT email FROM users WHERE username = %s) ORDER BY post_id DESC LIMIT 1;",(session['user_id'],))
    result = cursor.fetchone()
    img_data = ''
    print(result)
    if session['post_type'] == 'vehicle':
      img_data = '/static/images/vehicleicon.jpg'
    elif session['post_type'] == 'mobiles':
       img_data = '/static/images/mobilesicon.jpg'
    elif session['post_type'] == 'laptops':
       img_data = '/static/images/laptopsicon.jpg'
    else:
       img_data = '/static/images/defaultprice.jpg'
    
    if result[2] == None:
       Price = 'Calculating Price Please check in a while'
    else:
       Price = result[2]   
    return render_template('/postdata/price.html',Name = result[0], Type = result[1], Price = Price,img_data = img_data)

@app.route('/postdata/mobiles', methods = ['GET','POST'])
def mobiles():
    # Add logic for the Mobiles page here
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

      cursor.execute("SELECT email FROM users WHERE username = %s",(session['user_id'],))
      data = cursor.fetchone()

      cursor.execute('INSERT INTO mobiles (email, brand, model_name, sim_slots, processor, ram, storage_size, battery_size, display, camera, description) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (data[0],brand, model_name, sim_slots, processor, ram, storage_size, battery_size, display, camera, description))
      mydb.commit()
      session['post_type'] = 'mobiles'
      cursor.execute("SELECT post_id FROM mobiles where email = %s ORDER BY post_id DESC LIMIT 1;",(data[0],))
      post_id = cursor.fetchone()
      #add post type as m
      cursor.execute('INSERT INTO price (email, brand, model, description, post_id, post_type) VALUES (%s, %s, %s, %s, %s, %s)', (data[0], brand, model_name, description, post_id[0], session['post_type']))
      mydb.commit()

      create_csv()
      return render_template('index.html')
    return render_template('/postdata/mobiles.html')

@app.route('/postdata/laptops', methods = [ 'GET','POST'])
def laptops():
    # Add logic for the Laptops page here
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
      
      cursor.execute("SELECT email FROM users WHERE username = %s",(session['user_id'],))
      data = cursor.fetchone()

      cursor.execute('INSERT INTO laptops (email, brandlap, model, processor, ram_size, memory_type, memory_size, display_size, refresh_rate, battery, laptop_type, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (data[0], brandlap, model, processor, ram_size, memory_type, memory_size, display_size, refresh_rate, battery, laptop_type, description))
      mydb.commit()
      session['post_type'] = 'laptops'
      cursor.execute("SELECT post_id FROM laptops where email = %s ORDER BY post_id DESC LIMIT 1;",(data[0],))
      post_id = cursor.fetchone()
      #add post type as l
      cursor.execute('INSERT INTO price (email, brand, model, description, post_id, post_type) VALUES (%s, %s, %s, %s, %s, %s)', (data[0], brandlap, model, description, post_id[0], session['post_type']))
      mydb.commit()

      create_csv()
      return render_template('index.html')
    return render_template('/postdata/laptops.html')

@app.route('/userdata/userprofile', methods = ['GET','POST'])
def userprofile():
    data = get_user_data(session['user_id'])
    
    cursor.execute("SELECT * FROM price where email in (SELECT email from users where username = %s)",(session['user_id'],))
    result = cursor.fetchall()
   
    return render_template('/userdata/userprofile.html',username = data[0],name = data[1], email = data[2], number = data[3], password = data[4],items = result, post_type_img = 'pfp')

@app.route('/misc/about', methods = ['GET','POST'])
def about():
  data = ret_session()
  return render_template('/misc/about.html', user_is_signed_in = data)

@app.route('/misc/contact', methods = ['GET','POST'])
def contact():
  data = ret_session()
  return render_template('/misc/contact.html', user_is_signed_in = data)

@app.route('/logout')
def logout():
    if 'user_id' in session:
          session.pop('user_id', None)
          flash('You have been logged out.', 'info')
    
    flash('Logged out successfully', 'success')
    return redirect('/')

def ret_session():
  if 'user_id' in session:
    user_is_signed_in = True
  else:
    user_is_signed_in = False
  return user_is_signed_in

def get_user_data(user_id):
    cursor.execute("SELECT * FROM users WHERE username = %s", (user_id,))
    user_data = cursor.fetchone()
    return user_data

def ret_db_data():
  if session ['post_type'] == 'vehicle':
      cursor.execute("SELECT * FROM vehicle where user_email IN (SELECT email from users where username = %s)",(session['user_id'],))
      data = cursor.fetchall()
  elif session ['post_type'] == 'mobiles':
      cursor.execute("SELECT * FROM mobiles where email IN (SELECT email from users where username = %s)",(session['user_id'],))
      data = cursor.fetchall()
  elif session ['post_type'] == 'laptops':
      cursor.execute("SELECT * FROM laptops where email IN (SELECT email from users where username = %s)",(session['user_id'],))
      data = cursor.fetchall()
  return data

def ret_single_data():
  if session ['post_type'] == 'vehicle':
      cursor.execute("SELECT brand,location,model_year,km_driven,fuel_type,transmission,owner_type,mileage,engine_capacity,power,seats,description,name_model FROM vehicle where user_email IN (SELECT email from users where username = %s) ORDER BY post_id DESC LIMIT 1",(session['user_id'],))
      data = cursor.fetchall()
  elif session ['post_type'] == 'mobiles':
      cursor.execute("SELECT * FROM mobiles where email IN (SELECT email from users where username = %s) ORDER BY post_id DESC LIMIT 1",(session['user_id'],))
      data = cursor.fetchall()
  elif session ['post_type'] == 'laptops':
      cursor.execute("SELECT * FROM laptops where email IN (SELECT email from users where username = %s) ORDER BY post_id DESC LIMIT 1",(session['user_id'],))
      data = cursor.fetchall()
  return data
#INSERT INTO price  WHERE email IN (SELECT email FROM users WHERE username = 'aarav') AND post_type = 'vehicles' AND post_id IN (SELECT post_id FROM vehicles WHERE user_email = 'aaravbabu2002@gmail.com' ORDER BY post_id DESC LIMIT 1) 
CSV_HEADERS = {
  'vehicle': ['post_id', 'user_email', 'brand', 'model', 'location', 'vehicle_type', 'model_year', 'color', 'km_driven', 'mileage', 'fuel_type', 'transmission', 'owner_type', 'engine_capacity', 'power', 'seats', 'description'],
  'mobiles': ['post_id', 'email', 'brand', 'model_name', 'sim_slots', 'processor', 'ram', 'storage_size', 'battery_size', 'display', 'camera', 'description'],
  'laptops': ['post_id', 'email', 'brandlap', 'model', 'processor', 'ram_size', 'memory_type', 'memory_size', 'display_size', 'refresh_rate', 'battery', 'laptop_type', 'description'],
}


def create_csv():
  """Append the latest post to a CSV log. Best-effort: on a read-only
  filesystem (serverless) this is skipped without failing the request."""
  post_type = session['post_type']
  filename = {'vehicle': 'vehicles.csv', 'mobiles': 'mobiles.csv', 'laptops': 'laptops.csv'}.get(post_type)
  if not filename:
    return
  data = ret_db_data()
  path = _data_path(filename)
  try:
    if not os.path.exists(path):
      with open(path, 'w', newline='') as f:
        csv.writer(f).writerow(CSV_HEADERS[post_type])
    with open(path, 'a', newline='') as g:
      csv.writer(g).writerow(data[len(data) - 1])
  except OSError as exc:
    print(f"[create_csv] Skipping CSV log write ({path}): {exc}")


def input_query():
    try:
        if session['post_type'] == "vehicle":
            df = pd.read_csv(_data_path("vehicles.csv"))
            input_query = df.query("brand != '' and model != ''").apply(lambda row: f"{row['brand']} {row['model']}", axis=1)
        elif session['post_type'] == "mobiles":
            df = pd.read_csv(_data_path("mobiles.csv"))
            input_query = df.query("brand != '' and model_name != ''").apply(lambda row: f"{row['brand']} {row['model_name']}", axis=1)
        elif session['post_type'] == "laptops":
            df = pd.read_csv(_data_path("laptops.csv"))
            input_query = df.query("brandlap != '' and model != ''").apply(lambda row: f"{row['brandlap']} {row['model']}", axis=1)
        else:
            return None
        x = len(input_query)
        return input_query[x-1]
    except (OSError, KeyError, IndexError) as exc:
        print(f"[input_query] Skipped ({exc})")
        return None



def predict_from_cache(car_details):
  """Estimate a price without a live browser by training the model on the
  bundled market dataset. Used as the default path and as a fallback when live
  scraping is disabled or fails (e.g. on hosted, browserless environments)."""
  df = pd.read_csv(CACHED_CARS_DATASET)
  return int(mo.model_call(df, car_details))


def call_webscraper():
  car_details = {}
  if session['post_type'] == 'vehicle':
    keys = ['Brand','Location','Year','Kilometers_Driven','Fuel_Type','Transmission','Owner_Type','Mileage','Engine','Power','Seats','Seller_Comments','Model']
    data = ret_single_data()
    row = data[0]
    for i, key in enumerate(keys):
      car_details[key] = row[i]

  price = None
  if ENABLE_LIVE_SCRAPING:
    try:
      from scrapers import get_scraper
      df = get_scraper(SCRAPER_SOURCE).scrape(car_details)
      if df is not None and not df.empty:
        price = int(mo.model_call(df, car_details))
      else:
        print(f"[pricing] Scraper '{SCRAPER_SOURCE}' returned no rows; using cached dataset.")
    except Exception as exc:
      print(f"[pricing] Live scraping via '{SCRAPER_SOURCE}' failed, falling back to cached dataset: {exc}")
      price = None

  if price is None:
    price = predict_from_cache(car_details)

  pid = get_postid()
  email = get_email()
  enter_price(price,pid,email)

def enter_price(price,pid,email):
  if session['post_type'] == 'vehicle':
    cursor.execute('UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;', (price,email[0],session['post_type'],pid[0]))
    mydb.commit()
  elif session ['post_type'] == 'laptops':
    cursor.execute('UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;', (price,email,session['post_type'],pid))
    mydb.commit()
  elif session ['post_type'] == 'mobiles':
    cursor.execute('UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;', (price,email,session['post_type'],pid))
    mydb.commit()

def get_email():
  cursor.execute("SELECT email FROM users WHERE username = %s",(session['user_id'],))
  email = cursor.fetchone()
  return email

def get_postid():
  email = get_email()
  cursor.execute("SELECT post_id FROM vehicle WHERE user_email = %s ORDER BY post_id DESC LIMIT 1",(email))
  post_id = cursor.fetchone()
  return post_id

@app.route('/testpage',methods=[ 'GET','POST'])
def testingfile():
   return render_template('/tointegrate/newtemplogin.html')

if __name__ == '__main__':
  app.run(
    host=os.getenv("HOST", "127.0.0.1"),
    port=int(os.getenv("PORT", "5000")),
    debug=_env_bool("FLASK_DEBUG", True),
  )