from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt

patient_bp = Blueprint('patient_bp', __name__)

@patient_bp.route('/register-patient', methods=['POST'])
def register_patient():
    data = request.get_json()
    print(data)
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

@patient_bp.route('/select-doctor', methods=['POST'])
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

@patient_bp.route('/patient/<int:patient_id>', methods=['GET'])
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

@patient_bp.route('/init-patient-survey', methods=['POST'])
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
            activity,
            health_goals,
            dietary_restrictions,
            blood_type,
            patient_address,
            patient_zipcode,
            patient_city,
            patient_state,
            medical_conditions,
            family_history,
            past_procedures,
            favorite_meal
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data['patient_id'],
        data['mobile_number'],
        data['dob'],
        data.get('gender'),
        data.get('height'),
        data.get('weight'),
        data.get('activity'),  # Changed from fitness
        data.get('health_goals'),  # Changed from goal
        data.get('dietary_restrictions'),  # Changed from allergies
        data['blood_type'],
        data['patient_address'],
        data['patient_zipcode'],
        data['patient_city'],
        data['patient_state'],
        data.get('medical_conditions'),
        data.get('family_history', "None"),
        data.get('past_procedures', "None"),
        data.get('favorite_meal', "None")
    )

    try:
        cursor.execute(insert_query, values)
        mysql.connection.commit()
        return jsonify({"message": "Patient survey submitted successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

@patient_bp.route('/init-patient-survey/<int:patient_id>', methods=['GET'])
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

@patient_bp.route('/login-patient', methods=['POST'])
def login_patient():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    cursor = mysql.connection.cursor()

    # Query to fetch patient details based on email
    query = "SELECT patient_id, patient_password FROM PATIENT WHERE patient_email = %s"
    cursor.execute(query, (email,))
    patient = cursor.fetchone()

    if patient:
        stored_password = patient[1]  # Get the stored hashed password
        
        # Check if entered password matches the stored password
        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            return jsonify({"message": "Login successful", "patient_id": patient[0]}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    else:
        return jsonify({"error": "Patient not found"}), 404