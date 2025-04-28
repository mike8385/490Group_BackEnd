from flask import Blueprint, jsonify
from db import mysql

test_bp = Blueprint('test_bp', __name__)

@test_bp.route('/test-db')
def test_db_connection():
    """
    Test database connection
    ---
    responses:
      200:
        description: Successfully connected to the database
        schema:
          type: object
          properties:
            status:
              type: string
            result:
              type: array
              items:
                type: integer
      500:
        description: Failed to connect to the database
        schema:
          type: object
          properties:
            status:
              type: string
            message:
              type: string
    """
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        return jsonify({"status": "Connected: ", "result": result}), 200
    except Exception as e:
        return jsonify({"status": "Error: ", "message": str(e)}), 500