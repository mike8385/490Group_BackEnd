from flask import Blueprint, request, jsonify
from flask_socketio import SocketIO, emit
import eventlet
from db import mysql
import bcrypt, base64

comm_bp = Blueprint('chat_bp', __name__)

@socketio.on('send_message')
def handle_message(data):
    sender = data['sender']
    receiver = data['receiver']
    message = data['message']
    appointment_id = data['appointmentId']

    # Save to DB if desired
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO CHAT (sender_user_id, receiver_user_id, message, appointment_id) VALUES (%s, %s, %s, %s)",
        (sender, receiver, message, appointment_id)
    )
    mysql.connection.commit()
    cursor.close()

    # Emit to other user
    emit('receive_message', data, broadcast=True)