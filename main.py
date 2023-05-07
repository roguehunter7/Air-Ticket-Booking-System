from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql.cursors
import hashlib
import datetime
import random
import json

# Hashing for Passwords
def pw2md5(pw):
    return hashlib.md5(pw.encode()).hexdigest()

# Say Hi to the customer
def greet_customer():
    hour = datetime.datetime.today().time().hour
    time_msg = "nighttime"
    if hour > 6:
        time_msg = "morning"
    if hour > 10:
        time_msg = "noon"
    if hour > 14:
        time_msg = "afternoon"
    if hour > 17:
        time_msg = "evening"
    if hour > 20:
        time_msg = "night"
        
    out_msg = "Dear Customer, Good {}."
    return out_msg.format(time_msg)

# Authorising Customers
def authorise_customer():
    try:
        email = session["email"]
        query = "SELECT * FROM customer WHERE email = %s"
        cursor = conn.cursor()
        cursor.execute(query, (email))
        data = cursor.fetchall()
        cursor.close()
        if data:
            return session["class"] == "customer"
        return False
    except:
        return False

# Fetch Information for Customers 
def fetch_customer_upcoming():
    email = session["email"]
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE customer_email = %s AND status = "Upcoming" ORDER BY departure_time DESC LIMIT 10"""
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_customer_all():
    email = session["email"]
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE customer_email = %s ORDER BY departure_time DESC"""
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_customer_available():
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, seats, (seats - count(ticket_id)) AS available_seats 
            FROM flight NATURAL JOIN airplane NATURAL LEFT OUTER JOIN ticket WHERE status = "Upcoming" GROUP BY airline_name, flight_num HAVING available_seats > 0 ORDER BY departure_time DESC"""       
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()

    for row in data:
        for key in row.keys():
            row[key] = str(row[key])
    return data

def fetch_customer_spending():
    email = session["email"]
    query = """SELECT price, ticket_id, purchase_date 
               FROM purchases NATURAL JOIN ticket NATURAL JOIN flight WHERE customer_email = %s ORDER BY purchase_date ASC"""
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    if not data:
        return False, False, False, False
    months = []
    now = datetime.datetime.today().year*100 + datetime.datetime.today().month
    t = data[0]["purchase_date"].year*100 + data[0]["purchase_date"].month
    months.append(t)
    while t < now:
        if t % 100 == 12:
            t += 88
            
        t += 1
        months.append(t)
    spendings = [0 for _ in range(len(months))]
    
    for row in data:
        price = row["price"]
        month = row["purchase_date"].year*100 + row["purchase_date"].month
        m = months.index(month)
        spendings[m] += float(price)
        
    now = str(datetime.datetime.today().year) + "-" + str(datetime.datetime.today().month)
    past_year = datetime.datetime.today().year
    past_month = datetime.datetime.today().month - 6
    
    if past_month < 1:
        past_month += 12
        past_year -= 1
        
    past_6month = str(past_year) + "-" + str(past_month)
    
    if len(now) < 7:
        now = now[:5] + "0" + now[-1]
        
    if len(past_6month) < 7:
        past_6month = past_6month[:5] + "0" + past_6month[-1]
        
    return months, spendings, now, past_6month
    
# Main 
# Initialize flask
app = Flask(__name__)
app.secret_key = pw2md5(str(random.random()))


conn = pymysql.connect(host='localhost',
                       user='root',
                       password='mysql',
                       db='online_Air_Ticket_Reservation_System',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


# Home Page
@app.route("/")
def home():
    return render_template("home.html")

# Public Info
@app.route("/public_info", methods=['GET', 'POST'])
def public_info():
    query = "SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status FROM flight ORDER BY departure_time DESC"
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template("public_info.html", data = data)

# Public Search
@app.route("/public_search", methods=['GET', 'POST'])
def public_search():
    text = request.form["text"]
    method = request.form["method"]
    cursor = conn.cursor()
    query = "SELECT {} FROM {} WHERE {} = %s ORDER BY departure_time DESC"
    if method == "departure_airport" or method == "arrival_airport":
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status", "flight", method)
        cursor.execute(query, (text))
    elif method == "departure_city":
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status",
                             "flight, airport",
                             "departure_airport = airport_name and airport_city")
        cursor.execute(query, (text))
    elif method == "arrival_city":
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status",
                             "flight, airport",
                             "arrival_airport = airport_name and airport_city")
        cursor.execute(query, (text))
    elif method == "status":
        text = text[0].upper() + text[1:].lower()
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status", "flight", method)
        cursor.execute(query, (text))
    else:
        date_start = text + " 00:00:00"
        date_end = request.form["text2"] + " 23:59:59"
        query = "SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status FROM flight WHERE {} >= '{}' AND {} <= '{}' ORDER BY departure_time DESC"
        query = query.format(method, date_start, method, date_end)
        cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template("public_info.html", data = data)

# Customer ############################################################################################

# Customer Sign Up
@app.route("/customer_signup", methods=['GET', 'POST'])
def customer_signup():
    return render_template("customer_signup.html", email_taken = False, saved_val = [None for _ in range(12)])

@app.route("/customer_signup_go", methods=['GET', 'POST'])
def customer_signup_go():
    # Check whether the email is taken
    email = request.form["email"]
    query = "SELECT * FROM customer WHERE email = %s"
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    if data:
        return render_template("customer_signup.html", email_taken = email, saved_val = [request.form["email"], request.form["name"], request.form["password"], 
            request.form["building_number"], request.form["street"], request.form["city"], request.form["state"], request.form["phone_number"], request.form["passport_number"], 
            request.form["passport_expiration"], request.form["passport_country"], request.form["date_of_birth"]])

    else:
        query = "INSERT INTO customer VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        cursor = conn.cursor()
        cursor.execute(query, (request.form["email"], request.form["name"], pw2md5(request.form["password"]), 
            request.form["building_number"], request.form["street"], request.form["city"], request.form["state"], request.form["phone_number"], request.form["passport_number"], 
            request.form["passport_expiration"], request.form["passport_country"], request.form["date_of_birth"]))
        cursor.close()
        conn.commit()
        return render_template("customer_login.html", email_taken = email, login_fail = False)

# Customer Log In
@app.route("/customer_login", methods=['GET', 'POST'])
def customer_login():
    return render_template("customer_login.html", email_taken = False, login_fail = False)

@app.route("/customer_login_go", methods=['GET', 'POST'])
def customer_login_go():
    email = request.form["email"]
    password = pw2md5(request.form["password"])
    query = "SELECT name FROM customer WHERE (email, password) = (%s, %s)"
    cursor = conn.cursor()
    cursor.execute(query, (email, password))
    data = cursor.fetchall()
    cursor.close()
    if data:
        session["email"] = email
        session["class"] = "customer"
        session["name"] = data[0]["name"]
        months, spendings, now, past6m = fetch_customer_spending()
        return render_template("customer_home.html", greet = greet_customer(), data = fetch_customer_upcoming(), months = months, spendings = spendings, now = now, past6m = past6m)
    return render_template("customer_login.html", email_taken = False, login_fail = True)

# Customer Home
@app.route("/customer_home", methods=['GET', 'POST'])
def customer_home():
    if authorise_customer() == True:
        months, spendings, now, past6m = fetch_customer_spending()
        return render_template("customer_home.html", greet = greet_customer(), data = fetch_customer_upcoming(), months = months, spendings = spendings, now = now, past6m = past6m)
    return render_template("home.html")

# Customer Log out
@app.route("/customer_logout", methods=['GET', 'POST'])
def customer_logout():
    try:
        session.pop("email")
        session.pop("class")
        session.pop("name")
    except:
        pass
    return render_template("home.html")

# Customer View My Flights 
@app.route("/customer_myflights", methods=['GET', 'POST'])
def customer_myflights():
    if authorise_customer() == True:
        return render_template("customer_myflights.html", data = fetch_customer_all())
    return render_template("home.html")

# Customer View My Flights (search)
@app.route("/customer_myflights_search", methods=['GET', 'POST'])
def customer_myflights_search():
    if authorise_customer() == True:
        # Search by the given requirements
        text = request.form["text"]
        method = request.form["method"]
        email = session["email"]
        cursor = conn.cursor()
        query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date 
                   FROM purchases NATURAL JOIN ticket NATURAL JOIN flight {} WHERE {} = (%s,%s) ORDER BY departure_time DESC"""
        if method == "departure_airport":
            query = query.format("", "(customer_email, departure_airport)")
            cursor.execute(query, (email, text))
        elif method == "arrival_airport":
            query = query.format("", "(customer_email, arrival_airport)")
            cursor.execute(query, (email, text))
        elif method == "departure_city":
            query = query.format(", airport", "departure_airport = airport_name and (customer_email, airport_city)")
            cursor.execute(query, (email, text))
        elif method == "arrival_city":
            query = query.format(", airport", "arrival_airport = airport_name and (customer_email, airport_city)")
            cursor.execute(query, (email, text))
        elif method == "status":
            text = text[0].upper() + text[1:].lower()
            query = query.format("", "(customer_email, status)")
            cursor.execute(query, (email, text))
        else:
            date_start = text + " 00:00:00"
            date_end = request.form["text2"] + " 23:59:59"
            query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date 
                   FROM purchases NATURAL JOIN ticket NATURAL JOIN flight WHERE {} >= '{}' AND {} <= '{}' AND customer_email = %s ORDER BY departure_time DESC"""
            query = query.format(method, date_start, method, date_end)
            cursor.execute(query, (email))
        data = cursor.fetchall()
        cursor.close()
        return render_template("customer_myflights.html", data = data)
    return render_template("home.html")

# Customer Search for Flights / Purchase Tickets
@app.route("/customer_availableflights", methods=['GET', 'POST'])
def customer_availableflights():
    if authorise_customer() == True:
        return render_template("customer_availableflights.html", data = fetch_customer_available())
    return render_template("home.html")

@app.route("/customer_availableflights_search", methods=['GET', 'POST'])
def customer_availableflights_search():
    if authorise_customer() == True:
        text = request.form["text"]
        method = request.form["method"]
        cursor = conn.cursor()
        query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, seats, seats - count(ticket_id) AS available_seats 
            FROM flight NATURAL JOIN ticket NATURAL JOIN airplane {} WHERE status = "Upcoming" AND {} = %s GROUP BY airline_name, flight_num HAVING seats > count(ticket_id) ORDER BY departure_time DESC"""
        if method == "departure_airport":
            query = query.format("","departure_airport")
            cursor.execute(query, (text))
        elif method == "arrival_airport":
            query = query.format("", "arrival_airport")
            cursor.execute(query, (text))
        elif method == "departure_city":
            query = query.format(", airport", "departure_airport = airport_name and airport_city")
            cursor.execute(query, (text))
        elif method == "arrival_city":
            query = query.format(", airport", "arrival_airport = airport_name and airport_city")
            cursor.execute(query, (text))
        elif method == "status":
            text = text[0].upper() + text[1:].lower()
            query = query.format("", "status")
            cursor.execute(query, (text))
        else:
            date_start = text + " 00:00:00"
            date_end = request.form["text2"] + " 23:59:59"
            query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, seats, seats - count(ticket_id) AS available_seats 
                       FROM flight NATURAL JOIN ticket NATURAL JOIN airplane WHERE status = "Upcoming" AND {} >= '{}' AND {} <= '{}' GROUP BY airline_name, flight_num HAVING available_seats > 0 ORDER BY departure_time DESC"""
            query = query.format(method, date_start, method, date_end)
            cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        for row in data:
            for key in row.keys():
                row[key] = str(row[key])
        return render_template("customer_availableflights.html", data = data)
    return render_template("home.html")

@app.route("/customer_availableflights_purchase", methods=['GET', 'POST'])
def customer_availableflights_purchase():
    if authorise_customer() == True:
        data = request.form["data"]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        return render_template("customer_availableflights_purchase.html", data = data, error = False)
    return render_template("home.html")

@app.route("/customer_availableflights_purchase_go", methods=['GET', 'POST'])
def customer_availableflights_purchase_go():
    try:
        assert authorise_customer()
        data = request.form["data"]
        data = data.replace('\'','\"')
        print("data:", data)
        if isinstance(data, str):
            data = json.loads(data)
        quant = request.form["quantity"]
        email = session["email"]
        for _ in range(int(quant)):
            query = "SELECT MAX(ticket_id) AS max_id FROM ticket"
            cursor = conn.cursor()
            cursor.execute(query)
            try:
                new_id = int(cursor.fetchall()[0]["max_id"]) + 1
            except:
                 new_id = 0
            query = """SELECT * FROM flight NATURAL JOIN ticket NATURAL JOIN airplane WHERE status = "Upcoming" AND (airline_name, flight_num) = (%s, %s) GROUP BY airline_name, flight_num HAVING seats > count(ticket_id)"""
            cursor.execute(query, (data["airline_name"], data["flight_num"]))
            assert(cursor.fetchall())
            query = "INSERT INTO ticket VALUES (%s, %s, %s)"
            cursor.execute(query, (new_id, data["airline_name"], data["flight_num"]))
            query = "INSERT INTO purchases(ticket_id, customer_email, purchase_date) VALUES (%s, %s, %s)"
            cursor.execute(query, (new_id, email, datetime.datetime.today()))
            cursor.close()
        conn.commit()
        return render_template("customer_availableflights_purchase_thankyou.html")
    except:
        return render_template("customer_availableflights_purchase.html", data = [data], error = True)

if __name__ == "__main__":
    app.run("127.0.0.1", 5000, debug = True)
