from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt, base64
from google.cloud import storage
import time

doctor_bp = Blueprint('doctor_bp', __name__)

GCS_BUCKET = "clinic-db-bucket"
storage_client = storage.Client()
@doctor_bp.route('/register-doctor', methods=['POST'])
def register_doctor():
    data = request.get_json()

    # hash the password before storing it
    password = data['password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    doctor_picture_url = None

    #for the picture i'm still not sure
    doctor_picture = data.get('doctor_picture')  # Base64 encoded image data

    # saving data into GCS bucket. it saves the url in the db instead of binary data.
    if doctor_picture:
        try:
            # Decode the base64 string to binary data
            doctor_picture = base64.b64decode(doctor_picture)
            filename = f"doctors/{data['first_name']}_{int(time.time())}.png"
            bucket = storage_client.bucket(GCS_BUCKET)
            blob = bucket.blob(filename)
            blob.upload_from_string(doctor_picture, content_type='image/png')
            # blob.make_public()
            doctor_picture_url = blob.public_url
        except Exception as e:
            return jsonify({"error": f"Failed to upload image: {str(e)}"}), 400
    cursor = mysql.connection.cursor()
    query = """
        INSERT INTO DOCTOR (
            first_name, last_name, email, password, description, license_num,
            license_exp_date, dob, med_school, years_of_practice, specialty, payment_fee,
            gender, phone_number, address, zipcode, city, state, doctor_picture
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        data['med_school'],
        data['years_of_practice'],
        data['specialty'],
        data['payment_fee'],
        data['gender'],
        data['phone_number'],
        data['address'],
        data['zipcode'],
        data['city'],
        data['state'],
        doctor_picture_url  # saving url instead of binary data
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
               license_exp_date, dob, med_school, specialty, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture,
               doctor_rating
        FROM DOCTOR
        WHERE doctor_id = %s
    """
    cursor.execute(query, (doctor_id,))
    doctor = cursor.fetchone()

    if doctor:
        doctor_picture = doctor[18]  # Adjusted index due to added fields
        if doctor_picture:
            if isinstance(doctor_picture, str):
                doctor_picture = doctor_picture.encode('utf-8')
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
            "med_school": doctor[8],
            "specialty": doctor[9],
            "years_of_practice": doctor[10],
            "payment_fee": doctor[11],
            "gender": doctor[12],
            "phone_number": doctor[13],
            "address": doctor[14],
            "zipcode": doctor[15],
            "city": doctor[16],
            "state": doctor[17],
            "doctor_picture": doctor_picture,
            "accepting_patients": doctor[19],
            "doctor_rating": doctor[20]
        }), 200
    else:
        return jsonify({"error": "Doctor not found"}), 404

@doctor_bp.route('/login-doctor', methods=['POST'])
def login_doctor():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    cursor = mysql.connection.cursor()

    try:
        # Step 1: Get all emails from the first 50 entries
        cursor.execute("SELECT email FROM DOCTOR ORDER BY doctor_id ASC LIMIT 50")
        test_emails = set(row[0] for row in cursor.fetchall())

        # Step 2: Get patient info by email
        cursor.execute("SELECT doctor_id, password FROM DOCTOR WHERE email = %s", (email,))
        doctor = cursor.fetchone()

        if doctor:
            doctor_id, stored_password = doctor

            if email in test_emails:
                # Password is in plain text
                if password == stored_password:
                    return jsonify({"message": "Login successful (legacy plain text)", "doctor_id": doctor_id}), 200
                else:
                    return jsonify({"error": "Invalid credentials"}), 401
            else:
                # Password is hashed
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return jsonify({"message": "Login successful", "doctor_id": doctor_id}), 200
                else:
                    return jsonify({"error": "Invalid credentials"}), 401
        else:
            return jsonify({"error": "Doctor not found"}), 404
    finally:
        cursor.close()

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
               license_exp_date, dob, med_school, specialty, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture, password,
               created_at, updated_at
        FROM DOCTOR
    """
    cursor.execute(query)
    doctors = cursor.fetchall()

    result = []
    for doc in doctors:
        doctor_picture = doc[19]
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
            "med_school": doc[8],
            "specialty": doc[9],
            "years_of_practice": doc[10],
            "payment_fee": doc[11],
            "gender": doc[12],
            "phone_number": doc[13],
            "address": doc[14],
            "zipcode": doc[15],
            "city": doc[16],
            "state": doc[17],
            "password": doc[18],
            "doctor_picture": doctor_picture
        })

    return jsonify(result), 200

# get appointments by doctor
@doctor_bp.route('/doc-appointments/<int:doctor_id>', methods=['GET'])
def get_appointments_by_doctor(doctor_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            pa.patient_appt_id,
            pa.patient_id,
            pa.appointment_datetime,
            pa.reason_for_visit,
            pa.current_medications,
            pa.exercise_frequency,
            pa.doctor_appointment_note,
            pa.accepted,
            pa.meal_prescribed,
            pa.created_at,
            pa.updated_at,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name
        FROM PATIENT_APPOINTMENT pa
        JOIN PATIENT p ON pa.patient_id = p.patient_id
        WHERE p.doctor_id = %s
        ORDER BY pa.appointment_datetime DESC
    """

    try:
        cursor.execute(query, (doctor_id,))
        appointments = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in appointments]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
# doctor accepts an appointment [1], else default 0
@doctor_bp.route('/doc-appointments-status/<int:appointment_id>', methods=['PATCH'])
def update_appointment_status(appointment_id):
    data = request.get_json()
    new_status = data.get('accepted')

    if new_status not in [0, 1]:
        return jsonify({"error": "Invalid status. 'accepted' must be 0 (deny) or 1 (accept)."}), 400

    cursor = mysql.connection.cursor()

    query = """
        UPDATE PATIENT_APPOINTMENT
        SET accepted = %s, updated_at = CURRENT_TIMESTAMP
        WHERE patient_appt_id = %s
    """

    try:
        cursor.execute(query, (new_status, appointment_id))
        mysql.connection.commit()
        return jsonify({"message": "Appointment status updated successfully."}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

# doctor adds a prescription for a patient
@doctor_bp.route('/prescription/add', methods=['POST'])
def add_prescription():
    data = request.get_json()
    patient_id = data.get('patient_id')
    medicine_id = data.get('medicine_id')
    quantity = data.get('quantity')

    # Basic validation
    if not all([patient_id, medicine_id, quantity]):
        return jsonify({"error": "patient_id, medicine_id, and quantity are required."}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "quantity must be a positive integer."}), 400

    cursor = mysql.connection.cursor()

    query = """
        INSERT INTO PATIENT_PRESCRIPTION (
            patient_id, medicine_id, quantity
        ) VALUES (%s, %s, %s)
    """
    values = (patient_id, medicine_id, quantity)

    try:
        cursor.execute(query, values)
        mysql.connection.commit()
        return jsonify({"message": "Prescription added successfully."}), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cursor.close()

# accepting patients - general
@doctor_bp.route('/doctor-accepting-status/<int:doctor_id>', methods=['PATCH'])
def update_accepting_status(doctor_id):
    data = request.get_json()
    new_status = data.get('accepting_patients')

    if new_status not in [0, 1]:
        return jsonify({"error": "Invalid status. 'accepting_patients' must be 0 (no) or 1 (yes)."}), 400

    cursor = mysql.connection.cursor()

    query = """
        UPDATE DOCTOR
        SET accepting_patients = %s, updated_at = CURRENT_TIMESTAMP
        WHERE doctor_id = %s
    """

    try:
        cursor.execute(query, (new_status, doctor_id))
        mysql.connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Doctor not found or no change made."}), 404

        return jsonify({"message": "Doctor's accepting status updated successfully."}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

# add appointment notes
@doctor_bp.route('/appointment/<int:appt_id>/add_note', methods=['PATCH'])
def add_appointment_note(appt_id):
    data = request.get_json()
    note = data.get('doctor_appointment_note')

    cursor = mysql.connection.cursor()

    try:
        # Add the appointment's note
        cursor.execute("""
            UPDATE PATIENT_APPOINTMENT
            SET doctor_appointment_note = %s
            WHERE patient_appt_id = %s
        """, (note, appt_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Appointment not found."}), 404

        mysql.connection.commit()

        return jsonify({
            "message": "Doctor's appointment note added successfully.",
            "appt_id": appt_id,
            "doctor_appointment_note": note
        }), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

