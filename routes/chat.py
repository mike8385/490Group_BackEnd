from flask import Blueprint, request, jsonify
from datetime import datetime
from db import mysql
import bcrypt

chat_bp = Blueprint('chat_bp', __name__)

   

@chat_bp.route('/chat/send', methods=['POST'])
def send_chat_message():
    data = request.get_json()
    appointment_id = data.get('appointment_id')
    sender_type = data.get('sender_type')  # 'patient' or 'doctor'
    text = data.get('text')

    if not all([appointment_id, sender_type, text]):
        return jsonify({'error': 'Missing required fields'}), 400

    cursor = mysql.connection.cursor()
    try:
        # Get patient_id and doctor_id from the appointment
        cursor.execute("""
            SELECT patient_id, doctor_id
            FROM patient_appointment
            WHERE patient_appt_id = %s
        """, (appointment_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Invalid appointment_id'}), 404

        patient_id, doctor_id = result

        # Determine sender and receiver IDs
        if sender_type == "patient":
            sender_id = patient_id
            receiver_id = doctor_id
        elif sender_type == "doctor":
            sender_id = doctor_id
            receiver_id = patient_id
        else:
            return jsonify({'error': 'Invalid sender_type'}), 400

        # Find or create chat_id for this patient-doctor pair
        cursor.execute("""
            SELECT chat_id FROM chat
            WHERE patient_id = %s AND doctor_id = %s
        """, (patient_id, doctor_id))
        chat = cursor.fetchone()

        if chat:
            chat_id = chat[0]
        else:
            # Create new chat row
            cursor.execute("""
                INSERT INTO chat (patient_id, doctor_id, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
            """, (patient_id, doctor_id))
            chat_id = cursor.lastrowid

        # Insert message
        cursor.execute("""
            INSERT INTO chat_message (chat_id, sender_id, receiver_id, message, sent_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (chat_id, sender_id, receiver_id, text))

        mysql.connection.commit()
        return jsonify({'message': 'Message saved successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@chat_bp.route('/chat/<int:appointment_id>', methods=['GET'])
def get_chat_messages(appointment_id):
    cursor = mysql.connection.cursor()
    try:
        # Step 1: Get patient_id and doctor_id for the appointment
        cursor.execute("""
            SELECT patient_id, doctor_id
            FROM patient_appointment
            WHERE patient_appt_id = %s
        """, (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            return jsonify({'error': 'Invalid appointment_id'}), 404

        patient_id, doctor_id = appointment

        # Step 2: Get chat_id from chat table
        cursor.execute("""
            SELECT chat_id
            FROM chat
            WHERE patient_id = %s AND doctor_id = %s
        """, (patient_id, doctor_id))
        chat = cursor.fetchone()

        if not chat:
            return jsonify([]), 200  # No chat yet, return empty list

        chat_id = chat[0]

        # Step 3: Fetch messages for this chat
        cursor.execute("""
            SELECT sender_id, message AS text, sent_at AS timestamp
            FROM chat_message
            WHERE chat_id = %s
            ORDER BY sent_at ASC
        """, (chat_id,))
        messages = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in messages]

        return jsonify(results), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

