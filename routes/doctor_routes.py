from flask import Blueprint, request, jsonify
from rabbitmq_utils import send_medication_request
from emails_utils import send_appointment_email
from db import mysql
import bcrypt, base64
# from google.cloud import storage
import time

doctor_bp = Blueprint('doctor_bp', __name__)

# GCS_BUCKET = "clinic-db-bucket"
# storage_client = storage.Client()
@doctor_bp.route('/register-doctor', methods=['POST'])
def register_doctor():
    """
    Register a new doctor
    ---
    responses:
      201:
        description: Doctor registered successfully!
      400:
        description: Error based on what went wrong.
    """
    data = request.get_json()

    # hash the password before storing it
    password = data['password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # doctor_picture_url = None

    #for the picture i'm still not sure
    doctor_picture = data.get('doctor_picture')  # Base64 encoded image data

    # saving data into GCS bucket. it saves the url in the db instead of binary data.
    # if doctor_picture:
    #     try:
    #         # Decode the base64 string to binary data
    #         doctor_picture = base64.b64decode(doctor_picture)
    #         filename = f"doctors/{data['first_name']}_{int(time.time())}.png"
    #         bucket = storage_client.bucket(GCS_BUCKET)
    #         blob = bucket.blob(filename)
    #         blob.upload_from_string(doctor_picture, content_type='image/png')
    #         # blob.make_public()
    #         doctor_picture_url = blob.public_url
    #     except Exception as e:
    #         return jsonify({"error": f"Failed to upload image: {str(e)}"}), 400
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
        data.get('doctor_picture')
        # doctor_picture_url  # saving url instead of binary data
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
    """
    Retrieve a doctor's information by their ID number
    ---
    responses:
      200:
        description: return doctor information including doctor_id, first_name, last_name, email, description, license_num,
               license_exp_date, dob, med_school, specialty, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture,
               accepting_patients, doctor_rating
      404:
        description: Doctor not found.
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT doctor_id, first_name, last_name, email, description, license_num,
               license_exp_date, dob, med_school, specialty, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture,
               accepting_patients, doctor_rating
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
            "doctor_rating": doctor[20],
        }), 200
    else:
        return jsonify({"error": "Doctor not found"}), 404

@doctor_bp.route('/login-doctor', methods=['POST'])
def login_doctor():
    """
    Doctor Login
    ---
    responses:
      200:
        description: Login Successful with the Doctor ID.
      401:
        description: Invalid credentials.
      404:
        description: Doctor not found.
    """
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
    """
    Delete Doctor by their ID number
    ---
    responses:
      200:
        description: Doctor with denoted ID has been deleted.
      404:
        description: Doctor not found.
    """
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
    """
    Retrieve all doctors' information
    ---
    responses:
      200:
        description: Doctor with denoted ID's information is returned
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT doctor_id, first_name, last_name, email, description, license_num,
               license_exp_date, dob, med_school, specialty, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture, password,
               accepting_patients, doctor_rating, created_at, updated_at
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
            "doctor_picture": doctor_picture,
            "accepting_patients" : doc[20],
            "doctor_rating": doc[21]
        })

    return jsonify(result), 200

# get appointments by doctor
@doctor_bp.route('/doc-appointments/<int:doctor_id>', methods=['GET'])
def get_appointments_by_doctor(doctor_id):
    """
    Get appointments by doctor ID
    ---
    responses:
      200:
        description: Information about the appointments is returned
      400:
        description: Error message based on what went wrong.
    """
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
    
@doctor_bp.route('/doc-appointments-status/<int:appointment_id>', methods=['PATCH'])
def update_appointment_status(appointment_id):
    """
    Updates the appointment status: accepts (1) or sets to 2 if denied.
    ---
    responses:
      200:
        description: Appointment status updated successfully
      400:
        description: Error message based on what went wrong.
    """
    data = request.get_json()
    new_status = data.get('accepted')

    if new_status not in [0, 1]:
        return jsonify({"error": "Invalid status. 'accepted' must be 0 (deny) or 1 (accept)."}), 400

    cursor = mysql.connection.cursor()

    try:
        if new_status == 1:
            # Accept: update status to 1
            query = """
                UPDATE PATIENT_APPOINTMENT
                SET accepted = %s, updated_at = CURRENT_TIMESTAMP
                WHERE patient_appt_id = %s
            """
            cursor.execute(query, (new_status, appointment_id))
            message = "Appointment accepted successfully."
        else:
            # Deny: update status to 0.5 instead of deleting
            query = """
                UPDATE PATIENT_APPOINTMENT
                SET accepted = 2, updated_at = CURRENT_TIMESTAMP
                WHERE patient_appt_id = %s
            """
            cursor.execute(query, (appointment_id,))
            message = "Appointment denied (status set to 0.5) successfully."

        mysql.connection.commit()

        # After updating the DB status...
        cursor.execute("""
            SELECT p.email, p.first_name, pa.appointment_datetime
            FROM PATIENT_APPOINTMENT pa
            JOIN PATIENT p ON pa.patient_id = p.patient_id
            WHERE pa.patient_appt_id = %s
        """, (appointment_id,))
        result = cursor.fetchone()

        if result:
            patient_email, patient_name, appt_time = result
            if new_status == 1:
                subject = "Appointment Confirmed"
                html = f"""
                <h3>Hi {patient_name},</h3>
                <p>Your appointment on <strong>{appt_time}</strong> has been <span style="color:green;">accepted</span>.</p>
                <p>Thank you for using our portal!</p>
                """
            else:
                subject = "Appointment Denied"
                html = f"""
                <h3>Hi {patient_name},</h3>
                <p>Your appointment on <strong>{appt_time}</strong> has been <span style="color:red;">denied</span>.</p>
                <p>Please try rescheduling.</p>
                """

            send_appointment_email(patient_email, patient_name, subject, html)

        return jsonify({"message": message}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cursor.close()


# doctor adds a prescription for a patient
@doctor_bp.route('/prescription/add', methods=['POST'])
def add_prescription():
    """
    Prescribe a medicine to a patient with the quantity
    ---
    responses:
      200:
        description: Prescription added successfully.
      400:
        description: patient_id, medicine_id, and quantity are required.
      400:
        description: quantity must be a positive integer.
      400:
        description: Error message based on what went wrong.
    """
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
    """
    Handles if doctor is accepting patients or not.
    ---
    responses:
      200:
        description: Doctor's accepting status updated successfully.
      404:
        description: Doctor not found or no change made.
      400:
        description: Error message based on what went wrong.
    """
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
    """
    Handles if doctor is accepting patients or not.
    ---
    responses:
      200:
        description: Doctor's appointment note added successfully, with the appointment id and doctor appointment note.
      404:
        description: Appointment not found
      400:
        description: Error message based on what went wrong.
    """
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

# get average doctor rating
@doctor_bp.route('/doctor/<int:doctor_id>/rating', methods=['GET'])
def get_doctor_average_rating(doctor_id):
    """
    Compute the average rating for a doctor based on patient appointments.
    ---
    responses:
      200:
        description: Average rating retrieved successfully with the doctor_id and average_rating.
      200:
        description: This doctor has no ratings yet with the doctor_id and the average_rating as None
      400:
        description: Error message based on what went wrong.
    """
    cursor = mysql.connection.cursor()

    try:
        # Compute average appointment rating for the doctor
        cursor.execute("""
            SELECT AVG(appt_rating)
            FROM PATIENT_APPOINTMENT
            WHERE doctor_id = %s AND appt_rating IS NOT NULL
        """, (doctor_id,))
        result = cursor.fetchone()
        avg_rating = float(result[0]) if result[0] is not None else None

        if avg_rating is None:
            return jsonify({
                "message": "This doctor has no ratings yet.",
                "doctor_id": doctor_id,
                "average_rating": None
            }), 200

        return jsonify({
            "message": "Average rating retrieved successfully.",
            "doctor_id": doctor_id,
            "average_rating": round(avg_rating, 2)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

@doctor_bp.route('/doc_patients/<int:doctor_id>', methods=['GET'])
def get_patients_by_doctor(doctor_id):
    """
    Get all patients assigned to a specific doctor
    ---
    responses:
      200:
        description: return information about the doctor's patient based on the doctor id and patient id.
      404:
        description: Error, no description.
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT p.patient_id, p.doctor_id, p.patient_email, pis.mobile_number,
               p.first_name, p.last_name, pis.medical_conditions, p.pharmacy_id, p.profile_pic,
               pis.past_procedures, pis.blood_type, pis.health_goals, pis.activity, 
               p.insurance_provider, p.insurance_policy_number, p.insurance_expiration_date,
               p.acct_balance, p.created_at, p.updated_at
        FROM PATIENT as p
        JOIN PATIENT_INIT_SURVEY as pis ON p.patient_id = pis.patient_id
        WHERE p.doctor_id = %s
    """
    cursor.execute(query, (doctor_id,))
    patients = cursor.fetchall()
    cursor.close()

    result = []
    for pat in patients:
        profile_pic = pat[8]
        if profile_pic:
            if isinstance(profile_pic, str):
                profile_pic = profile_pic.encode('utf-8')
            profile_pic = base64.b64encode(profile_pic).decode('utf-8')

        result.append({
            "patient_id": pat[0],
            "doctor_id": pat[1],
            "patient_email": pat[2],
            "mobile_number": pat[3],
            "first_name": pat[4],
            "last_name": pat[5],
            "medical_conditions": pat[6],
            "pharmacy_id": pat[7],
            "profile_pic": profile_pic,
            "past_procedures": pat[9],
            "blood_type": pat[10],
            "health_goals": pat[11],
            "activity": pat[12],
            "insurance_provider": pat[13],
            "insurance_policy_number": pat[14],
            "insurance_expiration_date": str(pat[15]),
            "acct_balance": float(pat[16]),
            "created_at": str(pat[17]),
            "updated_at": str(pat[18])
        })

    return jsonify(result), 200 if result else 404

@doctor_bp.route('/doc-past/<int:doctor_id>', methods=['GET'])
def get_past_appointments_by_doctor(doctor_id):
    """
    Get past appointments by doctor ID
    ---
    responses:
      200:
        description: return information about the past appointments based on the doctor id and patient id.
      400:
        description: Error message based on what went wrong.
    """
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
        WHERE p.doctor_id = %s AND pa.appointment_datetime < NOW()
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

@doctor_bp.route('/doc-upcoming/<int:doctor_id>', methods=['GET'])
def get_upcoming_appointments_by_doctor(doctor_id):
    """
    Get upcoming appointments by doctor ID
    ---
    responses:
      200:
        description: return information about the upcoming appointments based on the doctor id and patient id.
      400:
        description: Error message based on what went wrong.
    """
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
        WHERE p.doctor_id = %s AND pa.appointment_datetime >= NOW() AND pa.accepted = 1
        ORDER BY pa.appointment_datetime ASC
    """

    try:
        cursor.execute(query, (doctor_id,))
        appointments = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in appointments]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@doctor_bp.route('/requested-appointments/<int:doctor_id>', methods=['GET'])
def get_requested_appointments(doctor_id):
    """
    Get upcoming requested (not yet accepted) appointments by doctor ID
    ---
    responses:
      200:
        description: Returns upcoming appointments that have not been accepted yet for the specified doctor.
      400:
        description: Error message based on what went wrong.
    """
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
          AND pa.appointment_datetime >= NOW()
          AND (pa.accepted = 0 OR pa.accepted IS NULL)
        ORDER BY pa.appointment_datetime ASC
    """

    try:
        cursor.execute(query, (doctor_id,))
        appointments = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in appointments]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

@doctor_bp.route('/request-prescription', methods=['POST'])
def request_prescription():
    """
    Prescription request for a patient that goes to the pharmacy
    ---
    responses:
      200:
        description: Prescription request sent successfully.
      400:
        description: Missing required fields
      500:
        description: Error message based on what went wrong.
    """
    data = request.json
    required_fields = ['appt_id', 'medicine_id', 'quantity']

    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        send_medication_request(data)
        return jsonify({'message': 'Prescription request sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
# edit doctor info
@doctor_bp.route('/edit-doctor', methods=['PUT'])
def edit_doctor():
    """
    Can edit doctor information.
    ---
    responses:
      200:
        description: Doctor information updated successfully.
      400:
        description: Missing required fields
      500:
        description: Error message based on what went wrong.
    """
    data = request.get_json()
    print(data)
    doctor_id = data.get('doctor_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    description = data.get('description')
    years_of_practice = data.get('years_of_practice')
    specialty = data.get('specialty')
    payment_fee = data.get('payment_fee')
    gender = data.get('gender')
    phone_number = data.get('phone_number')
    address = data.get('address')
    zipcode = data.get('zipcode')
    city = data.get('city')
    state = data.get('state')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            UPDATE doctor
            SET first_name = %s,
                last_name = %s,
                email = %s,
                description = %s,
                years_of_practice = %s,
                specialty = %s,
                payment_fee = %s,
                gender = %s,
                phone_number = %s,
                address = %s,
                zipcode = %s,
                city = %s,
                state = %s,
                updated_at = NOW()
            WHERE doctor_id = %s
        """, (
            first_name, last_name, email, description,
            years_of_practice, specialty, payment_fee, gender,
            phone_number, address, zipcode, city, state, doctor_id
        ))

        mysql.connection.commit()
        return jsonify({'message': 'Doctor information updated successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()

# retrieve top 3 rated doctors
@doctor_bp.route('/top-doctors', methods=['GET'])
def get_top_doctors():
    """
    Get the top 3 rated doctors

    ---
    tags:
      - Doctor
    responses:
      200:
        description: Successfully retrieved top 3 doctors.
      400:
        description: Error occurred.
      404:
        description: Ratings not found.
    """
    cursor = mysql.connection.cursor()

    query = """
    SELECT first_name, last_Name, description, doctor_rating, doctor_picture FROM DOCTOR
    ORDER BY doctor_rating DESC
    LIMIT 3;
    """

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        if results:
            details = [{"first_name": result[0], "last_name": result[1], "description": result[2],
                        "doctor_rating": result[3], "doctor_picture": result[4]} for result in results]
            return jsonify(details), 200
        else:
            return jsonify({"error": "Ratings not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()




