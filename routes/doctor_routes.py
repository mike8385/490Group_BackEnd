from flask import Blueprint, request, jsonify
from rabbitmq_utils import send_medication_request
from db import mysql
import bcrypt, base64
from google.cloud import storage
import time
import os

doctor_bp = Blueprint('doctor_bp', __name__)

credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
GCS_BUCKET = "image-bucket-490"
storage_client = storage.Client()

@doctor_bp.route('/register-doctor', methods=['POST'])
def register_doctor():
    """
    Register a new doctor
    ---
    tags:
      - Doctor
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - first_name
              - last_name
              - email
              - password
              - license_num
              - license_exp_date
              - dob
              - med_school
              - years_of_practice
              - specialty
              - payment_fee
              - gender
              - phone_number
              - address
              - zipcode
              - city
              - state
            properties:
              first_name:
                type: string
              last_name:
                type: string
              email:
                type: string
              password:
                type: string
              description:
                type: string
              license_num:
                type: string
              license_exp_date:
                type: string
                format: date
              dob:
                type: string
                format: date
              med_school:
                type: string
              years_of_practice:
                type: integer
              specialty:
                type: string
              payment_fee:
                type: number
              gender:
                type: string
              phone_number:
                type: string
              address:
                type: string
              zipcode:
                type: string
              city:
                type: string
              state:
                type: string
              doctor_picture:
                type: string
                description: Base64 encoded image string
          example:
            first_name: "Jane"
            last_name: "Smith"
            email: "jane.smith@example.com"
            password: "securepass123"
            license_num: "LIC2024123"
            license_exp_date: "2026-01-01"
            dob: "1982-05-12"
            med_school: "Stanford School of Medicine"
            years_of_practice: 12
            specialty: "Pediatrics"
            payment_fee: 120.0
            gender: "Female"
            phone_number: "555-123-4567"
            address: "123 Wellness Way"
            zipcode: "94043"
            city: "Mountain View"
            state: "CA"
            doctor_picture: "https://storage.googleapis.com/doctors/file"
    responses:
      201:
        description: Doctor registered successfully!
      400:
        description: Validation error or image upload failure
      500:
        description: Server/database error
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # Validate required fields
    required_fields = [
        'first_name', 'last_name', 'email', 'password', 'license_num',
        'license_exp_date', 'dob', 'med_school', 'years_of_practice',
        'specialty', 'payment_fee', 'gender', 'phone_number',
        'address', 'zipcode', 'city', 'state'
    ]
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Hash the password
    password = data.get('password')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    doctor_picture_url = None
    doctor_picture = data.get('doctor_picture')  # Base64 encoded image data
    if doctor_picture:
        try:
            doctor_picture = base64.b64decode(doctor_picture)
            filename = f"doctors/{data['first_name']}_{data['last_name']}_{int(time.time())}.png"
            bucket = storage_client.bucket(GCS_BUCKET)
            blob = bucket.blob(filename)
            blob.upload_from_string(doctor_picture, content_type='image/png')

            doctor_picture_url = f"https://storage.googleapis.com/{GCS_BUCKET}/{filename}"
        except Exception as e:
            return jsonify({"error": f"Failed to upload image: {str(e)}"}), 400

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
        doctor_picture_url  # or doctor_picture_url if using GCS
    )

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(query, values)
        mysql.connection.commit()
        return jsonify({"message": "Doctor registered successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@doctor_bp.route('/doctor/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    """
    Retrieve a doctor's info by their ID
    ---
    tags:
      - Doctor
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Doctor information returned successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                doctor_id: { type: integer }
                first_name: { type: string }
                last_name: { type: string }
                email: { type: string }
                description: { type: string }
                license_num: { type: string }
                license_exp_date: { type: string, format: date }
                dob: { type: string, format: date }
                med_school: { type: string }
                specialty: { type: string }
                years_of_practice: { type: integer }
                payment_fee: { type: number }
                gender: { type: string }
                phone_number: { type: string }
                address: { type: string }
                zipcode: { type: string }
                city: { type: string }
                state: { type: string }
                doctor_picture: { type: string }
                accepting_patients: { type: boolean }
                doctor_rating: { type: number }
            example:
              doctor_id: 1
              first_name: "Alice"
              last_name: "Nguyen"
              email: "alice@example.com"
              description: "Cardiology specialist"
              license_num: "MD123"
              license_exp_date: "2028-12-31"
              dob: "1980-01-15"
              med_school: "Harvard"
              specialty: "Cardiology"
              years_of_practice: 10
              payment_fee: 200.0
              gender: "Female"
              phone_number: "1234567890"
              address: "123 Lane"
              zipcode: "10001"
              city: "New York"
              state: "NY"
              doctor_picture: "https://storage.googleapis.com/doctor/doctor1.png"
              accepting_patients: true
              doctor_rating: 4.9
      404:
        description: Doctor not found
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
            "doctor_picture": doctor[18],
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
    tags:
    - Doctor
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - email
              - password
            properties:
              email:
                type: string
              password:
                type: string
          example:
            email: "alice@example.com"
            password: "password123"
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
        # Step 1: get "legacy" emails
        cursor.execute("SELECT email FROM DOCTOR ORDER BY doctor_id ASC LIMIT 50")
        test_emails = set(row[0] for row in cursor.fetchall())

        # Step 2: get doctor by email
        cursor.execute("SELECT doctor_id, password FROM DOCTOR WHERE email = %s", (email,))
        doctor = cursor.fetchone()

        if doctor:
            doctor_id, stored_password = doctor

            if email in test_emails:
                # Legacy: compare as plaintext
                if password == stored_password:
                    return jsonify({"message": "Login successful (legacy plain text)", "doctor_id": doctor_id}), 200
                else:
                    return jsonify({"error": "Invalid credentials"}), 401
            else:
                # Modern: compare using bcrypt
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')

                if bcrypt.checkpw(password.encode('utf-8'), stored_password):
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
    Delete a doctor by their ID number
    ---
    tags:
      - Doctor
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Doctor deleted successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
            example:
              message: "Doctor with ID 1 has been deleted."
      404:
        description: Doctor not found
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
            example:
              error: "Doctor not found"
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
    tags:
      - Doctor
    responses:
      200:
        description: List of all registered doctors
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  doctor_id: { type: integer }
                  first_name: { type: string }
                  last_name: { type: string }
                  email: { type: string }
                  description: { type: string }
                  license_num: { type: string }
                  license_exp_date: { type: string, format: date }
                  dob: { type: string, format: date }
                  med_school: { type: string }
                  specialty: { type: string }
                  years_of_practice: { type: integer }
                  payment_fee: { type: number }
                  gender: { type: string }
                  phone_number: { type: string }
                  address: { type: string }
                  zipcode: { type: string }
                  city: { type: string }
                  state: { type: string }
                  doctor_picture: { type: string }
                  accepting_patients: { type: boolean }
                  doctor_rating: { type: number }
            example:
              - doctor_id: 1
                first_name: "Alice"
                last_name: "Nguyen"
                email: "alice@example.com"
                description: "Cardiology specialist"
                license_num: "MD123"
                license_exp_date: "2028-12-31"
                dob: "1980-01-15"
                med_school: "Harvard"
                specialty: "Cardiology"
                years_of_practice: 10
                payment_fee: 200.0
                gender: "Female"
                phone_number: "1234567890"
                address: "123 Lane"
                zipcode: "10001"
                city: "New York"
                state: "NY"
                doctor_picture: "https://storage.googleapis.com/bucket/doctor1.png"
                accepting_patients: true
                doctor_rating: 4.9
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT doctor_id, first_name, last_name, email, description, license_num,
               license_exp_date, dob, med_school, specialty, years_of_practice, payment_fee,
               gender, phone_number, address, zipcode, city, state, doctor_picture,
               accepting_patients, doctor_rating, created_at, updated_at
        FROM DOCTOR
    """
    cursor.execute(query)
    doctors = cursor.fetchall()

    result = []
    for doc in doctors:
        # doctor_picture = doc[18]  # Corrected index due to password removal
        # if doctor_picture:
        #     if isinstance(doctor_picture, str):
        #         doctor_picture = doctor_picture.encode('utf-8')
        #     doctor_picture = base64.b64encode(doctor_picture).decode('utf-8')

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
            "doctor_picture": doc[18],
            "accepting_patients": doc[19],
            "doctor_rating": doc[20],
            # created_at and updated_at are fetched but not returned
        })

    return jsonify(result), 200

# need to test this
# get appointments by doctor
@doctor_bp.route('/doc-appointments/<int:doctor_id>', methods=['GET'])
def get_appointments_by_doctor(doctor_id):
    """
    Get appointments by doctor ID
    ---
    tags:
      - Appointment
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
        description: ID of the doctor
    responses:
      200:
        description: List of appointments for the doctor
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  patient_appt_id:
                    type: integer
                  patient_id:
                    type: integer
                  appointment_datetime:
                    type: string
                    format: date-time
                  reason_for_visit:
                    type: string
                  current_medications:
                    type: string
                  exercise_frequency:
                    type: string
                  doctor_appointment_note:
                    type: string
                  accepted:
                    type: number
                  meal_prescribed:
                    type: int
                  created_at:
                    type: string
                    format: date-time
                  updated_at:
                    type: string
                    format: date-time
                  patient_first_name:
                    type: string
                  patient_last_name:
                    type: string
      400:
        description: Error retrieving appointments
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
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
            pa.created_at,
            pa.updated_at,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name,
            mp.meal_plan_title AS meal_prescribed
        FROM PATIENT_APPOINTMENT pa
        JOIN PATIENT p ON pa.patient_id = p.patient_id
        JOIN MEAL_PLAN mp ON pa.meal_prescribed = mp.meal_plan_id
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
    Update the acceptance status of an appointment
    ---
    tags:
      - Appointment
    parameters:
      - name: appointment_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - accepted
            properties:
              accepted:
                type: integer
                description: 1 to accept, 0 to deny (will be set to 2)
          example:
            accepted: 1
    responses:
      200:
        description: Status update message
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      400:
        description: Invalid input or database error
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
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
    Prescribe a medicine to a patient
    ---
    tags:
      - Prescription
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - patient_id
              - medicine_id
              - quantity
            properties:
              patient_id:
                type: integer
              medicine_id:
                type: integer
              quantity:
                type: integer
                minimum: 1
          example:
            patient_id: 1
            medicine_id: 3
            quantity: 2
    responses:
      201:
        description: Prescription added successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      400:
        description: Validation or database error
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
    """
    data = request.get_json()
    patient_id = data.get('patient_id')
    medicine_id = data.get('medicine_id')
    quantity = data.get('quantity')

    # Basic validation
    if patient_id is None or medicine_id is None or quantity is None:
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

# need to test this
@doctor_bp.route('/appointment/meal', methods=['POST'])
def assign_plan_to_patient():
    data = request.get_json()
    appt_id = data.get('appt_id')
    meal_plan_id = data.get('meal_plan_id')

    if not appt_id or not meal_plan_id:
        return jsonify({"error": "appt_id and meal_plan_id are required."}), 400

    cursor = mysql.connection.cursor()

    try:
        # Update the appointment
        update_query = """
            UPDATE PATIENT_APPOINTMENT
            SET meal_prescribed = %s, updated_at = CURRENT_TIMESTAMP
            WHERE patient_appt_id = %s
        """
        cursor.execute(update_query, (meal_plan_id, appt_id))

        # Fetch patient_id using consistent column name
        patient_id_query = """
            SELECT patient_id FROM PATIENT_APPOINTMENT
            WHERE patient_appt_id = %s
        """
        cursor.execute(patient_id_query, (appt_id,))
        result = cursor.fetchone()

        if result is None:
            return jsonify({"error": "No appointment found for this ID."}), 404

        patient_id = result[0]  # Extract value

        # ✅ FIXED: Correct argument order
        insert_query = """
            INSERT INTO PATIENT_PLANS (meal_plan_id, user_id, created_at, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        cursor.execute(insert_query, (meal_plan_id, patient_id))  # Corrected order

        mysql.connection.commit()
        return jsonify({"message": "Meal plan assigned successfully."}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()



# accepting patients - general
@doctor_bp.route('/doctor-accepting-status/<int:doctor_id>', methods=['PATCH'])
def update_accepting_status(doctor_id):
    """
    Update whether a doctor is accepting patients
    ---
    tags:
      - Doctor
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - accepting_patients
            properties:
              accepting_patients:
                type: integer
                description: 1 for accepting, 0 for not accepting
          example:
            accepting_patients: 1
    responses:
      200:
        description: Doctor's accepting status updated
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      404:
        description: Doctor not found or unchanged
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
      400:
        description: Invalid input or database error
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
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
    Add a note to an appointment
    ---
    tags:
      - Appointment
    parameters:
      - name: appt_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - doctor_appointment_note
            properties:
              doctor_appointment_note:
                type: string
          example:
            doctor_appointment_note: "Patient advised to follow up in 2 weeks."
    responses:
      200:
        description: Note added successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message: { type: string }
                appt_id: { type: integer }
                doctor_appointment_note: { type: string }
      404:
        description: Appointment not found
        content:
          application/json:
            schema:
              type: object
              properties:
                error: { type: string }
      400:
        description: Invalid input or database error
        content:
          application/json:
            schema:
              type: object
              properties:
                error: { type: string }
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
    Get average rating for a doctor based on appointment reviews
    ---
    tags:
      - Doctor
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Doctor rating retrieved or no ratings found
        content:
          application/json:
            schema:
              type: object
              properties:
                message: { type: string }
                doctor_id: { type: integer }
                average_rating:
                  type: number
                  nullable: true
      400:
        description: Retrieval error
        content:
          application/json:
            schema:
              type: object
              properties:
                error: { type: string }
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
    Get all patients assigned to a doctor
    ---
    tags:
      - Doctor
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of patients assigned to the doctor
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      404:
        description: No patients found for this doctor
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
        result.append({
            "patient_id": pat[0],
            "doctor_id": pat[1],
            "patient_email": pat[2],
            "mobile_number": pat[3],
            "first_name": pat[4],
            "last_name": pat[5],
            "medical_conditions": pat[6],
            "pharmacy_id": pat[7],
            "profile_pic": pat[8],
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

# need to test this
# changed meal_plan_prescribed to get meal_plans in db 
@doctor_bp.route('/doc-past/<int:doctor_id>', methods=['GET'])
def get_past_appointments_by_doctor(doctor_id):
    """
    Get past appointments for a doctor
    ---
    tags:
      - Appointment
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of past appointments
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      400:
        description: Retrieval error
        content:
          application/json:
            schema:
              type: object
              properties:
                error: { type: string }
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
            pa.created_at,
            pa.updated_at,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name,
            mp.meal_plan_title AS meal_prescribed
        FROM PATIENT_APPOINTMENT pa
        JOIN PATIENT p ON pa.patient_id = p.patient_id
        JOIN MEAL_PLAN mp ON pa.meal_prescribed = mp.meal_plan_id
        WHERE p.doctor_id = %s
        AND (pa.appointment_datetime < NOW() OR pa.appt_status = 2)
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

# changed meal_plan_prescribed to get meal_plans in db
@doctor_bp.route('/doc-upcoming/<int:doctor_id>', methods=['GET'])
def get_upcoming_appointments_by_doctor(doctor_id):
    """
    Get upcoming accepted appointments for a doctor
    ---
    tags:
      - Appointment
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of upcoming accepted appointments
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      400:
        description: Error retrieving appointments
        content:
          application/json:
            schema:
              type: object
              properties:
                error: { type: string }
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

# need to test this
# changed meal_plan_prescribed to get meal_plans in db
@doctor_bp.route('/requested-appointments/<int:doctor_id>', methods=['GET'])
def get_requested_appointments(doctor_id):
    """
    Get requested (not yet accepted) upcoming appointments for a doctor
    ---
    tags:
      - Appointment
    parameters:
      - name: doctor_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of upcoming requested appointments
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      400:
        description: Error retrieving appointments
        content:
          application/json:
            schema:
              type: object
              properties:
                error: { type: string }
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
    Send a prescription request to the pharmacy
    ---
    tags:
      - Prescription
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - appt_id
              - medicine_id
              - quantity
            properties:
              appt_id: { type: integer }
              medicine_id: { type: integer }
              quantity: { type: integer }
          example:
            appt_id: 7
            medicine_id: 2
            quantity: 30
    responses:
      200:
        description: Prescription request sent successfully
      400:
        description: Missing required fields
      500:
        description: Server error during processing
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
    Edit an existing doctor's information
    ---
    tags:
      - Doctor
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - doctor_id
              - first_name
              - last_name
              - email
            properties:
              doctor_id: { type: integer }
              first_name: { type: string }
              last_name: { type: string }
              email: { type: string }
              description: { type: string }
              years_of_practice: { type: integer }
              specialty: { type: string }
              payment_fee: { type: number }
              gender: { type: string }
              phone_number: { type: string }
              address: { type: string }
              zipcode: { type: string }
              city: { type: string }
              state: { type: string }
              doctor_picture: { type: string, description: "Base64-encoded image" }
          example:
            doctor_id: 3
            first_name: "Jane"
            last_name: "Smith"
            email: "jane@example.com"
            gender: "Female"
            city: "Chicago"
    responses:
      200:
        description: Doctor info updated successfully
      400:
        description: Validation or image upload error
      500:
        description: Database update error
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

    doctor_picture_url = None
    doctor_picture = data.get('doctor_picture')  # Base64 encoded image data
    if doctor_picture:
        try:
            doctor_picture = base64.b64decode(doctor_picture)
            filename = f"doctors/{data['first_name']}_{data['last_name']}_{int(time.time())}.png"
            bucket = storage_client.bucket(GCS_BUCKET)
            blob = bucket.blob(filename)
            blob.upload_from_string(doctor_picture, content_type='image/png')

            doctor_picture_url = f"https://storage.googleapis.com/{GCS_BUCKET}/{filename}"
        except Exception as e:
            return jsonify({"error": f"Failed to upload image: {str(e)}"}), 400

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
                doctor_picture = %s,
                updated_at = NOW()
            WHERE doctor_id = %s
        """, (
            first_name, last_name, email, description,
            years_of_practice, specialty, payment_fee, gender,
            phone_number, address, zipcode, city, state, doctor_picture_url, doctor_id
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
    Retrieve the top 3 highest-rated doctors
    ---
    tags:
      - Doctor
    responses:
      200:
        description: Top 3 rated doctors returned successfully
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      400:
        description: Database error
      404:
        description: No ratings found
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
@doctor_bp.route('/appt-status/<int:appointment_id>', methods=['PUT'])
def update_app_status(appointment_id):
    """
    Update appointment status
    ---
    tags:
      - Appointment
    parameters:
      - name: appointment_id
        in: path
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              appt_status:
                type: integer
                enum: [0, 1, 2]
                description: "0 = upcoming, 1 = ongoing, 2 = ended"
    responses:
      200:
        description: Appointment status updated successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message: { type: string }
                appt_status: { type: integer }
      400:
        description: Update error
        content:
          application/json:
            schema:
              type: object
              properties:
                error: { type: string }
    """
    data = request.get_json()
    appt_status = data.get('appt_status')

    if appt_status is None or appt_status not in [0, 1, 2]:
        return jsonify({'error': 'Invalid or missing appt_status'}), 400

    cursor = mysql.connection.cursor()

    try:
        update_query = """
            UPDATE PATIENT_APPOINTMENT
            SET appt_status = %s, updated_at = NOW()
            WHERE patient_appt_id = %s
        """
        cursor.execute(update_query, (appt_status, appointment_id))
        mysql.connection.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Appointment not found'}), 404

        return jsonify({
            'message': 'Appointment status updated',
            'appt_status': appt_status
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400
