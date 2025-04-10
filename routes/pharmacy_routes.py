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