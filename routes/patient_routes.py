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
        if "Duplicate entry" in str(e) and "patient_email" in str(e):
            return jsonify({"error": "A patient with this email already exists."}), 400
        return jsonify({"error": str(e)}), 400
    
# register patient + init survey combined
@patient_bp.route('/register-patient-with-survey', methods=['POST'])
def register_patient_with_survey():
    data = request.get_json()
    cursor = mysql.connection.cursor()

    try:
        # hash the password ---
        password = data['patient_password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Get pharmacy ID ---
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

        if not pharmacy:
            return jsonify({"error": "Pharmacy not found. Please register the pharmacy first."}), 400
        pharmacy_id = pharmacy[0]

        # Insert patient ---
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
        cursor.execute(insert_patient_query, patient_values)

        # Get the newly inserted patient's ID
        patient_id = cursor.lastrowid

        # Insert initial survey ---
        insert_survey_query = """
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
                past_procedures
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        survey_values = (
            patient_id,
            data['mobile_number'],
            data['dob'],
            data.get('gender'),
            data.get('height'),
            data.get('weight'),
            data.get('activity'),
            data.get('health_goals'),
            data.get('dietary_restrictions'),
            data['blood_type'],
            data['patient_address'],
            data['patient_zipcode'],
            data['patient_city'],
            data['patient_state'],
            data.get('medical_conditions'),
            data.get('family_history', "None"),
            data.get('past_procedures', "None")
        )
        cursor.execute(insert_survey_query, survey_values)

        # Commit transaction ---
        mysql.connection.commit()
        return jsonify({"message": "Patient and survey registered successfully!"}), 201

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

    try:
        # Step 1: Get all emails from the first 351 entries
        cursor.execute("SELECT patient_email FROM PATIENT ORDER BY patient_id ASC LIMIT 351")
        test_emails = set(row[0] for row in cursor.fetchall())

        # Step 2: Get patient info by email
        cursor.execute("SELECT patient_id, patient_password FROM PATIENT WHERE patient_email = %s", (email,))
        patient = cursor.fetchone()

        if patient:
            patient_id, stored_password = patient

            if email in test_emails:
                # Password is in plain text
                if password == stored_password:
                    return jsonify({"message": "Login successful (legacy plain text)", "patient_id": patient_id}), 200
                else:
                    return jsonify({"error": "Invalid credentials"}), 401
            else:
                # Password is hashed
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return jsonify({"message": "Login successful", "patient_id": patient_id}), 200
                else:
                    return jsonify({"error": "Invalid credentials"}), 401
        else:
            return jsonify({"error": "Patient not found"}), 404
    finally:
        cursor.close()

# @patient_bp.route('/login-patient', methods=['POST'])
# def login_patient():
#     data = request.get_json()
#     email = data.get('email')
#     # Ignoring password for testing

#     cursor = mysql.connection.cursor()

#     query = "SELECT patient_id FROM PATIENT WHERE patient_email = %s"
#     cursor.execute(query, (email,))
#     patient = cursor.fetchone()

#     if patient:
#         return jsonify({"message": "Login successful", "patient_id": patient[0]}), 200
#     else:
#         return jsonify({"error": "Patient not found"}), 404

    
# add to daily survey
@patient_bp.route('/daily-survey', methods=['POST'])
def add_daily_survey():
    data = request.get_json()
    cursor = mysql.connection.cursor()

    insert_query = """
        INSERT INTO PATIENT_DAILY_SURVEY (
            patient_id,
            date,
            water_intake,
            calories_consumed,
            heart_rate,
            exercise,
            mood,
            follow_plan
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    values = (
        data['patient_id'],
        data['date'],
        data['water_intake'],
        data['calories_consumed'],
        data['heart_rate'],
        data['exercise'],
        data.get('mood'),
        data.get('follow_plan', 0)
    )

    try:
        cursor.execute(insert_query, values)
        mysql.connection.commit()
        return jsonify({"message": "Daily survey submitted successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    
# get daily survey
@patient_bp.route('/daily-surveys/<int:patient_id>', methods=['GET'])
def get_daily_surveys(patient_id):
    cursor = mysql.connection.cursor()
    
    query = """
        SELECT * FROM PATIENT_DAILY_SURVEY
        WHERE patient_id = %s
        ORDER BY date DESC
    """
    
    try:
        cursor.execute(query, (patient_id,))
        surveys = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in surveys]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# add to weekly survey
@patient_bp.route('/weekly-survey', methods=['POST'])
def add_weekly_survey():
    data = request.get_json()
    cursor = mysql.connection.cursor()

    insert_query = """
        INSERT INTO PATIENT_WEEKLY (
            patient_id,
            week_start,
            blood_pressure,
            weight_change
        ) VALUES (%s, %s, %s, %s)
    """
    
    values = (
        data['patient_id'],
        data['week_start'],
        data['blood_pressure'],
        data['weight_change']
    )

    try:
        cursor.execute(insert_query, values)
        mysql.connection.commit()
        return jsonify({"message": "Weekly survey submitted successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

# get weekly survey
@patient_bp.route('/weekly-surveys/<int:patient_id>', methods=['GET'])
def get_weekly_surveys(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT * FROM PATIENT_WEEKLY
        WHERE patient_id = %s
        ORDER BY week_start DESC
    """

    try:
        cursor.execute(query, (patient_id,))
        surveys = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in surveys]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
# add an appt
@patient_bp.route('/appointments', methods=['POST'])
def add_appointment():
    data = request.get_json()
    cursor = mysql.connection.cursor()

    insert_query = """
        INSERT INTO PATIENT_APPOINTMENT (
            patient_id,
            doctor_id,
            appointment_datetime,
            reason_for_visit,
            current_medications,
            exercise_frequency,
            doctor_appointment_note,
            accepted,
            meal_prescribed
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data['patient_id'],
        data['doctor_id'],
        data['appointment_datetime'],
        data['reason_for_visit'],
        data.get('current_medications'),
        data.get('exercise_frequency'),
        data.get('doctor_appointment_note'),
        data.get('accepted', 0),
        data.get('meal_prescribed')
    )

    try:
        cursor.execute(insert_query, values)
        mysql.connection.commit()
        return jsonify({"message": "Appointment created successfully!"}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

# get appt by patient id
@patient_bp.route('/appointments/<int:patient_id>', methods=['GET'])
def get_appointments(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT * FROM PATIENT_APPOINTMENT
        WHERE patient_id = %s
        ORDER BY appointment_datetime DESC
    """

    try:
        cursor.execute(query, (patient_id,))
        appointments = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in appointments]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# get appt by patient id past
@patient_bp.route('/appointments/<int:patient_id>', methods=['GET'])
def get_all_appointments(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT * FROM PATIENT_APPOINTMENT
        WHERE patient_id = %s
        ORDER BY appointment_datetime DESC
    """

    try:
        cursor.execute(query, (patient_id,))
        appointments = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in appointments]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@patient_bp.route('/appointmentsupcoming/<int:patient_id>', methods=['GET'])
def get_upcoming_appointments(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT * FROM PATIENT_APPOINTMENT
        WHERE patient_id = %s AND appointment_datetime >= NOW()
        ORDER BY appointment_datetime ASC
    """

    try:
        cursor.execute(query, (patient_id,))
        appointments = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in appointments]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@patient_bp.route('/appointmentspast/<int:patient_id>', methods=['GET'])
def get_past_appointments(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT * FROM PATIENT_APPOINTMENT
        WHERE patient_id = %s AND appointment_datetime < NOW()
        ORDER BY appointment_datetime DESC
    """

    try:
        cursor.execute(query, (patient_id,))
        appointments = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in appointments]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@patient_bp.route('/patient/<int:patient_id>/email', methods=['GET'])
def get_patient_email(patient_id):
    cursor = mysql.connection.cursor()

    query = "SELECT patient_email FROM PATIENT WHERE patient_id = %s"

    try:
        cursor.execute(query, (patient_id,))
        result = cursor.fetchone()

        if result:
            return jsonify({"patient_email": result[0]}), 200
        else:
            return jsonify({"error": "Patient not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
# updates a patients doctor rating (1-5)
@patient_bp.route('/patient/rating', methods=['PUT'])
def update_doctor_rating():
    data = request.get_json()
    patient_id = data.get('patient_id')
    rating = data.get('rating')

    if not isinstance(patient_id, int) or not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return jsonify({"error": "patient_id must be an integer and rating must be between 1 and 5."}), 400

    cursor = mysql.connection.cursor()

    query = "UPDATE PATIENT SET doctor_rating = %s WHERE patient_id = %s"

    try:
        cursor.execute(query, (rating, patient_id))
        mysql.connection.commit()
        return jsonify({"message": "Doctor rating updated successfully."}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# get a patient's prescription
@patient_bp.route('/patient/<int:patient_id>/prescriptions', methods=['GET'])
def get_patient_prescriptions(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT prescription_id, medicine_id, quantity, picked_up, filled, created_at
        FROM PATIENT_PRESCRIPTION
        WHERE patient_id = %s
    """

    try:
        cursor.execute(query, (patient_id,))
        rows = cursor.fetchall()
        prescriptions = [
            {
                "prescription_id": row[0],
                "medicine_id": row[1],
                "quantity": row[2],
                "picked_up": bool(row[3]),
                "filled": bool(row[4]),
                "created_at": row[5].isoformat()
            } for row in rows
        ]
        return jsonify(prescriptions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# updates if a patient has picked up their prescription
@patient_bp.route('/prescription/pickup', methods=['PUT'])
def update_prescription_pickup():
    data = request.get_json()
    prescription_id = data.get('prescription_id')

    if not isinstance(prescription_id, int):
        return jsonify({"error": "prescription_id must be an integer."}), 400

    cursor = mysql.connection.cursor()

    query = "UPDATE PATIENT_PRESCRIPTION SET picked_up = 1 WHERE prescription_id = %s"

    try:
        cursor.execute(query, (prescription_id,))
        mysql.connection.commit()
        return jsonify({"message": "Prescription marked as picked up."}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# add a patient's bill
@patient_bp.route('/patient/bill', methods=['POST'])
def add_patient_bill():
    data = request.get_json()
    appt_id = data.get('appt_id')
    credit = data.get('credit')

    if not isinstance(appt_id, int):
        return jsonify({"error": "appt_id must be an integer."}), 400

    if not isinstance(credit, (int, float)) or credit < 0:
        return jsonify({"error": "credit must be a non-negative number."}), 400

    cursor = mysql.connection.cursor()

    try:
        # Step 1: Get doctor_bill from appointment -> doctor
        cursor.execute("""
            SELECT pa.patient_id, d.payment_fee
            FROM PATIENT_APPOINTMENT pa
            JOIN DOCTOR d ON pa.doctor_id = d.doctor_id
            WHERE pa.patient_appt_id = %s
        """, (appt_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Invalid appt_id or doctor not found."}), 404

        patient_id = result[0]
        doctor_bill = float(result[1])

        # Step 2: Get pharm_bill from prescriptions
        cursor.execute("""
            SELECT IFNULL(SUM(pp.quantity * m.medicine_price), 0)
            FROM PATIENT_PRESCRIPTION pp
            JOIN MEDICINE m ON pp.medicine_id = m.medicine_id
            WHERE pp.appt_id = %s
        """, (appt_id,))
        pharm_result = cursor.fetchone()
        pharm_bill = float(pharm_result[0]) if pharm_result else 0.0

        # Step 3: Insert the bill
        cursor.execute("""
            INSERT INTO PATIENT_BILL (appt_id, doctor_bill, pharm_bill, credit)
            VALUES (%s, %s, %s, %s)
        """, (appt_id, doctor_bill, pharm_bill, credit))
        mysql.connection.commit()

        # Step 4: Calculate total balance for the patient
        cursor.execute("""
            SELECT 
                IFNULL(SUM(pb.credit), 0) - IFNULL(SUM(pb.charge), 0)
            FROM 
                PATIENT_BILL pb
            JOIN 
                PATIENT_APPOINTMENT pa ON pb.appt_id = pa.patient_appt_id
            WHERE 
                pa.patient_id = %s
        """, (patient_id,))
        balance_result = cursor.fetchone()
        balance = float(balance_result[0]) if balance_result else 0.0

        return jsonify({
            "message": "Bill added successfully.",
            "appt_id": appt_id,
            "doctor_bill": doctor_bill,
            "pharm_bill": pharm_bill,
            "credit": credit,
            "balance": balance
        }), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# # get a patient's bill
# @patient_bp.route('/patient/<int:appt_id>/bill', methods=['GET'])
# def get_patient_bill(appt_id):
#     cursor = mysql.connection.cursor()

#     query = """
#         SELECT bill_id, appt_id, doctor_bill, pharm_bill, charge, credit, current_bill, created_at
#         FROM PATIENT_BILL
#         WHERE appt_id = %s
#     """

#     try:
#         cursor.execute(query, (appt_id,))
#         result = cursor.fetchone()

#         if not result:
#             return jsonify({"error": "Bill not found for this appointment."}), 404

#         bill = {
#             "bill_id": result[0],
#             "appt_id": result[1],
#             "doctor_bill": float(result[2]),
#             "pharm_bill": float(result[3]),
#             "charge": float(result[4]),
#             "credit": float(result[5]),
#             "current_bill": float(result[6]),
#             "created_at": result[7].isoformat()
#         }

#         return jsonify(bill), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 400
#     finally:
#         cursor.close()

@patient_bp.route('/patient/<int:patient_id>/bills', methods=['GET'])
def get_all_bills_for_patient(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            pb.bill_id, pb.appt_id, pb.doctor_bill, pb.pharm_bill, pb.charge, 
            pb.credit, pb.current_bill, pb.created_at
        FROM 
            PATIENT_BILL pb
        JOIN 
            PATIENT_APPOINTMENT pa ON pb.appt_id = pa.patient_appt_id
        WHERE 
            pa.patient_id = %s
        ORDER BY 
            pb.created_at DESC
    """

    try:
        cursor.execute(query, (patient_id,))
        results = cursor.fetchall()

        if not results:
            return jsonify({"message": "No bills found for this patient."}), 200

        bills = []
        for row in results:
            bills.append({
                "bill_id": row[0],
                "appt_id": row[1],
                "doctor_bill": float(row[2]),
                "pharm_bill": float(row[3]),
                "charge": float(row[4]),
                "credit": float(row[5]),
                "current_bill": float(row[6]),
                "created_at": row[7].isoformat()
            })

        return jsonify(bills), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()


@patient_bp.route('/remove_doctor/<int:patient_id>', methods=['PUT'])
def remove_patient_doctor(patient_id):
    cursor = mysql.connection.cursor()

    try:
        # First, check if patient exists
        cursor.execute("SELECT doctor_id FROM PATIENT WHERE patient_id = %s", (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            return jsonify({"error": "Patient not found."}), 404

        if patient[0] is None:
            return jsonify({"message": "Patient already has no assigned doctor."}), 200

        # Then, remove the doctor
        cursor.execute("""
            UPDATE PATIENT
            SET doctor_id = NULL
            WHERE patient_id = %s
        """, (patient_id,))
        mysql.connection.commit()

        return jsonify({"message": "Doctor successfully removed from patient."}), 200

    except Exception as e:
        print(f"Exception: {e}")
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cursor.close()
