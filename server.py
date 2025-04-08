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

#register a pharmacy
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
    
# get the pharmacy info
@app.route('/pharmacy/<int:pharmacy_id>', methods=['GET'])
def get_pharmacy(pharmacy_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            pharmacy_id,
            pharmacy_name,
            email,
            address,
            zipcode,
            city,
            state,
            store_hours
        FROM PHARMACY
        WHERE pharmacy_id = %s
    """

    try:
        cursor.execute(query, (pharmacy_id,))
        result = cursor.fetchone()

        if result:
            keys = [
                'pharmacy_id', 'pharmacy_name', 'email', 'address',
                'zipcode', 'city', 'state', 'store_hours'
            ]
            pharmacy_info = dict(zip(keys, result))
            return jsonify(pharmacy_info), 200
        else:
            return jsonify({"error": "Pharmacy not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400


#------- PATIENT RELATED QUERIES -----------------------------------------

# basic info registration
@app.route('/register-patient', methods=['POST'])
def register_patient():
    data = request.get_json()

    # Hash the patient password before storing it
    password = data['patient_password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    cursor = mysql.connection.cursor()

    # Find the pharmacy by name, address, and zipcode
    find_pharmacy_query = """
        SELECT pharmacy_id FROM PHARMACY
        WHERE pharmacy_name = %s AND address = %s AND zipcode = %s
    """
    pharmacy_values = (
        data['pharmacy_name'],
        data['pharmacy_address'],
        data['pharmacy_zipcode']
    )

    cursor.execute(find_pharmacy_query, pharmacy_values)
    pharmacy = cursor.fetchone()

    if pharmacy:
        pharmacy_id = pharmacy[0]
    else:
        return jsonify({"error": "Pharmacy not found. Please register the pharmacy first."}), 400

    # Insert the patient with the new insurance-related fields
    insert_patient_query = """
        INSERT INTO PATIENT (
            patient_email, patient_password, first_name, last_name,
            pharmacy_id, insurance_provider, insurance_policy_number, insurance_expiration_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    patient_values = (
        data['patient_email'],
        hashed_password,
        data['first_name'],
        data['last_name'],
        pharmacy_id,
        data.get('insurance_provider'),  
        data.get('insurance_policy_number'),  
        data.get('insurance_expiration_date')  
    )

    try:
        cursor.execute(insert_patient_query, patient_values)
        mysql.connection.commit()
        return jsonify({"message": "Patient registered successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400


    
# used for a patient to select their doctor
@app.route('/select-doctor', methods=['POST'])
def select_doctor():
    data = request.get_json()

    cursor = mysql.connection.cursor()

    update_query = """
        UPDATE PATIENT
        SET doctor_id = %s
        WHERE patient_id = %s
    """
    values = (
        data['doctor_id'],
        data['patient_id']
    )

    try:
        cursor.execute(update_query, values)
        mysql.connection.commit()
        return jsonify({"message": "Doctor assigned successfully!"}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    
# get patient basic info
@app.route('/patient/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            patient_id,
            patient_email,
            first_name,
            last_name,
            doctor_id,
            pharmacy_id,
            doctor_rating,
            profile_pic,
            insurance_provider,
            insurance_policy_number,
            insurance_expiration_date
        FROM PATIENT
        WHERE patient_id = %s
    """

    try:
        cursor.execute(query, (patient_id,))
        result = cursor.fetchone()

        if result:
            keys = [
                'patient_id', 'patient_email', 'first_name', 'last_name',
                'doctor_id', 'pharmacy_id', 'doctor_rating', 'profile_pic',
                'insurance_provider', 'insurance_policy_number', 'insurance_expiration_date'
            ]
            patient_info = dict(zip(keys, result))
            return jsonify(patient_info), 200
        else:
            return jsonify({"error": "Patient not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# add initial survey info to db
@app.route('/init-patient-survey', methods=['POST'])
def init_patient_survey():
    data = request.get_json()
    cursor = mysql.connection.cursor()

    insert_query = """
        INSERT INTO PATIENT_INIT_SURVEY (
            patient_id,
            mobile_number,
            dob,
            gender,
            height,
            weight,
            allergies,
            blood_type,
            patient_address,
            patient_zipcode,
            patient_city,
            patient_state,
            medical_conditions,
            family_history,
            past_procedures
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data['patient_id'],
        data['mobile_number'],
        data['dob'],
        data.get('gender'),
        data.get('height'),
        data.get('weight'),
        data.get('allergies'),
        data['blood_type'],  
        data['patient_address'],
        data['patient_zipcode'],
        data['patient_city'],
        data['patient_state'],
        data.get('medical_conditions'),
        data.get('family_history'),
        data.get('past_procedures')
    )

    try:
        cursor.execute(insert_query, values)
        mysql.connection.commit()
        print("Blood Type: ", data['blood_type'])
        return jsonify({"message": "Patient survey submitted successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

# get init survey info
@app.route('/init-patient-survey/<int:patient_id>', methods=['GET'])
def get_patient_init_survey(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            is_id,
            patient_id,
            mobile_number,
            dob,
            gender,
            height,
            weight,
            allergies,
            blood_type,
            patient_address,
            patient_zipcode,
            patient_city,
            patient_state,
            medical_conditions,
            family_history,
            past_procedures
        FROM PATIENT_INIT_SURVEY
        WHERE patient_id = %s
    """

    try:
        cursor.execute(query, (patient_id,))
        result = cursor.fetchone()

        if result:
            keys = [
                'is_id', 'patient_id', 'mobile_number', 'dob', 'gender',
                'height', 'weight', 'allergies', 'blood_type', 'patient_address',
                'patient_zipcode', 'patient_city', 'patient_state', 'medical_conditions',
                'family_history', 'past_procedures'
            ]
            survey_info = dict(zip(keys, result))
            return jsonify(survey_info), 200
        else:
            return jsonify({"error": "Patient survey not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400


#--------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)