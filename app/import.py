import pymysql

# MySQL database configuration
config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'mysql',
    'database': 'online_Air_Ticket_Reservation_System',
}

# Path to the text file
file_path = 'db.txt'

# Establish a connection to the MySQL database
conn = pymysql.connect(**config)
cursor = conn.cursor()

# SQL query to load data from the text file
query = """
    LOAD DATA INFILE '{}'
    INTO TABLE dbdata
    FIELDS TERMINATED BY ','
    LINES TERMINATED BY '\n'
""".format(file_path)

try:
    # Execute the query
    cursor.execute(query)

    # Commit the changes
    conn.commit()

    print("Data loaded successfully from the file.")
except pymysql.Error as error:
    print("Error loading data from file: {}".format(error))

# Close the cursor and connection
cursor.close()
conn.close()
