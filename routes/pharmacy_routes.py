from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt

pharmacy_bp = Blueprint('pharmacy_bp', __name__)

@pharmacy_bp.route('/register-pharmacy', methods=['POST'])
def register_pharmacy():
    """
    Register a new pharmacy

    ---
    tags:
      - Pharmacy
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - email
              - address
              - zipcode
              - city
              - state
              - pharmacy_name
              - store_hours
              - password
            properties:
              email:
                type: string
                format: email
              address:
                type: string
              zipcode:
                type: string
              city:
                type: string
              state:
                type: string
              pharmacy_name:
                type: string
              store_hours:
                type: string
              password:
                type: string
                format: password
          example:
            email: "pharmacy@example.com"
            address: "123 Health St"
            zipcode: "10001"
            city: "New York"
            state: "NY"
            pharmacy_name: "Wellness RX"
            store_hours: "Mon-Fri: 9 AM - 9 PM"
            password: "securePass123"
    responses:
      201:
        description: Pharmacy registered successfully
      400:
        description: Registration failed
    """
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

@pharmacy_bp.route('/pharmacy/<int:pharmacy_id>', methods=['GET'])
def get_pharmacy(pharmacy_id):
    """
    Get pharmacy information by ID

    ---
    tags:
      - Pharmacy
    parameters:
      - name: pharmacy_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: Pharmacy details retrieved
        content:
          application/json:
            example:
              pharmacy_id: 1
              pharmacy_name: "Wellness RX"
              email: "pharmacy@example.com"
              address: "123 Health St"
              zipcode: "10001"
              city: "New York"
              state: "NY"
              store_hours: "Mon-Fri: 9 AM - 9 PM"
      404:
        description: Pharmacy not found
      400:
        description: Retrieval failed
    """
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

'''
#pharmacy login
@pharmacy_bp.route('/login-pharmacy', methods=['POST'])
def login_pharmacy():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    cursor = mysql.connection.cursor()

    # Query to fetch pharmacy details based on email
    query = "SELECT pharmacy_id, email, password FROM pharmacy WHERE email = %s"
    cursor.execute(query, (email,))
    pharmacy = cursor.fetchone()

    if pharmacy:
        stored_password = pharmacy[2]  # Get the stored hashed password (3rd field in query result)
        
        # Check if entered password matches the stored password
        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            return jsonify({"message": "Login successful", "pharmacy_id": pharmacy[0]}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    else:
        return jsonify({"error": "Pharmacy not found"}), 404
    
'''

#pharmacy login
@pharmacy_bp.route('/login-pharmacy', methods=['POST'])
def login_pharmacy():
    """
    Authenticate a pharmacy by email and password

    ---
    tags:
      - Pharmacy
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
                format: email
              password:
                type: string
                format: password
          example:
            email: "pharmacy@example.com"
            password: "securePass123"
    responses:
      200:
        description: Login successful
        content:
          application/json:
            example:
              message: Login successful
              pharmacy_id: 1
      404:
        description: Pharmacy not found
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    cursor = mysql.connection.cursor()

    # Query to fetch pharmacy details based on email
    query = "SELECT pharmacy_id, email, password FROM PHARMACY WHERE email = %s"
    cursor.execute(query, (email,))
    pharmacy = cursor.fetchone()

    if pharmacy:
        return jsonify({"message": "Login successful", "pharmacy_id": pharmacy[0]}), 200
    else:
        return jsonify({"error": "Pharmacy not found"}), 404
    
 # get medicine (already preloaded in database)   

@pharmacy_bp.route('/medicine/<int:medicine_id>', methods=['GET'])
def get_medicine(medicine_id):
    """
    Get medicine information by ID

    ---
    tags:
      - Medicine
    parameters:
      - name: medicine_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: Medicine details retrieved
        content:
          application/json:
            example:
              medicine_id: 2
              medicine_name: "Ibuprofen"
              medicine_price: 5.99
      404:
        description: Medicine not found
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT medicine_id, medicine_name, medicine_price
        FROM MEDICINE
        WHERE medicine_id = %s
    """
    cursor.execute(query, (medicine_id,))
    medicine = cursor.fetchone()

    if medicine:
        return jsonify({
            "medicine_id": medicine[0],
            "medicine_name": medicine[1],
            "medicine_price": float(medicine[2])
        }), 200
    else:
        return jsonify({"error": "Medicine not found"}), 404
    
#get all of stock (by pharmacy id)
@pharmacy_bp.route('/stock/<int:pharmacy_id>', methods=['GET'])
def get_stock(pharmacy_id):
    """
    Retrieve all medicine stock for a specific pharmacy

    ---
    tags:
      - Inventory
    parameters:
      - name: pharmacy_id
        in: path
        type: integer
        required: true
        description: ID of the pharmacy
    responses:
      200:
        description: Stock list retrieved
      404:
        description: No stock found for this pharmacy
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT 
            ms.stock_id, 
            ms.medicine_id, 
            m.medicine_name,
            ms.pharmacy_id, 
            ms.stock_count
        FROM MEDICINE_STOCK ms
        JOIN MEDICINE m ON ms.medicine_id = m.medicine_id
        WHERE ms.pharmacy_id = %s
    """
    cursor.execute(query, (pharmacy_id,))
    stocks = cursor.fetchall()

    if stocks:
        result = []
        for stock in stocks:
            result.append({
                "stock_id": stock[0],
                "medicine_id": stock[1],
                "medicine_name": stock[2],
                "pharmacy_id": stock[3],
                "stock_count": stock[4]
            })
        return jsonify(result), 200
    else:
        return jsonify({"error": "No medicine stock found for this pharmacy"}), 404

# update stock - based on pharmacy, medicine id, and quantity to add
@pharmacy_bp.route('/stock/update', methods=['PUT'])
def update_stock():
    """
    Update stock count for a specific medicine in a pharmacy

    ---
    tags:
      - Inventory
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - pharmacy_id
              - medicine_id
              - quantity_to_add
            properties:
              pharmacy_id:
                type: integer
              medicine_id:
                type: integer
              quantity_to_add:
                type: integer
          example:
            pharmacy_id: 1
            medicine_id: 3
            quantity_to_add: 50
    responses:
      200:
        description: Stock updated successfully
      400:
        description: Invalid input
      404:
        description: Stock record not found
      500:
        description: Database update failed
    """
    data = request.get_json()
    pharmacy_id = data.get('pharmacy_id')
    medicine_id = data.get('medicine_id')
    quantity_to_add = data.get('quantity_to_add')

    # Basic validation
    if not all([pharmacy_id, medicine_id, isinstance(quantity_to_add, int)]):
        return jsonify({"error": "Invalid input. pharmacy_id, medicine_id, and quantity_to_add are required."}), 400

    cursor = mysql.connection.cursor()

    # Check if the stock entry exists
    check_query = """
        SELECT stock_count FROM MEDICINE_STOCK
        WHERE pharmacy_id = %s AND medicine_id = %s
    """
    cursor.execute(check_query, (pharmacy_id, medicine_id))
    stock = cursor.fetchone()

    if not stock:
        return jsonify({"error": "Stock record not found for this pharmacy and medicine."}), 404

    new_stock_count = stock[0] + quantity_to_add

    # Update the stock
    update_query = """
        UPDATE MEDICINE_STOCK
        SET stock_count = %s
        WHERE pharmacy_id = %s AND medicine_id = %s
    """
    try:
        cursor.execute(update_query, (new_stock_count, pharmacy_id, medicine_id))
        mysql.connection.commit()
        return jsonify({
            "message": "Stock updated successfully.",
            "new_stock_count": new_stock_count
        }), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500
    
# get all pharmacies
@pharmacy_bp.route('/pharmacies', methods=['GET'])
def get_pharmacies():
    """
    Retrieve all registered pharmacies

    ---
    tags:
      - Pharmacy
    responses:
      200:
        description: List of pharmacies
        content:
          application/json:
            example:
              - id: 1
                name: "Wellness RX"
                address: "123 Health St"
                zipcode: "10001"
                city: "New York"
      500:
        description: Retrieval failed
    """
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT pharmacy_id, pharmacy_name, address, zipcode, city FROM PHARMACY")
        rows = cursor.fetchall()

        pharmacies = [
            {
                "id": row[0],
                "name": row[1],
                "address": row[2],
                "zipcode": row[3],
                "city": row[4]
            } for row in rows
        ]

        return jsonify(pharmacies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# update a patient's prescription to filled if filled is clicked
@pharmacy_bp.route('/prescription/fill', methods=['PUT'])
def fill_prescription():
    """
    Fill a prescription and deduct from pharmacy stock

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
              - prescription_id
            properties:
              prescription_id:
                type: integer
          example:
            prescription_id: 15
    responses:
      200:
        description: Prescription filled and stock updated
      400:
        description: Insufficient stock or validation failed
      404:
        description: Prescription or stock not found
    """
    data = request.get_json()
    prescription_id = data.get('prescription_id')

    if not isinstance(prescription_id, int):
        return jsonify({"error": "prescription_id must be an integer."}), 400

    cursor = mysql.connection.cursor()

    try:
        cursor.execute("""
            SELECT pp.medicine_id, pp.quantity, p.pharmacy_id
            FROM PATIENT_PRESCRIPTION pp
            JOIN PATIENT_APPOINTMENT pa ON pp.appt_id = pa.patient_appt_id
            JOIN PATIENT p ON pa.patient_id = p.patient_id
            WHERE pp.prescription_id = %s
        """, (prescription_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Prescription not found."}), 404

        medicine_id, quantity, pharmacy_id = result

        cursor.execute("""
            SELECT stock_count
            FROM MEDICINE_STOCK
            WHERE medicine_id = %s AND pharmacy_id = %s
        """, (medicine_id, pharmacy_id))
        stock_result = cursor.fetchone()

        if not stock_result:
            return jsonify({"error": "Medicine not found in pharmacy stock."}), 404

        current_stock = stock_result[0]

        if current_stock < quantity:
            return jsonify({
                "error": "Not enough stock to fill this prescription.",
                "available_stock": current_stock,
                "required_quantity": quantity
            }), 400

        cursor.execute("""
            UPDATE PATIENT_PRESCRIPTION
            SET filled = 1
            WHERE prescription_id = %s
        """, (prescription_id,))

        cursor.execute("""
            UPDATE MEDICINE_STOCK
            SET stock_count = stock_count - %s
            WHERE medicine_id = %s AND pharmacy_id = %s
        """, (quantity, medicine_id, pharmacy_id))

        mysql.connection.commit()
        return jsonify({"message": "Prescription filled and stock updated."}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cursor.close()

@pharmacy_bp.route('/all_meds', methods=['GET'])
def get_all_medicines():
    """
    Get list of all medicines available in the system

    ---
    tags:
      - Medicine
    responses:
      200:
        description: List of medicines
        content:
          application/json:
            example:
              - medicine_id: 1
                medicine_name: "Ibuprofen"
                medicine_price: 5.99
    """
    cursor = mysql.connection.cursor()

    query = """
        SELECT *
        FROM MEDICINE
    """
    cursor.execute(query)
    medicines = cursor.fetchall()

    result = []
    for med in medicines:
        result.append({
            "medicine_id": med[0],
            "medicine_name": med[1],
            "medicine_price": float(med[2]),
            "description" : med[3],
            "side_effects" : med[4],
            "benefits" : med[5]
        })

    return jsonify(result), 200

@pharmacy_bp.route('/pickup/<int:pharmacy_id>', methods=['GET'])
def get_pickups_for_pharmacy(pharmacy_id):
    """
    Get list of filled prescriptions not yet picked up for a pharmacy

    ---
    tags:
      - Prescription
    parameters:
      - name: pharmacy_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: List of prescriptions ready for pickup
        content:
          application/json:
            example:
              - patient_name: "John Doe"
                medicine_name: "Lisinopril"
                quantity: 30
    """
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
            m.medicine_name,
            pp.quantity
        FROM PATIENT_PRESCRIPTION pp
        JOIN PATIENT_APPOINTMENT pa ON pp.appt_id = pa.patient_appt_id
        JOIN PATIENT p ON pa.patient_id = p.patient_id
        JOIN MEDICINE m ON pp.medicine_id = m.medicine_id
        WHERE p.pharmacy_id = %s
            AND pp.filled = 1
            AND pp.picked_up = 0
    """
    cursor.execute(query, (pharmacy_id,))
    results = cursor.fetchall()

    pickup_list = []
    for row in results:
        pickup_list.append({
            "patient_name": row[0],
            "medicine_name": row[1],
            "quantity": row[2]
        })

    return jsonify(pickup_list), 200

@pharmacy_bp.route('/all_prescriptions', methods=['GET'])
def get_all_prescriptions():
    """
    Retrieve all prescriptions from the system

    ---
    tags:
      - Prescription
    responses:
      200:
        description: Full prescription list
    """
    cursor = mysql.connection.cursor()

    query = """
        SELECT *
        FROM PATIENT_PRESCRIPTION
    """
    cursor.execute(query)
    prescriptions = cursor.fetchall()

    # Define the result as a list of dictionaries
    result = []
    for prescription in prescriptions:
        prescription_dict = {
            "prescription_id": prescription[0],
            "appt_id": prescription[1],
            "medicine_id": prescription[2],
            "quantity": prescription[3],
            "picked_up": prescription[4],
            "filled": prescription[5],
            "created_at": prescription[6],
            "updated_at": prescription[7]
        }
        result.append(prescription_dict)

    return jsonify(result), 200

@pharmacy_bp.route('/unfilled_prescriptions/<int:pharmacy_id>', methods=['GET'])
def get_unfilled_prescriptions(pharmacy_id):
    """
    Retrieve all unfilled prescriptions for a specific pharmacy

    ---
    tags:
      - Prescription
    parameters:
      - name: pharmacy_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: List of unfilled prescriptions
        content:
          application/json:
            example:
              - prescription_id: 101
                doctor_name: "Dr. Jane Smith"
                patient_name: "John Doe"
                medication: "Atorvastatin"
                quantity: 30
                filled: 0
    """
    cursor = mysql.connection.cursor()

    query = """
        SELECT 
            pp.prescription_id, 
            CONCAT(d.first_name, ' ', d.last_name) AS doctor_name, 
            CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
            m.medicine_name,
            pp.quantity
        FROM PATIENT_PRESCRIPTION pp
        JOIN PATIENT_APPOINTMENT pa ON pp.appt_id = pa.patient_appt_id
        JOIN PATIENT p ON pa.patient_id = p.patient_id
        JOIN MEDICINE m ON pp.medicine_id = m.medicine_id
        JOIN DOCTOR d ON pa.doctor_id = d.doctor_id
        WHERE p.pharmacy_id = %s
            AND pp.filled = 0  -- Only unfilled prescriptions
    """
    cursor.execute(query, (pharmacy_id,))
    results = cursor.fetchall()

    unfilled_prescriptions = []
    for row in results:
        unfilled_prescriptions.append({
            "prescription_id": row[0],
            "doctor_name": row[1],
            "patient_name": row[2],
            "medication": row[3],
            "quantity": row[4],
            "filled": 0  # Marking unfilled prescriptions
        })

    return jsonify(unfilled_prescriptions), 200
