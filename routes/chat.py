from flask import Blueprint, request, jsonify
from datetime import datetime
from db import mysql
import bcrypt

chat_bp = Blueprint('chat_bp', __name__)

   
@chat_bp.route('/chat/send', methods=['POST'])
def send_chat_message():
    """
    Send a chat message between patient and doctor
    ---
    tags:
      - Chat
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - appointment_id
              - sender
              - text
            properties:
              appointment_id:
                type: integer
              sender:
                type: string
                enum: [patient, doctor]
              text:
                type: string
    responses:
      200:
        description: Message saved successfully
      400:
        description: Invalid input
      404:
        description: Appointment or user not found
      500:
        description: Internal server error
    """
    data = request.get_json()
    appointment_id = data.get('appointment_id')  # maps to appt_id
    sender_type = data.get('sender')            # "patient" or "doctor"
    message = data.get('text')
    sent_at = datetime.now()

    cursor = mysql.connection.cursor()
    try:
        # Step 1: Get patient_id and doctor_id from patient_appointment
        cursor.execute("""
            SELECT patient_id, doctor_id FROM PATIENT_APPOINTMENT
            WHERE patient_appt_id = %s
        """, (appointment_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Appointment not found'}), 404

        patient_id, doctor_id = row

        # Step 2: Get corresponding user_ids from user table
        if sender_type == "patient":
            cursor.execute("SELECT user_id FROM USER WHERE patient_id = %s", (patient_id,))
            sender_row = cursor.fetchone()
            cursor.execute("SELECT user_id FROM USER WHERE doctor_id = %s", (doctor_id,))
            receiver_row = cursor.fetchone()
        else:
            cursor.execute("SELECT user_id FROM USER WHERE doctor_id = %s", (doctor_id,))
            sender_row = cursor.fetchone()
            cursor.execute("SELECT user_id FROM USER WHERE patient_id = %s", (patient_id,))
            receiver_row = cursor.fetchone()

        if not sender_row or not receiver_row:
            return jsonify({'error': 'User not found'}), 404

        sender_id = sender_row[0]
        receiver_id = receiver_row[0]

        # Step 3: Insert into chat
        cursor.execute("""
            INSERT INTO CHAT (appt_id, sender_id, receiver_id, message, sent_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (appointment_id, sender_id, receiver_id, message, sent_at))

        mysql.connection.commit()
        return jsonify({'message': 'Message saved successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@chat_bp.route('/chat/<int:appointment_id>', methods=['GET'])
def get_chat_messages(appointment_id):
    """
    Retrieve chat messages for a specific appointment
    ---
    tags:
      - Chat
    parameters:
      - name: appointment_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of chat messages
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  sender_id:
                    type: integer
                  receiver_id:
                    type: integer
                  message:
                    type: string
                  sent_at:
                    type: string
                    format: date-time
      404:
        description: No messages found
      500:
        description: Internal server error
    """
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT sender_id, receiver_id, message, sent_at
            FROM CHAT
            WHERE appt_id = %s
            ORDER BY sent_at ASC
        """, (appointment_id,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]

        # Optional: Format timestamp
        for msg in results:
            msg['sent_at'] = msg['sent_at'].isoformat()

        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@chat_bp.route('/user', methods=['GET'])
def get_user_by_role_id():
    """
    Get user info by patient_id or doctor_id
    ---
    tags:
      - Chat
    parameters:
      - name: patient_id
        in: query
        required: false
        schema:
          type: string
      - name: doctor_id
        in: query
        required: false
        schema:
          type: string
    responses:
      200:
        description: User object
        content:
          application/json:
            schema:
              type: object
      400:
        description: Missing required parameter
      404:
        description: User not found
      500:
        description: Internal server error
    """
    patient_id = request.args.get('patient_id')
    doctor_id = request.args.get('doctor_id')

    patient_id = patient_id.strip() if patient_id else None
    doctor_id = doctor_id.strip() if doctor_id else None

    cursor = mysql.connection.cursor()
    try:
        if patient_id:
            cursor.execute("SELECT * FROM USER WHERE patient_id = %s", (patient_id,))
        elif doctor_id:
            cursor.execute("SELECT * FROM USER WHERE doctor_id = %s", (doctor_id,))
        else:
            return jsonify({'error': 'You must provide either patient_id or doctor_id'}), 400

        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        columns = [desc[0] for desc in cursor.description]
        user_dict = dict(zip(columns, user))
        return jsonify(user_dict), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()