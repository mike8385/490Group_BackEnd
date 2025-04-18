from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt

pharmacy_bp = Blueprint('pharmacy_bp', __name__)

@pharmacy_bp.route('/register-pharmacy', methods=['POST'])
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

@pharmacy_bp.route('/pharmacy/<int:pharmacy_id>', methods=['GET'])
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
    
 # get medicine (already preloaded in database)   
@pharmacy_bp.route('/medicine/<int:medicine_id>', methods=['GET'])
def get_medicine(medicine_id):
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
    
    #get all pharmacies
@pharmacy_bp.route('/pharmacies', methods=['GET'])
def get_pharmacies():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT pharmacy_name, address, zipcode, city FROM PHARMACY")
        rows = cursor.fetchall()

        pharmacies = [
            {
                "name": row[0],
                "address": row[1],
                "zipcode": row[2],
                "city": row[3]
            } for row in rows
        ]

        return jsonify(pharmacies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
