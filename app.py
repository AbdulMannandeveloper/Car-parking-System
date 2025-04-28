from flask import Flask, Response, render_template, request, redirect, url_for, flash
from flask import Flask, jsonify
import sqlite3
from datetime import datetime
import hashlib
import os
import json
import jsonify

app = Flask(__name__)

# Path to the SQLite database file
DATABASE = 'database.db'
app.secret_key = 'your_secret_key'  # Needed for flash messages

DATABASE = 'database.db'

import serial

class RFIDReader:
    def __init__(self, port, baudrate=9600, timeout=1):
        """
        Initialize the RFID reader with the specified serial port parameters.

        :param port: Serial port to which the RFID reader is connected (e.g., 'COM3', '/dev/ttyUSB0')
        :param baudrate: Baud rate for the serial communication (default is 9600)
        :param timeout: Timeout for serial read operations (default is 1 second)
        """
        self.port = None
        self.baudrate = 9600
        self.timeout = 1
        self.serial_connection = None
        self.connect()

    def connect(self):
        """Establish a serial connection to the RFID reader."""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            print(f"Connected to RFID reader on port {self.port}")
        except serial.SerialException as e:
            print(f"Failed to connect to RFID reader: {e}")

    def read_rfid(self):
        return '123456799'
    #     """
    #     Read data from the RFID reader.

    #     :return: RFID tag data as a string, or None if no data is read
    #     """
    #     if self.serial_connection and self.serial_connection.is_open:
    #         try:
    #             data = self.serial_connection.readline().decode('utf-8').strip()
    #             if data:
    #                 return '123456789'
    #         except serial.SerialException as e:
    #             print(f"Error reading from RFID reader: {e}")
    #     return None


    def close(self):
        """Close the serial connection to the RFID reader."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print(f"Connection to RFID reader on port {self.port} closed")


class System:
    def __init__(self, database='database.db'):
        self.database = database

    def get_connection(self):
        return get_db_connection()
    
    def get_balance(self, rfid_tag):
        """
        Get the current balance for a user given their RFID tag.

        :param rfid_tag: The RFID tag of the user
        :return: The current balance of the user, or None if the RFID tag is not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT current_balance FROM users WHERE rfid_tag = ?"
        cursor.execute(query, (rfid_tag,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        else:
            return f"RFID tag {rfid_tag} not found in users table."
        
    
    def get_vehivle(self, rfid_tag):
        """
        Get the vehicle of a user given their RFID tag.

        :param rfid_tag: The RFID tag of the user
        :return: The vehicle of the user, or None if the RFID tag is not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT vehicle_name FROM users WHERE rfid_tag = ?"
        cursor.execute(query, (rfid_tag,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        else:
            return f"RFID tag {rfid_tag} not found in users table."

    def enter_parking(self, rfid_tag):
        """
        Enter the current time and RFID tag into both the parking_sessions and current_in_parking tables.

        :param rfid_tag: The RFID tag of the user
        """
        try:
            # Get the current time
            current_time = datetime.now()

            # Insert into parking_sessions table
            conn = self.get_connection()
            cursor = conn.cursor()
            query_parking_sessions = '''
            INSERT INTO parking_sessions (rfid_tag, entrance_time)
            VALUES (?, ?)
            '''
            cursor.execute(query_parking_sessions, (rfid_tag, current_time))
            parking_id = cursor.lastrowid  # Get the last inserted id

            # Insert into current_in_parking table
            query_current_in_parking = '''
            INSERT INTO current_in_parking (rfid_tag, enter_time, parking_id)
            VALUES (?, ?, ?)
            '''
            cursor.execute(query_current_in_parking, (rfid_tag, current_time, parking_id))
            # Commit the transaction
            conn.commit()

            print(f"RFID tag {rfid_tag} entered parking at {current_time}")
            return current_time
        except sqlite3.Error as e:
            conn.rollback()
            return f"An error occurred: {e}"

    def get_name(self, rfid_tag):
        """
        Get the Name for a user given their RFID tag.

        :param rfid_tag: The RFID tag of the user
        :return: The Name of the user, or None if the RFID tag is not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT name FROM users WHERE rfid_tag = ?"
        cursor.execute(query, (rfid_tag,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        else:
            return (f"RFID tag {rfid_tag} not found in users table.")
    
    def check_vehicle_in_parking(self, rfid):
        """"
        A function to evaluate whether the vehicle is in the parking or not at the moment
        
        :param rfid_tag: to search in the table
        :return: True or False
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
        SELECT * FROM current_in_parking 
        WHERE rfid_tag = ?
        '''
        cursor.execute(query,(rfid,))
        result = cursor.fetchone()

        if result:
            return True
        else:
            return False

    def exit_parking(self, rfid_tag):
        """
        Record the exit time in the parking_sessions table, fetch and return the entrance and exit times,
        calculate the duration, calculate the bill based on duration and price, update the user's balance,
        and delete the corresponding record from the current_in_parking table.

        :param rfid_tag: The RFID tag of the user
        :return: A tuple containing the entrance and exit times, or None if the RFID tag is not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            
            # Get the current time
            exit_time = datetime.now()

            # Fetch the entrance time from parking_sessions
            query_fetch_times = '''
            SELECT entrance_time FROM parking_sessions
            WHERE rfid_tag = ? AND exit_time IS NULL
            '''
            cursor.execute(query_fetch_times, (rfid_tag,))
            result = cursor.fetchone()

            if not result:
                print(f"No active parking session found for RFID tag {rfid_tag}.")
                return None

            entrance_time = result[0]

            # Ensure the format string accounts for potential microseconds in the timestamp
            try:
                entrance_time_obj = datetime.strptime(entrance_time, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                entrance_time_obj = datetime.strptime(entrance_time, "%Y-%m-%d %H:%M:%S")

            # Calculate the duration in hours
            duration = (exit_time - entrance_time_obj).total_seconds() / 3600

            # Fetch the hourly rate from the price table
            cursor.execute("SELECT hour_rate FROM price ORDER BY set_date DESC LIMIT 1")
            hour_rate = cursor.fetchone()[0]

            # Update the parking_sessions table with the exit time, duration, and bill
            query_update_exit_time = '''
            UPDATE parking_sessions
            SET exit_time = ?
            WHERE rfid_tag = ? AND exit_time IS NULL
            '''
            cursor.execute(query_update_exit_time, (exit_time, rfid_tag))

            conn.commit()

            query = '''
            SELECT duration*24 FROM parking_sessions where exit_time = ? AND rfid_tag = ?
            '''

            duration = cursor.execute(query, (exit_time, rfid_tag))
            duration = cursor.fetchone()
            bill = duration[0] * hour_rate


            # Update the user's balance
            query_update_balance = '''
            UPDATE users
            SET current_balance = current_balance - ?
            WHERE rfid_tag = ?
            '''
            cursor.execute(query_update_balance, (bill, rfid_tag))

            query_update_bill = '''
            UPDATE parking_sessions
            SET bill = ?
            WHERE rfid_tag = ? AND exit_time = ?
            '''
            cursor.execute(query_update_bill, (bill, rfid_tag, exit_time))
    

            # Delete the record from the current_in_parking table
            query_delete_current_in_parking = '''
            DELETE FROM current_in_parking
            WHERE rfid_tag = ?
            '''
            cursor.execute(query_delete_current_in_parking, (rfid_tag,))

            # Commit the transaction
            conn.commit()

            return entrance_time, exit_time, bill, duration
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            conn.rollback()
            return None
    
class Staff(System):
    def __init__(self, database='database.db'):
        super().__init__(database)
    
    def Category(self):
        return "Faculty/Staff"


class Student(System):
    def __init__(self, database='database.db'):
        super().__init__(database)

    def __init__(self, database='database.db'):
        self.database = database

    def get_connection(self):
        return get_db_connection()

    def get_student_semester(self, rfid_tag):
        """
        Fetch the semester of a student based on their RFID tag.

        :param rfid_tag: The RFID tag of the student
        :return: The semester of the student, or None if the student is not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT semester FROM student WHERE student_id = ?"
            cursor.execute(query, (rfid_tag,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None

    def get_student_department(self, rfid_tag):
        """
        Fetch the department of a student based on their RFID tag.

        :param rfid_tag: The RFID tag of the student
        :return: The Department of the student, or None if the student is not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT department FROM student WHERE student_id = ?"
            cursor.execute(query, (rfid_tag,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None
        
    def Category(self):
        return "Student"


class Login:
    def __init__(self, database=DATABASE):
        self.database = database
        
    def get_connection(self):
        return get_db_connection()

    def _create_admin_table(self):
        """Create the admin table if it does not exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT NOT NULL,
                name TEXT(30) NOT NULL
            );
        ''')
        conn.commit()

    def hash_password(self, password):
        """Hash the password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def sign_up(self, username, password, name):
        """
        Sign up a new administrator.
        
        :param username: The username of the new admin
        :param password: The password of the new admin
        :param name: The name of the new admin
        :return: True if sign-up is successful, False otherwise
        """
        hashed_password = self.hash_password(password)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO admin (username, password, name) VALUES (?, ?, ?)
            ''', (username, hashed_password, name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def admin_login(self, username, password):
        """
        Log in an administrator.
        
        :param username: The username of the admin
        :param password: The password of the admin
        :return: True if login is successful, False otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        hashed_password = self.hash_password(password)
        cursor.execute('''
            SELECT * FROM admin WHERE username = ? AND password = ?
        ''', (username, hashed_password))
        result = cursor.fetchone()
        return result is not None

class Admin:
    def __init__(self, database = 'Database.db'):
        self.database = database
        self.name = None
        self.username = None

    def get_connection(self):
        return get_db_connection()

    def login(self, username, password):
        login = Login()
        val = login.login(username, password)
        if val:
            self.username = username
        else:
            return "Wrong Password"

    def vehicles_in_the_parking(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = '''
            SELECT 
                c.enter_time,
                c.rfid_tag,
                u.vehicle_name,
                u.name AS owner_name,
                u.type AS owner_type
            FROM 
                current_in_parking c
            JOIN 
                users u ON c.rfid_tag = u.rfid_tag
            JOIN 
                parking_sessions p ON c.parking_id = p.id
            WHERE 
                p.exit_time IS NULL;
            '''

            cursor.execute(query)
            results = cursor.fetchall()
            
            return results
        
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None
        
    def vehicles_entered_today(self):
        try:
            # Get today's date in the format YYYY-MM-DD
            today_date = datetime.now().date()


            conn = self.get_connection()
            cursor = conn.cursor()
            # SQL query to fetch details of vehicles entered today
            query = '''
            SELECT 
                p.entrance_time,
                p.rfid_tag,
                u.vehicle_name,
                u.name AS owner_name,
                u.type AS owner_type
            FROM 
                parking_sessions p
            JOIN 
                users u ON p.rfid_tag = u.rfid_tag
            WHERE 
                DATE(p.entrance_time) = ?
            '''

            cursor.execute(query, (today_date,))
            results = cursor.fetchall()

            if results:
                return results
            else:
                return "No Vehicle entered today"
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None
        
    def update_hour_rate(self, new_rate):
        """
        Update the hour_rate in the price table and set the set_date to the current timestamp.

        :param new_rate: The new hourly rate to be set
        :param database: The path to the database file
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
           # Get the current timestamp
            current_timestamp = datetime.now()

            # SQL query to update the hour_rate and set_date
            query = '''
            UPDATE price
            SET hour_rate = ?, set_date = ?
            '''

            cursor.execute(query, (new_rate, current_timestamp))

            # Commit the transaction
            conn.commit()

            return "done"
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")

    
    def check_hour_rate(self):
        """
        Check the current hour rate in the price table.

        :param database: The path to the database file
        :return: A tuple containing the hour rate and set date, or None if an error occurs
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # SQL query to fetch the current hour rate and set date
            query = '''
            SELECT hour_rate, set_date FROM price
            ORDER BY set_date DESC LIMIT 1
            '''

            cursor.execute(query)
            result = cursor.fetchone()

            if result:
                hour_rate, set_date = result
                return hour_rate, set_date
            else:
                print("No hour rate found in the price table.")
                return None
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None
        
    def add_user(self, rfid_tag, user_type, name, current_balance, vehicle_name, semester=None, department=None):
        """
        Add a user to the database. If the user is a student, also add their semester and department.

        :param rfid_tag: The RFID tag of the user
        :param user_type: The type of the user (Student or Staff)
        :param name: The name of the user
        :param current_balance: The current balance of the user
        :param vehicle_name: The vehicle name of the user
        :param semester: The semester of the student (required if user_type is Student)
        :param department: The department of the student (required if user_type is Student)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Insert user into the users table
            user_query = '''
            INSERT INTO users (rfid_tag, type, name, current_balance, vehicle_name)
            VALUES (?, ?, ?, ?, ?)
            '''
            cursor.execute(user_query, (rfid_tag, user_type, name, current_balance, vehicle_name))

            # If the user is a student, insert additional information into the student table
            if user_type == 'Student':
                if semester is None or department is None:
                    raise ValueError("Semester and department are required for students")

                student_query = '''
                INSERT INTO student (student_id, semester, department)
                VALUES (?, ?, ?)
                '''
                cursor.execute(student_query, (rfid_tag, semester, department))

            # Commit the transaction
            conn.commit()
        
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
                    
    def add_balance(self, rfid_tag, amount):
        """
        Add a specified amount to the user's current balance.

        :param rfid_tag: The RFID tag of the user
        :param amount: The amount to be added to the current balance
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Fetch the current balance
            fetch_balance_query = "SELECT current_balance FROM users WHERE rfid_tag = ?"
            cursor.execute(fetch_balance_query, (rfid_tag,))
            result = cursor.fetchone()

            if not result:
                print(f"No user found with RFID tag {rfid_tag}.")
                return

            current_balance = result[0]
            new_balance = current_balance + amount

            # Update the balance
            update_balance_query = "UPDATE users SET current_balance = ? WHERE rfid_tag = ?"
            cursor.execute(update_balance_query, (new_balance, rfid_tag))

            # Commit the transaction
            conn.commit()
            print(f"Updated balance for RFID tag {rfid_tag}. New balance: {new_balance}")
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            

def get_db_connection():
    """Create a new database connection."""
    conn = sqlite3.connect(DATABASE)
    #conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def init_db():
    """Initialize the database."""
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()


            cursor.execute('''
                CREATE TABLE current_in_parking (
                rfid_tag TEXT(50) NOT NULL,
                enter_time TIMESTAMP NOT NULL,
                parking_id INTEGER NOT NULL,
                FOREIGN KEY (rfid_tag) REFERENCES users(rfid_tag),
                FOREIGN KEY (parking_id) REFERENCES parking_sessions(id),
                UNIQUE (rfid_tag, parking_id) -- This ensures that a combination of rfid_tag and parking_id is unique
            );
            ''')

            cursor.execute('''
                CREATE TABLE price (
                hour_rate REAL NOT NULL,
                set_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            ''')

            cursor.execute('''
                CREATE TABLE users (
                rfid_tag TEXT(30) PRIMARY KEY,
                type TEXT(10) CHECK(type IN ('Student', 'Staff')),
                name TEXT(30) NOT NULL,
                current_balance REAL,
                vehicle_name TEXT(30)
                );

            ''')

            cursor.execute('''
                CREATE TABLE student (
                student_id TEXT(30),
                semester INTEGER,
                department TEXT(20),
                FOREIGN KEY (student_id) REFERENCES users(rfid_tag)
                );
                           
            ''')

            cursor.execute('''
                CREATE TABLE parking_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfid_tag TEXT(30) NOT NULL,
                entrance_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                bill REAL,
                duration AS (julianday(exit_time) - julianday(entrance_time)),
                FOREIGN KEY (rfid_tag) REFERENCES users(rfid_tag)
                );
            ''')

            

            cursor.execute('''
                CREATE TABLE admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                name TEXT(30) NOT NULL
            );
            ''')

        print(f"Database '{DATABASE}' created and initialized.")

    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        # Print existing tables
        print(f"Database '{DATABASE}' already exists. Tables:")
        for table in tables:
            print(f"- {table[0]}")

@app.route('/')
def index():
    init_db()
    return render_template('Select Role.html')
login_system = Login()

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if login_system.admin_login(username, password):
            return redirect(url_for('admin_dashboard'))  # Correct endpoint for AdminOps
        else:
            flash('Incorrect username or password', 'error')
    return render_template('sign in_up.html')  # Correct template name

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        password = request.form['password']
        if login_system.sign_up(username, password, name):
            flash('Sign up successful, please log in.', 'success')
            return redirect(url_for('admin_login'))  # Redirect to login after successful signup
        else:
            flash('Username already exists', 'error')
    return render_template('sign in_up.html')  # Correct template name

def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

@app.route('/staff_faculty')
def staff_faculty():
    return render_template('Staff System.html')


@app.route('/staff_faculty_info', methods=['GET'])
def staff_faculty_info():
    rfid = RFIDReader(100)
    rfid_tag = rfid.read_rfid()
    sys = System()

    if rfid_tag:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        in_parking = sys.check_vehicle_in_parking(rfid_tag)
        
        if in_parking:
            name = sys.get_name(rfid_tag)
            vehicle = sys.get_vehivle(rfid_tag)
            details = sys.exit_parking(rfid_tag)
            balance = sys.get_balance(rfid_tag)
        
            response = {
                'name': name,
                'entrance_time': details[0],
                'exit_time': details[1].isoformat() if details[1] else '__',
                'current_balance': balance,
                'vehicle_name': vehicle,
            }
        else:
            name = sys.get_name(rfid_tag)
            vehicle = sys.get_vehivle(rfid_tag)
            details = sys.enter_parking(rfid_tag)
            balance = sys.get_balance(rfid_tag)
        
            response = {
                'name': name,
                'entrance_time': details.isoformat(),
                'exit_time': '__',
                'current_balance': balance,
                'vehicle_name': vehicle,
            }
        return Response(json.dumps(response, default=str), mimetype='application/json')
    
    return Response(json.dumps({'error': 'RFID not found'}), mimetype='application/json')


@app.route('/student')
def student():
    return render_template('StudentSystem.html')


@app.route('/student_info', methods=['GET'])
def student_info():
    rfid = RFIDReader(100)
    rfid_tag = rfid.read_rfid()
    sys = Student()

    if rfid_tag:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        in_parking = sys.check_vehicle_in_parking(rfid_tag)
        
        if in_parking:
            name = sys.get_name(rfid_tag)
            vehicle = sys.get_vehivle(rfid_tag)
            details = sys.exit_parking(rfid_tag)
            balance = sys.get_balance(rfid_tag)
            semester = sys.get_student_semester(rfid_tag)
            department = sys.get_student_department(rfid_tag)
        
            response = {
                'name': name,
                'entrance_time': details[0],
                'exit_time': details[1].isoformat() if details[1] else '__',
                'current_balance': balance,
                'vehicle_name': vehicle,
                'semester' : semester,
                'department' : department,
            }
        else:
            name = sys.get_name(rfid_tag)
            vehicle = sys.get_vehivle(rfid_tag)
            details = sys.enter_parking(rfid_tag)
            balance = sys.get_balance(rfid_tag)
            semester = sys.get_student_semester(rfid_tag)
            department = sys.get_student_department(rfid_tag)
        
            response = {
                'name': name,
                'entrance_time': details.isoformat(),
                'exit_time': '__',
                'current_balance': balance,
                'vehicle_name': vehicle,
                'semester' : semester,
                'department' : department,
            }
        return Response(json.dumps(response, default=str), mimetype='application/json')
    
    return Response(json.dumps({'error': 'RFID not found'}), mimetype='application/json')


@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('AdminOps.html')

@app.route('/admin_action/<action>', methods=['GET'])
def admin_action(action):
    admin = Admin()
    if action == 'vehicles_in_parking':
        result = admin.vehicles_in_the_parking()
    elif action == 'vehicles_entered_today':
        result = admin.vehicles_entered_today()
    elif action == 'update_hour_rate':
        new_rate = request.args.get('new_rate')
        if new_rate:
            result = admin.update_hour_rate(float(new_rate))
        else:
            result = {'error': 'No rate provided'}
    elif action == 'check_hour_rate':
        result = admin.check_hour_rate()
    elif action == 'add_user':
        rfid_tag = request.args.get('rfid_tag')
        user_type = request.args.get('user_type')
        name = request.args.get('name')
        current_balance = request.args.get('current_balance')
        vehicle_name = request.args.get('vehicle_name')
        semester = request.args.get('semester')
        department = request.args.get('department')
        result = admin.add_user(rfid_tag, user_type, name, float(current_balance), vehicle_name, semester, department)
        result = 'User added'
    elif action == 'add_balance':
        rfid_tag = request.args.get('rfid_tag')
        amount = request.args.get('amount')
        result = admin.add_balance(rfid_tag, float(amount))
        result = 'Balance Updated'
    else:
        result = {'error': 'Invalid action'}

    return Response(json.dumps(result, default=str), mimetype='application/json')

@app.route('/vehicles_in_parking')
def vehicles_in_parking():
    conn = login_system.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM current_in_parking')
    vehicles = cursor.fetchall()
    return render_template('data_display.html', title='Vehicles in Parking', data=vehicles, headers=['RFID Tag', 'Enter Time', 'Parking ID'])

@app.route('/vehicles_entered_today')
def vehicles_entered_today():
    today = datetime.now().date()
    conn = login_system.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM parking_sessions WHERE DATE(entrance_time) = ?', (today,))
    vehicles = cursor.fetchall()
    return render_template('data_display.html', title='Vehicles Entered Today', data=vehicles, headers=['ID', 'RFID Tag', 'Entrance Time', 'Exit Time', 'Bill', 'Duration'])

@app.route('/hour_rate')
def hour_rate():
    conn = login_system.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM price ORDER BY set_date DESC LIMIT 1')
    rate = cursor.fetchone()
    return render_template('data_display.html', title='Current Hour Rate', data=[rate], headers=['Hour Rate', 'Set Date'])

admin_ops = Admin('database_path.db')
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        rfid_tag = RFIDReader(100).read_rfid()  # Adjust based on your RFID reading method
        user_type = request.form['user_type']
        name = request.form['name']
        current_balance = float(request.form['current_balance'])
        vehicle_name = request.form['vehicle_name']
        semester = request.form.get('semester')
        department = request.form.get('department')
        
        try:
            admin_ops.add_user(rfid_tag, user_type, name, current_balance, vehicle_name, semester, department)
            flash('User added successfully', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash('An error occurred while adding the user', 'error')

    rfid_tag = RFIDReader(100).read_rfid()  # Read RFID tag again for the form
    return render_template('add_user.html', rfid_tag=rfid_tag)

@app.route('/update_balance', methods=['GET', 'POST'])
def update_balance():
    if request.method == 'POST':
        rfid_tag = RFIDReader(100).read_rfid()  # Adjust based on your RFID reading method
        amount = float(request.form['amount'])
        try:
            admin_ops.add_balance(rfid_tag, amount)
            flash('Balance updated successfully', 'success')
        except Exception as e:
            flash('An error occurred while updating the balance', 'error')
    
    rfid_tag = RFIDReader(100).read_rfid()  # Read RFID tag again for the form
    return render_template('update_balance.html', rfid_tag=rfid_tag)

@app.route('/update_hour_rate', methods=['GET', 'POST'])
def update_hour_rate():
    if request.method == 'POST':
        new_rate = float(request.form['hour_rate'])
        try:
            admin_ops.update_hour_rate(new_rate)
            flash('Hour rate updated successfully', 'success')
        except Exception as e:
            flash('An error occurred while updating the hour rate', 'error')
    
    return render_template('update_hour_rate.html')


if __name__ == "__main__":
    app.run(debug=True)