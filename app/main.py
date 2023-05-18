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

# Authorising Staff
def authorise_staff():
    try:
        username = session["username"]
        query = "SELECT * FROM airline_staff WHERE username = %s"
        cursor = conn.cursor()
        cursor.execute(query, (username))
        data = cursor.fetchall()
        cursor.close()
        if data:
            return session["class"] == "staff"
        return False
    except:
        return False

# Fetch Information for Staff
def fetch_staff_upcoming():
    airline = session["airline"]
    query = """SELECT * FROM flight WHERE airline_name = %s AND status = "Upcoming" AND departure_time > "{}" AND departure_time < "{}" ORDER BY departure_time DESC LIMIT 10"""
    query = query.format(str(datetime.datetime.today())[:-7], str(datetime.datetime.today()+datetime.timedelta(days=30))[:-7])
    cursor = conn.cursor()
    cursor.execute(query, (airline))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_staff_all():
    airline = session["airline"]
    query = """SELECT * FROM flight WHERE airline_name = %s ORDER BY departure_time DESC"""
    cursor = conn.cursor()
    cursor.execute(query, (airline))
    data = cursor.fetchall()
    cursor.close()
    for row in data:
        for key in row.keys():
            row[key] = str(row[key])
    return data

def fetch_staff_agent():
    airline = session["airline"]
    query = """SELECT booking_agent_id, email, SUM(price) * 0.1 AS commission
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases NATURAL JOIN booking_agent
            WHERE airline_name = "{}" AND purchase_date > "{}"
            GROUP BY booking_agent_id
            ORDER BY SUM(price) DESC LIMIT 5""".format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query)
    com_data = cursor.fetchall()
    query_temp = """SELECT booking_agent_id, email, COUNT(price) AS n_sales
                FROM flight NATURAL JOIN ticket NATURAL JOIN purchases NATURAL JOIN booking_agent
                WHERE airline_name = "{}" AND purchase_date > "{}"
                GROUP BY booking_agent_id
                ORDER BY COUNT(price) DESC LIMIT 5"""
    query_month = query_temp.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=30))[:-7])
    query_year = query_temp.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor.execute(query_month)
    nsales_data_month = cursor.fetchall()
    cursor.execute(query_year)
    nsales_data_year = cursor.fetchall()
    cursor.close()
    return com_data, nsales_data_month, nsales_data_year

def fetch_staff_customer():
    airline = session["airline"]
    query = """SELECT email, name, COUNT(ticket_id)
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases JOIN customer ON customer.email = purchases.customer_email
            WHERE airline_name = "{}" AND purchase_date > "{}"
            GROUP BY email
            ORDER BY COUNT(ticket_id) DESC
            LIMIT 5""".format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_staff_destination():
    airline = session["airline"]
    query = """SELECT airport_city, COUNT(*)
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, airport
            WHERE flight.arrival_airport = airport.airport_name AND airline_name = "{}" AND purchase_date > "{}"
            GROUP BY airport_city
            ORDER BY COUNT(*) DESC LIMIT 3"""
    query_3m = query.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=90))[:-7])
    query_12m = query.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query_3m)
    data_3m = cursor.fetchall()
    cursor.execute(query_12m)
    data_12m = cursor.fetchall()
    cursor.close()
    return [data_3m, data_12m]

def fetch_staff_sales():
    query = """SELECT purchase_date 
               FROM purchases NATURAL JOIN ticket NATURAL JOIN flight WHERE airline_name="{}" ORDER BY purchase_date ASC""".format(session["airline"])
    cursor = conn.cursor()
    cursor.execute(query)
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
        month = row["purchase_date"].year*100 + row["purchase_date"].month
        m = months.index(month)
        spendings[m] += 1
    now = str(datetime.datetime.today().year) + "-" + str(datetime.datetime.today().month)
    past_year = datetime.datetime.today().year
    past_month = datetime.datetime.today().month - 6
    if past_month < 1:
        past_month += 12
        past_year -= 1
    past6m = str(past_year) + "-" + str(past_month)
    if len(now) < 7:
        now = now[:5] + "0" + now[-1]
    if len(past6m) < 7:
        past6m = past6m[:5] + "0" + past6m[-1]
    return months, spendings, now, past6m

def fetch_staff_breakdown():
    airline = session["airline"]
    query = """SELECT SUM(price)
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases
            WHERE airline_name = "{}" AND {} AND purchase_date > "{}" """
    direct = "booking_agent_id IS NULL"
    indirect = "booking_agent_id"
    query_direct1m = query.format(airline, direct, str(datetime.datetime.today()-datetime.timedelta(days=30))[:-7])
    query_indirect1m = query.format(airline, indirect, str(datetime.datetime.today()-datetime.timedelta(days=30))[:-7])
    query_direct12m = query.format(airline, direct, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    query_indirect12m = query.format(airline, indirect, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query_direct1m)
    query_direct1m = cursor.fetchall()[0]["SUM(price)"]
    cursor.execute(query_indirect1m)
    query_indirect1m = cursor.fetchall()[0]["SUM(price)"]
    cursor.execute(query_direct12m)
    query_direct12m = cursor.fetchall()[0]["SUM(price)"]
    cursor.execute(query_indirect12m)
    query_indirect12m = cursor.fetchall()[0]["SUM(price)"]
    cursor.close()
    out = [query_indirect1m, query_direct1m, query_indirect12m, query_direct12m]
    for i in range(len(out)):
        try:
            out[i] = int(out[i])
        except:
            out[i] = 0
    return out
 
# Main 
# Initialize flask
app = Flask(__name__)
app.secret_key = pw2md5(str(random.random()))

conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='mysql',
    db='online_Air_Ticket_Reservation_System',
    cursorclass=pymysql.cursors.DictCursor
)


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
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        print("data:", data)
        print(type(data))

        if isinstance(data, str):
            data = json.loads(data)
        
        print("data:", data)
        print(type(data))
        quant = request.form["quantity"]
        email = session["email"]
        cursor = conn.cursor()
        for _ in range(int(quant)):
            cursor.execute("SELECT MAX(ticket_id) AS max_id FROM ticket")
            try:
                new_id = int(cursor.fetchall()[0]["max_id"]) + 1
            except:
                 new_id = 0
            query = """SELECT * FROM flight NATURAL JOIN ticket NATURAL JOIN airplane WHERE status = %s AND (airline_name, flight_num) = (%s, %s) GROUP BY airline_name, flight_num HAVING seats > count(ticket_id)"""
            cursor.execute(query, ("Upcoming", data["airline_name"], data["flight_num"]))
            assert(cursor.fetchall())
            query = "INSERT INTO ticket VALUES (%s, %s, %s)"
            cursor.execute(query, (new_id, data.get("airline_name"), data.get("flight_num")))
            query = "INSERT INTO purchases(ticket_id, customer_email, purchase_date) VALUES (%s, %s, %s)"
            cursor.execute(query, (new_id, email, datetime.datetime.today()))
        cursor.close()
        conn.commit()
        return render_template("customer_availableflights_purchase_thankyou.html")
    except:
        return render_template("customer_availableflights_purchase.html", data = [data], error = True)

# Staff ####################################################################################################################

# Airline Staff Sign Up
@app.route("/staff_signup", methods=['GET', 'POST'])
def staff_signup():
    query = "SELECT airline_name FROM airline"
    cursor = conn.cursor()
    cursor.execute(query)
    airlines = cursor.fetchall()
    cursor.close()
    return render_template("staff_signup.html", email_taken = False, saved_val = [None for _ in range(6)], airlines=airlines)

@app.route("/staff_signup_go", methods=['GET', 'POST'])
def staff_signup_go():
    # Check whether the email is taken
    username = request.form["username"]
    password = pw2md5(request.form["password"])
    query = "SELECT * FROM airline_staff WHERE username = %s"
    cursor = conn.cursor()
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close()
    if data:
        query = "SELECT airline_name FROM airline"
        cursor = conn.cursor()
        cursor.execute(query)
        airlines = cursor.fetchall()
        cursor.close()
        return render_template("staff_signup.html", email_taken = username, airlines=airlines, saved_val = [request.form["username"], request.form["password"], request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["airline"]])
    else:
        if request.form["airline"] == "new":
            query = "SELECT * FROM airline WHERE airline_name = %s"
            cursor = conn.cursor()
            cursor.execute(query, (request.form["new_airline"]))
            data = cursor.fetchall()
            cursor.close()
            if data:
                query = "SELECT airline_name FROM airline"
                cursor = conn.cursor()
                cursor.execute(query)
                airlines = cursor.fetchall()
                cursor.close()
                return render_template("staff_signup.html", email_taken = request.form["new_airline"], airlines=airlines, saved_val = [request.form["username"], request.form["password"], request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["airline"]])
            query = "INSERT INTO airline VALUES (%s)"
            cursor = conn.cursor()
            cursor.execute(query,(request.form["new_airline"]))
            cursor.close()
            conn.commit()
            query = "INSERT INTO airline_staff VALUES (%s, %s, %s, %s, %s, %s)"
            cursor = conn.cursor()
            cursor.execute(query,(username, password, request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["new_airline"]))
            cursor.close()
            conn.commit()
            
            return render_template("staff_login.html", email_taken = username, login_fail = False)

        else:
            query = "SELECT * FROM airline WHERE airline_name = %s"
            cursor = conn.cursor()
            cursor.execute(query, (request.form["airline"]))
            data = cursor.fetchall()
            cursor.close()

            if data:
                query = "INSERT INTO airline_staff VALUES (%s, %s, %s, %s, %s, %s)"
                cursor = conn.cursor()
                cursor.execute(query,(username, password, request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["airline"]))
                cursor.close()
                conn.commit()
            
                return render_template("staff_login.html", email_taken = username, login_fail = False)

        return render_template("staff_signup.html", email_taken = request.form["new_airline"], airlines=airlines, saved_val = [request.form["username"], request.form["password"], request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["airline"]])

# Staff Login
@app.route("/staff_login", methods=['GET', 'POST'])
def staff_login():
    return render_template("staff_login.html", email_taken = False, login_fail = False)

@app.route("/staff_login_go", methods=['GET', 'POST'])
def staff_login_go():
    username = request.form["username"]
    password = pw2md5(request.form["password"])
    query = "SELECT * FROM airline_staff WHERE (username, password) = (%s, %s)"
    cursor = conn.cursor()
    cursor.execute(query, (username, password))
    data = cursor.fetchall()
    cursor.close()
    if data:
        session["username"] = username
        session["class"] = "staff"
        session["airline"] = data[0]["airline_name"]
        months, sales, now, past6m = fetch_staff_sales()
        return render_template("staff_home.html", data=fetch_staff_upcoming(), customer_data=fetch_staff_customer(), destination_data=fetch_staff_destination(),months=months, spendings=sales, now=now, past6m=past6m, breakdown=fetch_staff_breakdown())
    return render_template("staff_login.html", email_taken = False, login_fail = True)

# Staff Home
@app.route("/staff_home", methods=['GET', 'POST'])
def staff_home():
    if authorise_staff() == True:
        months, sales, now, past6m = fetch_staff_sales()
        return render_template("staff_home.html", data=fetch_staff_upcoming(), customer_data=fetch_staff_customer(), destination_data=fetch_staff_destination(),months=months, spendings=sales, now=now, past6m=past6m, breakdown=fetch_staff_breakdown())
    return render_template("home.html")

# Staff Log out
@app.route("/staff_logout", methods=['GET', 'POST'])
def staff_logout():
    try:
        session.pop("username")
        session.pop("class")
        session.pop("airline")
    except:
        pass
    return render_template("home.html")

# Staff View My Flights 
@app.route("/staff_myflights", methods=['GET', 'POST'])
def staff_myflights():
    if authorise_staff() == True:
        return render_template("staff_myflights.html", data = fetch_staff_all())
    return render_template("staff_home.html")


# Staff View My Flights (search)
@app.route("/staff_myflights_search", methods=['GET', 'POST'])
def staff_myflights_search():
    if authorise_staff() == True:
        text = request.form["text"]
        method = request.form["method"]
        airline = session["airline"]
        cursor = conn.cursor()
        query = """SELECT * FROM flight WHERE {} = (%s,%s) ORDER BY departure_time DESC"""
        if method == "departure_airport":
            query = query.format("(airline_name, departure_airport)")
            cursor.execute(query, (airline, text))
        elif method == "arrival_airport":
            query = query.format("(airline_name, arrival_airport)")
            cursor.execute(query, (airline, text))
        elif method == "departure_city":
            query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, airplane_id
                       FROM flight, airport WHERE departure_airport = airport_name and (airline_name, airport_city) = (%s, %s) ORDER BY departure_time DESC"""
            cursor.execute(query, (airline, text))
        elif method == "arrival_city":
            query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, airplane_id
                       FROM flight, airport WHERE arrival_airport = airport_name and (airline_name, airport_city) = (%s, %s) ORDER BY departure_time DESC"""
            cursor.execute(query, (airline, text))
        elif method == "airplane_id":
            query = query.format("(airline_name, airplane_id)")
            cursor.execute(query, (airline, text))
        elif method == "status":
            text = text[0].upper() + text[1:].lower()
            query = query.format("(airline_name, status)")
            cursor.execute(query, (airline, text))
        else:
            date_start = text + " 00:00:00"
            date_end = request.form["text2"] + " 23:59:59"
            query = """SELECT * FROM flight 
                       WHERE {} >= '{}' AND {} <= '{}' AND airline_name = %s ORDER BY departure_time DESC"""
            query = query.format(method, date_start, method, date_end)
            cursor.execute(query, (airline))
        data = cursor.fetchall()
        cursor.close()
        for row in data:
            for key in row.keys():
                row[key] = str(row[key])
        return render_template("staff_myflights.html", data = data)
    return render_template("staff_home.html")

# Staff View My Flights (view customer details)
@app.route("/staff_myflights_viewcustomers", methods=['GET', 'POST'])
def staff_myflights_viewcustomers():
    if authorise_staff() == True:
        data = request.form["data"]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        flight_num = data[0]["flight_num"]
        airline = session["airline"]
        query = """SELECT email, name, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, customer
                   WHERE customer.email = purchases.customer_email AND (airline_name, flight_num) = (%s, %s) GROUP BY email,ticket_id ORDER BY ticket_id"""
        cursor = conn.cursor()
        cursor.execute(query, (airline, flight_num))
        customer_data = cursor.fetchall()
        cursor.close()
        return render_template("staff_myflights_viewcustomers.html", data=data, customer_data=customer_data)
    return render_template("staff_home.html")

@app.route("/staff_myflights_viewcustomers_changestatus", methods=['GET', 'POST'])
def staff_myflights_viewcustomers_changestatus():
    if authorise_staff() == True:
        data = request.form["data"][1:-1]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        flight_num = data[0]["flight_num"]
        airline = session["airline"]
        status = request.form['status']
        try:
            assert(data[0]['status'] != status)
            cursor = conn.cursor()
            query = """UPDATE flight SET status = %s WHERE airline_name="{}" AND flight_num={} """.format(airline, flight_num)
            cursor.execute(query, (status))
            cursor.close()
            conn.commit()
            cursor = conn.cursor()
            query = """SELECT email, name, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, customer
                    WHERE customer.email = purchases.customer_email AND (airline_name, flight_num) = (%s, %s) GROUP BY email ORDER BY ticket_id"""
            cursor.execute(query, (airline, flight_num))
            customer_data = cursor.fetchall()
            query = """SELECT * FROM flight WHERE (airline_name, flight_num) = (%s, %s)"""
            cursor.execute(query, (airline, flight_num))
            data = cursor.fetchall()
            cursor.close()
            for row in data:
                for key in row.keys():
                    row[key] = str(row[key])
            return render_template("staff_myflights_viewcustomers.html", data=data, customer_data=customer_data, success=True, error=False)
        except:
            cursor = conn.cursor()
            query = """SELECT email, name, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, customer
                    WHERE customer.email = purchases.customer_email AND (airline_name, flight_num) = (%s, %s) GROUP BY email ORDER BY ticket_id"""
            cursor.execute(query, (airline, flight_num))
            customer_data = cursor.fetchall()
            cursor.close()
            return render_template("staff_myflights_viewcustomers.html", data=data, customer_data=customer_data, error=True, success=False)
    return render_template("staff_home.html")

# Staff Add Flight
@app.route("/staff_addflight", methods=['GET', 'POST'])
def staff_addflight():
    if authorise_staff() == True:
        airline = session["airline"]
        query = "SELECT DISTINCT airport_name FROM airport"
        cursor = conn.cursor()
        cursor.execute(query)
        airports = cursor.fetchall()
        query = "SELECT DISTINCT airplane_id FROM airplane WHERE airline_name = %s"
        cursor.execute(query, (airline))
        airplane_ids = cursor.fetchall()
        query = "SELECT MAX(flight_num) FROM flight WHERE airline_name = %s"
        cursor.execute(query, (airline))
        flight_num = cursor.fetchall()
        cursor.close()
        try:
            for i in flight_num[0].keys():
                flight_num[0][i] = int(flight_num[0][i]) + 1
            return render_template("staff_addflight.html", airline=session["airline"], airports=airports, airplane_ids=airplane_ids, flight_num=flight_num)
        except:
            return render_template("staff_addflight.html", airline=session["airline"], airports=airports, airplane_ids=airplane_ids, flight_num=flight_num)

    return render_template("staff_home.html")

@app.route("/staff_addflight_go", methods=['GET', 'POST'])
def staff_addflight_go():
    if authorise_staff() == True:
        try:
            assert request.form["arrival_airport"] != request.form["departure_airport"]
            airline = session["airline"]
            start = request.form["departure_time"]
            end = request.form["arrival_time"]
            start = start[:-6] + " " + start[-5:] + ":00"
            end = end[:-6] + " " + end[-5:] + ":00"
            # Check for time conflicts
            query = """SELECT * FROM flight WHERE (airline_name = "{}" AND airplane_id = {} AND ((departure_time > '{}' AND departure_time < '{}') 
                    OR (arrival_time > '{}' AND arrival_time < '{}')
                    OR (departure_time < '{}' AND arrival_time > '{}')))
                    OR '{}' >= '{}'""".format(airline, request.form['plane_id'], start, end, start, end, start, end, start, end)
            cursor = conn.cursor()
            print(query)
            cursor.execute(query)
            data = cursor.fetchall()
            assert data == ()
    
            query = """INSERT INTO flight VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(query, (airline, request.form["flight_num"], request.form["departure_airport"], start, request.form["arrival_airport"], 
                end, request.form["price"], request.form["status"], request.form["plane_id"]))
            cursor.close()
            conn.commit()
            error = False
            success = True
        except:
            error = True
            success = False
        
        airline = session["airline"]
        query = "SELECT DISTINCT airport_name FROM airport"
        cursor = conn.cursor()
        cursor.execute(query)
        airports = cursor.fetchall()
        query = "SELECT DISTINCT airplane_id FROM airplane WHERE airline_name = %s"
        cursor.execute(query, (airline))
        airplane_ids = cursor.fetchall()
        query = "SELECT MAX(flight_num) FROM flight WHERE airline_name = %s"
        cursor.execute(query, (airline))
        flight_num = cursor.fetchall()
        cursor.close()
        for i in flight_num[0].keys():
            flight_num[0][i] = int(flight_num[0][i]) + 1
        return render_template("staff_addflight.html", airline=session["airline"], airports=airports, airplane_ids=airplane_ids, flight_num=flight_num, error=error, success=success)
    return render_template("staff_home.html")

# Staff Add Plane
@app.route("/staff_addplane", methods=['GET', 'POST'])
def staff_addplane():
    if authorise_staff() == True:
        query = """SELECT MAX(airplane_id) AS MAX_id FROM airplane WHERE airline_name = %s"""
        cursor = conn.cursor()
        cursor.execute(query, (session["airline"]))
        try:
            plane_id = int(cursor.fetchall()[0]['MAX_id']) + 1
        except:
            plane_id = 0
        cursor.close()
        return render_template("staff_addplane.html", airline=session["airline"], plane_id=plane_id)
    return render_template("staff_home.html")

@app.route("/staff_addplane_go", methods=['GET', 'POST'])
def staff_addplane_go():
    if authorise_staff() == True:
        try:
            airline = session["airline"]
            query = "INSERT INTO airplane VALUES (%s, %s, %s)"
            cursor = conn.cursor()
            cursor.execute(query, (airline, request.form["plane_id"], request.form["seats"]))
            cursor.close()
            conn.commit()
            query = """SELECT * FROM airplane WHERE airline_name = %s"""
            cursor = conn.cursor()
            cursor.execute(query, (airline))
            data = cursor.fetchall()
            cursor.close()
            return render_template("staff_addplane_go.html", data=data)
        except:
            return render_template("staff_addplane.html", airline=session["airline"], plane_id=request.form["plane_id"], seats=request.form["seats"], error=True)
    return render_template("staff_home.html")

# Staff Add Airport
@app.route("/staff_addairport", methods=['GET', 'POST'])
def staff_addairport():
    if authorise_staff() == True:
        username = session["username"]
        query = """SELECT permission_type FROM permission WHERE username = %s"""
        cursor = conn.cursor()
        cursor.execute(query, (username))
        data = cursor.fetchall()
        if data:
            query = """SELECT * FROM airport"""
            cursor = conn.cursor()
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            return render_template("staff_addairport.html", data=data)
    return render_template("staff_home.html")

@app.route("/staff_addairport_go", methods=['GET', 'POST'])
def staff_addairport_go():
    if authorise_staff() == True:
        username = session["username"]
        query = """SELECT permission_type FROM permission WHERE username = %s"""
        cursor = conn.cursor()
        cursor.execute(query, (username))
        data = cursor.fetchall()
        if data:
            try:
                query = """INSERT INTO airport VALUES (%s,%s)"""
                cursor = conn.cursor()
                cursor.execute(query, (request.form['airport'],request.form['city']))
                cursor.close()
                conn.commit()
                error = False
                success = True
            except:
                error = True
                success = False

            query = """SELECT * FROM airport"""
            cursor = conn.cursor()
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            return render_template("staff_addairport.html", data=data, error=error, success = success)
    return render_template("staff_home.html")

# Staff View All Agents
@app.route("/staff_agents", methods=['GET', 'POST'])
def staff_agents():
    if authorise_staff() == True:
        query = """SELECT email, booking_agent.booking_agent_id, COUNT(price), SUM(price)*0.1 FROM flight NATURAL JOIN ticket NATURAL JOIN purchases RIGHT JOIN booking_agent ON purchases.booking_agent_id = booking_agent.booking_agent_id WHERE airline_name = "{}" GROUP BY booking_agent.booking_agent_id ORDER BY booking_agent.booking_agent_id """.format(session["airline"])
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return render_template("staff_agents.html", data=data)
    return render_template("staff_home.html")

# Staff View All Relavant Customers
@app.route("/staff_customers", methods=['GET', 'POST'])
def staff_customers():
    if authorise_staff() == True:
        airline = session["airline"]
        query = """SELECT email, name, COUNT(ticket_id)
                FROM flight NATURAL JOIN ticket NATURAL JOIN purchases JOIN customer ON customer.email = purchases.customer_email
                WHERE airline_name = "{}"
                GROUP BY email
                ORDER BY COUNT(ticket_id) DESC""".format(airline)
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return render_template("staff_customers.html", data=data)
    return render_template("staff_home.html")

# Staff View Customer Flight (Ticket) Details
@app.route("/staff_customers_details", methods=['GET', 'POST'])
def staff_customers_details():
    if authorise_staff() == True:
        data = request.form["data"]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        airline = session["airline"]
        customer = data[0]["email"]
        query = """SELECT flight_num, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE airline_name = "{}" AND customer_email = "{}" """.format(airline, customer)
        cursor = conn.cursor()
        cursor.execute(query)
        flight_data = cursor.fetchall()
        cursor.close()
        return render_template("staff_customers_details.html", data=data, flight_data=flight_data)
    return render_template("staff_home.html")

# Staff Grant New Permissions
@app.route("/staff_addpermissions", methods=['GET', 'POST'])
def staff_permissions():
    if authorise_staff() == True:
        username = session["username"]
        query = """SELECT permission_type FROM permission WHERE username = %s"""
        cursor = conn.cursor()
        cursor.execute(query, (username))
        data = cursor.fetchall()
        if data:
            query = """SELECT * FROM permission"""
            cursor = conn.cursor()
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            return render_template("staff_addpermissions.html", data=data)
    return render_template("staff_home.html")

@app.route("/staff_addpermissions_go", methods=['GET', 'POST'])
def staff_addpermissions_go():
    if authorise_staff() == True:
        username = session["username"]
        query = """SELECT permission_type FROM permission WHERE username = %s"""
        cursor = conn.cursor()
        cursor.execute(query, (username))
        data = cursor.fetchall()
        if data:
            try:
                add_username, permission_type = request.form['username'], request.form['permission_type']
                cursor = conn.cursor()
                query = """SELECT airline_name FROM airline_staff WHERE username = %s"""
                cursor.execute(query, (add_username))
                data  = cursor.fetchall()
                if data[0]["airline_name"] == session['airline']:
                    query = """INSERT INTO permission VALUES (%s,%s)"""
                    cursor = conn.cursor()
                    cursor.execute(query, (add_username,permission_type))
                    cursor.close()
                    conn.commit()
                    error = False
                    success = True
                else:
                    return render_template("staff_home.html")
            except:
                error = True
                success = False

            query = """SELECT * FROM permission"""
            cursor = conn.cursor()
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            return render_template("staff_addpermissions.html", data=data, error=error, success = success)
    return render_template("staff_home.html")


if __name__ == "__main__":
    app.run("127.0.0.1", 5000, debug = True)
