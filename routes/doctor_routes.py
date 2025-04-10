from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt, base64

doctor_bp = Blueprint('doctor_bp', __name__)

@doctor_bp.route('/register-doctor', methods=['POST'])
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

@doctor_bp.route('/doctor/<int:doctor_id>', methods=['GET'])
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

@doctor_bp.route('/login-doctor', methods=['POST'])
def login_doctor():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    cursor = mysql.connection.cursor()

    # Query to fetch doctor details based on email
    query = "SELECT doctor_id, email, password FROM DOCTOR WHERE email = %s"
    cursor.execute(query, (email,))
    doctor = cursor.fetchone()

    if doctor:
        stored_password = doctor[2]  # Get the stored hashed password (3rd field in query result)
        
        # Check if entered password matches the stored password
        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            return jsonify({"message": "Login successful", "doctor_id": doctor[0]}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    else:
        return jsonify({"error": "Doctor not found"}), 404

@doctor_bp.route('/doctor/<int:doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    cursor = mysql.connection.cursor()

    # check if the doctor exists
    cursor.execute("SELECT * FROM DOCTOR WHERE doctor_id = %s", (doctor_id,))
    doctor = cursor.fetchone()

    if not doctor:
        return jsonify({"error": "Doctor not found"}), 404

    # delete the doctor
    cursor.execute("DELETE FROM DOCTOR WHERE doctor_id = %s", (doctor_id,))
    mysql.connection.commit()

    return jsonify({"message": f"Doctor with ID {doctor_id} has been deleted."}), 200

@doctor_bp.route('/doctors', methods=['GET'])
def get_all_doctors():
    cursor = mysql.connection.cursor()
    query = """
        SELECT doctor_id, first_name, last_name, email, description, license_num,
               license_exp_date, dob, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture,
               created_at, updated_at
        FROM DOCTOR
    """
    cursor.execute(query)
    doctors = cursor.fetchall()

    result = []
    for doc in doctors:
        doctor_picture = doc[16]
        if doctor_picture:
            if isinstance(doctor_picture, str):
                doctor_picture = doctor_picture.encode('utf-8')
            doctor_picture = base64.b64encode(doctor_picture).decode('utf-8')

        result.append({
            "doctor_id": doc[0],
            "first_name": doc[1],
            "last_name": doc[2],
            "email": doc[3],
            "description": doc[4],
            "license_num": doc[5],
            "license_exp_date": doc[6],
            "dob": doc[7],
            "years_of_practice": doc[8],
            "payment_fee": doc[9],
            "gender": doc[10],
            "phone_number": doc[11],
            "address": doc[12],
            "zipcode": doc[13],
            "city": doc[14],
            "state": doc[15],
            "doctor_picture": doctor_picture
        })

    return jsonify(result), 200