import mysql.connector
import UserInput as wsi


mydb2 = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = "",
    database = "capstone",
)
cursor2 = mydb2.cursor()


def ret_single_data(post_type,user_id):
  if post_type == 'vehicle':
      cursor2.execute("SELECT brand,location,model_year,km_driven,fuel_type,transmission,owner_type,mileage,engine_capacity,power,seats,description,name_model FROM vehicle where user_email IN (SELECT email from users where username = %s) ORDER BY post_id DESC LIMIT 1",(user_id,))
      data = cursor2.fetchall()
  elif post_type ==  'mobiles':
      cursor2.execute("SELECT * FROM mobiles where email IN (SELECT email from users where username = %s) ORDER BY post_id DESC LIMIT 1",(user_id,))
      data = cursor2.fetchall()
  elif post_type == 'laptops':
      cursor2.execute("SELECT * FROM laptops where email IN (SELECT email from users where username = %s) ORDER BY post_id DESC LIMIT 1",(user_id,))
      data = cursor2.fetchall()
  return data

def get_email(user_id):
  cursor2.execute("SELECT email FROM users WHERE username = %s",(user_id,))
  email = cursor2.fetchone()
  return email

def get_postid(user_id):
  email = get_email(user_id)
  cursor2.execute("SELECT post_id FROM vehicle WHERE user_email = %s ORDER BY post_id DESC LIMIT 1",(email,))
  post_id = cursor2.fetchone()
  return post_id

def enter_price(post_type, price,pid,email):
  if post_type == 'vehicle':
    cursor2.execute('UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;', (price,email[0],post_type,pid[0]))
    mydb2.commit()
  elif post_type =='laptops':
    cursor2.execute('UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;', (price,email,post_type,pid))
    mydb2.commit()
  elif post_type == 'mobiles':
    cursor2.execute('UPDATE price SET price = %s WHERE email = %s AND post_type = %s AND post_id = %s;', (price,email,post_type,pid))
    mydb2.commit()

def call_webscraper(post_type,user_id):
  if post_type == 'vehicle':
    keys = ['Brand','Location','Year','Kilometers_Driven','Fuel_Type','Transmission','Owner_Type','Mileage','Engine','Power','Seats','Seller_Comments','Model']
    car_details = {}
    data = ret_single_data(post_type,user_id)
    i = 0
    row = data[0]
    for key in keys:
      car_details[key] = row[i]
      i = i + 1
  
  driver=wsi.start_driver()
  price=wsi.ui_scrape(car_details,driver)
  pid = get_postid(user_id)
  email = get_email(user_id)
  enter_price(post_type,price,pid,email)