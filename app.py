from flask import Flask, render_template, request, redirect, session, flash
import pandas as pd
import csv
import os
import mysql.connector
import hashlib
import model as mo
import UserInput as wsi
# from celery import Celery
# from celery_worker import call_webscraper 
# import threading


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password,hashed_text):
  if make_hashes(password) == hashed_text:
      return hashed_text
  return False



# Configure the MySQL database connection
mydb = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = "",
    database = "capstone",
)
cursor = mydb.cursor()

app = Flask(__name__)

# app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
# app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
# celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
# celery.conf.update(app.config)



app.config['STATIC_URL_PATH'] = '/static'

app.secret_key = 'TYhffaithh321'

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
def create_csv ():
  data = ret_db_data()
  if session ['post_type'] == 'vehicle':
    if not os.path.exists('vehicles.csv'):
      with open('vehicles.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['post_id','user_email' , 'brand', 'model','location','vehicle_type', 'model_year', 'color', 'km_driven','mileage' 'fuel_type', 'transmission', 'owner_type', 'engine_capacity', 'power', 'seats', 'description'])
        f.close()
        # Create a CSV writer object
    with open('vehicles.csv', 'a', newline='') as g:
      writer = csv.writer(g)
      # Write each row of data to the CSV file
      #for row in data[len(data)-1]:
      writer.writerow(data[len(data)-1])
      g.close()

  elif session ['post_type'] == 'mobiles':
    if not os.path.exists('mobiles.csv'):
      with open('mobiles.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['post_id','email', 'brand', 'model_name', 'sim_slots', 'processor', 'ram', 'storage_size', 'battery_size', 'display', 'camera', 'description'])
        f.close()
        # Write each row of data to the CSV file
    with open('mobiles.csv', 'a', newline='') as g:
      writer = csv.writer(g)
      # Write each row of data to the CSV file
      #for row in data[len(data)-1]:
      writer.writerow(data[len(data)-1])
      g.close()

  elif session ['post_type'] == 'laptops':
    if not os.path.exists('laptops.csv'):
      with open('laptops.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        # Write the header row
        writer.writerow(['post_id','email', 'brandlap', 'model', 'processor', 'ram_size', 'memory_type', 'memory_size', 'display_size', 'refresh_rate', 'battery', 'laptop_type', 'description'])
        f.close()
    # Write each row of data to the CSV file
    with open('laptops.csv', 'a', newline='') as g:
      writer = csv.writer(g)
      # Write each row of data to the CSV file
      #for row in data[len(data)-1]:
      writer.writerow(data[len(data)-1])
      g.close()


def input_query():
    if session['post_type'] == "vehicle":
        df = pd.read_csv("vehicles.csv")
        input_query = df.query("brand != '' and model != ''").apply(lambda row: f"{row['brand']} {row['model']}", axis=1)
    elif session['post_type'] == "mobiles":
        df = pd.read_csv("mobiles.csv")
        input_query = df.query("brand != '' and model_name != ''").apply(lambda row: f"{row['brand']} {row['model_name']}", axis=1)
    elif session['post_type'] == "laptops":
        df = pd.read_csv("laptops.csv")
        input_query = df.query("brandlap != '' and model != ''").apply(lambda row: f"{row['brandlap']} {row['model']}", axis=1)
    x = len(input_query)
    return input_query[x-1]



def call_webscraper():
  if session['post_type'] == 'vehicle':
    keys = ['Brand','Location','Year','Kilometers_Driven','Fuel_Type','Transmission','Owner_Type','Mileage','Engine','Power','Seats','Seller_Comments','Model']
    car_details = {}
    data = ret_single_data()
    i = 0
    row = data[0]
    for key in keys:
      car_details[key] = row[i]
      i = i + 1
  
  driver=wsi.start_driver()
  price=wsi.ui_scrape(car_details,driver)
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
  app.run(debug=True)  