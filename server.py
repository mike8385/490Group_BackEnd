from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
import MySQLdb.cursors
from flask_cors import CORS
from datetime import datetime
import base64
import bcrypt


app = Flask(__name__)
CORS(app)

 
app.config['MYSQL_HOST'] = '127.0.0.1' #localhost
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'toor' 
app.config['MYSQL_DB'] = 'clinic_db'

mysql = MySQL(app)

#------- DOCTOR RELATED QUERIES -----------------------------------------
# register a new doctor
@app.route('/register-doctor', methods=['POST'])
def register_doctor():
    data = request.get_json()

    # hash the password before storing it
    password = data['password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    #for the picture i'm still not sure
    doctor_picture = data.get('doctor_picture')  # Base64 encoded image data

    if doctor_picture:
        # Decode the base64 string to binary data
        doctor_picture = base64.b64decode(doctor_picture)

    cursor = mysql.connection.cursor()
    query = """
        INSERT INTO DOCTOR (
            first_name, last_name, email, password, description, license_num,
            license_exp_date, dob, years_of_practice, payment_fee,
            gender, phone_number, address, zipcode, city, state, doctor_picture
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data['first_name'],
        data['last_name'],
        data['email'],
        hashed_password,
        data.get('description'),
        data['license_num'],
        data['license_exp_date'],
        data['dob'],
        data['years_of_practice'],
        data['payment_fee'],
        data['gender'],
        data['phone_number'],
        data['address'],
        data['zipcode'],
        data['city'],
        data['state'],
        doctor_picture  # should be binary if present
    )
    try:
        cursor.execute(query, values)
        mysql.connection.commit()
        return jsonify({"message": "Doctor registered successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

# get doctor info
@app.route('/doctor/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    cursor = mysql.connection.cursor()
    query = """
        SELECT doctor_id, first_name, last_name, email, description, license_num,
               license_exp_date, dob, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture,
               created_at, updated_at
        FROM DOCTOR
        WHERE doctor_id = %s
    """
    cursor.execute(query, (doctor_id,))
    doctor = cursor.fetchone()

    if doctor:
        
        #the doctor picture thing may need to be edited- need to test it with frontend
        doctor_picture = doctor[16]  
        if doctor_picture:
            if isinstance(doctor_picture, str):
                doctor_picture = doctor_picture.encode('utf-8')  # Ensure it's a bytes-like object
            doctor_picture = base64.b64encode(doctor_picture).decode('utf-8')

        return jsonify({
            "doctor_id": doctor[0],
            "first_name": doctor[1],
            "last_name": doctor[2],
            "email": doctor[3],
            "description": doctor[4],
            "license_num": doctor[5],
            "license_exp_date": doctor[6],
            "dob": doctor[7],
            "years_of_practice": doctor[8],
            "payment_fee": doctor[9],
            "gender": doctor[10],
            "phone_number": doctor[11],
            "address": doctor[12],
            "zipcode": doctor[13],
            "city": doctor[14],
            "state": doctor[15], 
            "doctor_picture": doctor_picture
        }), 200
    else:
        return jsonify({"error": "Doctor not found"}), 404

#for the doctor login
@app.route('/login-doctor', methods=['POST'])
def login_doctor():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    cursor = mysql.connection.cursor()

    # Query to fetch doctor details based on email
    query = "SELECT doctor_id, first_name, last_name, email, password FROM DOCTOR WHERE email = %s"
    cursor.execute(query, (email,))
    doctor = cursor.fetchone()

    if doctor:
        stored_password = doctor[4]  # Get the stored hashed password
        
        # Check if entered password matches the stored password
        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            return jsonify({"message": "Login successful", "doctor_id": doctor[0]}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    else:
        return jsonify({"error": "Doctor not found"}), 404
    
# update doctor info

#------- PHARMACY RELATED QUERIES -----------------------------------------
@app.route('/register-pharmacy', methods=['POST'])
def register_pharmacy():
    data = request.get_json()

    # Hash the pharmacy password before storing it
    password = data['password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    cursor = mysql.connection.cursor()
    query = """
        INSERT INTO PHARMACY (
            email, address, zipcode, city, state, pharmacy_name, store_hours, password
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data['email'],
        data['address'],
        data['zipcode'],
        data['city'],
        data['state'],
        data['pharmacy_name'],
        data['store_hours'],
        hashed_password
    )

    try:
        cursor.execute(query, values)
        mysql.connection.commit()
        return jsonify({"message": "Pharmacy registered successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

#------- PATIENT RELATED QUERIES -----------------------------------------

# STILL IN PROGRESS - basic info registration 
@app.route('/register-patient', methods=['POST'])
def register_patient():
    data = request.get_json()

    # Hash the patient password before storing it
    password = data['patient_password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    cursor = mysql.connection.cursor()
    query = """
        INSERT INTO PATIENT (
            doctor_id, patient_email, patient_password, first_name, last_name,
            pharmacy_id
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = (
        data['doctor_id'],  # Foreign key to DOCTOR table
        data['patient_email'],
        hashed_password,
        data['first_name'],
        data['last_name'],
        data['pharmacy_id'],  # Foreign key to PHARMACY table
    )

    try:
        cursor.execute(query, values)
        mysql.connection.commit()
        return jsonify({"message": "Patient registered successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400


#--------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)