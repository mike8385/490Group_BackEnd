from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt

patient_bp = Blueprint('patient_bp', __name__)

#--------------------REGISTRATION END POINTS------------------------------ 
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
                'doctor_id', 'pharmacy_id', 'profile_pic',
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
"""

# ----------------- PATIENT x DOCTOR ENDPOINTS -------------------------
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

# ------------------ LOGIN ENDPOINTS ---------------------------------------

'''
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
'''

""" 

@patient_bp.route('/login-patient', methods=['POST'])
def login_patient():
    data = request.get_json()
    email = data.get('email')
    # Ignoring password for testing

    cursor = mysql.connection.cursor()

    query = "SELECT patient_id FROM PATIENT WHERE patient_email = %s"
    cursor.execute(query, (email,))
    patient = cursor.fetchone()

    if patient:
        return jsonify({"message": "Login successful", "patient_id": patient[0]}), 200
    else:
        return jsonify({"error": "Patient not found"}), 404

#---------------------------- DAILY + WEEKLY SURVEY END POINTS ------------------------------------

    cursor = mysql.connection.cursor()

    query = "SELECT patient_id FROM PATIENT WHERE patient_email = %s"
    cursor.execute(query, (email,))
    patient = cursor.fetchone()

    if patient:
        return jsonify({"message": "Login successful", "patient_id": patient[0]}), 200
    else:
        return jsonify({"error": "Patient not found"}), 404 
    
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
        ORDER BY date ASC
        ORDER BY date ASC
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

#----------------------------APPOINTMENT ENDPOINTS--------------------------------- 
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

# rate an appointment + update doctors avg rating- tested
@patient_bp.route('/appointment/rate', methods=['PATCH'])
def rate_appointment():
    data = request.get_json()
    appt_id = data.get('appt_id')
    rating = data.get('rating')

    if not isinstance(appt_id, int):
        return jsonify({"error": "appt_id must be an integer."}), 400

    if not isinstance(rating, (int, float)) or not (0 <= rating <= 5):
        return jsonify({"error": "rating must be a number between 0 and 5."}), 400

    cursor = mysql.connection.cursor()

    try:
        # Update the appointment's rating
        cursor.execute("""
            UPDATE PATIENT_APPOINTMENT
            SET appt_rating = %s
            WHERE patient_appt_id = %s
        """, (rating, appt_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Appointment not found."}), 404

        # Get the doctor_id for this appointment
        cursor.execute("""
            SELECT doctor_id
            FROM PATIENT_APPOINTMENT
            WHERE patient_appt_id = %s
        """, (appt_id,))
        doctor_result = cursor.fetchone()
        if not doctor_result:
            return jsonify({"error": "Doctor not found for this appointment."}), 404

        doctor_id = doctor_result[0]

        # Compute the average rating for the doctor
        cursor.execute("""
            SELECT AVG(appt_rating)
            FROM PATIENT_APPOINTMENT
            WHERE doctor_id = %s AND appt_rating IS NOT NULL
        """, (doctor_id,))
        avg_result = cursor.fetchone()
        avg_rating = float(avg_result[0]) if avg_result and avg_result[0] is not None else None

        # Update the doctor's rating if an average exists
        if avg_rating is not None:
            cursor.execute("""
                UPDATE DOCTOR
                SET doctor_rating = %s
                WHERE doctor_id = %s
            """, (avg_rating, doctor_id))

        mysql.connection.commit()

        return jsonify({
            "message": "Appointment rated successfully and doctor's rating updated.",
            "appt_id": appt_id,
            "rating": rating,
            "doctor_id": doctor_id,
            "updated_doctor_rating": round(avg_rating, 2) if avg_rating is not None else None
        }), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

@patient_bp.route('/single_appointment/<int:appointment_id>', methods=['GET'])
def get_single_appointment_by_id(appointment_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
    PA.*, 
    P.first_name AS patient_name, 
    D.first_name AS doctor_name,
    S.mobile_number,
    S.dob,
    S.gender AS survey_gender,
    S.height AS survey_height,
    S.weight AS survey_weight,
    S.activity,
    S.health_goals,
    S.dietary_restrictions,
    S.blood_type,
    S.patient_address,
    S.patient_zipcode,
    S.patient_city,
    S.patient_state,
    S.medical_conditions,
    S.family_history,
    S.past_procedures,
    S.favorite_meal
FROM PATIENT_APPOINTMENT PA
JOIN PATIENT P ON PA.patient_id = P.patient_id
JOIN DOCTOR D ON PA.doctor_id = D.doctor_id
LEFT JOIN PATIENT_INIT_SURVEY S ON P.patient_id = S.patient_id
WHERE PA.patient_appt_id = %s

    """

    try:
        cursor.execute(query, (appointment_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Appointment not found"}), 404
        
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

#-------------------------BILL ENDPOINTS ------------------------------------------------
# add a patient's bill - tested 
@patient_bp.route('/patient/bill', methods=['POST'])
def add_patient_bill():
    data = request.get_json()
    appt_id = data.get('appt_id')

    if not isinstance(appt_id, int):
        return jsonify({"error": "appt_id must be an integer."}), 400

    cursor = mysql.connection.cursor()

    try:
        # Get patient_id and doctor_bill
        cursor.execute("""
            SELECT pa.patient_id, d.payment_fee
            FROM PATIENT_APPOINTMENT pa
            JOIN DOCTOR d ON pa.doctor_id = d.doctor_id
            WHERE pa.patient_appt_id = %s
        """, (appt_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Invalid appt_id or doctor not found."}), 404

        patient_id, doctor_bill = result
        doctor_bill = float(doctor_bill)

        # Get pharm_bill
        cursor.execute("""
            SELECT IFNULL(SUM(pp.quantity * m.medicine_price), 0)
            FROM PATIENT_PRESCRIPTION pp
            JOIN MEDICINE m ON pp.medicine_id = m.medicine_id
            WHERE pp.appt_id = %s
        """, (appt_id,))
        pharm_result = cursor.fetchone()
        pharm_bill = float(pharm_result[0]) if pharm_result else 0.0

        # Determine appointment count for article naming
        cursor.execute("""
            SELECT COUNT(*)
            FROM PATIENT_BILL pb
            JOIN PATIENT_APPOINTMENT pa ON pb.appt_id = pa.patient_appt_id
            WHERE pa.patient_id = %s
        """, (patient_id,))
        count_result = cursor.fetchone()
        appt_number = (count_result[0] or 0) + 1
        article_name = f"Appt {appt_number}"

        # Insert the new bill (charge only)
        current_bill = doctor_bill + pharm_bill
        cursor.execute("""
            INSERT INTO PATIENT_BILL (appt_id, doctor_bill, pharm_bill, current_bill, article)
            VALUES (%s, %s, %s, %s, %s)
        """, (appt_id, doctor_bill, pharm_bill, current_bill, article_name))

        # Calculate updated balance
        cursor.execute("""
            SELECT
                (SELECT IFNULL(SUM(amount), 0) FROM PATIENT_CREDIT WHERE patient_id = %s)
                -
                (SELECT IFNULL(SUM(charge), 0)
                 FROM PATIENT_BILL pb
                 JOIN PATIENT_APPOINTMENT pa ON pb.appt_id = pa.patient_appt_id
                 WHERE pa.patient_id = %s)
        """, (patient_id, patient_id))
        balance_result = cursor.fetchone()
        balance = float(balance_result[0]) if balance_result else 0.0

        # Update the patient's acct_balance
        cursor.execute("""
            UPDATE PATIENT
            SET acct_balance = %s
            WHERE patient_id = %s
        """, (balance, patient_id))

        mysql.connection.commit()

        return jsonify({
            "message": "Bill recorded successfully.",
            "appt_id": appt_id,
            "doctor_bill": doctor_bill,
            "pharm_bill": pharm_bill,
            "current_bill": current_bill,
            "article": article_name,
            "balance": balance
        }), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# get bills for patient - needs to be updated
@patient_bp.route('/patient/<int:patient_id>/bills', methods=['GET'])
def get_all_bills_for_patient(patient_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            pb.bill_id, pb.appt_id, pb.doctor_bill, pb.pharm_bill, pb.charge, 
            pb.credit, pb.current_bill, p.article, pb.created_at
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

# make a payment - take in credit - tested 
@patient_bp.route('/patient/<int:patient_id>/payment', methods=['POST'])
def make_general_payment(patient_id):
    data = request.get_json()
    credit = data.get('credit')

    if not isinstance(credit, (int, float)) or credit <= 0:
        return jsonify({"error": "credit must be a positive number."}), 400

    cursor = mysql.connection.cursor()

    try:
        # Check if patient exists
        cursor.execute("""
            SELECT 1 FROM PATIENT WHERE patient_id = %s
        """, (patient_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Invalid patient_id."}), 404

        # Compute current balance
        cursor.execute("""
            SELECT
                (SELECT IFNULL(SUM(amount), 0) FROM PATIENT_CREDIT WHERE patient_id = %s)
                -
                (SELECT IFNULL(SUM(charge), 0)
                 FROM PATIENT_BILL pb
                 JOIN PATIENT_APPOINTMENT pa ON pb.appt_id = pa.patient_appt_id
                 WHERE pa.patient_id = %s)
        """, (patient_id, patient_id))
        balance_result = cursor.fetchone()
        current_balance = float(balance_result[0]) if balance_result else 0.0

        # Prevent overpayment
        if credit + current_balance > 0:
            return jsonify({
                "error": "Payment exceeds outstanding balance.",
                "current_balance": current_balance,
                "requested_payment": credit,
                "maximum_allowed": -current_balance
            }), 400

        # Insert credit payment
        cursor.execute("""
            INSERT INTO PATIENT_CREDIT (patient_id, amount)
            VALUES (%s, %s)
        """, (patient_id, credit))

        # Recalculate balance after payment
        cursor.execute("""
            SELECT
                (SELECT IFNULL(SUM(amount), 0) FROM PATIENT_CREDIT WHERE patient_id = %s)
                -
                (SELECT IFNULL(SUM(charge), 0)
                 FROM PATIENT_BILL pb
                 JOIN PATIENT_APPOINTMENT pa ON pb.appt_id = pa.patient_appt_id
                 WHERE pa.patient_id = %s)
        """, (patient_id, patient_id))
        updated_balance_result = cursor.fetchone()
        updated_balance = float(updated_balance_result[0]) if updated_balance_result else 0.0

        # Update the patient's acct_balance
        cursor.execute("""
            UPDATE PATIENT
            SET acct_balance = %s
            WHERE patient_id = %s
        """, (updated_balance, patient_id))

        mysql.connection.commit()

        return jsonify({
            "message": "General payment recorded successfully.",
            "patient_id": patient_id,
            "credit": credit,
            "article": "Credit Card Payment",
            "new_balance": updated_balance
        }), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# -------------------- GENERAL PATIENT ENDPOINTS----------------------------------
# get a patient's prescription based on appt id
@patient_bp.route('/patient/<int:appt_id>/prescriptions', methods=['GET'])
def get_patient_prescriptions(appt_id):
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            pp.prescription_id, 
            pp.medicine_id, 
            m.medicine_name,
            m.medicine_price,
            pp.quantity, 
            pp.picked_up, 
            pp.filled, 
            pp.created_at
        FROM PATIENT_PRESCRIPTION pp
        JOIN MEDICINE m ON pp.medicine_id = m.medicine_id
        WHERE pp.appt_id = %s
    """

    try:
        cursor.execute(query, (appt_id,))
        rows = cursor.fetchall()
        prescriptions = [
            {
                "prescription_id": row[0],
                "medicine_id": row[1],
                "medicine_name": row[2],
                "medicine_price": float(row[3]),
                "quantity": row[4],
                "picked_up": bool(row[5]),
                "filled": bool(row[6]),
                "created_at": row[7].isoformat()
            } for row in rows
        ]
        return jsonify(prescriptions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()


# updates if a patient has picked up their prescription
@patient_bp.route('/prescription/pickup', methods=['PATCH'])
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

# edit patient info
@patient_bp.route('/edit-patient', methods=['PUT'])
def edit_patient():
    data = request.get_json()
    
    patient_id = data.get('patient_id')
    patient_email = data.get('email')
    patient_password = data.get('password')

    # Fields from PATIENT_INIT_SURVEY
    phone = data.get('phone')
    dob = data.get('dob')  
    gender = data.get('gender')
    height = data.get('height')
    weight = data.get('weight')
    blood_type = data.get('blood_type')
    allergies = data.get('allergies') 
    activity = data.get('activity') 
    medical_conditions = data.get('health_conditions')
    family_history = data.get('family_history')
    past_procedures = data.get('past_procedures')
    address = data.get('address')
    zipcode = data.get('zipcode')
    city = data.get('city')
    state = data.get('state')  

    cursor = mysql.connection.cursor()
    try:
        # Update PATIENT table
        cursor.execute("""
            UPDATE PATIENT
            SET patient_email = %s, patient_password = %s
            WHERE patient_id = %s
        """, (patient_email, patient_password, patient_id))

        # Update PATIENT_INIT_SURVEY table
        cursor.execute("""
            UPDATE PATIENT_INIT_SURVEY
            SET mobile_number = %s, dob = %s, gender = %s, height = %s, weight = %s,
                dietary_restrictions = %s, activity = %s, blood_type = %s, 
                patient_address = %s, patient_zipcode = %s, patient_city = %s, patient_state = %s,
                medical_conditions = %s, family_history = %s, past_procedures = %s
            WHERE patient_id = %s
        """, (
            phone, dob, gender, height, weight,
            allergies, activity, blood_type,
            address, zipcode, city, state,
            medical_conditions, family_history, past_procedures,
            patient_id
        ))

        mysql.connection.commit()
        return jsonify({'message': 'Patient information updated successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
